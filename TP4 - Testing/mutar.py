import argparse
import ast
import concurrent.futures
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

TIMEOUT_SEGUNDOS = 30


def _pytest_disponible():
    try:
        import pytest
        return True
    except ImportError:
        return False


def correr_suite(directorio, archivo_tests):
    if _pytest_disponible():
        return _correr_con_pytest(directorio, archivo_tests)
    return _correr_con_runner_interno(directorio, archivo_tests)


def _correr_con_pytest(directorio, archivo_tests):
    xml = os.path.join(directorio, "_resultado.xml")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           f"--junitxml={xml}", os.path.basename(archivo_tests)]
    try:
        proc = subprocess.run(cmd, cwd=directorio, capture_output=True,
                              text=True, timeout=TIMEOUT_SEGUNDOS)
    except subprocess.TimeoutExpired:
        return False, [], "timeout"

    resultados = []
    if os.path.exists(xml):
        for caso in ET.parse(xml).getroot().iter("testcase"):
            if caso.find("skipped") is not None:
                continue
            fallo = caso.find("failure") if caso.find("failure") is not None else caso.find("error")
            resultados.append({
                "nombre": caso.get("name"),
                "paso": fallo is None,
                "detalle": (fallo.get("message") or "")[:200] if fallo is not None else "",
            })
    error = None
    if proc.returncode not in (0, 1) or not resultados:
        error = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or ["error al correr la suite"]
        error = error[0]
    todo_paso = proc.returncode == 0 and bool(resultados)
    return todo_paso, resultados, error


def _correr_con_runner_interno(directorio, archivo_tests):
    salida = os.path.join(directorio, "_resultado.json")
    cmd = [sys.executable, os.path.abspath(__file__), "--_interno",
           directorio, os.path.basename(archivo_tests), salida]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS)
    except subprocess.TimeoutExpired:
        return False, [], "timeout"
    if not os.path.exists(salida):
        ultima = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or ["error al correr la suite"]
        return False, [], ultima[0]
    with open(salida, encoding="utf-8") as f:
        datos = json.load(f)
    return datos["todo_paso"], datos["resultados"], datos.get("error")


def _instalar_pytest_falso():
    import types

    falso = types.ModuleType("pytest")

    class _Raises:
        def __init__(self, tipo, match=None):
            self.tipo, self.match, self.value = tipo, match, None

        def __enter__(self):
            return self

        def __exit__(self, tipo, valor, tb):
            if tipo is None:
                raise AssertionError(f"DID NOT RAISE {self.tipo.__name__}")
            if not issubclass(tipo, self.tipo):
                return False
            self.value = valor
            if self.match and not re.search(self.match, str(valor)):
                raise AssertionError(f"'{valor}' no coincide con '{self.match}'")
            return True

    class _Mark:
        @staticmethod
        def parametrize(nombres, valores, ids=None):
            def decorador(fn):
                fn.__dict__.setdefault("_parametros", []).insert(0, (nombres, list(valores)))
                return fn
            return decorador

    def _fixture(fn=None, **_opciones):
        def marcar(f):
            f._es_fixture = True
            return f
        return marcar(fn) if callable(fn) else marcar

    falso.raises = lambda tipo, match=None: _Raises(tipo, match)
    falso.mark = _Mark()
    falso.fixture = _fixture
    sys.modules["pytest"] = falso


def _resolver_fixture(nombre, modulo, cache, finalizadores):
    import inspect
    import pathlib

    if nombre in cache:
        return cache[nombre]
    if nombre == "tmp_path":
        ruta = pathlib.Path(tempfile.mkdtemp(prefix="tmp_path_"))
        finalizadores.append(lambda: shutil.rmtree(ruta, ignore_errors=True))
        valor = ruta
    else:
        fx = getattr(modulo, nombre, None)
        if not getattr(fx, "_es_fixture", False):
            raise TypeError(f"fixture '{nombre}' no encontrada (definila en el mismo archivo)")
        kwargs = {p: _resolver_fixture(p, modulo, cache, finalizadores)
                  for p in inspect.signature(fx).parameters}
        resultado = fx(**kwargs)
        if inspect.isgenerator(resultado):
            valor = next(resultado)
            finalizadores.append(lambda g=resultado: next(g, None))
        else:
            valor = resultado
    cache[nombre] = valor
    return valor


def _expandir(fn):
    grupos = []
    for nombres, valores in fn.__dict__.get("_parametros", []):
        claves = [n.strip() for n in nombres.split(",")]
        opciones = []
        for v in valores:
            v = v if len(claves) > 1 else (v,)
            opciones.append(dict(zip(claves, v)))
        grupos.append(opciones)
    if not grupos:
        return [("", {})]
    casos = []
    for i, combo in enumerate(itertools.product(*grupos)):
        kwargs = {}
        for parte in combo:
            kwargs.update(parte)
        casos.append((f"[{i}]", kwargs))
    return casos


