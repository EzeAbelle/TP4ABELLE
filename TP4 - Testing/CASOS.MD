# CASOS.md — Casos de caja negra (Parte 1)

Hecho solo con `ESPECIFICACION.md`, sin leer el código. Notación: `$` = `Decimal`. Todos los importes se esperan como `Decimal` con 2 decimales.
Precios: buzo 24999.90 · remera 11999.50 · campera 47999.99.
Abreviaturas de ítem: `(producto, talle, cantidad)`. Salvo que se aclare, talle `M`, zona `CABA`, sin cupón.

---

## R1 — Catálogo y precios

**Particiones**
- V1: producto del catálogo (`buzo`, `remera`, `campera`).
- V2: ítem con precio propio o claves extra → se ignoran.
- I1: producto fuera del catálogo.
- I2: catálogo mal escrito (mayúsculas / espacios): el nombre debe ser exacto.
- I3: producto vacío, ausente o no-string.

**Límites:** no aplica (valores discretos). Se prueba cada producto.

| ID | Entrada | Esperado |
|---|---|---|
| R1-1 | `[("buzo",M,1)]` subtotal | `24999.90` |
| R1-2 | `[("remera",M,1)]` subtotal | `11999.50` |
| R1-3 | `[("campera",M,1)]` subtotal | `47999.99` |
| R1-4 | `{"producto":"buzo","talle":"M","cantidad":1,"precio":1}` subtotal | `24999.90` (ignora el precio) |
| R1-5 | ítem con clave extra `"color":"rojo"` | válido, sin error |
| R1-6 | producto `"zapatilla"` | `PRODUCTO_INEXISTENTE` |
| R1-7 | producto `"Buzo"` | `PRODUCTO_INEXISTENTE` |
| R1-8 | producto `"buzo "` (espacio) | `PRODUCTO_INEXISTENTE` |
| R1-9 | producto `""` | `PRODUCTO_INEXISTENTE` |
| R1-10 | producto `None` | `PRODUCTO_INEXISTENTE` |
| R1-11 | ítem sin clave `producto` | `PRODUCTO_INEXISTENTE` *(interpretación: nunca otra excepción)* |

---

## R2 — Talles

**Particiones**
- V1: cada talle válido (`XS`,`S`,`M`,`L`,`XL`,`XXL`).
- V2: minúscula / mezcla de mayúsculas.
- V3: espacios alrededor.
- I1: talle inexistente.
- I2: vacío, solo espacios, no-string o ausente.
- I3: espacios *internos* o parecidos (`"X L"`).

**Límites:** el más chico (`XS`) y el más grande (`XXL`); `XXXL` justo fuera.

| ID | Entrada (talle) | Esperado |
|---|---|---|
| R2-1 | `XS`, `S`, `M`, `L`, `XL`, `XXL` (uno por caso) | válido |
| R2-2 | `"m"` | válido |
| R2-3 | `"xXl"` | válido |
| R2-4 | `"  M "` | válido |
| R2-5 | `"XXXL"` | `TALLE_INVALIDO` |
| R2-6 | `""` | `TALLE_INVALIDO` |
| R2-7 | `"   "` | `TALLE_INVALIDO` |
| R2-8 | `"38"` | `TALLE_INVALIDO` |
| R2-9 | `"X L"` | `TALLE_INVALIDO` |
| R2-10 | `None` | `TALLE_INVALIDO` |
| R2-11 | ítem sin clave `talle` | `TALLE_INVALIDO` *(interpretación)* |

---

## R3 — Cantidad

**Particiones**
- V1: entero dentro de 1..10.
- I1: menor que 1 (0, negativos).
- I2: mayor que 10.
- I3: no entero (`1.5`, `"3"`, `None`, ausente).

**Límites:** 0 | **1** | 2 … 9 | **10** | 11.

| ID | Entrada (cantidad) | Esperado |
|---|---|---|
| R3-1 | `1` | válido |
| R3-2 | `10` | válido |
| R3-3 | `5` (valor intermedio) | válido |
| R3-4 | `0` | `CANTIDAD_INVALIDA` |
| R3-5 | `11` | `CANTIDAD_INVALIDA` |
| R3-6 | `-1` | `CANTIDAD_INVALIDA` |
| R3-7 | `1.5` | `CANTIDAD_INVALIDA` |
| R3-8 | `"3"` (texto) | `CANTIDAD_INVALIDA` |
| R3-9 | `None` | `CANTIDAD_INVALIDA` |
| R3-10 | ítem sin clave `cantidad` | `CANTIDAD_INVALIDA` *(interpretación)* |

