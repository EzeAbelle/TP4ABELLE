# Especificación — Backend de la tienda

**Tienda de Egresados 2026** · versión 1.0

La comisión de egresados vende buzos, remeras y camperas de la promoción a
través de una tienda online. El frontend ya está terminado. Este documento
define el backend, que tiene tres capas:

| Módulo        | Qué hace                                  | Reglas     |
|---------------|-------------------------------------------|------------|
| `checkout.py` | Calcula el total de una compra            | R1 a R9    |
| `pedidos.py`  | Guarda y recupera pedidos en SQLite       | R10        |
| `api.py`      | Expone todo por HTTP para el frontend     | R11        |

**Este documento es el contrato.** Si el código y la especificación no
coinciden, el que está mal es el código.

---

## 1. Contrato de `checkout.py`

Estas firmas son lo que las otras capas ya están llamando. **No se pueden cambiar
nombres, parámetros ni tipos de retorno.**

```python
class CheckoutError(Exception):
    code: str       # código estable, ver sección 4
    mensaje: str    # texto para mostrar al usuario

def validar_item(item: dict) -> None
def calcular_subtotal(carrito: list[dict]) -> Decimal
def calcular_descuento(subtotal: Decimal, cantidad_prendas: int,
                       cupon: str | None = None, fecha: date | None = None) -> Decimal
def calcular_envio(subtotal_con_descuento: Decimal, zona: str) -> Decimal
def calcular_total(carrito: list[dict], zona: str,
                   cupon: str | None = None, fecha: date | None = None) -> dict
```

**Formato de un ítem del carrito:**

```python
{"producto": "buzo", "talle": "M", "cantidad": 2}
```

Cualquier otra clave que venga en el ítem se ignora.

**`calcular_total` devuelve:**

```python
{"subtotal": Decimal, "descuento": Decimal, "envio": Decimal, "total": Decimal}
```

Ante cualquier dato inválido, las funciones lanzan `CheckoutError` con el
`code` correspondiente. Nunca otro tipo de excepción.

---

## 2. Reglas de negocio

### R1 — Catálogo y precios

| Producto  | Precio       |
|-----------|--------------|
| `buzo`    | $ 24.999,90  |
| `remera`  | $ 11.999,50  |
| `campera` | $ 47.999,99  |

- El nombre del producto se escribe exactamente así, en minúscula.
- **El precio sale siempre del catálogo.** Si el ítem trae un precio propio,
  se ignora.
- Un producto que no está en el catálogo → `PRODUCTO_INEXISTENTE`.

### R2 — Talles

- Talles válidos: `XS`, `S`, `M`, `L`, `XL`, `XXL`.
- No se distingue mayúscula de minúscula (`"m"` es válido).
- Se ignoran los espacios al principio y al final (`"  M "` es válido).
- Cualquier otro valor → `TALLE_INVALIDO`.

### R3 — Cantidad

- Número entero entre **1 y 10, ambos inclusive**.
- Cualquier otro valor, incluidos los no enteros → `CANTIDAD_INVALIDA`.

### R4 — Carrito

- Debe tener al menos un ítem → si no, `CARRITO_VACIO`.
- **Ninguna función modifica el carrito que recibe.** El frontend reutiliza
  ese objeto y espera encontrarlo igual.

### R5 — Descuento por cantidad

- Si la cantidad total de prendas del carrito (la suma de las cantidades de
  todos los ítems) es **5 o más**, se aplica un **10%** sobre el subtotal.

### R6 — Cupones

| Código          | Beneficio  | Condición                              |
|-----------------|------------|----------------------------------------|
| `EGRESADOS2026` | 15%        | Válido hasta el **30/11/2026 inclusive** |
| `BIENVENIDA`    | $ 3.000    | Subtotal de **$ 20.000 o más**          |

- **Estos son los únicos dos cupones que existen.**
- No se distingue mayúscula de minúscula y se ignoran los espacios alrededor.
- `None`, `""` o un texto de solo espacios equivalen a **no usar cupón**. No
  es un error.
