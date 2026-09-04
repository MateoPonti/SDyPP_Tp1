"""
Hit 3 — Servidor B tolera la desconexión de A.

Cubre:
- El servidor atiende múltiples saludos del cliente.
- El servidor tolera el cierre limpio del socket por parte de A sin lanzar excepciones.
- El servidor tolera la desconexión abrupta (corte de conexión, reset) y se recupera limpiamente.
"""

import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from helpers import load_module

servidor3 = load_module("hit3/ServidorTcp.py")
cliente3 = load_module("hit3/ClienteTcp.py")


def test_hit3_servidor_responde_saludos_consecutivos():
    """El servidor responde 'Hola A, soy B' a cada saludo recibido."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=servidor3.atender_conexion,
            args=(servidor_sock, ("127.0.0.1", 1111)),
            daemon=True,
        )
        t_servidor.start()

        for _ in range(3):
            cliente_sock.sendall("Hola B, soy A".encode())
            respuesta = cliente_sock.recv(1024).decode()
            assert respuesta == "Hola A, soy B"

        cliente_sock.close()
        t_servidor.join(timeout=2)
    finally:
        servidor_sock.close()


def test_hit3_servidor_tolera_cierre_limpio_de_cliente():
    """Cuando el cliente cierra el socket (recv() retorna vacío), el servidor finaliza la atención limpiamente."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=servidor3.atender_conexion,
            args=(servidor_sock, ("127.0.0.1", 2222)),
        )
        t_servidor.start()

        # Enviar un saludo y luego cerrar inmediatamente
        cliente_sock.sendall("Hola B, soy A".encode())
        _ = cliente_sock.recv(1024)
        cliente_sock.close()

        t_servidor.join(timeout=2)
        assert not t_servidor.is_alive()
    finally:
        servidor_sock.close()


def test_hit3_servidor_tolera_desconexion_abrupta():
    """Si ocurre un ConnectionResetError, el servidor no crashea y sale ordenadamente."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=servidor3.atender_conexion,
            args=(servidor_sock, ("127.0.0.1", 3333)),
        )
        t_servidor.start()

        # Simular corte abrupto cerrando el socket cliente mientras el servidor espera
        cliente_sock.close()

        t_servidor.join(timeout=2)
        assert not t_servidor.is_alive()
    finally:
        servidor_sock.close()


def test_hit3_cliente_enviar_saludo_y_reintento():
    """El cliente de Hit 3 envía saludo y reintenta ante caídas de conexión."""
    mock_socket = MagicMock()
    mock_socket.connect.side_effect = [OSError("Conexión rechazada"), None]

    with patch("socket.socket", return_value=mock_socket), \
         patch("time.sleep", return_value=None):
        s = cliente3.conectar()
        assert s == mock_socket
        assert mock_socket.connect.call_count == 2
