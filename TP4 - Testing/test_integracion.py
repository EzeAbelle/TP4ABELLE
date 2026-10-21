from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    assert pedidos.obtener_pedido(con, 999) is None


@pytest.fixture
def otra_con(ruta, con):
    conexion = pedidos.conectar(ruta)
    yield conexion
    conexion.close()


def guardar(con, carrito=None, email="ana@mail.com", zona="CABA", cupon=None):
    carrito = carrito if carrito is not None else [item()]
    return pedidos.guardar_pedido(con, email, carrito, zona, cupon, HOY_VIGENTE)


CASOS_DE_ERROR = [
    ([item()], "CABA", "NOEXISTE", HOY_VIGENTE, "CUPON_INVALIDO"),
    ([item(talle="XXXL")], "CABA", None, HOY_VIGENTE, "TALLE_INVALIDO"),
    ([item(cantidad=11)], "CABA", None, HOY_VIGENTE, "CANTIDAD_INVALIDA"),
    ([], "CABA", None, HOY_VIGENTE, "CARRITO_VACIO"),
    ([item()], "MARTE", None, HOY_VIGENTE, "ZONA_INVALIDA"),
    ([item(), item(producto="gorra")], "CABA", None, HOY_VIGENTE, "PRODUCTO_INEXISTENTE"),
    ([item()], "CABA", "EGRESADOS2026", date(2026, 12, 1), "CUPON_VENCIDO"),
    ([item(producto="remera")], "CABA", "BIENVENIDA", HOY_VIGENTE, "CUPON_MINIMO_NO_ALCANZADO"),
]


@pytest.mark.parametrize("carrito, zona, cupon, fecha, codigo", CASOS_DE_ERROR)
def test_un_error_de_checkout_se_propaga_con_su_codigo(con, carrito, zona, cupon, fecha, codigo):
    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, zona, cupon, fecha)

    assert error.value.code == codigo


@pytest.mark.parametrize("carrito, zona, cupon, fecha, codigo", CASOS_DE_ERROR)
def test_un_error_de_checkout_no_deja_pedido_ni_items_guardados(
    ruta, con, carrito, zona, cupon, fecha, codigo
):
    with pytest.raises(CheckoutError):
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, zona, cupon, fecha)

    assert (contar(ruta, "pedidos"), contar(ruta, "items")) == (0, 0)


def test_un_error_de_checkout_no_borra_los_pedidos_ya_guardados(ruta, con):
    guardar(con)

    with pytest.raises(CheckoutError):
        pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA", "NOEXISTE", HOY_VIGENTE)

    assert (contar(ruta, "pedidos"), contar(ruta, "items")) == (1, 1)


def test_el_pedido_guardado_es_visible_desde_otra_conexion_con_todos_sus_items(con, otra_con):
    carrito = [item(producto="buzo", cantidad=2), item(producto="remera", cantidad=1)]

    pedido_id = guardar(con, carrito)
    pedido = pedidos.obtener_pedido(otra_con, pedido_id)

    assert [(i["producto"], i["cantidad"]) for i in pedido["items"]] == [("buzo", 2), ("remera", 1)]


def test_el_pedido_guardado_es_visible_desde_otra_conexion_con_sus_importes(con, otra_con):
    pedido_id = guardar(con, [item(producto="remera")], cupon="EGRESADOS2026")

    pedido = pedidos.obtener_pedido(otra_con, pedido_id)

    assert pedido["total"] == Decimal("12699.57")


def test_los_importes_guardados_son_identicos_a_los_de_la_especificacion(con):
    pedido_id = guardar(con, [item(producto="remera")], cupon="EGRESADOS2026")

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert {m: pedido[m] for m in ("subtotal", "descuento", "envio", "total")} == {
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
    }


@pytest.mark.parametrize("monto", ["subtotal", "descuento", "envio", "total"])
def test_los_importes_guardados_se_devuelven_como_decimal(con, monto):
    pedido_id = guardar(con, [item(producto="remera")], cupon="EGRESADOS2026")

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert type(pedido[monto]) is Decimal


def test_un_precio_con_decimales_binarios_se_devuelve_sin_perdida(con):
    pedido_id = guardar(con, [item(producto="buzo")])

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert (pedido["subtotal"], pedido["items"][0]["precio_unitario"]) == (
        Decimal("24999.90"),
        Decimal("24999.90"),
    )


def test_el_pedido_se_devuelve_con_el_formato_de_la_especificacion(con):
    pedido_id = guardar(con, [item(producto="remera")], cupon="EGRESADOS2026")

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido == {
        "id": pedido_id,
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": "EGRESADOS2026",
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
        "items": [
            {"producto": "remera", "talle": "M", "cantidad": 1, "precio_unitario": Decimal("11999.50")},
        ],
    }


def test_los_items_se_guardan_en_el_orden_del_carrito(con):
    carrito = [item(producto="buzo", talle="M", cantidad=2), item(producto="remera", talle="S", cantidad=1)]

    pedido_id = guardar(con, carrito)
    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["items"] == [
        {"producto": "buzo", "talle": "M", "cantidad": 2, "precio_unitario": Decimal("24999.90")},
        {"producto": "remera", "talle": "S", "cantidad": 1, "precio_unitario": Decimal("11999.50")},
    ]


