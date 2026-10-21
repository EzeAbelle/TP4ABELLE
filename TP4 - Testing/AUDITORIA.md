# AUDITORIA.md — Parte 2

## Sección 1 — Los tests de la IA (`test_checkout_ia.py`)

### 1. Clasificación de los 8 tests

| Test | Clasificación | Por qué |
|---|---|---|
| `test_subtotal` | Tautológico | Compara contra `CATALOGO["buzo"] * 2`, que es el mismo dato y la misma cuenta que usa el código: si el catálogo está mal, el test también. |
| `test_total_funciona` | Inútil | Solo verifica `is not None`; un diccionario con cualquier valor lo cumple. |
| `test_total_positivo` | Débil | `> 0` pasa con cualquier total mal calculado mientras sea positivo. |
| `test_cupon_egresados` | Tautológico | El esperado es `100000 * 0.15`, la misma fórmula en `float` del código; además usa un monto redondo sin medio centavo y una fecha lejos del vencimiento. |
| `test_envio_caba` | Útil | Compara contra un valor literal de la spec (2500) y no depende del código; es acotado: solo CABA, lejos del umbral de envío gratis. |
| `test_descuento_por_cantidad` | Débil | Valor literal correcto, pero con 6 prendas: no toca el límite de 5, así que pasa aunque el código use `> 5`. |
| `test_talle_valido` | Inútil | No tiene ningún `assert`; solo comprueba que no explote. |
| `test_no_explota_con_varios_productos` | Inútil | Todo está dentro de `try/except Exception: pass`, así que no puede fallar nunca. |

### 2. Puntaje de mutación

`python mutar.py --tests test_checkout_ia.py` → **58.6 %** (29 mutantes: 17 muertos, 12 sobrevivientes).

Sobrevivientes: líneas 40 (`<`→`<=` y `10`→`11`), 60 (`>`→`>=`), 72 (`<`→`<=`), 76 (`==`→`!=`), 77 (`<`→`<=`), 82 (`+`→`-`), 96 (`>=`→`>` y `60000`→`60001`), 107 (`+`→`-`), 111 (`+`→`-` y `-`→`+`).

### 3. ¿Por qué cubre casi el 80 % y no detecta ninguna falla?

Cobertura medida: 77 % de las líneas (48 de 62) y 73 % con ramas. La cobertura solo dice qué líneas se **ejecutaron**, no si alguien **comprobó** el resultado:

- Dos tests (`test_total_funciona`, `test_no_explota_con_varios_productos`) recorren mucho código sin verificar nada: el primero solo mira `is not None` y el segundo no puede fallar.
- Los dos tests que calculan el esperado (`test_subtotal`, `test_cupon_egresados`) usan el mismo catálogo y la misma fórmula `float` que el código, así que repiten sus errores en vez de detectarlos.
- Todos los valores están lejos de los límites (6 prendas en vez de 5, fecha de octubre en vez del 30/11, subtotales de 10.000 y 100.000), así que los operadores `>`, `<`, `>=` pasan igual al cambiarlos (mutantes de las líneas 40, 60, 72, 96).
- Ningún test espera un `CheckoutError` ni una excepción: los caminos de error quedan sin probar o sin verificar.
- Ningún test mira el tipo `Decimal`, la mutación del carrito, el redondeo ni el envío con descuento.
- Resultado: el código pasa 8 de 8 y tiene más de 20 fallas; la suite mide que "corre", no que "cumple la especificación".

---

## Sección 2 — Hallazgos

Herramientas con las que se encontró cada falla:
- **Lectura**: leer el código y compararlo con la spec.
- **Ruff**: `ruff check checkout.py`.
- **Mutante Lxx**: mutante sobreviviente de la línea indicada, que revela un límite sin probar.
- **Ejecución**: script manual llamando a las funciones o a la API con datos de la spec.

### `checkout.py`

