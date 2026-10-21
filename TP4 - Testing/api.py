import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pedidos

RUTA_PEDIDOS = "/api/v1/pedidos"
RUTA_PEDIDO = re.compile(r"/api/v1/pedidos/(\d+)")


class _Manejador(BaseHTTPRequestHandler):
    ruta_db = None

    def log_message(self, *args):
        pass

    def _responder(self, status, cuerpo):
        datos = json.dumps(cuerpo, default=float).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_POST(self):
        if self.path != RUTA_PEDIDOS:
            self._responder(404, {"error": {"code": "RUTA_INEXISTENTE", "message": "La ruta no existe"}})
            return

        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(largo))

            con = pedidos.conectar(self.ruta_db)
            pedido_id = pedidos.guardar_pedido(
                con,
                datos["email"],
                datos["carrito"],
                datos["zona"],
                datos.get("cupon"),
                datos.get("fecha"),
            )
            pedido = pedidos.obtener_pedido(con, pedido_id)
            con.close()

            self._responder(201, {
                "id": pedido_id,
                "subtotal": pedido["subtotal"],
                "descuento": pedido["descuento"],
                "envio": pedido["envio"],
                "total": pedido["total"],
            })
        except Exception as e:
            self._responder(500, {"error": str(e)})

    def do_GET(self):
        coincide = RUTA_PEDIDO.fullmatch(self.path)
        if not coincide:
            self._responder(404, {"error": {"code": "RUTA_INEXISTENTE", "message": "La ruta no existe"}})
            return

        try:
            con = pedidos.conectar(self.ruta_db)
            pedido = pedidos.obtener_pedido(con, int(coincide.group(1)))
            con.close()
            self._responder(200, pedido)
        except Exception as e:
            self._responder(500, {"error": str(e)})


def crear_servidor(ruta_db, puerto=0):
    con = pedidos.conectar(ruta_db)
    pedidos.crear_esquema(con)
    con.close()
    manejador = type("Manejador", (_Manejador,), {"ruta_db": ruta_db})
    return ThreadingHTTPServer(("127.0.0.1", puerto), manejador)


if __name__ == "__main__":
    servidor = crear_servidor("tienda.db", 8000)
    print("Escuchando en http://127.0.0.1:8000")
    servidor.serve_forever()