@pytest.mark.parametrize("producto, precio_catalogo", [
    ("buzo", "24999.90"),
    ("remera", "11999.50"),
    ("campera", "47999.99"),
])
def test_el_precio_unitario_es_el_del_catalogo_aunque_el_cliente_mande_otro(con, producto, precio_catalogo):
    pedido_id = guardar(con, [item(producto=producto, precio=1)])

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["items"][0]["precio_unitario"] == Decimal(precio_catalogo)


def test_el_subtotal_usa_el_precio_del_catalogo_aunque_el_cliente_mande_otro(con):
    pedido_id = guardar(con, [item(producto="remera", precio=1)])

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["subtotal"] == Decimal("11999.50")


@pytest.mark.parametrize("email_enviado", ["Ana@Mail.COM", "  ana@mail.com  ", "  ANA@MAIL.COM "])
def test_el_email_se_guarda_en_minuscula_y_sin_espacios(con, email_enviado):
    pedido_id = guardar(con, email=email_enviado)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["email"] == "ana@mail.com"


@pytest.mark.parametrize("zona_enviada", ["caba", "  CABA  ", " Caba "])
def test_la_zona_se_guarda_en_mayuscula_y_sin_espacios(con, zona_enviada):
    pedido_id = guardar(con, zona=zona_enviada)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["zona"] == "CABA"


@pytest.mark.parametrize("talle_enviado", ["m", "  M  ", " m "])
def test_el_talle_se_guarda_en_mayuscula_y_sin_espacios(con, talle_enviado):
    pedido_id = guardar(con, [item(talle=talle_enviado)])

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["items"][0]["talle"] == "M"


@pytest.mark.parametrize("cupon_enviado", ["egresados2026", "  EGRESADOS2026  ", " Egresados2026 "])
def test_el_cupon_se_guarda_en_mayuscula_y_sin_espacios(con, cupon_enviado):
    pedido_id = guardar(con, cupon=cupon_enviado)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["cupon"] == "EGRESADOS2026"


@pytest.mark.parametrize("cupon_vacio", [None, "", "   "])
def test_un_cupon_vacio_se_guarda_como_none(con, cupon_vacio):
    pedido_id = guardar(con, cupon=cupon_vacio)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["cupon"] is None


def test_un_id_que_no_existe_devuelve_none_aunque_haya_otros_pedidos(con):
    pedido_id = guardar(con)

    assert pedidos.obtener_pedido(con, pedido_id + 1) is None


def test_guardar_un_pedido_no_modifica_el_carrito_recibido(con):
    carrito = [item(talle=" m ")]

    guardar(con, carrito)

    assert carrito == [{"producto": "buzo", "talle": " m ", "cantidad": 1}]


@pytest.mark.parametrize("email_buscado", ["ana@mail.com", "ANA@Mail.com", "  ana@mail.com  "])
def test_pedidos_de_no_distingue_mayusculas_ni_espacios_en_el_email(con, email_buscado):
    pedido_id = guardar(con, email="ana@mail.com")

    resultado = pedidos.pedidos_de(con, email_buscado)

    assert [p["id"] for p in resultado] == [pedido_id]


def test_pedidos_de_devuelve_primero_el_pedido_mas_reciente(con):
    primero = guardar(con, [item(producto="buzo")])
    segundo = guardar(con, [item(producto="remera")])
    tercero = guardar(con, [item(producto="campera")])

    resultado = pedidos.pedidos_de(con, "ana@mail.com")

    assert [p["id"] for p in resultado] == [tercero, segundo, primero]


def test_pedidos_de_devuelve_los_pedidos_completos_con_sus_items(con):
    guardar(con, [item(producto="buzo", cantidad=2), item(producto="remera")])

    resultado = pedidos.pedidos_de(con, "ana@mail.com")

    assert [i["producto"] for i in resultado[0]["items"]] == ["buzo", "remera"]


def test_pedidos_de_no_devuelve_los_pedidos_de_otro_email(con):
    pedido_de_ana = guardar(con, email="ana@mail.com")
    guardar(con, email="beto@mail.com")

    resultado = pedidos.pedidos_de(con, "ana@mail.com")

    assert [p["id"] for p in resultado] == [pedido_de_ana]


def test_pedidos_de_un_email_sin_pedidos_devuelve_lista_vacia(con):
    guardar(con, email="ana@mail.com")

    assert pedidos.pedidos_de(con, "otro@mail.com") == []


@pytest.mark.parametrize("email_hostil", [
    "' OR '1'='1",
    "x' OR 1=1 --",
    "' UNION SELECT id FROM pedidos --",
    "'; DROP TABLE pedidos; --",
])
def test_un_email_con_sql_no_altera_la_consulta_ni_devuelve_pedidos_ajenos(ruta, con, email_hostil):
    guardar(con, email="ana@mail.com")

    resultado = pedidos.pedidos_de(con, email_hostil)

    assert (resultado, contar(ruta, "pedidos")) == ([], 1)


def test_un_email_con_apostrofe_se_busca_como_texto(con):
    pedido_id = guardar(con, email="o'brien@mail.com")

    resultado = pedidos.pedidos_de(con, "o'brien@mail.com")

    assert [p["id"] for p in resultado] == [pedido_id]