*Casos ambiguos (la spec no los define, no se afirma resultado): `True`, `3.0`.*

---

## R4 — Carrito

**Particiones**
- V1: carrito con 1 ítem.
- V2: carrito con varios ítems.
- I1: carrito vacío.
- V3 (efecto lateral): el carrito recibido no se modifica.

**Límites:** 0 ítems | 1 ítem.

| ID | Entrada | Esperado |
|---|---|---|
| R4-1 | `[]` en `calcular_subtotal` y en `calcular_total` | `CARRITO_VACIO` |
| R4-2 | 1 ítem `(buzo,M,1)` | subtotal `24999.90` |
| R4-3 | 2 ítems `(buzo,M,2)`,`(remera,L,1)` | subtotal `61999.30` |
| R4-4 | copia profunda del carrito antes y después de `calcular_total` con 2 ítems, talle `" m "`, cupón | carrito **igual** al original |
| R4-5 | idem para `calcular_subtotal` y `validar_item` | carrito **igual** al original |

---

## R5 — Descuento por cantidad

**Particiones**
- V1: total de prendas < 5 → sin descuento.
- V2: total de prendas ≥ 5 → 10 % del subtotal.
- V3: las 5+ prendas salen de **sumar varios ítems**.

**Límites:** 4 prendas | **5** prendas | 6; máximo con un ítem (10).

| ID | Entrada | Descuento esperado |
|---|---|---|
| R5-1 | 4 remeras (sub `47998.00`) | `0.00` |
| R5-2 | 5 remeras (sub `59997.50`) | `5999.75` |
| R5-3 | 2 buzos + 3 remeras (2+3=5, sub `85998.30`) | `8599.83` |
| R5-4 | 10 remeras (sub `119995.00`) | `11999.50` |
| R5-5 | 1 ítem de 4 + 1 ítem de 1 (4+1=5) | descuento 10 % |
| R5-6 | 3 buzos + 1 remera (4 prendas, 2 ítems) | `0.00` |
| R5-7 | 5 campera + 1 remera (6 prendas, sub `251999.45`) | `25199.95` (ver R7) |

---

## R6 — Cupones

**Particiones**
- `EGRESADOS2026`: V1 antes del vencimiento · V2 **el último día** · I1 después del vencimiento.
- `BIENVENIDA`: V1 subtotal ≥ mínimo · I1 subtotal < mínimo.
- Normalización: V mayúsculas/minúsculas y espacios.
- Sin cupón: `None`, `""`, `"   "` → no es error.
- I: código inexistente (`CUPON_INVALIDO`).
- Combinación con R5: se aplica el **mayor**, nunca la suma.
- Fecha: dada, o ausente → hoy.

**Límites:** fecha 29/11 | **30/11** | 01/12 de 2026 · subtotal 19999.99 | **20000.00** (vía `calcular_descuento` directo; con el catálogo no hay carrito que dé exactamente 20000).

