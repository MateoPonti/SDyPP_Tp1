import socket

HOST = "127.0.0.1"
PORT = 5000


def enviar_saludo(sock):
    mensaje = "Hola B, soy A"
    sock.sendall(mensaje.encode())
    respuesta = sock.recv(1024).decode()
    print(f"Respuesta de B: {respuesta}")
    return respuesta


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    enviar_saludo(client_socket)
    client_socket.close()


if __name__ == "__main__":
    main()