- Código que no existe → `CUPON_INVALIDO`.
- `EGRESADOS2026` después de su fecha → `CUPON_VENCIDO`.
- `BIENVENIDA` con subtotal menor al mínimo → `CUPON_MINIMO_NO_ALCANZADO`.
- **El cupón no se acumula con el descuento por cantidad (R5).** Se calculan
  los dos y se aplica el mayor.
- El descuento nunca puede superar el subtotal.
- Si no se recibe `fecha`, se usa la fecha **del día en que se hace la
  llamada**.

### R7 — Dinero y redondeo

- **Todos los importes se manejan como `Decimal`.** Nunca `float`.
- Los descuentos porcentuales se redondean al centavo con **redondeo
  comercial**: el medio centavo redondea hacia arriba.

  > Ejemplo: 15% de $ 11.999,50 = $ 1.799,925 → **$ 1.799,93**

### R8 — Envío

| Zona       | Costo     |
|------------|-----------|
| `CABA`     | $ 2.500   |
| `GBA`      | $ 4.000   |
| `INTERIOR` | $ 6.500   |
| `RETIRO`   | $ 0 (retiro en el colegio) |

- No se distingue mayúscula de minúscula y se ignoran los espacios alrededor.
- El envío es **gratis** si el subtotal **ya con el descuento aplicado** es
  de **$ 60.000 o más**.
- Zona que no existe → `ZONA_INVALIDA`.

### R9 — Total

```
total = subtotal − descuento + envío
```

---

## 3. Orden de validación en `calcular_total`

Si una compra tiene más de un problema, se informa el primero según este
orden:

1. Carrito vacío.
2. Cada ítem, en el orden en que aparece: producto, talle, cantidad.
3. Cupón.
4. Zona.

---

## 4. Códigos de error

| `code`                       | Cuándo                                    |
|------------------------------|-------------------------------------------|
| `PRODUCTO_INEXISTENTE`       | El producto no está en el catálogo        |
| `TALLE_INVALIDO`             | El talle no es uno de los válidos         |
| `CANTIDAD_INVALIDA`          | No es un entero entre 1 y 10              |
| `CARRITO_VACIO`              | El carrito no tiene ítems                 |
| `CUPON_INVALIDO`             | El cupón no existe                        |
| `CUPON_VENCIDO`              | El cupón pasó su fecha de vigencia        |
| `CUPON_MINIMO_NO_ALCANZADO`  | No se alcanza la compra mínima del cupón  |
| `ZONA_INVALIDA`              | La zona de envío no existe                |

---

## 5. Ejemplo completo

Dos buzos talle M, envío a CABA, sin cupón:

| Concepto  | Cálculo              | Importe      |
|-----------|----------------------|--------------|
| Subtotal  | 24.999,90 × 2        | $ 49.999,80  |
| Descuento | 2 prendas, sin cupón | $ 0,00       |
| Envío     | CABA, < $ 60.000     | $ 2.500,00   |
| **Total** |                      | **$ 52.499,80** |

---

## 6. Persistencia — `pedidos.py`

### Contrato

```python
def conectar(ruta: str) -> sqlite3.Connection
def crear_esquema(con) -> None
def guardar_pedido(con, email: str, carrito: list[dict], zona: str,
                   cupon: str | None = None, fecha: date | None = None) -> int
def obtener_pedido(con, pedido_id: int) -> dict | None
def pedidos_de(con, email: str) -> list[dict]
```

**Formato de un pedido** (lo que devuelve `obtener_pedido`):

```python
{
    "id": 7,
    "email": "ana@mail.com",
    "zona": "CABA",
    "cupon": "EGRESADOS2026",          # o None
    "subtotal": Decimal("11999.50"),
    "descuento": Decimal("1799.93"),
    "envio": Decimal("2500.00"),
    "total": Decimal("12699.57"),
    "items": [
        {"producto": "remera", "talle": "M", "cantidad": 1,
         "precio_unitario": Decimal("11999.50")},
    ],
}
```

