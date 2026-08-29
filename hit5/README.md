# HIT 5 — Serialización JSON

## Enunciado

> Modifiquen el programa C para que los mensajes se envíen en formato JSON,
> serializando y deserializando al enviar/recibir.

## Contenido

- `NodoC.py`: misma estructura cliente+servidor del [HIT 4](../hit4/README.md),
  pero el saludo ahora viaja como JSON en vez de texto plano:
  - `enviar_json(sock, datos)`: serializa `datos` con `json.dumps` y lo manda
    delimitado por `\n` (framing por línea).
  - `recibir_json(sock, buffer)`: acumula bytes en un `bytearray` hasta
    encontrar un `\n`, y recién ahí hace `json.loads` de esa línea. Esto es
    necesario porque TCP es un stream de bytes sin límites de mensaje: un
    `recv()` puede traer un mensaje partido o varios pegados, y el delimitador
    `\n` es lo que permite reconstruir mensajes completos.
  - El saludo pasó de ser el string `"Hola, soy C"` a un objeto:
    `{"tipo": "saludo", "origen": "C", "texto": "Hola, soy C"}`.
  - Se agregó manejo de `json.JSONDecodeError`: si llega un mensaje mal
    formado, se descarta la conexión y se reconecta (del lado cliente) o se
    corta esa conexión (del lado servidor), igual que ante un corte de red.

## Cómo ejecutar

Igual que en el HIT 4, con dos instancias apuntándose entre sí:

```bash
# Terminal 1
python NodoC.py --puerto 6000 --peer-host 127.0.0.1 --peer-puerto 6001

# Terminal 2
python NodoC.py --puerto 6001 --peer-host 127.0.0.1 --peer-puerto 6000
```

## Cómo probar de punta a punta

1. Levantar las dos instancias y confirmar que los mensajes impresos ahora
   muestran el diccionario deserializado, no un string plano, por ejemplo:

   ```
   [Cliente] Respuesta de 127.0.0.1:6001: {'tipo': 'saludo', 'origen': 'C', 'texto': 'Hola, soy C'}
   [Servidor] Saludo recibido de ('127.0.0.1', ...): {'tipo': 'saludo', 'origen': 'C', 'texto': 'Hola, soy C'}
   ```

2. Confirmar que la reconexión ante caídas sigue funcionando igual que en los
   hits anteriores (matar una instancia, ver que la otra reintenta, volver a
   levantarla y ver que retoma el intercambio) — la serialización no debería
   haber roto la robustez de los hits previos.
3. Prueba específica de framing/JSON, para validar que el delimitador `\n`
   funciona incluso si el JSON llega fragmentado en varios paquetes: abrir una
   conexión manual contra el puerto de escucha de un nodo C y mandar el mismo
   mensaje partido en dos `send()`:

   ```bash
   python -c "
   import socket, time
   s = socket.socket(); s.connect(('127.0.0.1', 6000))
   s.sendall(b'{\"tipo\": \"sal')
   time.sleep(0.2)
   s.sendall(b'udo\", \"origen\": \"C\", \"texto\": \"hola\"}\n')
   print(s.recv(1024))
   "
   ```

   El nodo C debe responder igual que si el mensaje hubiese llegado entero de
   una sola vez (`recibir_json` lo reensambla antes de deserializar).
4. Prueba de mensaje inválido: repetir el envío manual anterior pero mandando
   JSON corrupto (ej. `b'{esto no es json}\n'`). El nodo C debe loguear
   `Mensaje JSON invalido...` y cerrar esa conexión sin caerse el proceso.
