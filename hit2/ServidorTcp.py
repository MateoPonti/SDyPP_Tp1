import socket

HOST = "0.0.0.0"
PORT = 5000


def atender_cliente(conn, addr):
    print(f"A se conectó desde {addr}")
    while True:
        mensaje = conn.recv(1024).decode()
        if not mensaje:
            break
        print(f"Saludo recibido: {mensaje}")
        respuesta = "Hola A, soy B"
        conn.sendall(respuesta.encode())


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"Servidor B esperando conexiones en el puerto {PORT}...")

    conn, addr = server_socket.accept()
    try:
        atender_cliente(conn, addr)
    finally:
        conn.close()
        server_socket.close()


if __name__ == "__main__":
    main()
