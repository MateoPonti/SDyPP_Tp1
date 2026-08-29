"""
Compara hit5 (JSON sobre TCP, framing manual) contra hit8 (gRPC + Protocol
Buffers) usando el mismo contenido logico de mensaje en los dos casos:

    {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}

Mide:
  1) Tamano del mensaje serializado, tal cual viaja por la red.
  2) Latencia de ida y vuelta (round-trip) cliente-servidor en localhost,
     usando las mismas funciones/clases que ya usan NodoC.py de cada hit
     (no una reimplementacion aparte), para que el numero refleje el
     protocolo real y no un microbenchmark idealizado.

Los resultados se imprimen por consola y se guardan en
resultados_comparacion.txt.
"""
import importlib.util
import json
import socket
import statistics
import threading
import time
from concurrent import futures
from pathlib import Path

import grpc

import nodos_pb2
import nodos_pb2_grpc

N_ITERACIONES = 200
HOST = "127.0.0.1"
HIT5_NODOC = Path(__file__).resolve().parent.parent / "hit5" / "NodoC.py"


def cargar_modulo_hit5():
    """Importa hit5/NodoC.py como modulo para reusar enviar_json/recibir_json
    tal cual estan escritas ahi, sin duplicar el codigo de framing."""
    spec = importlib.util.spec_from_file_location("hit5_nodoc", HIT5_NODOC)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def puerto_libre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, 0))
    puerto = s.getsockname()[1]
    s.close()
    return puerto


# ---------- 1) Tamano del mensaje ----------

def medir_tamanios():
    saludo_dict = {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}
    # hit5 delimita cada mensaje con '\n' (ver enviar_json en hit5/NodoC.py);
    # ese byte extra tambien viaja por la red, asi que se cuenta.
    bytes_json = json.dumps(saludo_dict).encode() + b"\n"

    saludo_pb = nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C")
    bytes_pb = saludo_pb.SerializeToString()

    return len(bytes_json), len(bytes_pb)


# ---------- 2a) Latencia hit5 (JSON/TCP) ----------

def benchmark_json(hit5, n=N_ITERACIONES):
    puerto = puerto_libre()
    listo = threading.Event()

    def servidor():
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, puerto))
        srv.listen()
        listo.set()
        conn, _ = srv.accept()
        buffer = bytearray()
        for _ in range(n):
            _, buffer = hit5.recibir_json(conn, buffer)
            hit5.enviar_json(conn, {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"})
        conn.close()
        srv.close()

    hilo = threading.Thread(target=servidor, daemon=True)
    hilo.start()
    listo.wait(timeout=5)

    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((HOST, puerto))
    buffer = bytearray()

    tiempos = []
    for _ in range(n):
        inicio = time.perf_counter()
        hit5.enviar_json(cliente, {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"})
        _, buffer = hit5.recibir_json(cliente, buffer)
        tiempos.append(time.perf_counter() - inicio)

    cliente.close()
    hilo.join(timeout=2)
    return tiempos


# ---------- 2b) Latencia hit8 (gRPC/Protobuf) ----------

class _SaludoServicer(nodos_pb2_grpc.NodoSaludoServicer):
    def Saludar(self, request, context):
        return nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C")


def benchmark_grpc(n=N_ITERACIONES):
    puerto = puerto_libre()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    nodos_pb2_grpc.add_NodoSaludoServicer_to_server(_SaludoServicer(), server)
    server.add_insecure_port(f"{HOST}:{puerto}")
    server.start()

    channel = grpc.insecure_channel(f"{HOST}:{puerto}")
    grpc.channel_ready_future(channel).result(timeout=5)
    stub = nodos_pb2_grpc.NodoSaludoStub(channel)

    tiempos = []
    for _ in range(n):
        inicio = time.perf_counter()
        stub.Saludar(nodos_pb2.Saludo(tipo="saludo", origen="C", texto="Hola, soy C"))
        tiempos.append(time.perf_counter() - inicio)

    channel.close()
    server.stop(grace=1).wait()
    return tiempos


def estadisticas(tiempos_seg):
    ms = [t * 1000 for t in tiempos_seg]
    return {
        "n": len(ms),
        "min_ms": min(ms),
        "max_ms": max(ms),
        "promedio_ms": statistics.mean(ms),
        "mediana_ms": statistics.median(ms),
        "p95_ms": statistics.quantiles(ms, n=20)[18] if len(ms) >= 20 else max(ms),
        "desvio_ms": statistics.pstdev(ms),
    }


def main():
    hit5 = cargar_modulo_hit5()

    bytes_json, bytes_pb = medir_tamanios()

    print(f"Midiendo latencia JSON/TCP (hit5) -- {N_ITERACIONES} iteraciones...")
    stats_json = estadisticas(benchmark_json(hit5))

    print(f"Midiendo latencia gRPC/Protobuf (hit8) -- {N_ITERACIONES} iteraciones...")
    stats_grpc = estadisticas(benchmark_grpc())

    reduccion_bytes = 100 * (1 - bytes_pb / bytes_json)
    diff_latencia = 100 * (1 - stats_grpc["promedio_ms"] / stats_json["promedio_ms"])

    lineas = []
    lineas.append("Comparacion hit5 (JSON/TCP) vs hit8 (gRPC/Protocol Buffers)")
    lineas.append("=" * 65)
    lineas.append(f"Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"Iteraciones por benchmark: {N_ITERACIONES}")
    lineas.append('Mensaje logico usado en ambos casos: '
                   '{"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}')
    lineas.append("")
    lineas.append("1) Tamano del mensaje en el cable")
    lineas.append("-" * 65)
    lineas.append(f"  JSON + delimitador '\\n' (hit5): {bytes_json} bytes")
    lineas.append(f"  Protocol Buffers (hit8):         {bytes_pb} bytes")
    lineas.append(f"  Reduccion con Protobuf:          {reduccion_bytes:.1f}%")
    lineas.append("")
    lineas.append("2) Latencia por llamada (round-trip cliente-servidor, localhost)")
    lineas.append("-" * 65)
    for nombre, s in (("JSON/TCP (hit5)", stats_json), ("gRPC/Protobuf (hit8)", stats_grpc)):
        lineas.append(f"  {nombre}:")
        lineas.append(
            f"    n={s['n']}  min={s['min_ms']:.3f}ms  promedio={s['promedio_ms']:.3f}ms  "
            f"mediana={s['mediana_ms']:.3f}ms  p95={s['p95_ms']:.3f}ms  "
            f"max={s['max_ms']:.3f}ms  desvio={s['desvio_ms']:.3f}ms"
        )
    lineas.append(
        f"  Diferencia de promedio (gRPC vs JSON): {diff_latencia:+.1f}% "
        "(positivo = gRPC mas rapido)"
    )
    lineas.append("")

    contenido = "\n".join(lineas)
    print("\n" + contenido)

    salida = Path(__file__).resolve().parent / "resultados_comparacion.txt"
    salida.write_text(contenido + "\n", encoding="utf-8")
    print(f"\nResultados guardados en {salida}")


if __name__ == "__main__":
    main()
