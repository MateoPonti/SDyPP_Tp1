import socket

HOST =  "127.0.0.1"
PORT = 5000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

mensaje = "Hola B, soy A"
client_socket.sendall(mensaje.encode())

respuesta = client_socket.recv(1024).decode()
print(f"Respuesta de B: {respuesta}")

client_socket.close()