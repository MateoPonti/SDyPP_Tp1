import argparse
import socket
import threading
import time

INTERVALO = 3
RETRY_DELAY = 3
BUFFER_SIZE = 1024


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Nodo C: actúa como cliente y servidor simultáneamente, "
                    "saludando y escuchando saludos de otro nodo C."
    )
    parser.add_argument("--host", default="0.0.0.0", help="IP propia para escuchar saludos (default: 0.0.0.0)")
    parser.add_argument("--puerto", type=int, required=True, help="Puerto propio para escuchar saludos")
    parser.add_argument("--peer-host", required=True, help="IP del otro nodo C")
    parser.add_argument("--peer-puerto", type=int, required=True, help="Puerto del otro nodo C")
    return parser.parse_args()


def atender_conexion(conn, addr):
    with conn:
        while True:
            try:
                mensaje = conn.recv(BUFFER_SIZE)
                if not mensaje:
                    print(f"[Servidor] {addr} cerró la conexión")
                    return
                print(f"[Servidor] Saludo recibido de {addr}: {mensaje.decode()}")
                respuesta = "Hola, soy C"
                conn.sendall(respuesta.encode())
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                print(f"[Servidor] Conexión con {addr} perdida ({e})")
                return


def servidor(host, puerto):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, puerto))
    server_socket.listen()
    print(f"[Servidor] Escuchando saludos en {host}:{puerto}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"[Servidor] Nodo conectado desde {addr}")
        threading.Thread(target=atender_conexion, args=(conn, addr), daemon=True).start()


def conectar(peer_host, peer_puerto):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer_host, peer_puerto))
            print(f"[Cliente] Conectado al nodo C en {peer_host}:{peer_puerto}")
            return s
        except OSError as e:
            print(f"[Cliente] No se pudo conectar a {peer_host}:{peer_puerto} ({e}). "
                  f"Reintentando en {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)


def cliente(peer_host, peer_puerto):
    client_socket = conectar(peer_host, peer_puerto)
    try:
        while True:
            try:
                mensaje = "Hola, soy C"
                client_socket.sendall(mensaje.encode())

                respuesta = client_socket.recv(BUFFER_SIZE)
                if not respuesta:
                    raise ConnectionResetError("El otro nodo cerró la conexión")

                print(f"[Cliente] Respuesta de {peer_host}:{peer_puerto}: {respuesta.decode()}")
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                print(f"[Cliente] Conexión perdida ({e}). Reconectando...")
                client_socket.close()
                client_socket = conectar(peer_host, peer_puerto)
                continue

            time.sleep(INTERVALO)
    finally:
        client_socket.close()


def main():
    args = parsear_argumentos()

    threading.Thread(target=servidor, args=(args.host, args.puerto), daemon=True).start()

    try:
        cliente(args.peer_host, args.peer_puerto)
    except KeyboardInterrupt:
        print("\nNodo C detenido manualmente.")


if __name__ == "__main__":
    main()
