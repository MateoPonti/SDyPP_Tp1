# Tests automatizados

Suite mínima de pruebas unitarias y de integración que cubre las
funcionalidades críticas del proyecto, pedidas en el enunciado del TP.

## Cómo ejecutar

Desde la raíz del repo:

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Deberían pasar 33 tests, sin necesidad de levantar procesos manualmente:
todos los tests usan `socket.socketpair()` (sockets TCP reales conectados
en memoria, sin puertos ni red real) o servidores HTTP/gRPC levantados en
un puerto aleatorio del propio proceso de test, así que corren solos y
en paralelo sin pisarse entre corridas.

## Qué cubre cada archivo

- **`test_hit1_saludo_tcp.py`**: handshake elemental entre cliente A y servidor B
  (envío de `"Hola B, soy A"`, recepción de `"Hola A, soy B"` y cierre tras
  un único intercambio).
- **`test_hit2_reconexion_cliente.py`**: envío del saludo continuo, detección de
  cierre de conexión por parte de B (`ConnectionResetError`) y lógica de
  reintentos ante fallos de conexión (`conectar`).
- **`test_hit3_servidor_tolerancia.py`**: servidor tolerante a fallos que
  procesa múltiples saludos en loop, tolera cierres limpios y desconexiones
  abruptas sin interrumpir el proceso.
- **`test_hit4_nodoc_bidireccional.py`**: nodo C unificado actuando en simultáneo
  como servidor (`atender_conexion`) y cliente (`enviar_saludo`), intercambio
  cruzado en paralelo entre dos nodos, y parseo de argumentos CLI.
- **`test_hit5_json_framing.py`**: el framing manual por `\n`
  (`enviar_json` / `recibir_json`) que sostiene toda la comunicación desde
  el hit 5 en adelante. Incluye el caso de mensaje fragmentado en dos
  paquetes, dos mensajes pegados en un solo `recv()`, conexión cerrada y
  JSON inválido — son los casos borde que más fácil se rompen al tocar el
  protocolo.
- **`test_hit6_registro_contactos.py`**: que el nodo D le devuelva a cada
  nodo C la "foto" correcta de peers (sin incluirse a sí mismo), que la
  lista en RAM se actualice con cada alta, y que `/health` devuelva el
  JSON esperado (y 404 en cualquier otra ruta).
- **`test_hit7_ventanas_inscripcion.py`**: la regla central del hit — un
  nodo que se registra queda anotado para la *próxima* ventana y sólo ve
  como peers a los ya *activos* (nunca a sus futuros compañeros) — más el
  swap de ventanas y la persistencia en `inscripciones.txt`.
- **`test_hit8_grpc_protobuf.py`**: round-trip de serialización de
  Protobuf, que efectivamente pese menos bytes que el JSON equivalente,
  la lógica del servicer aislada, y un round-trip real de gRPC (servidor +
  cliente reales sobre un puerto aleatorio).
- **`helpers.py`**: no es un archivo de test; es un loader que permite
  importar los módulos en el mismo proceso de test sin que se pisen entre sí
  y reiniciando el estado global en cada test.

