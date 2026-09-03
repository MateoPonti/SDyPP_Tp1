"""
Hit 6 — Nodo D: registro de contactos + health check.

Cubre:
- que D devuelva la lista de peers correcta (una "foto" tomada ANTES de
  agregar al nodo que se está registrando).
- que la lista en RAM se actualice con cada alta.
- que el endpoint HTTP /health devuelva el JSON esperado y 404 para
  cualquier otra ruta.
"""

import json
import socket
import threading
import urllib.error
import urllib.request

from helpers import load_module


def test_primer_nodo_registrado_recibe_lista_de_peers_vacia():
    nodod = load_module("hit6/NodoD.py")
    servidor_sock, cliente_sock = socket.socketpair()

    hilo = threading.Thread(
        target=nodod.atender_registro, args=(servidor_sock, ("test", 0))
    )
    hilo.start()
    try:
        nodod.enviar_json(
            cliente_sock, {"tipo": "registro", "ip": "10.0.0.1", "puerto": 6000}
        )
        respuesta, _ = nodod.recibir_json(cliente_sock, bytearray())

        assert respuesta == {"tipo": "peers", "peers": []}
        assert nodod.nodos_registrados == [{"ip": "10.0.0.1", "puerto": 6000}]
    finally:
        cliente_sock.close()
        hilo.join(timeout=2)


def test_segundo_nodo_recibe_al_primero_como_peer_y_no_a_si_mismo():
    nodod = load_module("hit6/NodoD.py")  # instancia con estado propio, en 0

    def registrar(ip, puerto):
        s1, s2 = socket.socketpair()
        hilo = threading.Thread(target=nodod.atender_registro, args=(s1, ("test", 0)))
        hilo.start()
        nodod.enviar_json(s2, {"tipo": "registro", "ip": ip, "puerto": puerto})
        respuesta, _ = nodod.recibir_json(s2, bytearray())
        s2.close()
        hilo.join(timeout=2)
        return respuesta

    primera_respuesta = registrar("10.0.0.1", 6000)
    segunda_respuesta = registrar("10.0.0.2", 6001)

    assert primera_respuesta["peers"] == []
    assert segunda_respuesta["peers"] == [{"ip": "10.0.0.1", "puerto": 6000}]
    assert nodod.nodos_registrados == [
        {"ip": "10.0.0.1", "puerto": 6000},
        {"ip": "10.0.0.2", "puerto": 6001},
    ]


def test_health_devuelve_json_esperado_y_404_en_otra_ruta():
    nodod = load_module("hit6/NodoD.py")
    nodod.nodos_registrados.extend(
        [{"ip": "10.0.0.1", "puerto": 6000}, {"ip": "10.0.0.2", "puerto": 6001}]
    )

    servidor_http = nodod.ThreadingHTTPServer(("127.0.0.1", 0), nodod.HealthHandler)
    puerto = servidor_http.server_address[1]
    hilo = threading.Thread(target=servidor_http.serve_forever, daemon=True)
    hilo.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/health") as resp:
            cuerpo = json.loads(resp.read())

        assert cuerpo["nodos_registrados"] == 2
        assert cuerpo["estado"] == "ok"
        assert "uptime_segundos" in cuerpo

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{puerto}/otra-ruta")
            assert False, "se esperaba HTTPError 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        servidor_http.shutdown()
        hilo.join(timeout=2)
