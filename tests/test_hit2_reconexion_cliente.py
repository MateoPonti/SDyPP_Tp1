"""
Hit 2 — Reconexión de A ante caídas de B.

Cubre:
- El cliente saluda y procesa la respuesta de B.
- Si B cierra la conexión, el cliente lo detecta lanzando ConnectionResetError
  para activar la rama de reconexión.
- La función de conexión reintenta ante fallos de red (OSError/ConnectionRefusedError).
- El servidor de Hit 2 atiende saludos en bucle sobre la misma conexión.
"""

import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from helpers import load_module

cliente2 = load_module("hit2/ClienteTcp.py")
servidor2 = load_module("hit2/ServidorTcp.py")


def test_hit2_enviar_saludo_exitoso():
    """El cliente envía 'Hola B, soy A' y retorna la respuesta de B."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        def responder():
            msg = servidor_sock.recv(1024).decode()
            assert msg == "Hola B, soy A"
            servidor_sock.sendall("Hola A, soy B".encode())

        t = threading.Thread(target=responder)
        t.start()

        respuesta = cliente2.enviar_saludo(cliente_sock)
        t.join(timeout=2)

        assert respuesta == "Hola A, soy B"
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_hit2_enviar_saludo_lanza_connection_reset_si_servidor_cierra():
    """Si B cierra el socket prematuramente, enviar_saludo debe lanzar ConnectionResetError."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        servidor_sock.close()

        with pytest.raises((ConnectionResetError, BrokenPipeError, OSError)):
            cliente2.enviar_saludo(cliente_sock)
    finally:
        cliente_sock.close()


def test_hit2_conectar_reintenta_tras_fallos_de_conexion():
    """Verifica que conectar() reintente tras fallas transitorias de conexión."""
    mock_socket_instance = MagicMock()
    # Falla 2 veces con OSError y en el 3er intento se conecta con éxito
    mock_socket_instance.connect.side_effect = [
        OSError("Servidor no disponible"),
        OSError("Servidor no disponible"),
        None,
    ]

    with patch("socket.socket", return_value=mock_socket_instance), \
         patch("time.sleep", return_value=None) as mock_sleep:
        s = cliente2.conectar()
        assert s == mock_socket_instance
        assert mock_socket_instance.connect.call_count == 3
        assert mock_sleep.call_count == 2


def test_hit2_servidor_atiende_multiples_saludos():
    """El servidor de hit 2 atiende múltiples saludos consecutivos en un loop."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=servidor2.atender_cliente,
            args=(servidor_sock, ("127.0.0.1", 9999)),
            daemon=True,
        )
        t_servidor.start()

        # Enviar 3 saludos seguidos
        for _ in range(3):
            cliente_sock.sendall("Hola B, soy A".encode())
            resp = cliente_sock.recv(1024).decode()
            assert resp == "Hola A, soy B"

        # Cerrar el lado del cliente para terminar el loop del servidor
        cliente_sock.close()
        t_servidor.join(timeout=2)
    finally:
        servidor_sock.close()
