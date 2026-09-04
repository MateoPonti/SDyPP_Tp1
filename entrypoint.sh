#!/bin/bash
set -eo pipefail

# Validar y activar entorno virtual
TARGET_VENV="${VIRTUAL_ENV:-${VENV_PATH:-/home/${APP_USER:-appuser}/venv}}"

if [ -f "${TARGET_VENV}/bin/activate" ]; then
    # shellcheck source=/dev/null
    source "${TARGET_VENV}/bin/activate"
else
    echo "[ERROR] No se encontró el entorno virtual en: ${TARGET_VENV}" >&2
    exit 1
fi

# Instalar dependencias desde el archivo configurado (por defecto requirements.txt)
TARGET_REQ="${APP_DIR:-/app}/${REQUIREMENTS_FILE:-requirements.txt}"

if [ -f "$TARGET_REQ" ]; then
    echo "=================================================="
    echo "Instalando dependencias desde: $TARGET_REQ"
    echo "=================================================="
    # --require-virtualenv garantiza que pip solo instale dentro del venv aislado
    pip install --no-cache-dir --require-virtualenv -r "$TARGET_REQ"
else
    echo "[INFO] No se encontró archivo de dependencias en: $TARGET_REQ"
fi

# Si no se especificaron argumentos o se pasa únicamente 'pytest', ejecutar suite configurada
if [ $# -eq 0 ] || [ "$1" = "pytest" -a $# -eq 1 ]; then
    TEST_TARGET="${DEFAULT_TEST_TARGET:-tests/}"
    echo "=================================================="
    echo "Ejecutando suite de pruebas en: $TEST_TARGET"
    echo "=================================================="
    exec pytest "$TEST_TARGET" -v
else
    exec "$@"
fi