| ID | Entrada | Esperado |
|---|---|---|
| R6-1 | 1 remera, `EGRESADOS2026`, fecha `2026-11-29` | desc `1799.93` |
| R6-2 | 1 remera, `EGRESADOS2026`, fecha `2026-11-30` | desc `1799.93` (último día válido) |
| R6-3 | 1 remera, `EGRESADOS2026`, fecha `2026-12-01` | `CUPON_VENCIDO` |
| R6-4 | `EGRESADOS2026`, fecha `2027-06-01` | `CUPON_VENCIDO` |
| R6-5 | 1 remera, `" egresados2026 "`, fecha `2026-11-30` | desc `1799.93` |
| R6-6 | 1 buzo, `BIENVENIDA` | desc `3000.00` |
| R6-7 | 1 remera (sub `11999.50`), `BIENVENIDA` | `CUPON_MINIMO_NO_ALCANZADO` |
| R6-8 | `calcular_descuento(Decimal("20000"),1,"BIENVENIDA")` | `3000.00` |
| R6-9 | `calcular_descuento(Decimal("19999.99"),1,"BIENVENIDA")` | `CUPON_MINIMO_NO_ALCANZADO` |
| R6-10 | `" bienvenida "` con 1 buzo | desc `3000.00` |
| R6-11 | `BIENVENIDA`, fecha `2030-01-01`, 1 buzo | desc `3000.00` (no vence) |
| R6-12 | cupón `None` / `""` / `"   "` con 1 buzo | desc `0.00`, sin error (3 casos) |
| R6-13 | `"PROMO10"` | `CUPON_INVALIDO` |
| R6-14 | `"EGRESADOS2025"` | `CUPON_INVALIDO` |
| R6-15 | 5 remeras + `EGRESADOS2026` (15 % = `8999.63` > 10 % = `5999.75`) | desc `8999.63` (no `14999.38`) |
| R6-16 | 5 remeras + `BIENVENIDA` (`3000` < 10 % = `5999.75`) | desc `5999.75` |
| R6-17 | `calcular_descuento(Decimal("30000"),5,"BIENVENIDA")` (empate 3000 = 3000) | `3000.00` |
| R6-18 | 5 remeras + `EGRESADOS2026` vencido | `CUPON_VENCIDO` (no cae al 10 %) |
| R6-19 | 1 buzo + `BIENVENIDA`: descuento ≤ subtotal | desc `3000.00` ≤ `24999.90` |
| R6-20 | sin `fecha`, con `EGRESADOS2026`: usa el día de la llamada | con "hoy" simulado = `2026-11-30` válido, `2026-12-01` vencido (se simula la fecha) |

---

## R7 — Dinero y redondeo

**Particiones**
- V1: tipos de retorno `Decimal` (nunca `float`).
- V2: porcentaje que da medio centavo exacto → sube (half-up).
- V3: porcentaje que no da medio centavo → redondeo normal.
- V4: valores sin pérdida de precisión (`24999.90` exacto).

**Límites:** el medio centavo. Se eligen casos donde half-up ≠ half-even (el dígito anterior es par).

| ID | Entrada | Esperado |
|---|---|---|
| R7-1 | 1 remera + `EGRESADOS2026` (15 % = 1799.925) | `1799.93` |
| R7-2 | 5 campera + 1 remera (10 % de 251999.45 = 25199.945) | `25199.95` |
| R7-3 | 3 remeras + 2 buzos + `EGRESADOS2026` (15 % de 85998.30 = 12899.745) | `12899.75` |
| R7-4 | 2 buzos + 1 remera + `EGRESADOS2026` (15 % de 61999.30 = 9299.895) | `9299.90` |
| R7-5 | tipo de `subtotal`, `descuento`, `envio`, `total` | todos `Decimal` (`isinstance`) |
| R7-6 | subtotal de 3 buzos | exactamente `Decimal("74999.70")` |
| R7-7 | 3 campera, 3 buzos: resultados | sin error de `float` (ej. `47999.99*3 = 143999.97`) |

---

## R8 — Envío

**Particiones**
- V: cada zona (`CABA`, `GBA`, `INTERIOR`, `RETIRO`).
- V: normalización (minúscula / espacios).
- V: envío gratis (subtotal con descuento ≥ 60000).
- V: `RETIRO` es 0 aun bajo 60000.
- I: zona inexistente, vacía o `None`.
- Regla especial: el umbral se mide **después** del descuento.

**Límites:** `59999.99` | **`60000.00`** (vía `calcular_envio` directo).