| ID | Archivo:línea | Falla (evidencia) | Categoría | Regla | Cómo | Sev. |
|---|---|---|---|---|---|---|
| C01 | checkout.py:23 | Existe un cupón `DEBUG100` (100 %) que la spec no define; `calcular_descuento(30000,1,"DEBUG100",...)` devuelve `30000.0`. | Seguridad | R6 (solo existen dos cupones) | Lectura + Ejecución | Alta |
| C02 | checkout.py:49 | `item.get("precio", CATALOGO[...])` usa el precio que manda el cliente: con `precio=1` el subtotal da `1`. | Seguridad | R1 | Lectura + Ejecución | Alta |
| C03 | checkout.py:34-41, 50-51 | `validar_item` no valida el producto y el `except: continue` se traga el error: un producto inexistente se ignora y el subtotal da `0` en vez de `PRODUCTO_INEXISTENTE`. | Manejo de errores | R1, orden de validación §3 | Ruff E722 + Ejecución | Alta |
| C04 | checkout.py:13-15, 21-23, 26-31, 45, 54, 61, 111, 117 | Todo el dinero se maneja en `float`/`int` (catálogo, porcentajes, subtotal, total); los resultados no son `Decimal`. | Numéricos | R7 | Lectura + Ejecución (`calcular_total` devuelve `float`) | Alta |
| C05 | checkout.py:54, 84, 117 | `round()` sobre `float` no hace redondeo comercial: 15 % de 11999.50 da `1799.92` y la spec pide `1799.93`. | Numéricos | R7 | Ejecución | Alta |
| C06 | checkout.py:60 | `cantidad_prendas > 5`: con exactamente 5 prendas no hay descuento (debe ser `>= 5`). | Lógica y límites | R5 | Mutante L60 + Ejecución | Alta |
| C07 | checkout.py:72 | `fecha < vence`: el 30/11/2026 da `CUPON_VENCIDO` (debe ser válido, "inclusive"). | Fechas | R6 | Mutante L72 + Ejecución | Alta |
| C08 | checkout.py:61, 74, 82 | El descuento por cantidad y el cupón se **suman** (`+=`): 6 prendas + `EGRESADOS2026` sobre 100000 da `25000` en vez de `15000`. Debe aplicarse el mayor. | Lógica y límites | R6, R5 | Lectura + Ejecución | Alta |
| C09 | checkout.py:93 | `ENVIOS.keys().join(', ')` no existe: una zona inválida lanza `AttributeError` en vez de `ZONA_INVALIDA`. | Alucinación | R8, contrato §1 ("nunca otro tipo de excepción") | Ejecución | Alta |
| C10 | checkout.py:35 | `item["talle"] = item["talle"].upper()` modifica el carrito recibido (con `"m"` queda `"M"`). | Efectos laterales | R4 | Lectura + Ejecución | Alta |
| C11 | checkout.py:72 (llamada desde pedidos.py:50) | `fecha=None` no se trata como "hoy": `calcular_descuento(..., "EGRESADOS2026", None)` lanza `TypeError`. `pedidos.py` y `api.py` pasan `None` cuando no hay fecha. | Fechas | R6 (sin fecha se usa hoy), firma §1 | Ejecución | Alta |
| C12 | checkout.py:57, 102 | `fecha=date.today()` como valor por defecto se evalúa **al importar el módulo**, no en cada llamada (en la prueba quedó fija con la fecha del import). | Fechas | R6 | Ruff B008 | Media |
| C13 | checkout.py:45-54 | No existe el control de carrito vacío: `calcular_subtotal([])` devuelve `0` en vez de lanzar `CARRITO_VACIO`. | Lógica y límites | R4, orden §3 | Ejecución | Media |
| C14 | checkout.py:40 | `1 <= cantidad < 10` rechaza la cantidad 10 (debe ser válida: "1 a 10 inclusive"). | Lógica y límites | R3 | Mutante L40 + Ejecución | Media |
| C15 | checkout.py:110 | `calcular_envio(subtotal, zona)` usa el subtotal **sin descuento**: 2 buzos + 1 remera con `EGRESADOS2026` da envío `0` (el subtotal con descuento es 52699.40, debe cobrar 4000 en GBA). | Lógica y límites | R8 | Ejecución | Media |
| C16 | checkout.py:35 | No se hace `strip()` del talle: `" M "` da `TALLE_INVALIDO`. | Strings | R2 | Ejecución | Media |
| C17 | checkout.py:63 | `cupon != None`: `""` y `"   "` se tratan como cupón y dan `CUPON_INVALIDO` (deben equivaler a "sin cupón"). | Strings | R6 | Ruff E711 + Ejecución | Media |
| C18 | checkout.py:64 | Se hace `strip()` pero no `upper()`: `"bienvenida"` da `CUPON_INVALIDO`. | Strings | R6 | Ejecución | Media |
| C19 | checkout.py:35, 40, 64, 88 | Sin validación de tipos: `talle=None` lanza `AttributeError`, `cantidad="3"` lanza `TypeError`, falta de clave lanza `KeyError`, `cantidad=1.5` pasa como válida. | Tipos | R3, R2, contrato §1 | Ejecución | Media |
| C20 | checkout.py:84 | No hay tope: el descuento puede superar el subtotal (con `DEBUG100` + cantidad llega al 110 %). | Lógica y límites | R6 | Lectura | Baja |
| C21 | checkout.py:1 | `import json` sin usar. | Code smell | — | Ruff F401 | Baja |

