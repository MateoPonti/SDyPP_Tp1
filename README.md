# Trabajo Práctico 1 de Sistemas Distribuidos y Programación Paralela 

## Integrantes

- Rodriguez Juan Cruz  
- Ponti Mateo Daniel

## Lenguaje de Programación
_Python_

---

## Entorno de Pruebas con Docker

Se provee un entorno dockerizado para ejecutar los tests automatizados y scripts de Python de manera replicable en cualquier host, sin valores hardcodeados y priorizando la seguridad.

### Principios de Seguridad y Diseño
- **Sin valores hardcodeados:** Todas las versiones, usuarios, identificadores de sistema (UID/GID) y rutas se parametrizan mediante `ARG` y `ENV` y pueden definirse en un archivo `.env`.
- **Protección de secretos y credenciales:** El archivo `.env` está expresamente excluido del build en `.dockerignore` y del repositorio en `.gitignore`. Se provee una plantilla segura en [.env.example](file:///c:/Users/Juan/Documents/UNLu/SD/2026/TP1/TP1/TP/SDyPP_Tp1/.env.example).
- **Mínimos privilegios (no-root):** La aplicación corre bajo un usuario y grupo dedicado sin privilegios de administración ni acceso a `sudo`.
- **Aislamiento del entorno virtual:** El `venv` reside en un directorio propio (`VENV_PATH`), fuera del directorio de la aplicación, evitando conflictos de permisos al montar volúmenes.
- **Instalación segura con pip:** El script de arranque utiliza `--require-virtualenv` para bloquear cualquier intento accidental de instalación en el intérprete del sistema.
- **Inmutabilidad del entrypoint:** El script de inicialización se copia con permisos restrictivos de solo lectura y ejecución (`555`).

---

### Configuración del archivo `.env`

Antes de construir o ejecutar, podés copiar la plantilla y ajustar las variables a tus necesidades:

```bash
# En Linux/macOS/PowerShell
cp .env.example .env
```

Variables disponibles en `.env`:
- `PYTHON_VERSION`: Versión base de Python (por defecto `3.11-slim`).
- `APP_USER` / `APP_GROUP`: Nombre del usuario y grupo sin privilegios.
- `APP_UID` / `APP_GID`: Identificadores numéricos del usuario y grupo (por defecto `1000`).
- `APP_DIR`: Directorio de trabajo interno del contenedor (`/app`).
- `VENV_PATH`: Ubicación del entorno virtual aislado.
- `REQUIREMENTS_FILE`: Archivo de dependencias a instalar al iniciar (`requirements.txt`).
- `DEFAULT_TEST_TARGET`: Directorio o archivo de tests por defecto (`tests/`).

---

### Construir la imagen

**Opción A: Con Docker Compose (automáticamente carga `.env`):**
```bash
docker compose build
```

**Opción B: Con Docker CLI tradicional:**
```bash
docker build -t sdypp-tests .
```

---

### Ejecución de tests y comandos

#### 1. Ejecutar la suite completa de tests
- **Con Docker Compose:**
  ```bash
  docker compose run --rm tests
  ```
- **Con Docker CLI:**
  ```bash
  docker run --rm --env-file .env sdypp-tests
  ```

#### 2. Ejecutar un archivo o test específico
- **Con Docker Compose:**
  ```bash
  docker compose run --rm tests pytest tests/test_hit5_json_framing.py -v
  docker compose run --rm tests pytest -k "grpc" -v
  ```
- **Con Docker CLI:**
  ```bash
  docker run --rm --env-file .env sdypp-tests pytest tests/test_hit5_json_framing.py -v
  ```

#### 3. Ejecutar scripts de Python
- **Con Docker Compose:**
  ```bash
  docker compose run --rm tests python hit6/NodoD.py
  ```
- **Con Docker CLI:**
  ```bash
  docker run --rm --env-file .env sdypp-tests python hit6/NodoD.py
  ```

#### 4. Modo interactivo (Terminal Bash para depuración)
- **Con Docker Compose:**
  ```bash
  docker compose run --rm tests bash
  ```
- **Con Docker CLI:**
  ```bash
  docker run -it --rm --env-file .env sdypp-tests bash
  ```

#### 5. Desarrollo en caliente con volumen local montado
Docker Compose ya incluye el volumen montado hacia `./` de forma predeterminada. Si usás Docker CLI:

- **Linux / macOS / PowerShell:**
  ```bash
  docker run --rm --env-file .env -v "${PWD}:/app" sdypp-tests
  ```
- **Windows (CMD):**
  ```cmd
  docker run --rm --env-file .env -v "%cd%:/app" sdypp-tests
  ```
