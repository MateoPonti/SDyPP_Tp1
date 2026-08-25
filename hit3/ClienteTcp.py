import socket
import time

HOST = "127.0.0.1"
PORT = 5000
INTERVALO = 3
RETRY_DELAY = 3


def conectar():
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            print("Conectado a B")
            return s
        except OSError as e:
            print(f"No se pudo conectar a B ({e}). Reintentando en {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)


def main():
    client_socket = conectar()
    try:
        while True:
            try:
                mensaje = "Hola B, soy A"
                client_socket.sendall(mensaje.encode())

                respuesta = client_socket.recv(1024)
                if not respuesta:
                    raise ConnectionResetError("B cerró la conexión")

                print(f"Respuesta de B: {respuesta.decode()}")
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
                print(f"Conexión con B perdida ({e}). Reconectando...")
                client_socket.close()
                client_socket = conectar()
                continue

            time.sleep(INTERVALO)
    except KeyboardInterrupt:
        print("\nCliente A detenido manualmente.")
    finally:
        client_socket.close()


if __name__ == "__main__":
    main()