### R10 — Reglas de persistencia

- `guardar_pedido` calcula los importes con `calcular_total`. Si eso lanza
  `CheckoutError`, el error se propaga y **no queda nada guardado**: ni el
  pedido ni sus ítems.
- Cuando `guardar_pedido` termina, el pedido es **definitivo**: cualquier
  otra conexión a la misma base lo ve completo, con todos sus ítems.
- Los montos que devuelve `obtener_pedido` son **idénticos** a los que
  calculó `checkout`: `Decimal`, mismo valor, sin ninguna pérdida.
- `precio_unitario` es el precio del catálogo, nunca uno enviado por el
  cliente.
- Los datos se guardan normalizados: el email en minúscula y sin espacios
  alrededor; zona, talle y cupón en mayúscula y sin espacios alrededor. Un
  cupón vacío se guarda como `None`.
- `obtener_pedido` de un id que no existe devuelve `None`.
- `pedidos_de` no distingue mayúsculas ni espacios en el email y devuelve
  los pedidos **del más reciente al más antiguo**. El email es un dato que
  escribe el usuario: ningún valor puede alterar la consulta a la base.

---

## 7. API HTTP — `api.py`

### Contrato

```python
def crear_servidor(ruta_db: str, puerto: int = 0) -> ThreadingHTTPServer
```

Crea el esquema y devuelve el servidor **sin arrancar**. Con `puerto=0` el
sistema operativo elige un puerto libre, que se consulta con
`servidor.server_address[1]`. Para arrancarlo: `servidor.serve_forever()`.

> **`ruta_db` tiene que ser un archivo, no `":memory:"`.** Cada request abre
> su propia conexión, y una base en memoria existe solo dentro de la conexión
> que la creó: el siguiente request encontraría una base vacía, sin tablas.
> Lo mismo vale para cualquier test que necesite dos conexiones a la misma
> base.

### R11 — Endpoints

**`POST /api/v1/pedidos`** — crea un pedido.

```json
{
  "email": "ana@mail.com",
  "zona": "CABA",
  "carrito": [{"producto": "remera", "talle": "M", "cantidad": 1}],
  "cupon": "EGRESADOS2026",
  "fecha": "2026-11-30"
}
```

`cupon` y `fecha` son opcionales. La fecha viaja como texto en formato
`AAAA-MM-DD`. Respuesta exitosa:

```json
201 Created
{"id": 7, "subtotal": "11999.50", "descuento": "1799.93",
 "envio": "2500.00", "total": "12699.57"}
```

**`GET /api/v1/pedidos/{id}`** — devuelve el pedido completo, con el formato
de la sección 6.

- **Los montos viajan siempre como texto** (`"1799.93"`), nunca como número
  JSON. Un número JSON se lee como `float` del lado del frontend.

### Errores

Todos los errores tienen el mismo formato:

```json
{"error": {"code": "TALLE_INVALIDO", "message": "Talle inválido: 'XXXL'"}}
```

| Situación                                         | Status | `code`                       |
|---------------------------------------------------|:------:|------------------------------|
| Cualquier `CheckoutError` (error de negocio)      | 422    | el `code` del `CheckoutError` |
| El cuerpo no es JSON válido                       | 400    | `JSON_INVALIDO`              |
| Falta email, zona o carrito, o tienen otro tipo   | 400    | `DATOS_INCOMPLETOS`          |
| La fecha no tiene formato `AAAA-MM-DD`            | 400    | `FECHA_INVALIDA`             |
| El pedido no existe                               | 404    | `PEDIDO_INEXISTENTE`         |
| La ruta no existe                                 | 404    | `RUTA_INEXISTENTE`           |

**Un error nunca puede devolver 500.** Si el sistema devuelve 500, es un bug.

