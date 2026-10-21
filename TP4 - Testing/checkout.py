from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class CheckoutError(Exception):
    def __init__(self, code, mensaje):
        super().__init__(mensaje)
        self.code = code
        self.mensaje = mensaje


CERO = Decimal("0.00")

CATALOGO = {
    "buzo": Decimal("24999.90"),
    "remera": Decimal("11999.50"),
    "campera": Decimal("47999.99"),
}

TALLES = ("XS", "S", "M", "L", "XL", "XXL")

ENVIOS = {
    "CABA": Decimal("2500.00"),
    "GBA": Decimal("4000.00"),
    "INTERIOR": Decimal("6500.00"),
    "RETIRO": CERO,
}
ENVIO_GRATIS_DESDE = Decimal("60000.00")

PORCENTAJE_POR_CANTIDAD = Decimal("0.10")

EGRESADOS_PORCENTAJE = Decimal("0.15")
EGRESADOS_VENCE = date(2026, 11, 30)
BIENVENIDA_DESCUENTO = Decimal("3000.00")
BIENVENIDA_MINIMO = Decimal("20000.00")


def _hoy():
    return date.today()


def _redondear(importe):
    """Redondeo comercial al centavo: el medio centavo sube."""
    return importe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validar_item(item):
    if not isinstance(item, dict):
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Ítem inválido: {item!r}")

    producto = item.get("producto")
    if not isinstance(producto, str) or producto not in CATALOGO:
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Producto inexistente: {producto!r}")

    talle = item.get("talle")
    if not isinstance(talle, str) or talle.strip().upper() not in TALLES:
        raise CheckoutError("TALLE_INVALIDO", f"Talle inválido: {talle!r}")

    cantidad = item.get("cantidad")
    if type(cantidad) is not int or not 1 <= cantidad <= 10:
        raise CheckoutError("CANTIDAD_INVALIDA", f"La cantidad debe ser un entero entre 1 y 10: {cantidad!r}")


def calcular_subtotal(carrito):
    if not carrito:
        raise CheckoutError("CARRITO_VACIO", "El carrito está vacío")

    subtotal = CERO
    for item in carrito:
        validar_item(item)
        subtotal += CATALOGO[item["producto"]] * item["cantidad"]
    return subtotal


def _descuento_por_cupon(subtotal, cupon, fecha):
    if cupon is None:
        return CERO

    codigo = cupon.strip().upper() if isinstance(cupon, str) else None
    if codigo == "":
        return CERO

    if codigo == "EGRESADOS2026":
        if fecha > EGRESADOS_VENCE:
            raise CheckoutError("CUPON_VENCIDO", "El cupón está vencido")
        return _redondear(subtotal * EGRESADOS_PORCENTAJE)

    if codigo == "BIENVENIDA":
        if subtotal < BIENVENIDA_MINIMO:
            raise CheckoutError(
                "CUPON_MINIMO_NO_ALCANZADO",
                f"El cupón requiere una compra mínima de ${BIENVENIDA_MINIMO}",
            )
        return BIENVENIDA_DESCUENTO

    raise CheckoutError("CUPON_INVALIDO", f"El cupón no existe: {cupon!r}")


def calcular_descuento(subtotal, cantidad_prendas, cupon=None, fecha=None):
    if fecha is None:
        fecha = _hoy()

    por_cantidad = CERO
    if cantidad_prendas >= 5:
        por_cantidad = _redondear(subtotal * PORCENTAJE_POR_CANTIDAD)

    por_cupon = _descuento_por_cupon(subtotal, cupon, fecha)

    return min(max(por_cantidad, por_cupon), subtotal)


def calcular_envio(subtotal_con_descuento, zona):
    costo = ENVIOS.get(zona.strip().upper()) if isinstance(zona, str) else None
    if costo is None:
        raise CheckoutError("ZONA_INVALIDA", f"Zona inválida: {zona!r}. Opciones: {', '.join(ENVIOS)}")

    if subtotal_con_descuento >= ENVIO_GRATIS_DESDE:
        return CERO
    return costo


def calcular_total(carrito, zona, cupon=None, fecha=None):
    subtotal = calcular_subtotal(carrito)
    prendas = sum(item["cantidad"] for item in carrito)
    descuento = calcular_descuento(subtotal, prendas, cupon, fecha)
    envio = calcular_envio(subtotal - descuento, zona)

    return {
        "subtotal": subtotal,
        "descuento": descuento,
        "envio": envio,
        "total": subtotal - descuento + envio,
    }
