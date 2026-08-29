# HIT 1 — Saludo TCP básico entre A y B

## Enunciado

> Elaboren un código de servidor TCP para B que espere el saludo de A y lo
> responda.
>
> Elaboren un código de cliente TCP para A que se conecte con B y lo salude.

## Contenido

- `ServidorTcp.py`: nodo **B**. Escucha en `0.0.0.0:5000`, acepta **una** conexión,
  recibe el saludo, responde y cierra todo (servidor de un solo uso).
- `ClienteTcp.py`: nodo **A**. Se conecta a `127.0.0.1:5000`, envía el saludo,
  imprime la respuesta y cierra la conexión.

No hay manejo de reconexión ni de errores: es el caso base sobre el que los
hits siguientes van agregando robustez.

## Cómo ejecutar

1. Levantar el servidor B:

   ```bash
   python ServidorTcp.py
   ```

2. En otra terminal, ejecutar el cliente A:

   ```bash
   python ClienteTcp.py
   ```

## Cómo probar de punta a punta

1. Ejecutar `ServidorTcp.py` y verificar que imprime:

   ```
   Servidor B esperando conexiones en el puerto 5000...
   ```

2. Ejecutar `ClienteTcp.py`. Se espera ver en la consola de A:

   ```
   Respuesta de B: Hola A, soy B
   ```

   y en la consola de B:

   ```
   A se conectó desde ('127.0.0.1', <puerto_efímero>)
   Saludo recibido: Hola B, soy A
   ```

3. Ambos procesos terminan solos después del intercambio (no hay loop): B
   cierra el socket de escucha y A cierra su conexión. Confirmar que ambas
   terminales vuelven al prompt sin quedar colgadas.

4. Caso de error esperado: si se ejecuta `ClienteTcp.py` **sin** tener a B
   corriendo, debe fallar con `ConnectionRefusedError` (todavía no hay
   reintentos — eso se agrega en el [HIT 2](../hit2/README.md)).