| ID | Entrada | Esperado |
|---|---|---|
| R8-1 | `calcular_envio(Decimal("11999.50"),"CABA")` | `2500.00` |
| R8-2 | `...,"GBA"` | `4000.00` |
| R8-3 | `...,"INTERIOR"` | `6500.00` |
| R8-4 | `...,"RETIRO"` | `0.00` |
| R8-5 | `" caba "` y `"gba"` | `2500.00` y `4000.00` |
| R8-6 | `calcular_envio(Decimal("59999.99"),"CABA")` | `2500.00` |
| R8-7 | `calcular_envio(Decimal("60000.00"),"CABA")` | `0.00` |
| R8-8 | `calcular_envio(Decimal("60000.01"),"INTERIOR")` | `0.00` |
| R8-9 | `calcular_envio(Decimal("1"),"RETIRO")` | `0.00` |
| R8-10 | zona `"MENDOZA"` | `ZONA_INVALIDA` |
| R8-11 | zona `""` | `ZONA_INVALIDA` |
| R8-12 | zona `None` | `ZONA_INVALIDA` |
| R8-13 | 1 campera + 1 remera (sub `59999.49`), `INTERIOR` | envío `6500.00` (justo bajo el umbral) |
| R8-14 | 1 buzo + 3 remeras (sub `60998.40`), `CABA` | envío `0.00` |
| R8-15 | 2 buzos + 1 remera (sub `61999.30`) + `EGRESADOS2026`, `GBA` (post-desc `52699.40`) | envío `4000.00` (el umbral usa el subtotal **con** descuento) |
| R8-16 | 2 buzos + 1 remera + `BIENVENIDA`, `GBA` (post-desc `58999.30`) | envío `4000.00` |

---

## R9 — Total

**Particiones:** sin descuento ni envío gratis · con descuento · con envío gratis · con `RETIRO` · combinaciones.

| ID | Entrada | subtotal / descuento / envío / total |
|---|---|---|
| R9-1 | 2 buzos, CABA (ejemplo de la spec) | `49999.80` / `0.00` / `2500.00` / `52499.80` |
| R9-2 | 1 remera + `EGRESADOS2026`, CABA, fecha `2026-11-30` | `11999.50` / `1799.93` / `2500.00` / `12699.57` |
| R9-3 | 4 remeras, CABA | `47998.00` / `0.00` / `2500.00` / `50498.00` |
| R9-4 | 5 remeras, CABA | `59997.50` / `5999.75` / `2500.00` / `56497.75` |
| R9-5 | 2 buzos + 3 remeras, CABA | `85998.30` / `8599.83` / `0.00` / `77398.47` |
| R9-6 | 5 remeras + `EGRESADOS2026`, CABA, fecha `2026-11-30` | `59997.50` / `8999.63` / `2500.00` / `53497.87` |
| R9-7 | 1 buzo + `BIENVENIDA`, CABA | `24999.90` / `3000.00` / `2500.00` / `24499.90` |
| R9-8 | 2 buzos + 1 remera + `EGRESADOS2026`, GBA, fecha `2026-11-30` | `61999.30` / `9299.90` / `4000.00` / `56699.40` |
| R9-9 | 2 buzos + 1 remera + `BIENVENIDA`, GBA | `61999.30` / `3000.00` / `4000.00` / `62999.30` |
| R9-10 | 3 camperas, CABA | `143999.97` / `0.00` / `0.00` / `143999.97` |
| R9-11 | 10 remeras, CABA | `119995.00` / `11999.50` / `0.00` / `107995.50` |
| R9-12 | 1 remera, RETIRO | `11999.50` / `0.00` / `0.00` / `11999.50` |
| R9-13 | 1 remera, GBA | `11999.50` / `0.00` / `4000.00` / `15999.50` |
| R9-14 | 1 remera, INTERIOR | `11999.50` / `0.00` / `6500.00` / `18499.50` |
| R9-15 | 1 campera + 1 remera, INTERIOR | `59999.49` / `0.00` / `6500.00` / `66499.49` |
| R9-16 | 5 campera + 1 remera, CABA | `251999.45` / `25199.95` / `0.00` / `226799.50` |

*(Todos los importes cumplen `total = subtotal − descuento + envío`.)*

### Orden de validación (sección 3 de la spec)

| ID | Entrada con varios problemas | Error esperado |
|---|---|---|
| OV-1 | carrito vacío + zona inválida + cupón inválido | `CARRITO_VACIO` |
| OV-2 | ítem 1 con producto inexistente **y** talle inválido | `PRODUCTO_INEXISTENTE` |
| OV-3 | ítem con talle inválido **y** cantidad inválida | `TALLE_INVALIDO` |
| OV-4 | ítem 1 con cantidad inválida, ítem 2 con producto inexistente | `CANTIDAD_INVALIDA` (ítem 1 primero) |
| OV-5 | ítem inválido + cupón inválido + zona inválida | error del ítem |
| OV-6 | cupón inválido + zona inválida | `CUPON_INVALIDO` |
| OV-7 | cupón válido + zona inválida | `ZONA_INVALIDA` |

