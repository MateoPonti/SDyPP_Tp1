# HIT 8 — gRPC con Protocol Buffers

## Enunciado

> Refactoricen la comunicación del Hit #5 (mensajes JSON sobre TCP)
> reemplazándola por gRPC con Protocol Buffers. Para ello:
> - Definan un archivo `.proto` que describa los mensajes y servicios de
>   comunicación entre los nodos C.
> - Generen los stubs de cliente y servidor con el compilador `protoc`.
> - Reemplacen la serialización/deserialización JSON manual por las llamadas
>   gRPC generadas.
> - Comparen en el informe: tamaño de los mensajes en bytes (JSON vs
>   Protobuf), latencia de las llamadas y experiencia de desarrollo (código
>   manual vs código generado).

## Contenido

- `nodos.proto`: define el mensaje `Saludo` (mismos campos que el dict JSON
  de hit5: `tipo`, `origen`, `texto`) y el servicio `NodoSaludo` con un único
  RPC, `Saludar(Saludo) returns (Saludo)`.
- `nodos_pb2.py` / `nodos_pb2_grpc.py`: generados con `protoc` a partir del
  `.proto` (no se editan a mano).
- `NodoC.py`: el mismo programa de [hit5](../hit5/README.md) (cliente +
  servidor en un solo proceso, con reconexión), pero con JSON/TCP manual
  reemplazado por gRPC.
- `benchmark_comparacion.py`: script que mide tamaño de mensaje y latencia
  de hit5 vs hit8 usando las funciones/clases reales de cada uno, y vuelca
  los resultados a `resultados_comparacion.txt`.

## Cómo generar los stubs (si se modifica `nodos.proto`)

Requiere `grpcio-tools` (`pip install grpcio grpcio-tools`):

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. nodos.proto
```

Esto regenera `nodos_pb2.py` (clases de mensajes) y `nodos_pb2_grpc.py`
(stub de cliente `NodoSaludoStub` y clase base de servidor
`NodoSaludoServicer`).

## Qué cambió respecto a JSON/TCP manual (hit5)

| | Hit 5 (JSON/TCP) | Hit 8 (gRPC/Protobuf) |
|---|---|---|
| Definición del mensaje | dict de Python | `message Saludo` en `nodos.proto` |
| Serialización | `json.dumps(...).encode()` a mano | la hace gRPC internamente al enviar |
| Framing (delimitar mensajes en el stream TCP) | `\n` a mano + reensamblado en `bytearray` | no hace falta: HTTP/2 (la capa de transporte de gRPC) ya delimita mensajes |
| Servidor | `socket.accept()` en loop + `threading.Thread` por conexión | clase `NodoSaludoServicer` con un método `Saludar(request, context)`, generada a partir del `.proto` |
| Arranque del servidor | loop bloqueante en un `threading.Thread` aparte | `grpc.server(...)` no bloqueante — gRPC administra sus propios hilos |
| Cliente | `socket.connect()` + reconexión manual (cerrar y recrear el socket) | `grpc.insecure_channel(...)` persistente + `stub.Saludar(...)`, se llama como una función local |
| Errores de red | `ConnectionResetError`, `BrokenPipeError`, `ConnectionAbortedError`, `OSError` | un único `grpc.RpcError`, con `.code()` y `.details()` |

## Cómo ejecutar

```bash
# Terminal 1
python NodoC.py --puerto 7000 --peer-host 127.0.0.1 --peer-puerto 7001

# Terminal 2
python NodoC.py --puerto 7001 --peer-host 127.0.0.1 --peer-puerto 7000
```

Cada nodo debe imprimir, cada ~3s, el saludo enviado y la respuesta recibida
(ver [detalle en la sección de pruebas de hit5](../hit5/README.md), el
comportamiento es el mismo, solo cambia el transporte).

## Comparación (tamaño de mensaje, latencia, experiencia de desarrollo)

### Cómo reproducir la medición

```bash
python benchmark_comparacion.py
```

El script:
1. Serializa el mismo mensaje lógico (`{"tipo": "saludo", "origen": "C",
   "texto": "Hola, soy C"}`) como lo serializa hit5 (JSON + `\n`) y como lo
   serializa hit8 (`Saludo.SerializeToString()`), y compara el tamaño en
   bytes.
2. Levanta un servidor/cliente JSON-TCP real (reusando `enviar_json`/
   `recibir_json` de `hit5/NodoC.py`) y un servidor/cliente gRPC real
   (reusando las clases de `hit8/NodoC.py`), y mide 200 round-trips
   consecutivos de cada uno en localhost, sin el `sleep(3)` del loop de la
   app (ese intervalo es solo ritmo de la aplicación, no parte del
   protocolo).
3. Guarda todo en `resultados_comparacion.txt`.

### Resultados obtenidos

```
Comparacion hit5 (JSON/TCP) vs hit8 (gRPC/Protocol Buffers)
=================================================================
Iteraciones por benchmark: 200
Mensaje logico usado en ambos casos: {"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}

1) Tamano del mensaje en el cable
-----------------------------------------------------------------
  JSON + delimitador '\n' (hit5): 58 bytes
  Protocol Buffers (hit8):         24 bytes
  Reduccion con Protobuf:          58.6%

