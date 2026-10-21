# TP 4 — Catch the AI Bug

Individual · 3 semanas · Testing

## Entrega

Subí tu trabajo a un repositorio de git y entregá el link. El repositorio
tiene que tener estos archivos:

| Archivo | Contenido |
| --- | --- |
| `checkout.py` | Tu versión corregida |
| `test_checkout.py` | Tus tests unitarios |
| `test_integracion.py` | Tus tests de integración |
| `test_e2e.py` | Tus tests end-to-end |
| `CASOS.md` | Parte 1 |
| `AUDITORIA.md` | Parte 2 |
| `REFLEXION.md` | Parte 5 |
| `cobertura.txt` | El reporte de cobertura de la parte 3 |

## Rúbrica

| Parte | Criterio | Puntos |
| --- | --- | ---: |
| 1 | Casos de caja negra | 10 |
| 2 | Auditoría de la suite de la IA y hallazgos | 15 |
| 3 | `checkout.py` con TDD y su suite unitaria | 25 |
| 4 | Integración y E2E | 20 |
| 5 | Reflexión | 30 |
| | **Total** | **100** |

## Situación

Una IA escribió el backend de la tienda online de egresados. Son tres
módulos de Python:

- `checkout.py` calcula el total de una compra.
- `pedidos.py` guarda las compras en una base de datos.
- `api.py` recibe los pedidos por HTTP.

La IA también escribió ocho tests para `checkout.py`. Los ocho pasan, pero
entre los tres módulos hay más de veinte fallas.

## Qué recibís

| Archivo | Para qué |
| --- | --- |
| `ESPECIFICACION.md` | Describe cómo tiene que funcionar el sistema. Si el código y la especificación no coinciden, el error está en el código. |
| `checkout.py` | Lo vas a corregir. |
| `pedidos.py`, `api.py` | Les vas a escribir tests. No hace falta corregirlos. |
| `test_checkout_ia.py` | Los tests de la IA. Los vas a evaluar. |
| `test_checkout.py`, `test_integracion.py`, `test_e2e.py` | Plantillas para tus tests. |
| `mutar.py` | Herramienta para medir tu suite unitaria. |
| `ruff.toml` | Configuración del linter. |

Para preparar el entorno, desde la carpeta del TP:

```bash
pip install pytest pytest-cov ruff
git init && git add . && git commit -m "Estado inicial"
```

## Reglas

1. No cambies los nombres ni los parámetros de las funciones, las rutas de la
   API ni `CheckoutError`. Las otras partes del sistema los usan.
2. No modifiques `ESPECIFICACION.md`.
3. Tus tests tienen que comprobar lo que dice la especificación, no lo que
   hace el código.
4. Las fixtures van en el mismo archivo de tests.

## Cómo funciona el sistema

Un pedido pasa por los tres módulos:

1. El frontend manda el pedido a `api.py` por HTTP.
2. `api.py` se lo pasa a `pedidos.py`.
3. `pedidos.py` le pide el total a `checkout.py` y guarda el pedido en la base
   de datos.

La base de datos es SQLite, que **ya viene integrada en Python**. No hay que
instalar nada ni levantar un servidor de base de datos: toda la base es un
solo archivo, `tienda.db`, que se crea automáticamente la primera vez que
arranca la API. El único servidor que se levanta es el de `api.py`.

Para probar el sistema a mano (Esto no es necesario, es solo si quieren probar como funciona):

**1. Levantá la API.**

```bash
python api.py
```

Queda escuchando en `http://127.0.0.1:8000`. Para detenerla, Ctrl+C.

**2. Mandale pedidos desde otra terminal.**

Para consultar un pedido, abrí en el navegador
`http://127.0.0.1:8000/api/v1/pedidos/1`.

Para crear un pedido, guardá este script como `probar.py` y corrélo con
`python probar.py`:

```python
import json, urllib.request

compra = {"email": "ana@mail.com", "zona": "CABA",
          "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/pedidos",
                             data=json.dumps(compra).encode(), method="POST")
with urllib.request.urlopen(req) as r:
    print(r.status, r.read().decode())
```

**3. Mirá qué quedó guardado en la base.**

Con la consola de SQLite:

```bash
sqlite3 tienda.db
.tables
SELECT * FROM pedidos;
SELECT * FROM items;
.quit
```

Si no tenés la consola de SQLite, con Python:

```bash
python -c "import sqlite3; print(*sqlite3.connect('tienda.db').execute('SELECT * FROM pedidos'), sep='\n')"
```

También podés abrir `tienda.db` con DB Browser for SQLite o con la extensión
SQLite Viewer de VS Code.

**4. Para empezar de cero**, detené la API y borrá `tienda.db`.

**Para correr los tests no hace falta nada de esto.** Las plantillas de
integración y E2E crean una base de datos nueva y vacía para cada test, y la
plantilla E2E levanta su propio servidor. No necesitás tener `api.py` corriendo ni tocar `tienda.db`.

## Las plantillas de tests

Las tres plantillas ya traen escrito el código auxiliar que vas a necesitar y
**un test de ejemplo** cada una. Escribí tus tests debajo del ejemplo,
siguiendo el mismo estilo.

Para usar una fixture, poné su nombre como parámetro del test, como hace el
ejemplo de cada plantilla.

**`test_checkout.py`** · ejemplo: `test_cantidad_cero_es_invalida`

## Comandos útiles

