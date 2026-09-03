# Tests automatizados

Suite mínima de pruebas unitarias y de integración que cubre las
funcionalidades críticas del proyecto, pedidas en el enunciado del TP.

## Cómo ejecutar

Desde la raíz del repo:

```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Deberían pasar 17 tests, sin necesidad de levantar procesos manualmente:
todos los tests usan `socket.socketpair()` (sockets TCP reales conectados
en memoria, sin puertos ni red real) o servidores HTTP/gRPC levantados en
un puerto aleatorio del propio proceso de test, así que corren solos y
en paralelo sin pisarse entre corridas.

## Qué cubre cada archivo

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
  importar, por ejemplo, `hit6/NodoD.py` y `hit7/NodoD.py` en el mismo
  proceso de test sin que se pisen entre sí (ambos archivos se llaman
  igual) y reiniciando el estado global (listas en RAM) en cada test.

## Qué queda fuera de esta suite (y por qué)

Los hits 1 a 4 (`ClienteTcp.py` / `ServidorTcp.py` / primera versión de
`NodoC.py`) son scripts de nivel superior sin funciones reutilizables:
ejecutan la lógica de sockets directamente al importarlos, con host/puerto
hardcodeados, y se conectan/bloquean apenas se cargan. Automatizarlos tal
cual están requeriría lanzarlos como subprocesos reales contra puertos
fijos, lo cual es frágil en CI (colisiones de puerto, necesidad de matar
procesos, timing). Su lógica de reconexión y tolerancia a fallos, sin
embargo, es la misma que quedó refactorizada en funciones testeables a
partir del hit 5 (`conectar`, `cliente`, `atender_conexion`), que sí están
cubiertas acá. Si se quiere tests explícitos de hit 1-4 en el futuro, la
forma más simple es agregarles un `if __name__ == "__main__":` (sin cambiar
su comportamiento) para poder importar sus funciones sin que se ejecuten
solas.