def _runner_interno(directorio, archivo, salida):
    import importlib.util
    import traceback

    os.chdir(directorio)
    sys.path.insert(0, directorio)
    try:
        import pytest
    except ImportError:
        _instalar_pytest_falso()

    resultado = {"todo_paso": False, "resultados": [], "error": None}
    try:
        spec = importlib.util.spec_from_file_location("_suite", os.path.join(directorio, archivo))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    except Exception as e:
        resultado["error"] = f"{type(e).__name__}: {e}"
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(resultado, f)
        sys.exit(2)

    import inspect

    for nombre, fn in list(vars(modulo).items()):
        if not (nombre.startswith("test") and callable(fn)) or getattr(fn, "_es_fixture", False):
            continue
        for sufijo, kwargs in _expandir(fn):
            finalizadores = []
            try:
                cache = {}
                for p in inspect.signature(fn).parameters:
                    if p not in kwargs:
                        kwargs[p] = _resolver_fixture(p, modulo, cache, finalizadores)
                fn(**kwargs)
                resultado["resultados"].append({"nombre": nombre + sufijo, "paso": True, "detalle": ""})
            except Exception as e:
                detalle = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                if isinstance(e, AssertionError) and not str(e):
                    detalle = "AssertionError: " + traceback.extract_tb(e.__traceback__)[-1].line
                resultado["resultados"].append({"nombre": nombre + sufijo, "paso": False, "detalle": detalle[:200]})
            finally:
                for fin in reversed(finalizadores):
                    try:
                        fin()
                    except Exception:
                        pass

    resultado["todo_paso"] = bool(resultado["resultados"]) and all(r["paso"] for r in resultado["resultados"])
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f)
    sys.exit(0 if resultado["todo_paso"] else 1)


_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
        ast.Is: ast.IsNot, ast.IsNot: ast.Is}
_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
_BOOL = {ast.And: ast.Or, ast.Or: ast.And}
_NOMBRES = {"max": "min", "min": "max"}
_SIMBOLO = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==",
            ast.NotEq: "!=", ast.In: "in", ast.NotIn: "not in", ast.Is: "is",
            ast.IsNot: "is not", ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
            ast.Div: "/", ast.And: "and", ast.Or: "or"}


def _padres(arbol):
    padres = {}
    for nodo in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(nodo):
            padres[hijo] = nodo
    return padres


def _es_numero(nodo):
    return (isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float))
            and not isinstance(nodo.value, bool))


def _sitios(arbol):
    padres = _padres(arbol)
    sitios = []
    for i, nodo in enumerate(ast.walk(arbol)):
        if isinstance(nodo, ast.Compare):
            for j, op in enumerate(nodo.ops):
                if type(op) in _CMP:
                    sitios.append((i, j, f"'{_SIMBOLO[type(op)]}' → '{_SIMBOLO[_CMP[type(op)]]}'"))
        elif isinstance(nodo, (ast.BinOp, ast.AugAssign)) and type(nodo.op) in _BIN:
            sitios.append((i, 0, f"'{_SIMBOLO[type(nodo.op)]}' → '{_SIMBOLO[_BIN[type(nodo.op)]]}'"))
        elif isinstance(nodo, ast.BoolOp) and type(nodo.op) in _BOOL:
            sitios.append((i, 0, f"'{_SIMBOLO[type(nodo.op)]}' → '{_SIMBOLO[_BOOL[type(nodo.op)]]}'"))
        elif isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, ast.Not):
            sitios.append((i, 0, "se elimina el 'not'"))
        elif isinstance(nodo, ast.Name) and nodo.id in _NOMBRES and isinstance(padres.get(nodo), ast.Call):
            sitios.append((i, 0, f"'{nodo.id}' → '{_NOMBRES[nodo.id]}'"))
        elif _es_numero(nodo):
            padre = padres.get(nodo)
            if isinstance(padre, (ast.Compare, ast.BinOp)) or (
                isinstance(padre, ast.Assign) and padres.get(padre) is arbol
            ):
                sitios.append((i, 0, f"{nodo.value!r} → {nodo.value + 1!r}"))
    return sitios


