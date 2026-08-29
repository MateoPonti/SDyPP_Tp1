import argparse
import json
import socket
import threading
import time
from datetime import datetime, timedelta
import sched
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUFFER_SIZE = 1024
ARCHIVO_INSCRIPCIONES = "inscripciones.txt"

# Estado compartido en RAM
registro_lock = threading.Lock()
nodos_registrados = []          # lista de {"ip": str, "puerto": int} -- ventana ACTUAL
nodos_inscriptos = []           # lista de {"ip": str, "puerto": int} -- ventana SIGUIENTE
proxima_ventana_ts = None       # timestamp (epoch) en que la ventana actual de nodos_inscriptos se activa
tiempo_inicio = time.time()
scheduler = sched.scheduler(time.time, time.sleep)

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
                print(f"[D] {addr} cerró la conexión sin enviar nada")
                return

            tipo = mensaje.get("tipo")

            if tipo == "registro":
                nuevo_nodo = {"ip": mensaje["ip"], "puerto": mensaje["puerto"]}

                with registro_lock:
                    # Foto de la ventana ACTUAL (antes de tocar nodos_inscriptos),
                    # para que el nuevo nodo sepa quién está activo ahora mismo.
                    peers_actuales = list(nodos_registrados)
                    nodos_inscriptos.append(nuevo_nodo)
                    ventana_asignada = proxima_ventana_ts

                persistir_inscripcion(nuevo_nodo, ventana_asignada)

                print(f"[D] Nodo C registrado: {nuevo_nodo} (desde {addr}) para la ventana "
                      f"{datetime.fromtimestamp(ventana_asignada).strftime('%H:%M:%S')}. "
                      f"Activos en la ventana actual: {len(peers_actuales)}")

                respuesta = {
                    "tipo": "peers",
                    "peers": peers_actuales,
                    "ventana_asignada": ventana_asignada,
                }
                enviar_json(conn, respuesta)

            elif tipo == "consulta":
                with registro_lock:
                    peers_actuales = list(nodos_registrados)

                enviar_json(conn, {"tipo": "peers", "peers": peers_actuales})

            else:
                print(f"[D] Mensaje desconocido de {addr}: {mensaje}")

        except (json.JSONDecodeError, KeyError, ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[D] Error atendiendo a {addr}: {e}")


def servidor_registro(host, puerto):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen()
    print(f"[D] Escuchando registros de nodos C en {host}:{puerto}...")

    
    global proxima_ventana_ts
    now = datetime.now()
    next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
    target = next_minute.timestamp()
    proxima_ventana_ts = target
    scheduler.enterabs(target, 1, swap, argument=(target,))
    threading.Thread(target=scheduler.run, daemon=True).start()

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=atender_registro, args=(conn, addr), daemon=True).start()


def swap(time_target):
    """Cierra la ventana actual: los inscriptos pasan a ser los activos,
    y se abre una nueva ventana de inscripción para dentro de 60s."""
    global proxima_ventana_ts
    siguiente = time_target + 60

    with registro_lock:
        cerrados = list(nodos_inscriptos)
        nodos_registrados.clear()
        nodos_registrados.extend(cerrados)
        nodos_inscriptos.clear()
        proxima_ventana_ts = siguiente

    persistir_evento_ventana(time_target, cerrados)
    print(f"[D] Ventana {datetime.fromtimestamp(time_target).strftime('%H:%M:%S')} activada "
          f"con {len(cerrados)} nodo(s): {cerrados}")

    scheduler.enterabs(siguiente, 1, swap, argument=(siguiente,))


def persistir_inscripcion(nodo: dict, ventana_asignada: float):
    """Escribe la inscripción como una línea JSON (JSON Lines / NDJSON)."""
    registro = {
        "tipo": "inscripcion",
        "ip": nodo["ip"],
        "puerto": nodo["puerto"],
        "hora_registro": datetime.now().isoformat(timespec="seconds"),
        "ventana_asignada": datetime.fromtimestamp(ventana_asignada).isoformat(timespec="seconds"),
    }
    with open(ARCHIVO_INSCRIPCIONES, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro) + "\n")


def persistir_evento_ventana(inicio_ventana: float, miembros: list):
    """Registra en el archivo la apertura de una nueva ventana y quiénes quedaron activos."""
    evento = {
        "tipo": "apertura_ventana",
        "inicio_ventana": datetime.fromtimestamp(inicio_ventana).isoformat(timespec="seconds"),
        "miembros": miembros,
    }
    with open(ARCHIVO_INSCRIPCIONES, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento) + "\n")

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
