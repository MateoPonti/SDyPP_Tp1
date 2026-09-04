# ------------------------------------------------------------------------------
# Argumentos de construcción configurables (Build Arguments)
# ------------------------------------------------------------------------------
ARG PYTHON_VERSION=3.11-slim
FROM python:${PYTHON_VERSION}

# Parámetros de usuario no privilegiado y rutas internas
ARG APP_USER=appuser
ARG APP_GROUP=appgroup
ARG APP_UID=1000
ARG APP_GID=1000
ARG APP_DIR=/app
ARG VENV_PATH=/home/${APP_USER}/venv

# Variables de entorno en tiempo de ejecución (configurables vía .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_USER="${APP_USER}" \
    APP_GROUP="${APP_GROUP}" \
    APP_UID="${APP_UID}" \
    APP_GID="${APP_GID}" \
    APP_DIR="${APP_DIR}" \
    VENV_PATH="${VENV_PATH}" \
    VIRTUAL_ENV="${VENV_PATH}" \
    PATH="${VENV_PATH}/bin:${PATH}" \
    REQUIREMENTS_FILE="requirements.txt" \
    DEFAULT_TEST_TARGET="tests/"

# Seguridad: Crear grupo y usuario con privilegios mínimos (no-root, sin sudo)
RUN groupadd -g ${APP_GID} ${APP_GROUP} && \
    useradd -m -u ${APP_UID} -g ${APP_GROUP} -s /bin/bash ${APP_USER}

# Directorio de trabajo
WORKDIR ${APP_DIR}

# Configurar entorno virtual con permisos exclusivos para el usuario sin privilegios
RUN python -m venv ${VENV_PATH} && \
    chown -R ${APP_UID}:${APP_GID} ${VENV_PATH} ${APP_DIR}

# Copiar script de inicialización con permisos de solo lectura/ejecución (555)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chmod 555 /usr/local/bin/entrypoint.sh

# Copiar el código del proyecto asignando la propiedad al usuario no privilegiado
COPY --chown=${APP_UID}:${APP_GID} . ${APP_DIR}/

# Aplicar usuario con privilegios mínimos para todas las operaciones posteriores
USER ${APP_USER}

# Script de inicialización (activa venv, valida e instala requerimientos)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Comando por defecto al levantar el contenedor
CMD ["pytest"]
