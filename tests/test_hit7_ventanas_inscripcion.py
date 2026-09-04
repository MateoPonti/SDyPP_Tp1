"""
Hit 7 — Sistema de inscripciones por ventana de tiempo.

Cubre la regla central del hit: un nodo C que se registra queda anotado
para la *próxima* ventana (nodos_inscriptos) y sólo ve como peers a los
nodos ya *activos* (nodos_registrados) — nunca a sus futuros compañeros de
ventana. También cubre que swap() mueve correctamente los inscriptos a
activos y que todo se persiste en el archivo de inscripciones.

Los tests redirigen ARCHIVO_INSCRIPCIONES a un archivo temporal
(tmp_path) para no ensuciar el repo ni pisar corridas manuales.
"""

import json
import socket
import threading
import time

from helpers import load_module


def _registrar(nodod7, ip, puerto):
    s1, s2 = socket.socketpair()
    hilo = threading.Thread(target=nodod7.atender_registro, args=(s1, ("test", 0)))
    hilo.start()
    nodod7.enviar_json(s2, {"tipo": "registro", "ip": ip, "puerto": puerto})
    respuesta, _ = nodod7.recibir_json(s2, bytearray())
    s2.close()
    hilo.join(timeout=2)
    return respuesta


def _consultar(nodod7):
    s1, s2 = socket.socketpair()
    hilo = threading.Thread(target=nodod7.atender_registro, args=(s1, ("test", 0)))
    hilo.start()
    nodod7.enviar_json(s2, {"tipo": "consulta"})
    respuesta, _ = nodod7.recibir_json(s2, bytearray())
    s2.close()
    hilo.join(timeout=2)
    return respuesta


def test_registro_asigna_proxima_ventana_y_no_revela_futuros_compañeros(
    tmp_path, monkeypatch
):
    nodod7 = load_module("hit7/NodoD.py")
    monkeypatch.setattr(nodod7, "ARCHIVO_INSCRIPCIONES", str(tmp_path / "inscripciones.txt"))
    nodod7.proxima_ventana_ts = time.time() + 60

    respuesta = _registrar(nodod7, "10.0.0.1", 7000)

    assert respuesta["ventana_asignada"] == nodod7.proxima_ventana_ts
    assert respuesta["peers"] == []  # todavía no hay nadie activo
    assert nodod7.nodos_inscriptos == [{"ip": "10.0.0.1", "puerto": 7000}]
    assert nodod7.nodos_registrados == []  # el inscripto no es "activo" todavía

    lineas = (tmp_path / "inscripciones.txt").read_text().splitlines()
    evento = json.loads(lineas[0])
    assert evento["tipo"] == "inscripcion"
    assert evento["ip"] == "10.0.0.1"
    assert evento["puerto"] == 7000


def test_consulta_solo_ve_activos_nunca_inscriptos_para_la_proxima_ventana(
    tmp_path, monkeypatch
):
    nodod7 = load_module("hit7/NodoD.py")
    monkeypatch.setattr(nodod7, "ARCHIVO_INSCRIPCIONES", str(tmp_path / "inscripciones.txt"))
    nodod7.proxima_ventana_ts = time.time() + 60
    nodod7.nodos_inscriptos.append({"ip": "10.0.0.9", "puerto": 9999})

    respuesta = _consultar(nodod7)

    assert respuesta == {"tipo": "peers", "peers": []}


def test_swap_mueve_inscriptos_a_activos_y_persiste_apertura_de_ventana(
    tmp_path, monkeypatch
):
    nodod7 = load_module("hit7/NodoD.py")
    monkeypatch.setattr(nodod7, "ARCHIVO_INSCRIPCIONES", str(tmp_path / "inscripciones.txt"))
    nodod7.nodos_inscriptos.extend(
        [{"ip": "10.0.0.1", "puerto": 7000}, {"ip": "10.0.0.2", "puerto": 7001}]
    )
    ts_cierre = time.time()

    nodod7.swap(ts_cierre)

    assert nodod7.nodos_registrados == [
        {"ip": "10.0.0.1", "puerto": 7000},
        {"ip": "10.0.0.2", "puerto": 7001},
    ]
    assert nodod7.nodos_inscriptos == []
    assert nodod7.proxima_ventana_ts == ts_cierre + 60

    lineas = (tmp_path / "inscripciones.txt").read_text().splitlines()
    evento = json.loads(lineas[-1])
    assert evento["tipo"] == "apertura_ventana"
    assert len(evento["miembros"]) == 2


def test_despues_del_swap_consulta_ya_ve_a_los_recien_activados(tmp_path, monkeypatch):
    nodod7 = load_module("hit7/NodoD.py")
    monkeypatch.setattr(nodod7, "ARCHIVO_INSCRIPCIONES", str(tmp_path / "inscripciones.txt"))
    nodod7.proxima_ventana_ts = time.time() + 60

    _registrar(nodod7, "10.0.0.1", 7000)
    assert _consultar(nodod7)["peers"] == []  # aún no activado

    nodod7.swap(nodod7.proxima_ventana_ts)

    assert _consultar(nodod7)["peers"] == [{"ip": "10.0.0.1", "puerto": 7000}]
