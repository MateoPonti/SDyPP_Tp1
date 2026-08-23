import socket

HOST = "0.0.0.0"
PORT = 5000

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print(f"Servidor B esperando conexiones en el puerto {PORT}...")

conn, addr = server_socket.accept()
print(f"A se conectó desde {addr}")

mensaje = conn.recv(1024).decode()
print(f"Saludo recibido: {mensaje}")

respuesta = "Hola A, soy B"
conn.sendall(respuesta.encode())

conn.close()
server_socket.close()