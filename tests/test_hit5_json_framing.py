"""
Hit 5 — Serialización JSON sobre TCP.

Cubre la funcionalidad crítica de este hit: el framing manual por '\\n'
(enviar_json / recibir_json), que es la base de la que dependen los hits
6 y 7. Se usa socket.socketpair() para tener sockets TCP reales de extremo
a extremo sin necesitar puertos ni red.
"""

import json
import socket
import threading

import pytest

from helpers import load_module

nodoc5 = load_module("hit5/NodoC.py")


def test_enviar_y_recibir_json_mensaje_completo():
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        datos = {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}
        nodoc5.enviar_json(cliente_sock, datos)

        recibido, resto = nodoc5.recibir_json(servidor_sock, bytearray())

        assert recibido == datos
        assert resto == b""
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_recibir_json_reensambla_mensaje_fragmentado_en_dos_paquetes():
    """TCP es un stream de bytes: un mismo mensaje puede llegar partido en
    varios recv(). recibir_json debe acumularlo hasta ver el '\\n'."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        mensaje = b'{"tipo": "saludo", "origen": "C", "texto": "hola"}\n'
        mitad = len(mensaje) // 2
        cliente_sock.sendall(mensaje[:mitad])
        cliente_sock.sendall(mensaje[mitad:])

        recibido, _ = nodoc5.recibir_json(servidor_sock, bytearray())

        assert recibido == {"tipo": "saludo", "origen": "C", "texto": "hola"}
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_recibir_json_separa_dos_mensajes_pegados_en_un_solo_envio():
    """El caso inverso: dos mensajes que llegan juntos en un solo recv()
    deben poder leerse uno por uno usando el buffer devuelto."""
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        m1 = {"tipo": "saludo", "origen": "C", "texto": "uno"}
        m2 = {"tipo": "saludo", "origen": "C", "texto": "dos"}
        cliente_sock.sendall((json.dumps(m1) + "\n" + json.dumps(m2) + "\n").encode())

        primero, buffer = nodoc5.recibir_json(servidor_sock, bytearray())
        segundo, _ = nodoc5.recibir_json(servidor_sock, buffer)

        assert primero == m1
        assert segundo == m2
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_recibir_json_devuelve_none_si_la_conexion_se_cierra():
    servidor_sock, cliente_sock = socket.socketpair()
    cliente_sock.close()  # simula al peer cerrando la conexión sin mandar nada

    recibido, _ = nodoc5.recibir_json(servidor_sock, bytearray())

    assert recibido is None
    servidor_sock.close()


def test_recibir_json_lanza_jsondecodeerror_con_json_invalido():
    servidor_sock, cliente_sock = socket.socketpair()
    try:
        cliente_sock.sendall(b"{esto no es json valido}\n")

        with pytest.raises(json.JSONDecodeError):
            nodoc5.recibir_json(servidor_sock, bytearray())
    finally:
        servidor_sock.close()
        cliente_sock.close()


def test_atender_conexion_responde_con_el_saludo_fijo_de_c():
    """Test de integración del handler completo del servidor: recibe un
    saludo por un socket real y debe responder el saludo fijo de C."""
    servidor_sock, cliente_sock = socket.socketpair()
    hilo = threading.Thread(
        target=nodoc5.atender_conexion, args=(servidor_sock, ("test", 0))
    )
    hilo.start()
    try:
        nodoc5.enviar_json(
            cliente_sock, {"tipo": "saludo", "origen": "C", "texto": "hola"}
        )
        respuesta, _ = nodoc5.recibir_json(cliente_sock, bytearray())

        assert respuesta == {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}
    finally:
        cliente_sock.close()
        hilo.join(timeout=2)
        assert not hilo.is_alive()