2) Latencia por llamada (round-trip cliente-servidor, localhost)
-----------------------------------------------------------------
  JSON/TCP (hit5):
    n=200  min=0.045ms  promedio=0.117ms  mediana=0.090ms  p95=0.279ms  max=0.759ms  desvio=0.097ms
  gRPC/Protobuf (hit8):
    n=200  min=0.343ms  promedio=1.259ms  mediana=0.714ms  p95=3.786ms  max=10.156ms  desvio=1.379ms
  Diferencia de promedio (gRPC vs JSON): -974.6% (JSON fue mas rapido en este benchmark)
```

(Los números exactos van a variar levemente entre corridas y máquinas —
correr `benchmark_comparacion.py` de nuevo actualiza
`resultados_comparacion.txt` con los valores reales de tu equipo.)

### Análisis

- **Tamaño de mensaje**: Protobuf gana claramente — el mismo saludo pesa
  **58% menos bytes** que su equivalente JSON. Esto es esperado: Protobuf es
  un formato binario con tags numéricos (1 byte por campo chico) en vez de
  nombres de clave repetidos como texto (`"tipo":`, `"origen":`, `"texto":`),
  y no hay comillas, llaves, ni el delimitador `\n` que JSON necesita agregar
  a mano para poder reensamblar mensajes sobre TCP.

- **Latencia**: contra la intuición, en este benchmark **JSON/TCP crudo fue
  más rápido por llamada que gRPC** (promedio ~0.12ms vs ~1.26ms). La razón
  no es Protobuf en sí (serializar/deserializar un mensaje de 3 campos es
  prácticamente gratis) sino el **costo fijo por llamada de HTTP/2**: cada
  RPC de gRPC pasa por manejo de streams HTTP/2, control de flujo, y una capa
  de interceptors/threading del lado del servidor (`ThreadPoolExecutor`),
  mientras que el benchmark de JSON reutiliza un socket TCP crudo sin ninguna
  capa intermedia. Ese overhead fijo por llamada es mayor que el ahorro que
  da tener un mensaje más chico, sobre todo con mensajes tan pequeños y en
  localhost (sin latencia de red real de por medio). Es un resultado
  consistente con lo documentado para gRPC: su ventaja de performance se nota
  más con mensajes grandes, alto volumen de llamadas concurrentes,
  keep-alive de conexión en escenarios distribuidos reales (no localhost) y,
  sobre todo, en las features que no tiene el JSON/TCP manual (streaming
  bidireccional, multiplexado de muchos RPCs sobre una sola conexión,
  balanceo de carga, deadlines/cancelación integrados), no en la latencia
  mínima de una sola llamada request/response chica.

- **Experiencia de desarrollo**:
  - *JSON/TCP manual (hit5)*: hubo que escribir a mano el framing por `\n`
    (`enviar_json`/`recibir_json`), decidir y mantener a mano la forma del
    mensaje (`{"tipo": ...}`) sin ninguna validación de tipos ni de campos
    obligatorios, y manejar por separado varios tipos de excepción de socket
    (`ConnectionResetError`, `BrokenPipeError`, `ConnectionAbortedError`,
    `OSError`, `json.JSONDecodeError`).
  - *gRPC (hit8)*: el `.proto` es la única fuente de verdad del contrato
    (mensaje + firma del RPC); `protoc` generó automáticamente las clases de
    mensajes con sus tipos y el código de cliente/servidor, así que no hubo
    que escribir serialización, framing, ni parsing a mano. El código de
    aplicación quedó más corto y se reduce a implementar la lógica de negocio
    (`Saludar`). El costo es la etapa de generación de código (`protoc`) como
    paso extra del build, y un único tipo de excepción (`grpc.RpcError`) más
    genérico para manejar del lado cliente.