### `pedidos.py`

| ID | Archivo:línea | Falla (evidencia) | Categoría | Regla | Cómo | Sev. |
|---|---|---|---|---|---|---|
| P01 | pedidos.py:107 | La consulta se arma con un f-string: `pedidos_de(con,"' OR '1'='1")` devuelve los pedidos de otros; un email con apóstrofe (`o'brien@x.com`) lanza `OperationalError`. | Seguridad | R10 | Lectura + Ejecución | Alta |
| P02 | pedidos.py:39-50 | Inserta el pedido y hace `commit()` **antes** de llamar a `calcular_total`: si lanza `CheckoutError`, el pedido queda guardado (tras un cupón inválido había 1 fila). | Efectos laterales | R10 | Lectura + Ejecución | Alta |
| P03 | pedidos.py:63-71 | No hay `commit()` al final: el `UPDATE` de importes y los ítems se pierden al cerrar la conexión; otra conexión ve 0 ítems. Por la API, el `GET` posterior devolvió montos `0.0` e `items: []`. | Efectos laterales | R10 | Ejecución | Alta |
| P04 | pedidos.py:12-15, 23, 55-58, 88-97 | Montos en columnas `REAL`, guardados con `float()` y leídos con `Decimal(float)`: `24999.90` vuelve como `24999.9000000000014551915...`. | Numéricos | R10, R7 | Ejecución | Alta |
| P05 | pedidos.py:64 | `precio_unitario` sale de `item.get("precio", ...)`, el precio enviado por el cliente. | Seguridad | R10, R1 | Lectura + Ejecución | Alta |
| P06 | pedidos.py:109 | `pedidos_de` hace una consulta por cada pedido (N+1). | Code smell | — | Lectura | Baja |

### `api.py`

