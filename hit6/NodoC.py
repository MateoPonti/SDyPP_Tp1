import argparse
import json
import socket
import threading
import time

INTERVALO = 3
RETRY_DELAY = 3
BUFFER_SIZE = 1024


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Nodo C: se registra en un Nodo D (registro de contactos), "
                    "obtiene la lista de pares y se saluda con todos ellos (JSON sobre TCP)."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Interfaz propia para escuchar saludos (default: 0.0.0.0)")
    parser.add_argument("--d-host", required=True, help="IP del Nodo D (registro de contactos)")
    parser.add_argument("--d-puerto", type=int, required=True, help="Puerto TCP del Nodo D")
    return parser.parse_args()


# ---------- Utilidades de framing JSON sobre TCP ----------

def enviar_json(sock, datos):
    """Serializa 'datos' a JSON y lo envia delimitado por '\n'."""
    mensaje = json.dumps(datos) + "\n"
    sock.sendall(mensaje.encode())


def recibir_json(sock, buffer):
    """
    Lee del socket hasta completar una linea (mensaje JSON delimitado por '\n').
    Devuelve (datos_deserializados, buffer_actualizado) o (None, buffer) si se cerro la conexion.
    """
    while b"\n" not in buffer:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            return None, buffer
        buffer += chunk

    linea, _, resto = buffer.partition(b"\n")
    return json.loads(linea.decode()), resto


# ---------- Lado servidor: acepta saludos de otros nodos C ----------

def atender_conexion(conn, addr):
    with conn:
        buffer = bytearray()
        while True:
            try:
                mensaje, buffer = recibir_json(conn, buffer)
                if mensaje is None:
                    print(f"[Servidor] {addr} cerro la conexion")
                    return
                print(f"[Servidor] Saludo recibido de {addr}: {mensaje}")

                respuesta = {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}
                enviar_json(conn, respuesta)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                print(f"[Servidor] Conexion con {addr} perdida ({e})")
                return
            except json.JSONDecodeError as e:
                print(f"[Servidor] Mensaje JSON invalido de {addr} ({e})")
                return


def iniciar_servidor(host):
    """Crea el socket servidor en un puerto aleatorio (puerto 0) y lo deja escuchando."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, 0))
    server_socket.listen()
    puerto_asignado = server_socket.getsockname()[1]
    print(f"[Servidor] Escuchando saludos en {host}:{puerto_asignado}...")
    return server_socket, puerto_asignado


def servidor_loop(server_socket):
    while True:
        conn, addr = server_socket.accept()
        print(f"[Servidor] Nodo conectado desde {addr}")
        threading.Thread(target=atender_conexion, args=(conn, addr), daemon=True).start()


# ---------- Lado cliente: saluda a un par especifico, con reconexion ----------

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
    buffer = bytearray()
    try:
        while True:
            try:
                saludo = {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}
                enviar_json(client_socket, saludo)

                respuesta, buffer = recibir_json(client_socket, buffer)
                if respuesta is None:
                    raise ConnectionResetError("El otro nodo cerro la conexion")

                print(f"[Cliente] Respuesta de {peer_host}:{peer_puerto}: {respuesta}")
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError,
                    ConnectionAbortedError, OSError) as e:
                print(f"[Cliente] Conexion con {peer_host}:{peer_puerto} perdida ({e}). Reconectando...")
                client_socket.close()
                client_socket = conectar(peer_host, peer_puerto)
                buffer = bytearray()
                continue
            except json.JSONDecodeError as e:
                print(f"[Cliente] Mensaje JSON invalido de {peer_host}:{peer_puerto} ({e}). Reconectando...")
                client_socket.close()
                client_socket = conectar(peer_host, peer_puerto)
                buffer = bytearray()
                continue

            time.sleep(INTERVALO)
    finally:
        client_socket.close()


# ---------- Registro ante el Nodo D ----------

def obtener_ip_propia(destino_host):
    """
    Determina la IP local que el sistema usaria para alcanzar a 'destino_host',
    sin necesidad de enviar datos realmente (truco con socket UDP 'connect').
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((destino_host, 1))
        return s.getsockname()[0]
    finally:
        s.close()


def registrarse_en_d(d_host, d_puerto, ip_propia, puerto_propio):
    """
    Se conecta al Nodo D, informa la propia IP/puerto y devuelve la lista
    de pares (nodos C) que D ya tenia registrados antes de este.
    Reintenta indefinidamente si D no esta disponible.
    """
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((d_host, d_puerto))
                enviar_json(s, {"tipo": "registro", "ip": ip_propia, "puerto": puerto_propio})

                buffer = bytearray()
                respuesta, buffer = recibir_json(s, buffer)
                if respuesta is None or respuesta.get("tipo") != "peers":
                    raise ValueError(f"Respuesta inesperada de D: {respuesta}")

                peers = respuesta.get("peers", [])
                print(f"[Registro] Registrado en D ({d_host}:{d_puerto}). Pares recibidos: {peers}")
                return peers

        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"[Registro] No se pudo completar el registro con D ({e}). "
                  f"Reintentando en {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)


def main():
    args = parsear_argumentos()

    # 1) Levantar el servidor propio en un puerto aleatorio
    server_socket, puerto_propio = iniciar_servidor(args.host)
    threading.Thread(target=servidor_loop, args=(server_socket,), daemon=True).start()

    # 2) Determinar la IP propia (la que se usaria para llegar a D) y registrarse
    ip_propia = obtener_ip_propia(args.d_host)
    peers = registrarse_en_d(args.d_host, args.d_puerto, ip_propia, puerto_propio)

    # 3) Lanzar un hilo cliente por cada par recibido, para saludarlos a todos
    for peer in peers:
        threading.Thread(
            target=cliente,
            args=(peer["ip"], peer["puerto"]),
            daemon=True,
        ).start()

    if not peers:
        print("[Registro] No habia otros nodos C registrados todavia. "
              "Este nodo quedara escuchando a la espera de que otros se conecten.")

    # 4) Mantener el proceso principal vivo
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nNodo C detenido manualmente.")


if __name__ == "__main__":
    main()
