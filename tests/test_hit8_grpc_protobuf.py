"""
Hit 8 — gRPC con Protocol Buffers.

Cubre:
- que el mensaje Saludo serialice/deserialice sin pérdida de datos.
- que Protobuf efectivamente pese menos bytes que el JSON equivalente
  del hit5 (la comparación que pide el enunciado).
- la lógica de negocio del servicer (Saludar) de forma aislada.
- un round-trip real de gRPC extremo a extremo (cliente -> servidor -> cliente).
"""

import json
from concurrent import futures

import grpc

from helpers import load_module

nodoc8 = load_module("hit8/NodoC.py")
nodos_pb2 = nodoc8.nodos_pb2
nodos_pb2_grpc = nodoc8.nodos_pb2_grpc


def test_serializacion_protobuf_round_trip_sin_perdida():
    original = nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C")

    crudo = original.SerializeToString()
    reconstruido = nodos_pb2.Saludo()
    reconstruido.ParseFromString(crudo)

    assert reconstruido.tipo == "saludo"
    assert reconstruido.origen == "C"
    assert reconstruido.texto == "Hola, soy C"


def test_mensaje_protobuf_pesa_menos_bytes_que_su_equivalente_json():
    logico = {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}

    json_bytes = (json.dumps(logico) + "\n").encode()  # framing de hit5
    proto_bytes = nodos_pb2.Saludo(**logico).SerializeToString()

    assert len(proto_bytes) < len(json_bytes)


def test_servicer_saludar_devuelve_el_saludo_fijo_de_c():
    servicer = nodoc8.NodoSaludoServicer()
    pedido = nodos_pb2.Saludo(tipo="saludo", origen="C", texto="hola desde el test")

    class ContextoFalso:
        def peer(self):
            return "test-peer:0"

    respuesta = servicer.Saludar(pedido, ContextoFalso())

    assert respuesta.tipo == "saludo"
    assert respuesta.origen == "C"
    assert respuesta.texto == "Hola, soy C"


def test_integracion_grpc_extremo_a_extremo_real():
    """Levanta un servidor gRPC real en un puerto aleatorio y lo llama con
    un stub real, para validar el contrato definido en nodos.proto."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    nodos_pb2_grpc.add_NodoSaludoServicer_to_server(
        nodoc8.NodoSaludoServicer(), server
    )
    puerto = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        channel = grpc.insecure_channel(f"127.0.0.1:{puerto}")
        stub = nodos_pb2_grpc.NodoSaludoStub(channel)

        respuesta = stub.Saludar(
            nodos_pb2.Saludo(tipo="saludo", origen="C", texto="hola"), timeout=5
        )

        assert respuesta.texto == "Hola, soy C"
    finally:
        server.stop(grace=0).wait()