| ID | Archivo:línea | Falla (evidencia) | Categoría | Regla | Cómo | Sev. |
|---|---|---|---|---|---|---|
| A01 | api.py:53-54 | Todo error (incluido `CheckoutError`) cae en `except Exception` y responde **500**: un talle inválido devuelve 500 en vez de 422 `TALLE_INVALIDO`; el formato del error tampoco es el de la spec. | Manejo de errores | R11 | Ejecución | Alta |
| A02 | api.py:41 | La `fecha` llega como texto y se pasa sin convertir a `date`: con cupón da `TypeError` → 500 (`'<' not supported between 'str' and 'date'`); sin cupón acepta cualquier texto (`"30/11"` dio 201) en vez de `FECHA_INVALIDA` 400. | Tipos | R11 | Ejecución | Alta |
| A03 | api.py:18 | `json.dumps(..., default=float)`: los `Decimal` viajan como número JSON (`11999.5`) y no como texto (`"11999.50"`). | Numéricos | R11 | Ejecución | Alta |
| A04 | api.py:32 | JSON inválido da 500 en vez de 400 `JSON_INVALIDO`. | Manejo de errores | R11 | Ejecución | Media |
| A05 | api.py:36-39 | Falta de `email`/`zona`/`carrito` o tipos incorrectos dan `KeyError`/`TypeError` → 500 en vez de 400 `DATOS_INCOMPLETOS`. | Manejo de errores | R11 | Ejecución | Media |
| A06 | api.py:64-66 | `GET` de un pedido inexistente responde `200 null` en vez de 404 `PEDIDO_INEXISTENTE`. | Lógica y límites | R11 | Ejecución | Media |
| A07 | api.py:54, 68 | `str(e)` de la excepción interna se devuelve al cliente (filtra detalles internos como `'<' not supported ...`). | Seguridad | R11 | Ejecución | Media |
| A08 | api.py:34-44 | Si hay una excepción, `con.close()` nunca se ejecuta: la conexión queda abierta. | Efectos laterales | — | Lectura | Baja |

### Tabla final (de la más grave a la menos grave)

| # | ID | Falla | Sev. |
|---|---|---|---|
| 1 | P01 | Inyección SQL en `pedidos_de` | Alta |
| 2 | C01 | Cupón oculto `DEBUG100` (100 %) | Alta |
| 3 | C02 | Precio enviado por el cliente en checkout | Alta |
| 4 | P05 | Precio enviado por el cliente guardado en ítems | Alta |
| 5 | P03 | Falta `commit` final: pedido sin ítems ni importes | Alta |
| 6 | P02 | `commit` antes de calcular: pedidos huérfanos | Alta |
| 7 | P04 | Importes en `REAL`/`float` y `Decimal(float)` | Alta |
| 8 | C04 | Dinero en `float` en todo `checkout` | Alta |
| 9 | C05 | Redondeo no comercial | Alta |
| 10 | A01 | `CheckoutError` devuelve 500 | Alta |
| 11 | A02 | Fecha sin parsear ni validar | Alta |
| 12 | C11 | `fecha=None` lanza `TypeError` | Alta |
| 13 | C03 | Producto inexistente ignorado (`except: continue`) | Alta |
| 14 | C08 | Descuento por cantidad y cupón se suman | Alta |
| 15 | C06 | Descuento por cantidad desde 6 y no desde 5 | Alta |
| 16 | C07 | `EGRESADOS2026` vence un día antes | Alta |
| 17 | C09 | `.keys().join` (zona inválida → `AttributeError`) | Alta |
| 18 | C10 | `validar_item` modifica el carrito | Alta |
| 19 | A03 | Montos como número JSON | Alta |
| 20 | C13 | Carrito vacío sin `CARRITO_VACIO` | Media |
| 21 | C15 | Envío gratis calculado sin el descuento | Media |
| 22 | C14 | Cantidad 10 rechazada | Media |
| 23 | C16 | Talle sin `strip()` | Media |
| 24 | C17 | Cupón vacío o con espacios da `CUPON_INVALIDO` | Media |
| 25 | C18 | Cupón sensible a minúsculas | Media |
| 26 | C19 | Sin validación de tipos | Media |
| 27 | C12 | `date.today()` evaluado al importar | Media |
| 28 | A04 | JSON inválido da 500 | Media |
| 29 | A05 | Datos incompletos dan 500 | Media |
| 30 | A06 | Pedido inexistente da `200 null` | Media |
| 31 | A07 | Se filtra el texto de la excepción interna | Media |
| 32 | C20 | Sin tope de descuento ≤ subtotal | Baja |
| 33 | A08 | Conexión sin cerrar ante errores | Baja |
| 34 | P06 | Consulta N+1 en `pedidos_de` | Baja |
| 35 | C21 | `import json` sin uso | Baja |