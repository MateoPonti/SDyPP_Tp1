"""
Hit 4 — Programa C bidireccional (cliente y servidor unificados).

Cubre:
- La función de servidor atender_conexion responde 'Hola, soy C' a cada saludo.
- El servidor tolera la desconexión limpia o abrupta del peer.
- La función de cliente enviar_saludo despacha el mensaje y retorna la respuesta.
- Intercambio bidireccional cruzado entre dos nodos C (cada uno actuando como cliente y servidor).
- Validación de argumentos de línea de comandos (host, puerto, peer-host, peer-puerto).
"""

import socket
import sys
import threading

import pytest

from helpers import load_module

nodoc4 = load_module("hit4/NodoC.py")


def test_hit4_servidor_responde_hola_soy_c():
    """El hilo servidor debe responder 'Hola, soy C' a los mensajes recibidos."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=nodoc4.atender_conexion,
            args=(servidor_sock, ("127.0.0.1", 6001)),
            daemon=True,
        )
        t_servidor.start()

        cliente_sock.sendall("Hola, soy C".encode())
        respuesta = cliente_sock.recv(1024).decode()
        assert respuesta == "Hola, soy C"

        cliente_sock.close()
        t_servidor.join(timeout=2)
    finally:
        servidor_sock.close()


def test_hit4_servidor_tolera_desconexion_del_peer():
    """atender_conexion debe salir limpiamente cuando el peer se desconecta."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        t_servidor = threading.Thread(
            target=nodoc4.atender_conexion,
            args=(servidor_sock, ("127.0.0.1", 6002)),
        )
        t_servidor.start()

        # Enviar saludo y luego cerrar inmediatamente
        cliente_sock.sendall("Hola, soy C".encode())
        _ = cliente_sock.recv(1024)
        cliente_sock.close()

        t_servidor.join(timeout=2)
        assert not t_servidor.is_alive()
    finally:
        servidor_sock.close()


def test_hit4_cliente_enviar_saludo_exitoso():
    """enviar_saludo envía el mensaje y recibe la confirmación."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        def responder():
            msg = servidor_sock.recv(1024).decode()
            assert msg == "Hola, soy C"
            servidor_sock.sendall("Hola, soy C".encode())

        t = threading.Thread(target=responder)
        t.start()

        respuesta = nodoc4.enviar_saludo(cliente_sock, peer_host="127.0.0.1", peer_puerto=6001)
        t.join(timeout=2)

        assert respuesta == "Hola, soy C"
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_hit4_intercambio_bidireccional_cruzado():
    """
    Dos nodos C interactúan en simultáneo:
    - Canal 1: Cliente de C1 saluda al Servidor de C2
    - Canal 2: Cliente de C2 saluda al Servidor de C1
    """
    s1_serv, c1_cli = socket.socketpair()
    s2_serv, c2_cli = socket.socketpair()

    try:
        t_s1 = threading.Thread(target=nodoc4.atender_conexion, args=(s1_serv, ("127.0.0.1", 6000)), daemon=True)
        t_s2 = threading.Thread(target=nodoc4.atender_conexion, args=(s2_serv, ("127.0.0.1", 6001)), daemon=True)
        t_s1.start()
        t_s2.start()

        # C1 saluda a S2
        resp1 = nodoc4.enviar_saludo(c2_cli, peer_host="127.0.0.1", peer_puerto=6001)
        # C2 saluda a S1
        resp2 = nodoc4.enviar_saludo(c1_cli, peer_host="127.0.0.1", peer_puerto=6000)

        assert resp1 == "Hola, soy C"
        assert resp2 == "Hola, soy C"

        c1_cli.close()
        c2_cli.close()
        t_s1.join(timeout=2)
        t_s2.join(timeout=2)
    finally:
        s1_serv.close()
        s2_serv.close()


def test_hit4_parsear_argumentos(monkeypatch):
    """Verifica que los argumentos por línea de comandos se parseen correctamente."""
    args_simulados = [
        "NodoC.py",
        "--host", "127.0.0.1",
        "--puerto", "6000",
        "--peer-host", "127.0.0.2",
        "--peer-puerto", "6001",
    ]
    monkeypatch.setattr(sys, "argv", args_simulados)
    args = nodoc4.parsear_argumentos()

    assert args.host == "127.0.0.1"
    assert args.puerto == 6000
    assert args.peer_host == "127.0.0.2"
    assert args.peer_puerto == 6001
