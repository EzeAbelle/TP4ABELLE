import sqlite3
from decimal import Decimal

from checkout import CATALOGO, calcular_total

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    email     TEXT NOT NULL,
    zona      TEXT NOT NULL,
    cupon     TEXT,
    subtotal  REAL NOT NULL DEFAULT 0,
    descuento REAL NOT NULL DEFAULT 0,
    envio     REAL NOT NULL DEFAULT 0,
    total     REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos(id),
    producto        TEXT NOT NULL,
    talle           TEXT NOT NULL,
    cantidad        INTEGER NOT NULL,
    precio_unitario REAL NOT NULL
);
"""


def conectar(ruta):
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    return con


def crear_esquema(con):
    con.executescript(ESQUEMA)


def guardar_pedido(con, email, carrito, zona, cupon=None, fecha=None):
    cursor = con.execute(
        "INSERT INTO pedidos (email, zona, cupon) VALUES (?, ?, ?)",
        (
            email.strip().lower(),
            zona.strip().upper(),
            cupon.strip().upper() if cupon and cupon.strip() else None,
        ),
    )
    pedido_id = cursor.lastrowid
    con.commit()

    resultado = calcular_total(carrito, zona, cupon, fecha)

    con.execute(
        "UPDATE pedidos SET subtotal = ?, descuento = ?, envio = ?, total = ? WHERE id = ?",
        (
            float(resultado["subtotal"]),
            float(resultado["descuento"]),
            float(resultado["envio"]),
            float(resultado["total"]),
            pedido_id,
        ),
    )

    for item in carrito:
        precio = item.get("precio", CATALOGO[item["producto"]])
        con.execute(
            "INSERT INTO items (pedido_id, producto, talle, cantidad, precio_unitario)"
            " VALUES (?, ?, ?, ?, ?)",
            (pedido_id, item["producto"], item["talle"].strip().upper(), item["cantidad"], float(precio)),
        )

    return pedido_id


def obtener_pedido(con, pedido_id):
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if fila is None:
        return None

    items = con.execute(
        "SELECT * FROM items WHERE pedido_id = ? ORDER BY id", (pedido_id,)
    ).fetchall()

    return {
        "id": fila["id"],
        "email": fila["email"],
        "zona": fila["zona"],
        "cupon": fila["cupon"],
        "subtotal": Decimal(fila["subtotal"]),
        "descuento": Decimal(fila["descuento"]),
        "envio": Decimal(fila["envio"]),
        "total": Decimal(fila["total"]),
        "items": [
            {
                "producto": i["producto"],
                "talle": i["talle"],
                "cantidad": i["cantidad"],
                "precio_unitario": Decimal(i["precio_unitario"]),
            }
            for i in items
        ],
    }


def pedidos_de(con, email):
    email = email.strip().lower()
    filas = con.execute(
        f"SELECT id FROM pedidos WHERE email = '{email}' ORDER BY id DESC"
    ).fetchall()
    return [obtener_pedido(con, f["id"]) for f in filas]
