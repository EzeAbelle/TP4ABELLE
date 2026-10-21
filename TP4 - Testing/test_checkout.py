from datetime import date
from decimal import Decimal

import pytest

import checkout
from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def test_cantidad_cero_es_invalida():
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


# ---------------------------------------------------------------- CheckoutError

def test_checkout_error_guarda_codigo_y_mensaje():
    # Arrange / Act
    error = CheckoutError("TALLE_INVALIDO", "Talle inválido")

    # Assert
    assert (error.code, error.mensaje) == ("TALLE_INVALIDO", "Talle inválido")


# ---------------------------------------------------------------- R1 catálogo

@pytest.mark.parametrize("producto, precio", [
    ("buzo", "24999.90"),
    ("remera", "11999.50"),
    ("campera", "47999.99"),
])
def test_subtotal_de_una_unidad_es_el_precio_del_catalogo(producto, precio):
    # Arrange
    carrito = [item(producto=producto)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal(precio)


def test_precio_enviado_por_el_cliente_se_ignora():
    # Arrange
    carrito = [item(producto="remera", precio=1)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("11999.50")


def test_claves_extra_del_item_se_ignoran():
    # Arrange
    carrito = [item(color="rojo")]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("24999.90")


@pytest.mark.parametrize("producto", ["zapatilla", "Buzo", "buzo ", "", None, ["buzo"]])
def test_producto_fuera_del_catalogo_es_inexistente(producto):
    # Arrange
    elemento = item(producto=producto)

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


def test_item_sin_producto_es_inexistente():
    # Arrange
    elemento = {"talle": "M", "cantidad": 1}

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


@pytest.mark.parametrize("elemento", [None, "buzo", 5])
def test_item_que_no_es_un_diccionario_es_inexistente(elemento):
    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


# ---------------------------------------------------------------- R2 talles

@pytest.mark.parametrize("talle", ["XS", "S", "M", "L", "XL", "XXL", "m", "xXl", "  M "])
def test_talle_valido_es_aceptado(talle):
    # Arrange
    carrito = [item(talle=talle)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("24999.90")


@pytest.mark.parametrize("talle", ["XXXL", "", "   ", "38", "X L", None, 5])
def test_talle_fuera_de_los_validos_es_invalido(talle):
    # Arrange
    elemento = item(talle=talle)

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "TALLE_INVALIDO"


def test_item_sin_talle_es_invalido():
    # Arrange
    elemento = {"producto": "buzo", "cantidad": 1}

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "TALLE_INVALIDO"


# ---------------------------------------------------------------- R3 cantidad

@pytest.mark.parametrize("cantidad, esperado", [
    (1, "11999.50"),
    (5, "59997.50"),
    (10, "119995.00"),
])
def test_cantidad_entre_1_y_10_multiplica_el_precio(cantidad, esperado):
    # Arrange
    carrito = [item(producto="remera", cantidad=cantidad)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal(esperado)


@pytest.mark.parametrize("cantidad", [0, 11, -1, 1.5, "3", None])
def test_cantidad_fuera_de_rango_o_no_entera_es_invalida(cantidad):
    # Arrange
    elemento = item(cantidad=cantidad)

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "CANTIDAD_INVALIDA"


def test_item_sin_cantidad_es_invalido():
    # Arrange
    elemento = {"producto": "buzo", "talle": "M"}

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "CANTIDAD_INVALIDA"


def test_item_con_producto_y_talle_invalidos_informa_el_producto():
    # Arrange
    elemento = item(producto="zapatilla", talle="XXXL", cantidad=0)

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "PRODUCTO_INEXISTENTE"


def test_item_con_talle_y_cantidad_invalidos_informa_el_talle():
    # Arrange
    elemento = item(talle="XXXL", cantidad=0)

    # Act
    codigo = codigo_de_error(validar_item, elemento)

    # Assert
    assert codigo == "TALLE_INVALIDO"


# ---------------------------------------------------------------- R4 carrito

def test_carrito_vacio_es_invalido_en_subtotal_y_en_total():
    # Act
    codigo_subtotal = codigo_de_error(calcular_subtotal, [])
    codigo_total = codigo_de_error(calcular_total, [], "CABA")

    # Assert
    assert (codigo_subtotal, codigo_total) == ("CARRITO_VACIO", "CARRITO_VACIO")


def test_subtotal_suma_los_items_del_carrito():
    # Arrange
    carrito = [item("buzo", cantidad=2), item("remera", "L", 1)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert subtotal == Decimal("61999.30")


def test_subtotal_es_decimal_y_exacto():
    # Arrange
    carrito = [item("buzo", cantidad=3)]

    # Act
    subtotal = calcular_subtotal(carrito)

    # Assert
    assert isinstance(subtotal, Decimal)
    assert str(subtotal) == "74999.70"


def test_calcular_subtotal_no_modifica_el_carrito():
    # Arrange
    carrito = [item(talle="m")]
    original = [item(talle="m")]

    # Act
    calcular_subtotal(carrito)

    # Assert
    assert carrito == original


def test_calcular_total_no_modifica_el_carrito():
    # Arrange
    carrito = [item(talle=" m "), item("remera", "l", 5, precio=1)]
    original = [item(talle=" m "), item("remera", "l", 5, precio=1)]

    # Act
    calcular_total(carrito, "caba", " bienvenida ")

    # Assert
    assert carrito == original


# ---------------------------------------------------------------- R5 cantidad

@pytest.mark.parametrize("prendas, esperado", [
    (1, "0.00"),
    (4, "0.00"),
    (5, "10000.00"),
    (6, "10000.00"),
    (10, "10000.00"),
])
def test_descuento_por_cantidad_desde_5_prendas(prendas, esperado):
    # Arrange
    subtotal = Decimal("100000")

    # Act
    descuento = calcular_descuento(subtotal, prendas, None, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal(esperado)


def test_prendas_se_suman_entre_los_items_del_carrito():
    # Arrange
    carrito = [item("buzo", cantidad=2), item("remera", "S", 3)]

    # Act
    resultado = calcular_total(carrito, "CABA")

    # Assert
    assert resultado["descuento"] == Decimal("8599.83")


def test_cuatro_prendas_en_dos_items_no_tienen_descuento():
    # Arrange
    carrito = [item("buzo", cantidad=3), item("remera", "S", 1)]

    # Act
    resultado = calcular_total(carrito, "CABA")

    # Assert
    assert resultado["descuento"] == Decimal("0.00")


# ---------------------------------------------------------------- R6 cupones

@pytest.mark.parametrize("fecha", [date(2026, 11, 29), date(2026, 11, 30)])
def test_egresados_vigente_hasta_el_30_de_noviembre_inclusive(fecha):
    # Arrange
    subtotal = Decimal("100000")

    # Act
    descuento = calcular_descuento(subtotal, 1, "EGRESADOS2026", fecha)

    # Assert
    assert descuento == Decimal("15000.00")


@pytest.mark.parametrize("fecha", [date(2026, 12, 1), date(2027, 6, 1)])
def test_egresados_vencido_despues_del_30_de_noviembre(fecha):
    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("100000"), 1, "EGRESADOS2026", fecha)

    # Assert
    assert codigo == "CUPON_VENCIDO"


def test_egresados_vencido_no_vuelve_al_descuento_por_cantidad():
    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("100000"), 5, "EGRESADOS2026", date(2026, 12, 1))

    # Assert
    assert codigo == "CUPON_VENCIDO"


def test_bienvenida_descuenta_3000_con_subtotal_en_el_minimo():
    # Act
    descuento = calcular_descuento(Decimal("20000"), 1, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("3000.00")


def test_bienvenida_con_subtotal_bajo_el_minimo_no_alcanza():
    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("19999.99"), 1, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert codigo == "CUPON_MINIMO_NO_ALCANZADO"


def test_bienvenida_no_vence():
    # Act
    descuento = calcular_descuento(Decimal("24999.90"), 1, "BIENVENIDA", date(2030, 1, 1))

    # Assert
    assert descuento == Decimal("3000.00")


@pytest.mark.parametrize("cupon", [" egresados2026 ", "Egresados2026", "EGRESADOS2026"])
def test_egresados_ignora_mayusculas_y_espacios(cupon):
    # Act
    descuento = calcular_descuento(Decimal("100000"), 1, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("15000.00")


@pytest.mark.parametrize("cupon", [" bienvenida ", "bienvenida", "BIENVENIDA"])
def test_bienvenida_ignora_mayusculas_y_espacios(cupon):
    # Act
    descuento = calcular_descuento(Decimal("24999.90"), 1, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("3000.00")


@pytest.mark.parametrize("cupon", [None, "", "   "])
def test_cupon_ausente_vacio_o_con_espacios_equivale_a_no_usar_cupon(cupon):
    # Act
    descuento = calcular_descuento(Decimal("100000"), 1, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("0.00")


@pytest.mark.parametrize("cupon", ["PROMO10", "EGRESADOS2025", "DEBUG100", 123])
def test_cupon_inexistente_es_invalido(cupon):
    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("100000"), 1, cupon, HOY_VIGENTE)

    # Assert
    assert codigo == "CUPON_INVALIDO"


def test_egresados_gana_al_descuento_por_cantidad_y_no_se_acumulan():
    # Act
    descuento = calcular_descuento(Decimal("100000"), 6, "EGRESADOS2026", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("15000.00")


def test_descuento_por_cantidad_gana_a_bienvenida():
    # Act
    descuento = calcular_descuento(Decimal("100000"), 5, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("10000.00")


def test_bienvenida_gana_al_descuento_por_cantidad_cuando_es_mayor():
    # Act
    descuento = calcular_descuento(Decimal("25000"), 5, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("3000.00")


def test_bienvenida_y_descuento_por_cantidad_empatan_en_3000():
    # Act
    descuento = calcular_descuento(Decimal("30000"), 5, "BIENVENIDA", HOY_VIGENTE)

    # Assert
    assert descuento == Decimal("3000.00")


def test_cupon_invalido_se_informa_aunque_haya_descuento_por_cantidad():
    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("100000"), 5, "PROMO10", HOY_VIGENTE)

    # Assert
    assert codigo == "CUPON_INVALIDO"


def test_descuento_sin_fecha_usa_el_dia_de_la_llamada_vigente(monkeypatch):
    # Arrange
    monkeypatch.setattr(checkout, "_hoy", lambda: date(2026, 11, 30))

    # Act
    descuento = calcular_descuento(Decimal("100000"), 1, "EGRESADOS2026")

    # Assert
    assert descuento == Decimal("15000.00")


def test_descuento_sin_fecha_usa_el_dia_de_la_llamada_vencido(monkeypatch):
    # Arrange
    monkeypatch.setattr(checkout, "_hoy", lambda: date(2026, 12, 1))

    # Act
    codigo = codigo_de_error(calcular_descuento, Decimal("100000"), 1, "EGRESADOS2026")

    # Assert
    assert codigo == "CUPON_VENCIDO"


def test_fecha_enviada_tiene_prioridad_sobre_el_dia_de_la_llamada(monkeypatch):
    # Arrange
    monkeypatch.setattr(checkout, "_hoy", lambda: date(2030, 1, 1))

    # Act
    descuento = calcular_descuento(Decimal("100000"), 1, "EGRESADOS2026", date(2026, 11, 30))

    # Assert
    assert descuento == Decimal("15000.00")


# ---------------------------------------------------------------- R7 redondeo

@pytest.mark.parametrize("subtotal, prendas, cupon, esperado", [
    ("11999.50", 1, "EGRESADOS2026", "1799.93"),   # 1799.925 -> sube
    ("251999.45", 6, None, "25199.95"),            # 25199.945 -> sube
    ("85998.30", 1, "EGRESADOS2026", "12899.75"),  # 12899.745 -> sube
    ("61999.30", 1, "EGRESADOS2026", "9299.90"),   # 9299.895 -> sube
    ("10000.03", 1, "EGRESADOS2026", "1500.00"),   # 1500.0045 -> baja
    ("10000.04", 1, "EGRESADOS2026", "1500.01"),   # 1500.006 -> sube
])
def test_descuento_porcentual_redondea_el_medio_centavo_hacia_arriba(subtotal, prendas, cupon, esperado):
    # Arrange
    monto = Decimal(subtotal)

    # Act
    descuento = calcular_descuento(monto, prendas, cupon, HOY_VIGENTE)

    # Assert
    assert descuento == Decimal(esperado)


def test_importes_del_total_son_decimal():
    # Arrange
    carrito = [item("remera")]

    # Act
    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", date(2026, 11, 30))

    # Assert
    tipos = {clave: type(valor) for clave, valor in resultado.items()}
    assert tipos == {"subtotal": Decimal, "descuento": Decimal, "envio": Decimal, "total": Decimal}


# ---------------------------------------------------------------- R8 envío

@pytest.mark.parametrize("zona, costo", [
    ("CABA", "2500"),
    ("GBA", "4000"),
    ("INTERIOR", "6500"),
    ("RETIRO", "0"),
])
def test_envio_segun_la_zona(zona, costo):
    # Arrange
    subtotal = Decimal("11999.50")

    # Act
    envio = calcular_envio(subtotal, zona)

    # Assert
    assert envio == Decimal(costo)


@pytest.mark.parametrize("zona, costo", [
    (" caba ", "2500"),
    ("gba", "4000"),
    ("Interior", "6500"),
    (" retiro", "0"),
])
def test_envio_ignora_mayusculas_y_espacios_en_la_zona(zona, costo):
    # Act
    envio = calcular_envio(Decimal("11999.50"), zona)

    # Assert
    assert envio == Decimal(costo)


@pytest.mark.parametrize("subtotal, esperado", [
    ("59999.99", "2500"),
    ("60000.00", "0"),
    ("60000.01", "0"),
])
def test_envio_es_gratis_desde_60000(subtotal, esperado):
    # Act
    envio = calcular_envio(Decimal(subtotal), "CABA")

    # Assert
    assert envio == Decimal(esperado)


@pytest.mark.parametrize("zona", ["MENDOZA", "", "   ", None, 5])
def test_zona_inexistente_es_invalida(zona):
    # Act
    codigo = codigo_de_error(calcular_envio, Decimal("1000"), zona)

    # Assert
    assert codigo == "ZONA_INVALIDA"


def test_zona_invalida_se_informa_aunque_el_envio_sea_gratis():
    # Act
    codigo = codigo_de_error(calcular_envio, Decimal("80000"), "MENDOZA")

    # Assert
    assert codigo == "ZONA_INVALIDA"


# ---------------------------------------------------------------- R9 total

@pytest.mark.parametrize("carrito, zona, cupon, esperado", [
    # ejemplo de la especificación: dos buzos a CABA
    ([item("buzo", cantidad=2)], "CABA", None, ("49999.80", "0.00", "2500.00", "52499.80")),
    ([item("remera")], "CABA", "EGRESADOS2026", ("11999.50", "1799.93", "2500.00", "12699.57")),
    ([item("remera", cantidad=4)], "CABA", None, ("47998.00", "0.00", "2500.00", "50498.00")),
    ([item("remera", cantidad=5)], "CABA", None, ("59997.50", "5999.75", "2500.00", "56497.75")),
    ([item("buzo", cantidad=2), item("remera", "S", 3)], "CABA", None,
     ("85998.30", "8599.83", "0.00", "77398.47")),
    ([item("remera", cantidad=5)], "CABA", "EGRESADOS2026", ("59997.50", "8999.63", "2500.00", "53497.87")),
    ([item("buzo")], "CABA", "BIENVENIDA", ("24999.90", "3000.00", "2500.00", "24499.90")),
    ([item("buzo", cantidad=2), item("remera")], "GBA", "EGRESADOS2026",
     ("61999.30", "9299.90", "4000.00", "56699.40")),
    ([item("buzo", cantidad=2), item("remera")], "GBA", "BIENVENIDA",
     ("61999.30", "3000.00", "4000.00", "62999.30")),
    ([item("campera", cantidad=3)], "CABA", None, ("143999.97", "0.00", "0.00", "143999.97")),
    ([item("remera", cantidad=10)], "CABA", None, ("119995.00", "11999.50", "0.00", "107995.50")),
    ([item("remera")], "RETIRO", None, ("11999.50", "0.00", "0.00", "11999.50")),
    ([item("remera")], "GBA", None, ("11999.50", "0.00", "4000.00", "15999.50")),
    ([item("remera")], "INTERIOR", None, ("11999.50", "0.00", "6500.00", "18499.50")),
    ([item("campera"), item("remera")], "INTERIOR", None, ("59999.49", "0.00", "6500.00", "66499.49")),
    ([item("buzo"), item("remera", cantidad=3)], "CABA", None, ("60998.40", "0.00", "0.00", "60998.40")),
    ([item("campera", cantidad=5), item("remera")], "CABA", None,
     ("251999.45", "25199.95", "0.00", "226799.50")),
])
def test_total_calcula_subtotal_descuento_envio_y_total(carrito, zona, cupon, esperado):
    # Arrange
    fecha = date(2026, 11, 30)
    subtotal, descuento, envio, total = (Decimal(valor) for valor in esperado)

    # Act
    resultado = calcular_total(carrito, zona, cupon, fecha)

    # Assert
    assert resultado == {"subtotal": subtotal, "descuento": descuento, "envio": envio, "total": total}


def test_envio_gratis_se_decide_con_el_subtotal_ya_descontado():
    # Arrange
    carrito = [item("buzo", cantidad=2), item("remera")]

    # Act
    resultado = calcular_total(carrito, "GBA", "EGRESADOS2026", HOY_VIGENTE)

    # Assert
    assert resultado["envio"] == Decimal("4000.00")


@pytest.mark.parametrize("carrito, zona, cupon, esperado", [
    ([], "MENDOZA", "PROMO10", "CARRITO_VACIO"),
    ([item(producto="zapatilla", talle="XXXL")], "CABA", None, "PRODUCTO_INEXISTENTE"),
    ([item(talle="XXXL", cantidad=0)], "CABA", None, "TALLE_INVALIDO"),
    ([item(cantidad=0), item(producto="zapatilla")], "CABA", None, "CANTIDAD_INVALIDA"),
    ([item(talle="XXXL")], "MENDOZA", "PROMO10", "TALLE_INVALIDO"),
    ([item()], "MENDOZA", "PROMO10", "CUPON_INVALIDO"),
    ([item()], "MENDOZA", None, "ZONA_INVALIDA"),
])
def test_con_varios_problemas_se_informa_el_primero_segun_el_orden(carrito, zona, cupon, esperado):
    # Act
    codigo = codigo_de_error(calcular_total, carrito, zona, cupon, HOY_VIGENTE)

    # Assert
    assert codigo == esperado


def test_total_sin_fecha_usa_el_dia_de_la_llamada(monkeypatch):
    # Arrange
    monkeypatch.setattr(checkout, "_hoy", lambda: date(2026, 11, 30))

    # Act
    resultado = calcular_total([item("remera")], "CABA", "EGRESADOS2026")

    # Assert
    assert resultado["total"] == Decimal("12699.57")


def test_total_sin_fecha_con_cupon_vencido_el_dia_de_la_llamada(monkeypatch):
    # Arrange
    monkeypatch.setattr(checkout, "_hoy", lambda: date(2026, 12, 1))

    # Act
    codigo = codigo_de_error(calcular_total, [item("remera")], "CABA", "EGRESADOS2026")

    # Assert
    assert codigo == "CUPON_VENCIDO"