def _aplicar(fuente, sitio):
    arbol = ast.parse(fuente)
    padres = _padres(arbol)
    indice, sub, _ = sitio
    nodo = list(ast.walk(arbol))[indice]

    if isinstance(nodo, ast.Compare):
        nodo.ops[sub] = _CMP[type(nodo.ops[sub])]()
    elif isinstance(nodo, (ast.BinOp, ast.AugAssign)):
        nodo.op = _BIN[type(nodo.op)]()
    elif isinstance(nodo, ast.BoolOp):
        nodo.op = _BOOL[type(nodo.op)]()
    elif isinstance(nodo, ast.UnaryOp):
        padre = padres[nodo]
        for campo, valor in ast.iter_fields(padre):
            if valor is nodo:
                setattr(padre, campo, nodo.operand)
            elif isinstance(valor, list):
                setattr(padre, campo, [nodo.operand if v is nodo else v for v in valor])
    elif isinstance(nodo, ast.Name):
        nodo.id = _NOMBRES[nodo.id]
    elif _es_numero(nodo):
        nodo.value = nodo.value + 1

    linea = getattr(nodo, "lineno", 0)
    return ast.unparse(ast.fix_missing_locations(arbol)), linea


def _probar_mutante(args):
    fuente, sitio, modulo, archivo_tests = args
    codigo, linea = _aplicar(fuente, sitio)
    tmp = tempfile.mkdtemp(prefix="mutante_")
    try:
        with open(os.path.join(tmp, os.path.basename(modulo)), "w", encoding="utf-8") as f:
            f.write(codigo)
        shutil.copy(archivo_tests, tmp)
        todo_paso, _, _ = correr_suite(tmp, os.path.join(tmp, os.path.basename(archivo_tests)))
        return {"linea": linea, "cambio": sitio[2], "sobrevivio": todo_paso}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mutar(modulo, archivo_tests, procesos=None):
    modulo, archivo_tests = os.path.abspath(modulo), os.path.abspath(archivo_tests)
    with open(modulo, encoding="utf-8") as f:
        fuente = f.read()
    lineas = fuente.splitlines()

    tmp = tempfile.mkdtemp(prefix="base_")
    try:
        shutil.copy(modulo, tmp)
        shutil.copy(archivo_tests, tmp)
        verde, resultados, error = correr_suite(tmp, os.path.join(tmp, os.path.basename(archivo_tests)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not verde:
        rojos = [r["nombre"] for r in resultados if not r["paso"]]
        return {"ok": False, "motivo": error or f"tests en rojo: {', '.join(rojos[:5])}"}

    sitios = _sitios(ast.parse(fuente))
    tareas = [(fuente, s, modulo, archivo_tests) for s in sitios]
    with concurrent.futures.ThreadPoolExecutor(max_workers=procesos or os.cpu_count() or 2) as pool:
        resultados = list(pool.map(_probar_mutante, tareas))

    sobrevivientes = [r for r in resultados if r["sobrevivio"]]
    for r in sobrevivientes:
        r["codigo"] = lineas[r["linea"] - 1].strip() if 0 < r["linea"] <= len(lineas) else ""
    total = len(resultados)
    muertos = total - len(sobrevivientes)
    return {
        "ok": True,
        "total": total,
        "muertos": muertos,
        "puntaje": round(100 * muertos / total, 1) if total else 0.0,
        "sobrevivientes": sorted(sobrevivientes, key=lambda r: r["linea"]),
    }


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--_interno":
        _runner_interno(*sys.argv[2:5])

    p = argparse.ArgumentParser(description="Mutation testing para el TP 4.")
    p.add_argument("--modulo", default="checkout.py")
    p.add_argument("--tests", default="test_checkout.py")
    p.add_argument("--json", help="guardar el resultado en un archivo JSON")
    args = p.parse_args()

    for ruta in (args.modulo, args.tests):
        if not os.path.exists(ruta):
            sys.exit(f"No encuentro {ruta}")

    motor = "pytest" if _pytest_disponible() else "runner interno"
    print(f"Mutando {args.modulo} contra {args.tests}  (motor: {motor})\n")
    r = mutar(args.modulo, args.tests)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)

    if not r["ok"]:
        print("✗ No se puede mutar: tu suite tiene que estar en verde primero.")
        print(f"  {r['motivo']}")
        sys.exit(1)

    print(f"Mutantes generados : {r['total']}")
    print(f"Muertos            : {r['muertos']}")
    print(f"Sobrevivientes     : {len(r['sobrevivientes'])}")
    print(f"Puntaje de mutación: {r['puntaje']}%\n")
    if r["sobrevivientes"]:
        print("Sobrevivientes — había un error acá y ningún test lo detectó:\n")
        for s in r["sobrevivientes"]:
            print(f"  línea {s['linea']:>3}  {s['cambio']:<22}  {s['codigo'][:60]}")
        print("\nAlgunos pueden ser equivalentes: el cambio no altera el comportamiento.")


if __name__ == "__main__":
    main()
