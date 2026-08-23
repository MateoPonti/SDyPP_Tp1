import socket

HOST = "0.0.0.0"
PORT = 5000

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print(f"Servidor B esperando conexiones en el puerto {PORT}...")

while True:
    conn, addr = server_socket.accept()
    print(f"A se conectó desde {addr}")

    try:
        while True:
            mensaje = conn.recv(1024)
            if not mensaje:
                print("A cerró la conexión")
                break

            print(f"Saludo recibido: {mensaje.decode()}")

            respuesta = "Hola A, soy B"
            conn.sendall(respuesta.encode())
    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print(f"Conexión con A perdida ({e})")
    finally:
        conn.close()
