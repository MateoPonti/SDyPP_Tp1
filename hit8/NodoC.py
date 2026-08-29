import argparse
import time
from concurrent import futures

import grpc

import nodos_pb2
import nodos_pb2_grpc

INTERVALO = 3
RETRY_DELAY = 3
MAX_WORKERS = 10


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Nodo C: actua como cliente y servidor gRPC simultaneamente, "
                    "saludando y escuchando saludos de otro nodo C. "
                    "Equivalente a hit5, reemplazando JSON sobre TCP por gRPC + Protocol Buffers."
    )
    parser.add_argument("--host", default="0.0.0.0", help="IP propia para escuchar saludos (default: 0.0.0.0)")
    parser.add_argument("--puerto", type=int, required=True, help="Puerto propio para escuchar saludos")
    parser.add_argument("--peer-host", required=True, help="IP del otro nodo C")
    parser.add_argument("--peer-puerto", type=int, required=True, help="Puerto del otro nodo C")
    return parser.parse_args()


# ---------- Lado servidor: implementa el RPC Saludar de nodos.proto ----------

class NodoSaludoServicer(nodos_pb2_grpc.NodoSaludoServicer):
    """Reemplaza a atender_conexion()/servidor() de hit5.

    gRPC ya se encarga de aceptar conexiones, multiplexarlas sobre HTTP/2 y
    deserializar cada mensaje Saludo entrante: no hace falta framing manual
    con '\\n' ni json.loads/json.JSONDecodeError.
    """

    def Saludar(self, request, context):
        print(f"[Servidor] Saludo recibido de {context.peer()}: "
              f"tipo={request.tipo!r} origen={request.origen!r} texto={request.texto!r}")
        return nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C")


def servidor(host, puerto):
    """Crea y arranca el servidor gRPC. A diferencia de hit5, server.start()
    no bloquea: gRPC administra su propio pool de hilos para atender RPCs,
    asi que no hace falta lanzar esto en un threading.Thread aparte."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    nodos_pb2_grpc.add_NodoSaludoServicer_to_server(NodoSaludoServicer(), server)
    puerto_asignado = server.add_insecure_port(f"{host}:{puerto}")
    server.start()
    print(f"[Servidor] Escuchando saludos en {host}:{puerto_asignado}...")
    return server


# ---------- Lado cliente: saluda a un par especifico, con reintentos ----------

def cliente(peer_host, peer_puerto):
    """Un grpc.Channel es persistente: gRPC reconecta la conexion TCP/HTTP2
    subyacente por su cuenta, a diferencia del socket de hit5 que habia que
    recrear a mano en cada corte. Lo que si hay que atajar es RpcError en
    cada llamada, que es donde gRPC envuelve cualquier problema de transporte
    (peer caido, timeout, etc.) -- equivalente a los
    ConnectionResetError/BrokenPipeError/ConnectionAbortedError/OSError que
    se atajaban explicitamente en hit5."""
    target = f"{peer_host}:{peer_puerto}"
    channel = grpc.insecure_channel(target)
    stub = nodos_pb2_grpc.NodoSaludoStub(channel)

    while True:
        try:
            saludo = nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C")
            respuesta = stub.Saludar(saludo, timeout=RETRY_DELAY)
            print(f"[Cliente] Respuesta de {target}: "
                  f"tipo={respuesta.tipo!r} origen={respuesta.origen!r} texto={respuesta.texto!r}")
        except grpc.RpcError as e:
            print(f"[Cliente] No se pudo saludar a {target} "
                  f"({e.code()}: {e.details()}). Reintentando en {RETRY_DELAY}s...")

        time.sleep(INTERVALO)


def main():
    args = parsear_argumentos()

    server = servidor(args.host, args.puerto)

    try:
        cliente(args.peer_host, args.peer_puerto)
    except KeyboardInterrupt:
        print("\nNodo C detenido manualmente.")
        server.stop(grace=1).wait()


if __name__ == "__main__":
    main()
