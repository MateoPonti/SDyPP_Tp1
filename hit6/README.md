# HIT 6 — Nodo D: registro de contactos + health check

## Enunciado

> Cree un programa D, el cual actuará como un "Registro de contactos". Para
> ello, en un array en RAM, inicialmente vacío, este nodo D llevará un
> registro de los programas C que estén en ejecución.
>
> Además, el nodo D debe exponer un endpoint HTTP `/health` que devuelva el
> estado del servicio en formato JSON (cantidad de nodos C registrados,
> uptime, estado general). Este endpoint será utilizado como health check
> público del sistema.
>
> Modifique el programa C de manera tal que reciba por parámetros únicamente
> la IP y el puerto del programa D. C debe iniciar la escucha en un puerto
> aleatorio y debe comunicarse con D para informarle su IP y su puerto
> aleatorio donde está escuchando. D le debe responder con las IPs y puertos
> de los otros nodos C que estén corriendo, haga que C se conecte a cada uno
> de ellos y envíe el saludo.
>
> Es decir, el objetivo de este HIT es incorporar un nuevo tipo de nodo (D)
> que actúe como registro de contactos para que al iniciar cada nodo C no
> tenga que indicar las IPs de sus pares. Esto debe funcionar con múltiples
> instancias de C, no solo con 2.

## Contenido

- `NodoD.py`: nodo coordinador nuevo.
  - Mantiene `nodos_registrados`, una lista en RAM (protegida por
    `registro_lock`) de `{"ip": ..., "puerto": ...}`, inicialmente vacía.
  - Servidor TCP (`--puerto`): por cada conexión entrante espera un mensaje
    `{"tipo": "registro", "ip": ..., "puerto": ...}`, toma una foto de los
    nodos ya registrados (antes de agregar al nuevo) y se la devuelve como
    `{"tipo": "peers", "peers": [...]}`. Recién después agrega el nodo nuevo a
    la lista — así el nuevo nodo nunca se recibe a sí mismo como peer.
  - Servidor HTTP (`--http-puerto`, default `--puerto + 1`) con el endpoint
    `GET /health`, que devuelve `{"nodos_registrados": N, "uptime_segundos":
    ..., "estado": "ok"}`.
- `NodoC.py`: ya no recibe la IP/puerto de un peer fijo por parámetro. Ahora:
  1. Levanta su propio servidor en un **puerto aleatorio** (`bind((host, 0))`,
     el SO asigna el puerto).
  2. Calcula su propia IP de salida hacia D (`obtener_ip_propia`, truco con
     socket UDP para no depender de configuración manual de red).
  3. Se registra en D (`--d-host`/`--d-puerto`, únicos parámetros
     obligatorios) enviando su IP y puerto de escucha.
  4. Con la lista de peers que le devuelve D, lanza un hilo `cliente()` por
     cada uno (igual que en el HIT 5) para saludarlos a todos.
  5. Si D no tenía ningún peer todavía, el nodo queda solo escuchando.

## Cómo ejecutar

1. Levantar D (elegir un puerto libre, ej. 8000):

   ```bash
   python NodoD.py --puerto 8000
   ```

   Registro de contactos en `0.0.0.0:8000`, health check en
   `http://0.0.0.0:8001/health` (por defecto `--puerto + 1`).

2. Levantar varios nodos C apuntando a D (sin indicarse IPs entre sí):

   ```bash
   python NodoC.py --d-host 127.0.0.1 --d-puerto 8000
   ```

   Repetir este mismo comando en tantas terminales como nodos C se quieran
   (no hace falta ningún parámetro distinto entre instancias — D resuelve los
   puertos aleatorios y quién saluda a quién).

## Cómo probar de punta a punta

### Registro con múltiples nodos C (no solo 2)

1. Levantar D.
2. Levantar el primer nodo C. Consola esperada:

   ```
   [Servidor] Escuchando saludos en 0.0.0.0:<puerto_aleatorio_1>...
   [Registro] Registrado en D (127.0.0.1:8000). Pares recibidos: []
   [Registro] No habia otros nodos C registrados todavia. ...
   ```

3. Levantar un segundo nodo C. Debe recibir al primero como peer:

   ```
   [Registro] Registrado en D (127.0.0.1:8000). Pares recibidos: [{'ip': '127.0.0.1', 'puerto': <puerto_1>}]
   ```

   y ambos nodos deben empezar a intercambiar saludos JSON cada 3s (uno porque
   se conectó como cliente al otro, el otro porque lo recibe en su servidor).
4. Levantar un **tercer** nodo C. Debe recibir a los **dos** anteriores como
   peers y conectarse a ambos. Confirmar en la consola de los nodos 1 y 2 que
   también reciben el saludo del nodo 3 en su lado servidor (aunque D nunca les
   avisó de él explícitamente — el nodo 3 es quien inicia la conexión hacia
   ellos).
5. Repetir con un cuarto/quinto nodo para confirmar que el mecanismo escala a
   N nodos sin cambiar ningún parámetro salvo D.

### Verificación del endpoint `/health`

Con D y algunos nodos C corriendo:

```bash
curl http://127.0.0.1:8001/health
```

Debe devolver algo como:

```json
{"nodos_registrados": 3, "uptime_segundos": 42.1, "estado": "ok"}
```

- `nodos_registrados` debe coincidir con la cantidad de nodos C levantados
  hasta el momento.
- `uptime_segundos` debe crecer entre consultas sucesivas.
- Pedir una ruta distinta (`curl http://127.0.0.1:8001/otracosa`) debe
  devolver `404`.

### Robustez ante caídas

1. Con varios nodos C corriendo, matar uno de ellos (`Ctrl+C` o `kill`).
2. Confirmar que D **no** se cae (su lista de registrados no se limpia sola en
   este hit — D no hace pruning de nodos caídos, solo registra altas) y que
   los demás nodos C simplemente ven sus hilos `cliente()` reintentando
   conectarse al nodo caído sin afectar al resto de los saludos.
3. Verificar con `/health` que `nodos_registrados` no baja (es esperado: este
   hit no implementa baja de registros, solo alta — el registro es un
   historial de altas, no una lista de "vivos").