| Para | Comando |
| --- | --- |
| Correr todos los tests | `pytest` |
| Correr un solo archivo | `pytest test_e2e.py` |
| Ver el nombre y el resultado de cada test | `pytest -v` |
| Generar el reporte de cobertura | `pytest test_checkout.py --cov=checkout --cov-branch --cov-report=term-missing > cobertura.txt` |
| Medir la mutación de tu suite | `python mutar.py` |
| Correr el linter | `ruff check checkout.py` |
| Levantar la API | `python api.py` |

## Consignas

### Parte 1 — Casos de caja negra · `CASOS.md`

Hacé esta parte **antes de leer el código**, trabajando solo con
`ESPECIFICACION.md`.

Para cada regla de R1 a R11, escribí:

- las particiones válidas e inválidas,
- los valores límite,
- al menos un caso por partición, con la entrada y el resultado que debería
  dar.

Hacé un commit con `CASOS.md` antes del primer cambio a `checkout.py`. El
orden se revisa en el historial de git.

### Parte 2 — Auditoría · `AUDITORIA.md`

El archivo tiene dos secciones.

**Sección 1: los tests de la IA**

1. Para cada uno de los ocho tests de `test_checkout_ia.py`, indicá si es
   útil, débil, tautológico o inútil, y explicá por qué en una línea.
2. Corré `python mutar.py --tests test_checkout_ia.py` y anotá el puntaje.
3. Esta suite cubre casi el 80% del código y no detecta ninguna falla.
   Explicá por qué.

**Sección 2: hallazgos**

1. Corré `ruff check checkout.py`.
2. Leé `checkout.py`, `pedidos.py` y `api.py`.
3. Por cada falla que encuentres, anotá:
   - archivo y línea,
   - categoría,
   - regla de la especificación que no cumple,
   - cómo la encontraste,
   - severidad: alta, media o baja.
4. Terminá con una tabla de todas las fallas, de la más grave a la menos
   grave.

Categorías: lógica y límites · numéricos · strings · efectos laterales ·
fechas · alucinación · seguridad · manejo de errores · tipos · code smell.

Las fallas de `pedidos.py` y `api.py` se documentan acá, pero no es necesario corregirlos.

### Parte 3 — `checkout.py` y sus tests unitarios · `test_checkout.py`

**Corrección con TDD.** Por cada falla que corrijas:

1. Escribí un test que la demuestre y corrélo: tiene que fallar. Hacé un
   commit.
2. Corregí `checkout.py` y volvé a correr el test: tiene que pasar. Hacé otro
   commit.

```bash
git commit -m "test(R6): <comportamiento esperado>"
git commit -m "fix(R6): <qué corregiste>"
```

No hace falta corregir todas las fallas de esta manera. Tiene que haber al menos 5 pares de
commits como estos.

**La suite.** Todos tus tests unitarios van en `test_checkout.py`. Cuando
termines, la suite tiene que:

- pasar completa contra tu `checkout.py` corregido,
- tener cobertura de ramas de 85% o más,
- tener un puntaje de mutación de 85% o más,
- seguir el patrón Arrange-Act-Assert,
- tener nombres que digan qué comportamiento prueba cada test,
- no tener asserts débiles: nada de `is not None`, `> 0` ni tests sin assert.

Para generar `cobertura.txt` y medir la mutación:

```bash
pytest test_checkout.py --cov=checkout --cov-branch --cov-report=term-missing > cobertura.txt
python mutar.py
```

### Parte 4 — Integración y end-to-end · `test_integracion.py`, `test_e2e.py`

En esta parte **no corregís** `pedidos.py` ni `api.py`: solo les escribís
tests.

**Integración.** En `test_integracion.py`, probá `pedidos.py` contra una base
SQLite real. Escribí al menos un test por cada punto de R10. No uses mocks.

**End-to-end.** En `test_e2e.py`, levantá el servidor y mandale requests
HTTP reales. Escribí al menos un test por cada endpoint y por cada error de la
tabla de R11.

**Qué esperar.** Contra el `pedidos.py` y el `api.py` que recibiste, varios de
tus tests van a fallar: esas son las fallas que estás buscando. Un test que
falla contra este código está bien. Un test que fallaría aunque el código
cumpliera la especificación está mal escrito.

### Parte 5 — Reflexión · `REFLEXION.md`

Respondé las seis preguntas. Cada una vale 5 puntos. En cada respuesta:

- escribí entre cuatro y ocho oraciones,
- usá al menos un ejemplo concreto de este TP: una falla, un test o un
  resultado que hayas obtenido.

Una respuesta correcta pero general, que se podría escribir sin haber hecho el
TP, no obtiene el puntaje completo.

1. ¿Cuántos tests unitarios, de integración y E2E tenés? ¿Por qué esa
   proporción?
2. ¿Qué falla de `pedidos.py` no podía encontrarse con un test unitario de
   `checkout.py`? ¿Por qué?
3. ¿Qué falla de `api.py` estaba en el paso de información entre dos partes
   del sistema? ¿Qué parte tendría que haberla resuelto?
4. ¿Cuál de las fallas que encontraste habría sido la más cara de descubrir
   en producción? ¿Por qué?
5. ¿Qué mide la cobertura, qué mide la mutación y qué mide la inyección de
   fallas? ¿En qué se diferencian?
6. Si una IA escribiera tus tests de integración y E2E, ¿qué le faltaría
   probar? ¿Cómo lo comprobarías?