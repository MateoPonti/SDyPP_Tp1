# HIT 3 — B sobrevive a la desconexión de A

## Enunciado

> Modifique el código de B para que si el proceso A cierra la conexión (por
> ejemplo matando el proceso) siga funcionando.

## Contenido

- `ServidorTcp.py`: nodo **B**. Ahora corre en un `while True` externo que
  vuelve a hacer `accept()` después de cada conexión, y un `while True` interno
  que atiende los saludos de esa conexión. Si `recv()` devuelve vacío (A cerró
  prolijamente) o salta una excepción de conexión
  (`ConnectionResetError`, `BrokenPipeError`, `ConnectionAbortedError`,
  `OSError` — A cerrado abruptamente), B captura el error, cierra su lado del
  socket y vuelve a esperar una nueva conexión, sin terminar el proceso.
  Se agregó también `SO_REUSEADDR` para poder reiniciar B rápido sin esperar el
  timeout del puerto.
- `ClienteTcp.py`: nodo **A**. Igual que en el [HIT 2](../hit2/README.md)
  (saluda en loop y se reconecta si pierde a B).

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

### Caso 1: A se desconecta abruptamente y B sigue vivo

1. Levantar B y luego A. Confirmar el intercambio de saludos cada 3s en ambas
   consolas.
2. Matar el proceso de A (`Ctrl+C`, `kill -9` o terminar la terminal).
3. Verificar en la consola de B que imprime algo como:

   ```
   Conexión con A (('127.0.0.1', ...)) perdida abruptamente: ...
   Esperando nueva conexión de A...
   ```

   y que el proceso de B **sigue corriendo** (no termina, no lanza excepción
   sin capturar).
4. Levantar `ClienteTcp.py` de nuevo (nueva instancia de A). B debe aceptar la
   nueva conexión sin haber sido reiniciado y retomar el intercambio de
   saludos.

### Caso 2: A cierra prolijamente

1. Con B y A corriendo, interrumpir A con `Ctrl+C` (cierre limpio vía
   `KeyboardInterrupt`, que cierra el socket antes de salir).
2. Confirmar que B detecta el cierre (`recv` vacío → `"A (...) cerró la
   conexión"` o el mensaje de conexión perdida, según el momento exacto del
   cierre) y vuelve a quedar esperando (`Esperando nueva conexión de A...`)
   sin caerse.

### Caso 3: múltiples ciclos

Repetir el apagado/encendido de A varias veces seguidas contra el mismo
proceso de B, para confirmar que el `while True` externo de B tolera
reconexiones repetidas indefinidamente.
