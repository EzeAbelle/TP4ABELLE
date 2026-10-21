import json
import threading
import urllib.error
import urllib.request

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def test_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", "/api/v1/otra")
    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


def compra_sin(clave):
    cuerpo = compra()
    del cuerpo[clave]
    return cuerpo


def crear(url, **cambios):
    return pedir(url, "POST", RUTA, compra(**cambios))


def consultar(url, pedido_id):
    return pedir(url, "GET", f"{RUTA}/{pedido_id}")


def test_crear_un_pedido_devuelve_201_con_los_importes_de_la_especificacion(url):
    estado, cuerpo = crear(
        url,
        carrito=[{"producto": "remera", "talle": "M", "cantidad": 1}],
        cupon="EGRESADOS2026",
        fecha="2026-11-30",
    )

    assert (estado, {clave: valor for clave, valor in cuerpo.items() if clave != "id"}) == (201, {
        "subtotal": "11999.50",
        "descuento": "1799.93",
        "envio": "2500.00",
        "total": "12699.57",
    })


def test_crear_un_pedido_devuelve_un_id_entero(url):
    estado, cuerpo = crear(url)

    assert (estado, type(cuerpo["id"])) == (201, int)


def test_crear_un_pedido_devuelve_solo_los_campos_de_la_especificacion(url):
    estado, cuerpo = crear(url)

    assert (estado, sorted(cuerpo)) == (201, ["descuento", "envio", "id", "subtotal", "total"])


def test_crear_dos_pedidos_devuelve_ids_distintos(url):
    _, primero = crear(url)
    _, segundo = crear(url)

    assert primero["id"] != segundo["id"]


@pytest.mark.parametrize("monto", ["subtotal", "descuento", "envio", "total"])
def test_los_importes_de_la_creacion_viajan_como_texto(url, monto):
    estado, cuerpo = crear(url)

    assert (estado, type(cuerpo[monto])) == (201, str)


def test_crear_un_pedido_sin_cupon_ni_fecha_calcula_el_ejemplo_completo(url):
    estado, cuerpo = crear(url, carrito=[{"producto": "buzo", "talle": "M", "cantidad": 2}])

    assert (estado, cuerpo["subtotal"], cuerpo["descuento"], cuerpo["envio"], cuerpo["total"]) == (
        201, "49999.80", "0.00", "2500.00", "52499.80",
    )


def test_cinco_prendas_aplican_el_descuento_por_cantidad_y_envio_gratis(url):
    estado, cuerpo = crear(url, carrito=[{"producto": "buzo", "talle": "M", "cantidad": 5}])

    assert (estado, cuerpo["subtotal"], cuerpo["descuento"], cuerpo["envio"], cuerpo["total"]) == (
        201, "124999.50", "12499.95", "0.00", "112499.55",
    )


def test_el_envio_se_cobra_si_el_subtotal_con_descuento_no_llega_a_60000(url):
    carrito = [
        {"producto": "buzo", "talle": "M", "cantidad": 2},
        {"producto": "remera", "talle": "S", "cantidad": 1},
    ]

    estado, cuerpo = crear(url, carrito=carrito, zona="GBA", cupon="EGRESADOS2026", fecha="2026-10-01")

    assert (estado, cuerpo["subtotal"], cuerpo["descuento"], cuerpo["envio"], cuerpo["total"]) == (
        201, "61999.30", "9299.90", "4000.00", "56699.40",
    )


def test_un_cupon_sin_fecha_se_acepta_y_se_aplica(url):
    estado, cuerpo = crear(url, cupon="BIENVENIDA")

    assert (estado, cuerpo["descuento"], cuerpo["total"]) == (201, "3000.00", "24499.90")


def test_el_precio_enviado_por_el_cliente_se_ignora(url):
    carrito = [{"producto": "buzo", "talle": "M", "cantidad": 1, "precio": 1}]

    estado, cuerpo = crear(url, carrito=carrito)

    assert (estado, cuerpo["subtotal"]) == (201, "24999.90")


