import argparse
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUFFER_SIZE = 1024

# Estado compartido en RAM
registro_lock = threading.Lock()
nodos_registrados = []          # lista de {"ip": str, "puerto": int}
tiempo_inicio = time.time()


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Nodo D: registro de contactos para nodos C, con health check HTTP."
    )
    parser.add_argument("--host", default="0.0.0.0", help="IP para escuchar registros (default: 0.0.0.0)")
    parser.add_argument("--puerto", type=int, required=True, help="Puerto TCP para registro de nodos C")
    parser.add_argument("--http-puerto", type=int, default=None,
                         help="Puerto HTTP para /health (default: puerto + 1)")
    return parser.parse_args()


def enviar_json(sock, datos):
    mensaje = json.dumps(datos) + "\n"
    sock.sendall(mensaje.encode())


def recibir_json(sock, buffer):
    while b"\n" not in buffer:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            return None, buffer
        buffer += chunk
    linea, _, resto = buffer.partition(b"\n")
    return json.loads(linea.decode()), resto


def atender_registro(conn, addr):
    with conn:
        buffer = bytearray()
        try:
            mensaje, buffer = recibir_json(conn, buffer)
            if mensaje is None:
                print(f"[D] {addr} cerró la conexión sin registrarse")
                return

            if mensaje.get("tipo") != "registro":
                print(f"[D] Mensaje inesperado de {addr}: {mensaje}")
                return

            nuevo_nodo = {"ip": mensaje["ip"], "puerto": mensaje["puerto"]}

            with registro_lock:
                # Foto de los nodos ya existentes ANTES de agregar al nuevo,
                # para que el nuevo nodo sepa a quién conectarse.
                peers_actuales = list(nodos_registrados)
                nodos_registrados.append(nuevo_nodo)

            print(f"[D] Nodo C registrado: {nuevo_nodo} (desde {addr}). "
                  f"Total registrados: {len(nodos_registrados)}")

            respuesta = {"tipo": "peers", "peers": peers_actuales}
            enviar_json(conn, respuesta)

        except (json.JSONDecodeError, KeyError, ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[D] Error atendiendo registro de {addr}: {e}")


def servidor_registro(host, puerto):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen()
    print(f"[D] Escuchando registros de nodos C en {host}:{puerto}...")

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=atender_registro, args=(conn, addr), daemon=True).start()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        with registro_lock:
            cantidad = len(nodos_registrados)

        estado = {
            "nodos_registrados": cantidad,
            "uptime_segundos": round(time.time() - tiempo_inicio, 2),
            "estado": "ok",
        }
        cuerpo = json.dumps(estado).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, format, *args):
        # Silencia el log por defecto de BaseHTTPRequestHandler
        print(f"[D-HTTP] {self.address_string()} - {format % args}")


def servidor_http(host, puerto):
    server = ThreadingHTTPServer((host, puerto), HealthHandler)
    print(f"[D] Endpoint /health disponible en http://{host}:{puerto}/health")
    server.serve_forever()


def main():
    args = parsear_argumentos()
    http_puerto = args.http_puerto if args.http_puerto is not None else args.puerto + 1

    threading.Thread(target=servidor_http, args=(args.host, http_puerto), daemon=True).start()

    try:
        servidor_registro(args.host, args.puerto)
    except KeyboardInterrupt:
        print("\nNodo D detenido manualmente.")


if __name__ == "__main__":
    main()
