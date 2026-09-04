import socket

HOST = "0.0.0.0"
PORT = 5000


def atender_conexion(conn, addr):
    try:
        while True:
            mensaje = conn.recv(1024)

            if not mensaje:
                print(f"A ({addr}) cerró la conexión")
                break

            print(f"Saludo recibido: {mensaje.decode()}")

            respuesta = "Hola A, soy B"
            conn.sendall(respuesta.encode())

    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
        print(f"Conexión con A ({addr}) perdida abruptamente: {e}")

    finally:
        conn.close()
        print("Esperando nueva conexión de A...")


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"Servidor B esperando conexiones en el puerto {PORT}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"A se conectó desde {addr}")
        atender_conexion(conn, addr)


if __name__ == "__main__":
    main()