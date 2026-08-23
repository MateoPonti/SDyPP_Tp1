# HIT 4

Refactorización de los programas A (hit1/hit2 `ClienteTcp.py`) y B (hit1/hit2 `ServidorTcp.py`)
en un único programa `NodoC.py` que funciona simultáneamente como cliente y como servidor.

## Contenido

- `NodoC.py`: nodo TCP que, en paralelo:
  - **Servidor**: escucha saludos en la IP/puerto propios (`--host`/`--puerto`) y responde a cada uno.
  - **Cliente**: se conecta a la IP/puerto de otro nodo C (`--peer-host`/`--peer-puerto`) y le envía
    saludos cada 3 segundos, reintentando la conexión si se pierde.

## Instrucciones

Ejecutar dos instancias, cada una apuntando a la otra como peer:

```bash
# Nodo 1: escucha en el puerto 5000, saluda al nodo en el puerto 6000
python NodoC.py --puerto 5000 --peer-host 127.0.0.1 --peer-puerto 6000

# Nodo 2: escucha en el puerto 6000, saluda al nodo en el puerto 5000
python NodoC.py --puerto 6000 --peer-host 127.0.0.1 --peer-puerto 5000
```

Parámetros:

- `--host`: IP propia donde escuchar saludos (default `0.0.0.0`).
- `--puerto`: puerto propio donde escuchar saludos (obligatorio).
- `--peer-host`: IP del otro nodo C (obligatorio).
- `--peer-puerto`: puerto del otro nodo C (obligatorio).

Con ambas instancias corriendo y configuradas una con los datos de la otra, se saludan
mutuamente por dos canales TCP independientes (cada una como cliente del otro y como
servidor propio).
