# HIT 4 — Programa C bidireccional (cliente + servidor unificados)

## Enunciado

> Refactoriza el código de los programas A y B en un único programa, que
> funcione simultáneamente como cliente y servidor. Esto significa que al
> iniciar el programa C, se le deben proporcionar por parámetros la dirección
> IP y el puerto para escuchar saludos, así como la dirección IP y el puerto
> de otro nodo C. De esta manera, al tener dos instancias de C en ejecución,
> cada una configurada con los parámetros del otro, ambas se saludan
> mutuamente a través de cada canal de comunicación.

## Contenido

- `NodoC.py`: fusiona los roles de A y B de los hits anteriores en un solo
  programa:
  - **Servidor** (`servidor()` + `atender_conexion()`): escucha en
    `--host:--puerto`, acepta conexiones en loop, y por cada una lanza un
    hilo (`threading.Thread`) que responde "Hola, soy C" a cada saludo
    recibido, tolerando que el peer se desconecte (igual que B en el
    [HIT 3](../hit3/README.md)).
  - **Cliente** (`cliente()` + `conectar()`): se conecta a `--peer-host:--peer-puerto`,
    saluda cada `INTERVALO=3s`, y se reconecta ante cortes (igual que A en el
    [HIT 2](../hit2/README.md)).
  - Ambos roles corren en paralelo: el servidor en un hilo daemon, el cliente
    en el hilo principal.

Los mensajes en este hit siguen siendo texto plano (`"Hola, soy C"`); la
serialización a JSON se agrega en el [HIT 5](../hit5/README.md).

## Cómo ejecutar

Se necesitan **dos instancias** de `NodoC.py`, cada una escuchando en un
puerto propio y apuntando a la otra como peer:

```bash
# Terminal 1 (nodo C1, escucha en 6000, saluda a C2 en 6001)
python NodoC.py --puerto 6000 --peer-host 127.0.0.1 --peer-puerto 6001

# Terminal 2 (nodo C2, escucha en 6001, saluda a C1 en 6000)
python NodoC.py --puerto 6001 --peer-host 127.0.0.1 --peer-puerto 6000
```

Parámetros:
- `--host`: interfaz propia para escuchar (default `0.0.0.0`).
- `--puerto`: puerto propio para escuchar (obligatorio).
- `--peer-host` / `--peer-puerto`: IP y puerto del otro nodo C (obligatorios).

## Cómo probar de punta a punta

1. Levantar las dos instancias como en el ejemplo de arriba (el orden no
   importa: cada una reintenta conectarse hasta que la otra esté disponible).
2. Verificar en **ambas** consolas que aparecen, cada ~3s:
   - Del lado cliente: `[Cliente] Respuesta de 127.0.0.1:<puerto>: Hola, soy C`
   - Del lado servidor: `[Servidor] Saludo recibido de (...): Hola, soy C`

   Esto confirma que cada nodo C está saludando al otro **y** siendo saludado
   simultáneamente (dos canales TCP independientes, uno por dirección).
3. Matar una de las dos instancias (`Ctrl+C` o `kill`) y confirmar que la
   instancia restante:
   - seguirá intentando reconectarse como cliente (`[Cliente] No se pudo
     conectar a ... Reintentando en 3s...`), y
   - su lado servidor sigue vivo y listo para aceptar una nueva conexión.
4. Volver a levantar el nodo caído con los mismos parámetros: ambos deben
   retomar el saludo mutuo sin reiniciar el otro proceso.
5. (Opcional) Probar con tres o más instancias en distintos puertos, formando
   pares cruzados manualmente (ej. C1↔C2, C2↔C3), para confirmar que el mismo
   programa sirve para cualquier topología punto a punto — la generalización a
   "N pares sin configurarlos a mano" es justamente lo que resuelve el
   [HIT 6](../hit6/README.md) con el nodo D.