### Contrato de errores
| ID | Caso | Esperado |
|---|---|---|
| CE-1 | cualquier dato inválido | se lanza `CheckoutError`, nunca `TypeError`, `KeyError`, etc. |
| CE-2 | `CheckoutError` | tiene `code` (estable) y `mensaje` (texto) |

---

## R10 — Persistencia (`pedidos.py`)

**Particiones y límites**
- Atomicidad: error de negocio → nada guardado (ni pedido ni ítems). Límite: error en el **último** ítem de un carrito con ítems válidos antes.
- Durabilidad: otra conexión ve el pedido completo.
- Fidelidad de montos: `Decimal`, igual valor, sin pérdida.
- Precio de catálogo (ignora el del cliente).
- Normalización de email, zona, talle, cupón.
- `obtener_pedido`: id existente / inexistente (0, negativo, grande).
- `pedidos_de`: 0, 1 y varios pedidos; normalización del email; orden; inyección SQL.

| ID | Entrada | Esperado |
|---|---|---|
| R10-1 | `guardar_pedido` válido: 1 remera, CABA, `EGRESADOS2026`, fecha `2026-11-30` | devuelve `int`; `obtener_pedido` = `{id, email, zona:"CABA", cupon:"EGRESADOS2026", subtotal:11999.50, descuento:1799.93, envio:2500.00, total:12699.57, items:[{remera,M,1,11999.50}]}` |
| R10-2 | carrito con 2 ítems válidos | `items` con **ambos**, en orden |
| R10-3 | ítem 1 válido, ítem 2 con talle inválido | `CheckoutError(TALLE_INVALIDO)`; tablas `pedidos` e `items` con **0 filas** |
| R10-4 | zona inválida | `CheckoutError(ZONA_INVALIDA)`; 0 filas en ambas tablas |
| R10-5 | cupón vencido / inválido / carrito vacío | el error se propaga; 0 filas |
| R10-6 | error tras un pedido válido ya guardado | el pedido anterior sigue intacto (1 fila) |
| R10-7 | tras guardar, abrir **otra conexión** a la misma base | ve el pedido con todos sus ítems |
| R10-8 | `subtotal`, `descuento`, `envio`, `total` leídos | `Decimal`, igual a lo de `calcular_total` |
| R10-9 | un monto con centavos (`24999.90`, `12699.57`) | `str(valor)` idéntico, sin `24999.9` ni `12699.570000001` |
| R10-10 | ítem con `"precio": 1` | `precio_unitario` = precio del catálogo |
| R10-11 | email `"  Ana@Mail.COM "` | guardado `"ana@mail.com"` |
| R10-12 | zona `" caba "` | guardada `"CABA"` |
| R10-13 | talle `" m "` | guardado `"M"` |
| R10-14 | cupón `" egresados2026 "` | guardado `"EGRESADOS2026"` |
| R10-15 | cupón `""`, `"   "`, `None` | guardado `None` (3 casos) |
| R10-16 | `obtener_pedido(con, 999)` | `None` |
| R10-17 | `obtener_pedido(con, 0)` y `-1` | `None` |
| R10-18 | `pedidos_de` con email sin pedidos | `[]` |
| R10-19 | `pedidos_de(con,"  ANA@mail.com ")` con pedidos de `ana@mail.com` | devuelve esos pedidos |
| R10-20 | 3 pedidos de la misma persona | orden: más reciente → más antiguo (ids descendentes) |
| R10-21 | pedidos de dos emails distintos | cada email ve solo los suyos |
| R10-22 | `pedidos_de(con,"' OR '1'='1")` con pedidos de otros | `[]` |
| R10-23 | `pedidos_de(con,"x'; DROP TABLE pedidos;--")` | `[]` y la tabla `pedidos` sigue existiendo |
| R10-24 | email con apóstrofe `"o'brien@mail.com"` guardado y consultado | se guarda y se recupera sin error |

