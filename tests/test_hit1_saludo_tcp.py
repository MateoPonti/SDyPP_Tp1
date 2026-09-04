"""
Hit 1 — Saludo TCP básico entre A (cliente) y B (servidor).

Cubre el handshake elemental:
- A envía "Hola B, soy A"
- B responde "Hola A, soy B"
- Ambos cierran la conexión tras un único intercambio (servidor y cliente de un solo uso).
Usa socket.socketpair() para probar la lógica sobre sockets TCP reales en memoria.
"""

import socket
import threading

from helpers import load_module

cliente1 = load_module("hit1/ClienteTcp.py")
servidor1 = load_module("hit1/ServidorTcp.py")


def test_cliente_envia_saludo_y_recibe_respuesta_esperada():
    """El cliente debe enviar 'Hola B, soy A' y recibir 'Hola A, soy B'."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        def responder():
            datos = servidor_sock.recv(1024).decode()
            assert datos == "Hola B, soy A"
            servidor_sock.sendall("Hola A, soy B".encode())

        t = threading.Thread(target=responder)
        t.start()

        respuesta = cliente1.enviar_saludo(cliente_sock)
        t.join(timeout=2)

        assert respuesta == "Hola A, soy B"
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_servidor_atiende_saludo_y_responde_correctamente():
    """El servidor B debe leer el saludo y responder con 'Hola A, soy B'."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        def saludar():
            cliente_sock.sendall("Hola B, soy A".encode())
            respuesta = cliente_sock.recv(1024).decode()
            assert respuesta == "Hola A, soy B"

        t = threading.Thread(target=saludar)
        t.start()

        mensaje_recibido = servidor1.atender_cliente(servidor_sock, ("127.0.0.1", 12345))
        t.join(timeout=2)

        assert mensaje_recibido == "Hola B, soy A"
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_intercambio_completo_cliente_servidor_hit1():
    """Integra la función del cliente con la función del servidor directamente."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        resultado = {}

        def correr_servidor():
            resultado["servidor_recibio"] = servidor1.atender_cliente(
                servidor_sock, ("127.0.0.1", 54321)
            )

        def correr_cliente():
            resultado["cliente_recibio"] = cliente1.enviar_saludo(cliente_sock)

        t_servidor = threading.Thread(target=correr_servidor)
        t_cliente = threading.Thread(target=correr_cliente)

        t_servidor.start()
        t_cliente.start()

        t_servidor.join(timeout=2)
        t_cliente.join(timeout=2)

        assert resultado["servidor_recibio"] == "Hola B, soy A"
        assert resultado["cliente_recibio"] == "Hola A, soy B"
    finally:
        servidor_sock.close()
        cliente_sock.close()
