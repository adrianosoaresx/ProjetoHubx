#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-${PROJECT_ROOT}/.venv}" 
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"
NEXT_TELEMETRY_DISABLED="${NEXT_TELEMETRY_DISABLED:-1}"

log() {
    printf '\n\033[1;34m[hubx]\033[0m %s\n' "$1"
}

if [[ ! -f "${ENV_FILE}" ]]; then
    log "Arquivo ${ENV_FILE} não encontrado. Copie deploy/install/env.production.example para ${ENV_FILE} e ajuste as variáveis antes de executar este script."
    exit 1
fi

log "Criando ambiente virtual em ${VENV_PATH}"
if [[ ! -d "${VENV_PATH}" ]]; then
    "${PYTHON_BIN}" -m venv "${VENV_PATH}"
fi

# shellcheck source=/dev/null
source "${VENV_PATH}/bin/activate"

log "Atualizando pip e instalando dependências Python"
pip install --upgrade pip wheel
pip install -r "${PROJECT_ROOT}/requirements.txt"

export NEXT_TELEMETRY_DISABLED

if command -v npm >/dev/null 2>&1; then
    log "Instalando dependências front-end"
    if [[ -f "${PROJECT_ROOT}/package-lock.json" ]]; then
        (cd "${PROJECT_ROOT}" && npm ci)
    else
        (cd "${PROJECT_ROOT}" && npm install)
    fi

    log "Gerando build do front-end"
    (cd "${PROJECT_ROOT}" && npm run build)
else
    log "npm não encontrado. Pule a etapa de build do front-end ou instale Node.js 18+."
fi

log "Aplicando migrações do banco de dados"
python "${PROJECT_ROOT}/manage.py" migrate --noinput

log "Coletando arquivos estáticos"
python "${PROJECT_ROOT}/manage.py" collectstatic --noinput

log "Verificando projeto"
python "${PROJECT_ROOT}/manage.py" check --deploy

log "Setup concluído. Use um servidor ASGI (ex.: uvicorn ou daphne) e configure um serviço systemd conforme necessário."
