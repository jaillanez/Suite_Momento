#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_DIR}/backend"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
VENV_DIR="${BACKEND_DIR}/.venv"
API_PID=""
API_PORT=""
WEB_PORT=""

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

first_available_port() {
  local port="$1"
  while lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  printf '%s' "$port"
}

for command_name in python3 node npm lsof; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "No se encontró $command_name. No se instalará automáticamente."
  fi
done

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)'; then
  fail "Momento necesita Python 3.13 o superior. Se usará el Python ya instalado."
fi

if ! node -e 'const [major, minor] = process.versions.node.split(".").map(Number); const ok = (major === 20 && minor >= 19) || (major >= 22 && (major > 22 || minor >= 12)); process.exit(ok ? 0 : 1)'; then
  fail "Vite requiere Node 20.19+ o 22.12+. Revisa la versión de Node instalada."
fi

printf 'Python: '
python3 --version
printf 'Node: '
node --version
printf 'npm: '
npm --version
if command -v psql >/dev/null 2>&1; then
  printf 'PostgreSQL cliente: '
  psql --version
else
  printf 'No se encontró psql; la aplicación podrá iniciar, pero PostgreSQL quedará pendiente.\n'
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  printf '\nCreando el entorno Python local del proyecto...\n'
  python3 -m venv "$VENV_DIR"
fi

printf '\nPreparando dependencias del backend dentro de backend/.venv...\n'
(
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -e ".[dev]"
)

if [[ ! -d "${FRONTEND_DIR}/node_modules" || ! -f "${FRONTEND_DIR}/package-lock.json" || "${FRONTEND_DIR}/package.json" -nt "${FRONTEND_DIR}/package-lock.json" ]]; then
  printf '\nPreparando dependencias web dentro de frontend/node_modules...\n'
  (
    cd "$FRONTEND_DIR"
    npm install --no-audit --no-fund
  )
fi

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "$API_PID" ]]; then
    pkill -TERM -P "$API_PID" >/dev/null 2>&1 || true
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

API_PORT="$(first_available_port 8020)"
WEB_PORT="$(first_available_port 5173)"
if [[ "$API_PORT" != "8020" ]]; then
  printf 'El puerto 8020 está ocupado; usaré el puerto %s para la API.\n' "$API_PORT"
fi
if [[ "$WEB_PORT" != "5173" ]]; then
  printf 'El puerto 5173 está ocupado; usaré el puerto %s para la aplicación web.\n' "$WEB_PORT"
fi

printf '\nIniciando API en http://127.0.0.1:%s ...\n' "$API_PORT"
(
  cd "$BACKEND_DIR"
  exec "$VENV_DIR/bin/uvicorn" momento_api.main:app --reload --host 127.0.0.1 --port "$API_PORT"
) &
API_PID=$!

printf 'Iniciando aplicación web en http://127.0.0.1:%s ...\n' "$WEB_PORT"
printf 'Presiona Control+C para detener ambos servicios.\n\n'
cd "$FRONTEND_DIR"
MOMENTO_API_PROXY_TARGET="http://127.0.0.1:${API_PORT}" npm run dev -- --host 127.0.0.1 --port "$WEB_PORT" --strictPort
