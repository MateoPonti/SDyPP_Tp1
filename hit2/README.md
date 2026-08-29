# HIT 2 — Reconexión de A ante caídas de B

## Enunciado

> Revise el código de A para implementar una funcionalidad que permita la
> reconexión y el envío del saludo nuevamente en caso de que el proceso B
> cierre la conexión, como por ejemplo, al ser terminado abruptamente.

## Contenido

- `ClienteTcp.py`: nodo **A**. Ahora saluda en loop (cada `INTERVALO=3s`) en
  vez de una sola vez. Si la conexión falla o se cierra
  (`ConnectionRefusedError`, `ConnectionResetError`, `BrokenPipeError`,
  `ConnectionAbortedError`, `OSError`), reintenta conectarse cada
  `RETRY_DELAY=3s` indefinidamente, sin terminar el proceso.
- `ServidorTcp.py`: nodo **B**. Mismo comportamiento que el HIT 1 (acepta una
  sola conexión y termina); sirve para provocar el corte y observar cómo A se
  recupera.

## Cómo ejecutar

1. Levantar B:

   ```bash
   python ServidorTcp.py
   ```

2. Levantar A:

   ```bash
   python ClienteTcp.py
   ```

## Cómo probar de punta a punta

### Caso 1: A arranca antes que B (B no disponible)

1. Ejecutar `ClienteTcp.py` sin tener a B corriendo. Debe imprimir:

   ```
   No se pudo conectar a B (...). Reintentando en 3s...
   ```

   en loop, sin caerse.
2. Levantar `ServidorTcp.py`. En el próximo reintento (máx. 3s), A debe
   conectarse, saludar, e imprimir la respuesta de B.

### Caso 2: B se cae abruptamente mientras A está conectado

1. Levantar B y luego A; confirmar que A imprime `Respuesta de B: Hola A, soy B`
   repetidamente cada 3s.
2. Matar el proceso de B (`Ctrl+C` o `kill`/`taskkill`).
3. Verificar que A **no** se cae: debe imprimir algo como

   ```
   Conexión con B perdida (...). Reconectando...
   No se pudo conectar a B (...). Reintentando en 3s...
   ```

   y seguir reintentando cada 3s sin intervención manual.
4. Levantar `ServidorTcp.py` de nuevo. En el siguiente reintento, A debe
   reconectarse y volver a recibir el saludo — sin haber sido reiniciado.
5. Confirmar con `Ctrl+C` sobre A que termina limpio (`Cliente A detenido
   manualmente.`) y cierra el socket.

Nota: como `ServidorTcp.py` en este hit sigue siendo de un solo uso (termina
tras la primera conexión), cada reconexión de A requiere volver a levantar B a
mano. El servidor que sobrevive a las desconexiones de A se resuelve en el
[HIT 3](../hit3/README.md).