---

## R11 — API HTTP (`api.py`)

**Particiones**
- `POST /api/v1/pedidos`: éxito (con/sin cupón, con/sin fecha).
- `GET /api/v1/pedidos/{id}`: existente / inexistente.
- Montos siempre como **texto**.
- Errores: 422 (los 8 `CheckoutError`), 400 (`JSON_INVALIDO`, `DATOS_INCOMPLETOS`, `FECHA_INVALIDA`), 404 (`PEDIDO_INEXISTENTE`, `RUTA_INEXISTENTE`).
- Nunca 500.

**Límites:** fecha `2026-11-30` (válida) vs `2026-12-01` (vencida); id `0` y id inexistente; carrito vacío (422) vs. ausente (400).

| ID | Request | Status / respuesta esperada |
|---|---|---|
| R11-1 | POST válido (1 remera, CABA, `EGRESADOS2026`, `2026-11-30`) | `201` `{"id":N,"subtotal":"11999.50","descuento":"1799.93","envio":"2500.00","total":"12699.57"}` |
| R11-2 | POST sin `cupon` ni `fecha` | `201` |
| R11-3 | en la respuesta, tipo de los 4 montos | `str`, nunca número JSON |
| R11-4 | GET del pedido creado en R11-1 | `200` con el formato de la sección 6, montos como texto, `items` con `precio_unitario` texto |
| R11-5 | GET de pedido sin cupón | `200`, `"cupon": null` |
| R11-6 | los 8 códigos de negocio vía POST (`PRODUCTO_INEXISTENTE`, `TALLE_INVALIDO`, `CANTIDAD_INVALIDA`, `CARRITO_VACIO`, `CUPON_INVALIDO`, `CUPON_VENCIDO`, `CUPON_MINIMO_NO_ALCANZADO`, `ZONA_INVALIDA`) | `422` con `{"error":{"code":<code>,"message":<texto>}}` (8 casos) |
| R11-7 | cuerpo `{no es json` | `400 JSON_INVALIDO` |
| R11-8 | cuerpo vacío | `400 JSON_INVALIDO` |
| R11-9 | falta `email` / `zona` / `carrito` (3 casos) | `400 DATOS_INCOMPLETOS` |
| R11-10 | `email` numérico / `zona` lista / `carrito` diccionario o texto (3 casos) | `400 DATOS_INCOMPLETOS` |
| R11-11 | JSON válido que no es objeto (`[1,2]`) | `400 DATOS_INCOMPLETOS` |
| R11-12 | `carrito: []` | `422 CARRITO_VACIO` (es lista; no es dato incompleto) |
| R11-13 | `fecha` `"30/11/2026"`, `"2026-13-01"`, `"2026-02-30"`, `"hoy"` (4 casos) | `400 FECHA_INVALIDA` |
| R11-14 | `fecha` `"2026-12-01"` con `EGRESADOS2026` | `422 CUPON_VENCIDO` (formato válido, error de negocio) |
| R11-15 | `GET /api/v1/pedidos/99999` | `404 PEDIDO_INEXISTENTE` |
| R11-16 | `GET /api/v1/otra`, `GET /`, `GET /api/v2/pedidos/1`, `POST /api/v1/otra` (4 casos) | `404 RUTA_INEXISTENTE` |
| R11-17 | entradas hostiles (cantidad texto, producto `None`, talle número) | siempre `422` o `400`, **nunca `500`** |
| R11-18 | POST con email `" Ana@Mail.COM "` y luego GET | email guardado normalizado |
| R11-19 | todos los errores | mismo formato `{"error":{"code","message"}}` |

*No especificado (no se afirma resultado, solo "no 500"): `GET /api/v1/pedidos/abc`, `fecha` no-string, método no soportado (`PUT`/`DELETE`), orden entre un 400 y un 422 cuando coinciden.*

---

## Supuestos
- Ítem con clave faltante → se trata como valor inválido de esa clave (cumple "nunca otra excepción").
- `calcular_descuento` y `calcular_envio` se prueban directo para los límites que el catálogo no permite alcanzar (20000.00 y 60000.00 exactos).
- La fecha "hoy" se simula con un reloj falso en los tests de R6-20.