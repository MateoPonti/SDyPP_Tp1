# HIT 7 — Sistema de inscripciones por ventana de tiempo

## Contenido

- `NodoD.py`: nodo coordinador. Mantiene dos listas: nodos **activos** en la ventana
  actual y nodos **inscriptos** para la próxima ventana. Cada 60s cierra la ventana
  actual (los inscriptos pasan a ser los activos) y abre una nueva. Expone:
  - Registro TCP (`--puerto`) para que los nodos C se inscriban o consulten.
  - Endpoint HTTP `/health` (`--http-puerto`, por defecto `--puerto + 1`).
  - Persistencia de todo lo que ocurre en `inscripciones.txt` (JSON Lines).
- `NodoC.py`: nodo participante. Se registra en D, y cuando se activa la ventana en
  la que quedó inscripto, consulta a D quiénes son sus pares reales y los saluda.

## Protocolo (JSON sobre TCP, delimitado por `\n`)

| Mensaje enviado a D | Respuesta de D | Efecto |
|---|---|---|
| `{"tipo":"registro","ip":..,"puerto":..}` | `{"tipo":"peers","peers":[...],"ventana_asignada":<epoch>}` | Inscribe al nodo para la **próxima** ventana. `peers` son los nodos activos **ahora** (no los futuros compañeros de ventana). |
| `{"tipo":"consulta"}` | `{"tipo":"peers","peers":[...]}` | Solo lectura: devuelve los nodos activos en la ventana actual, sin inscribir nada. |

`inscripciones.txt` acumula dos tipos de eventos, uno por línea:

```json
{"tipo": "inscripcion", "ip": "...", "puerto": ..., "hora_registro": "...", "ventana_asignada": "..."}
{"tipo": "apertura_ventana", "inicio_ventana": "...", "miembros": [...]}
```

## Cómo ejecutar

Requiere Python 3. Sin dependencias externas.

1. Levantar el nodo D (elige un puerto libre, ej. 9000):

   ```bash
   python NodoD.py --puerto 9000
   ```

   D queda escuchando registros en `0.0.0.0:9000` y el health check en
   `http://0.0.0.0:9001/health`. Al arrancar, programa el cierre de la primera
   ventana para el próximo minuto en punto (ej. si son las 11:28:34, la primera
   ventana se activa a las 11:29:00).

2. En otra terminal, levantar uno o más nodos C apuntando a D:

   ```bash
   python NodoC.py --d-host 127.0.0.1 --d-puerto 9000
   ```

   Cada nodo C abre su propio servidor en un puerto aleatorio, se registra en D,
   y queda a la espera de que se active su ventana.

## Cómo probar de punta a punta

### Prueba con varios nodos C en la misma máquina

1. Borrar cualquier `inscripciones.txt` previo (para partir de un estado limpio):

   ```bash
   rm -f inscripciones.txt
   ```

2. Levantar D:

   ```bash
   python NodoD.py --puerto 9000
   ```

3. Levantar 2 o 3 nodos C en terminales separadas, con unos segundos de diferencia
   entre uno y otro (para simular registros en momentos distintos dentro de la
   misma ventana de inscripción):

   ```bash
   python NodoC.py --d-host 127.0.0.1 --d-puerto 9000
   ```

4. Observar la consola de cada nodo C: al registrarse, imprime la ventana que le
   asignó D (ej. `11:29:00`) y los pares que ya estaban activos en ese momento
   (probablemente ninguno, si es la primera tanda).

5. Esperar a que llegue el minuto en punto de la ventana asignada. La consola de D
   imprime algo como:

   ```
   [D] Ventana 11:29:00 activada con 2 nodo(s): [{'ip': '127.0.0.1', 'puerto': ...}, ...]
   ```

   y cada nodo C imprime los pares reales de su ventana (obtenidos vía `consulta`)
   y comienza a saludarlos.

6. Verificar `inscripciones.txt`: debe tener una línea `"tipo": "inscripcion"` por
   cada nodo C que se registró, y una línea `"tipo": "apertura_ventana"` con la
   lista exacta de miembros que quedaron activos en esa ventana (debe coincidir con
   los nodos que se registraron antes del cierre, ni más ni menos).

7. (Opcional) Registrar un nuevo nodo C **después** de que se cerró la ventana
   anterior y verificar que D le asigna la ventana **siguiente** (un minuto más
   tarde), no la que ya cerró.

### Verificación del cierre de inscripciones (registro tardío)

Para comprobar puntualmente que D cierra las inscripciones al llegar el minuto en
punto y pasa cualquier registro posterior a la ventana siguiente:

1. Levantar D.
2. Registrar un nodo C unos segundos antes de que cambie el minuto (ej. a las
   `11:28:55`) y confirmar que `ventana_asignada` es `11:29:00`.
3. Esperar a que pase `11:29:00` y registrar otro nodo C (ej. a las `11:29:05`) y
   confirmar que a este D le asigna `ventana_asignada = 11:30:00`.
4. Revisar `inscripciones.txt`: debe haber dos `apertura_ventana` separadas por un
   minuto, cada una con el/los miembro/s correspondiente/s a su ventana.

### Prueba manual del endpoint de solo consulta

Sin necesidad de levantar un nodo C completo, se puede hablar el protocolo
directamente para verificar que `consulta` nunca inscribe ni devuelve datos de
ventanas futuras:

```bash
python -c "
import socket, json

def enviar(msg, puerto=9000):
    s = socket.socket(); s.connect(('127.0.0.1', puerto))
    s.sendall((json.dumps(msg) + '\n').encode())
    print(s.recv(1024))
    s.close()

enviar({'tipo': 'registro', 'ip': '1.2.3.4', 'puerto': 111})
enviar({'tipo': 'consulta'})   # debe devolver peers=[] hasta que cierre la ventana
"
```

Repetir el `consulta` después de que pase el minuto en punto: ahora debe devolver
`{"ip": "1.2.3.4", "puerto": 111}` como activo.

## Notas de verificación

- `inscripciones.txt` es la fuente de verdad para auditar la corrida: cada
  inscripción queda con su hora real y la ventana a la que fue asignada, y cada
  apertura de ventana deja registrados los miembros exactos que quedaron activos
  (sin arrastrar nodos de ventanas anteriores).
- Los nodos C nunca conocen a priori los pares de su propia ventana futura: el
  `peers` que reciben al registrarse corresponde a la ventana *actual* de D. Solo
  se enteran de sus verdaderos compañeros de ventana cuando, ya activada, hacen
  el `consulta` correspondiente.
