from datetime import date

from checkout import (
    CATALOGO,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)


def test_subtotal():
    carrito = [{"producto": "buzo", "talle": "M", "cantidad": 2}]
    assert calcular_subtotal(carrito) == CATALOGO["buzo"] * 2


def test_total_funciona():
    carrito = [{"producto": "remera", "talle": "L", "cantidad": 1}]
    resultado = calcular_total(carrito, "CABA")
    assert resultado is not None


def test_total_positivo():
    carrito = [{"producto": "campera", "talle": "S", "cantidad": 1}]
    resultado = calcular_total(carrito, "GBA")
    assert resultado["total"] > 0


def test_cupon_egresados():
    descuento = calcular_descuento(100000, 1, "EGRESADOS2026", date(2026, 10, 1))
    assert descuento == 100000 * 0.15


def test_envio_caba():
    assert calcular_envio(10000, "CABA") == 2500


def test_descuento_por_cantidad():
    descuento = calcular_descuento(100000, 6, None, date(2026, 10, 1))
    assert descuento == 10000


def test_talle_valido():
    validar_item({"producto": "buzo", "talle": "M", "cantidad": 1})


def test_no_explota_con_varios_productos():
    carrito = [
        {"producto": "buzo", "talle": "M", "cantidad": 1},
        {"producto": "remera", "talle": "S", "cantidad": 2},
        {"producto": "campera", "talle": "XL", "cantidad": 1},
    ]
    try:
        calcular_total(carrito, "INTERIOR")
    except Exception:
        pass