def test_consultar_un_pedido_devuelve_200_con_el_formato_de_la_especificacion(url):
    _, creado = crear(
        url,
        carrito=[{"producto": "remera", "talle": "M", "cantidad": 1}],
        cupon="EGRESADOS2026",
        fecha="2026-11-30",
    )

    estado, pedido = consultar(url, creado["id"])

    assert (estado, pedido) == (200, {
        "id": creado["id"],
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": "EGRESADOS2026",
        "subtotal": "11999.50",
        "descuento": "1799.93",
        "envio": "2500.00",
        "total": "12699.57",
        "items": [
            {"producto": "remera", "talle": "M", "cantidad": 1, "precio_unitario": "11999.50"},
        ],
    })


def test_los_importes_consultados_son_iguales_a_los_de_la_creacion(url):
    _, creado = crear(url, carrito=[{"producto": "buzo", "talle": "M", "cantidad": 1}])

    _, pedido = consultar(url, creado["id"])

    assert {m: pedido[m] for m in ("subtotal", "descuento", "envio", "total")} == {
        "subtotal": "24999.90",
        "descuento": "0.00",
        "envio": "2500.00",
        "total": "27499.90",
    }


def test_los_importes_consultados_viajan_como_texto(url):
    _, creado = crear(url)

    _, pedido = consultar(url, creado["id"])

    assert [type(pedido[m]) for m in ("subtotal", "descuento", "envio", "total")] == [str, str, str, str]


def test_el_precio_unitario_consultado_es_el_del_catalogo_aunque_el_cliente_mande_otro(url):
    carrito = [{"producto": "buzo", "talle": "M", "cantidad": 1, "precio": 1}]
    _, creado = crear(url, carrito=carrito)

    _, pedido = consultar(url, creado["id"])

    assert pedido["items"][0]["precio_unitario"] == "24999.90"


def test_consultar_un_pedido_devuelve_todos_sus_items_en_orden(url):
    carrito = [
        {"producto": "buzo", "talle": "M", "cantidad": 2},
        {"producto": "remera", "talle": "S", "cantidad": 1},
    ]
    _, creado = crear(url, carrito=carrito)

    _, pedido = consultar(url, creado["id"])

    assert [(i["producto"], i["talle"], i["cantidad"]) for i in pedido["items"]] == [
        ("buzo", "M", 2),
        ("remera", "S", 1),
    ]


def test_los_datos_del_pedido_se_guardan_normalizados(url):
    carrito = [{"producto": "buzo", "talle": " m ", "cantidad": 1}]
    _, creado = crear(url, email="  Ana@Mail.COM ", zona=" caba ", carrito=carrito, cupon=" bienvenida ")

    _, pedido = consultar(url, creado["id"])

    assert (pedido["email"], pedido["zona"], pedido["cupon"], pedido["items"][0]["talle"]) == (
        "ana@mail.com", "CABA", "BIENVENIDA", "M",
    )


def test_un_pedido_sin_cupon_se_consulta_con_cupon_nulo(url):
    _, creado = crear(url)

    _, pedido = consultar(url, creado["id"])

    assert pedido["cupon"] is None


def test_consultar_un_pedido_que_no_existe_devuelve_404(url):
    estado, cuerpo = consultar(url, 999)

    assert (estado, cuerpo["error"]["code"]) == (404, "PEDIDO_INEXISTENTE")


def test_un_pedido_rechazado_no_queda_guardado(url):
    estado, _ = crear(url, cupon="NOEXISTE")

    estado_consulta, cuerpo = consultar(url, 1)

    assert (estado, estado_consulta, cuerpo["error"]["code"]) == (422, 404, "PEDIDO_INEXISTENTE")


@pytest.mark.parametrize("cambios, codigo", [
    ({"carrito": [{"producto": "buzo", "talle": "XXXL", "cantidad": 1}]}, "TALLE_INVALIDO"),
    ({"carrito": [{"producto": "gorra", "talle": "M", "cantidad": 1}]}, "PRODUCTO_INEXISTENTE"),
    ({"carrito": [{"producto": "buzo", "talle": "M", "cantidad": 11}]}, "CANTIDAD_INVALIDA"),
    ({"carrito": []}, "CARRITO_VACIO"),
    ({"cupon": "NOEXISTE"}, "CUPON_INVALIDO"),
    ({"cupon": "EGRESADOS2026", "fecha": "2026-12-01"}, "CUPON_VENCIDO"),
    ({"carrito": [{"producto": "remera", "talle": "M", "cantidad": 1}], "cupon": "BIENVENIDA"},
     "CUPON_MINIMO_NO_ALCANZADO"),
    ({"zona": "MARTE"}, "ZONA_INVALIDA"),
])
def test_un_error_de_negocio_devuelve_422_con_el_codigo_del_checkout(url, cambios, codigo):
    estado, cuerpo = crear(url, **cambios)

    assert (estado, cuerpo["error"]["code"]) == (422, codigo)


def test_un_error_de_negocio_tiene_el_formato_de_la_especificacion(url):
    estado, cuerpo = crear(url, carrito=[{"producto": "buzo", "talle": "XXXL", "cantidad": 1}])

    assert (estado, list(cuerpo), sorted(cuerpo["error"]), "XXXL" in cuerpo["error"]["message"]) == (
        422, ["error"], ["code", "message"], True,
    )


@pytest.mark.parametrize("crudo", [b"{no es json", b"", b'{"email": "ana@mail.com", '])
def test_un_cuerpo_que_no_es_json_devuelve_400(url, crudo):
    estado, cuerpo = pedir(url, "POST", RUTA, crudo=crudo)

    assert (estado, cuerpo["error"]["code"]) == (400, "JSON_INVALIDO")


@pytest.mark.parametrize("cuerpo_enviado", [
    compra_sin("email"),
    compra_sin("zona"),
    compra_sin("carrito"),
    compra(email=123),
    compra(email=None),
    compra(zona=["CABA"]),
    compra(carrito="buzo"),
    compra(carrito={"producto": "buzo"}),
])
def test_los_datos_faltantes_o_de_otro_tipo_devuelven_400(url, cuerpo_enviado):
    estado, cuerpo = pedir(url, "POST", RUTA, cuerpo_enviado)

    assert (estado, cuerpo["error"]["code"]) == (400, "DATOS_INCOMPLETOS")


def test_un_json_que_no_es_un_objeto_devuelve_400(url):
    estado, cuerpo = pedir(url, "POST", RUTA, crudo=b"[1, 2, 3]")

    assert (estado, cuerpo["error"]["code"]) == (400, "DATOS_INCOMPLETOS")


@pytest.mark.parametrize("cambios", [
    {"fecha": "30/11/2026"},
    {"fecha": "2026-13-45"},
    {"fecha": "2026-02-30"},
    {"fecha": "mañana"},
    {"fecha": "30/11/2026", "cupon": "EGRESADOS2026"},
])
def test_una_fecha_que_no_es_aaaa_mm_dd_devuelve_400(url, cambios):
    estado, cuerpo = crear(url, **cambios)

    assert (estado, cuerpo["error"]["code"]) == (400, "FECHA_INVALIDA")


@pytest.mark.parametrize("metodo, ruta", [
    ("GET", "/"),
    ("GET", "/api/v1/otra"),
    ("GET", "/api/v2/pedidos/1"),
    ("POST", "/api/v1/otra"),
])
def test_una_ruta_que_no_existe_devuelve_404(url, metodo, ruta):
    cuerpo_enviado = compra() if metodo == "POST" else None

    estado, cuerpo = pedir(url, metodo, ruta, cuerpo_enviado)

    assert (estado, cuerpo["error"]["code"]) == (404, "RUTA_INEXISTENTE")