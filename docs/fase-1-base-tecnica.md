# Fase 1 — Base técnica local

**Estado:** en verificación en la Mac de Jorge.  
**Objetivo:** iniciar el repositorio nuevo con las herramientas ya instaladas y comprobar la conexión local entre React, la API y PostgreSQL.

## Entorno informado

El 26/10/2026 Jorge informó estas versiones:

- macOS 27.0.1, Apple Silicon arm64.
- Python 3.13.5.
- PostgreSQL 18.6.
- Node.js 22.18.0.
- npm 11.5.2.

Se comienza con estas instalaciones. No se instalará otra versión global de Python ni se modificarán Xcode o Command Line Tools. Docker queda fuera del entorno local.

## Base ya preparada en el repositorio

- API Python con comprobación de salud en `/api/health`.
- Comprobación de conexión PostgreSQL en `/api/health/database`.
- Aplicación React con Vite.
- Script `scripts/iniciar-local.sh`, que crea `backend/.venv` y prepara dependencias dentro de las carpetas del proyecto.
- Archivo de ejemplo `backend/.env.example`; los archivos `.env` locales están excluidos de Git.
- API local en el puerto **8020** para evitar el puerto 8000 ya utilizado en la Mac de Jorge.

La pantalla web continúa siendo de desarrollo. No registra residentes, historias clínicas ni actividades.

## Comprobación inicial en la Mac

Desde Terminal:

```bash
cd /Users/Jorge/Documents/GitHub/Suite-Momento
git pull
bash scripts/iniciar-local.sh
```

El script utiliza el Python disponible, comprueba las versiones requeridas y levanta la API y React. Si falta una dependencia, la instala dentro del entorno virtual del backend o de `frontend/node_modules`; no instala Python global, Homebrew, Xcode ni Command Line Tools.

Con los servicios en ejecución, comprobar:

- Web: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8020/api/health`
- Documentación interactiva de API: `http://127.0.0.1:8020/docs`

La comprobación de PostgreSQL puede aparecer como pendiente hasta crear la base local.

## Conexión local de PostgreSQL

Primero comprobar que el servidor local responde:

```bash
pg_isready
```

Si el servidor está disponible y el rol aún no existe, crear un usuario de desarrollo y una base vacía:

```bash
createuser --login --pwprompt momento_dev
createdb --owner=momento_dev momento_dev
```

Luego copiar el ejemplo de configuración y hacer que la contraseña de la URL coincida con la que se asignó al rol:

```bash
cp backend/.env.example backend/.env
```

La variable que utiliza la API es `MOMENTO_DATABASE_URL`. No subir `backend/.env` al repositorio. Si el rol o la base ya existen, o los comandos muestran errores de autenticación, revisar el estado actual antes de crear o modificar usuarios; no cambiar la configuración global de PostgreSQL sin revisar el error.

## Criterios de verificación

- El script inicia ambos servicios y se detiene con Control+C.
- La web carga y muestra la marca Momento.
- `/api/health` responde con estado correcto.
- La consulta de PostgreSQL informa disponibilidad después de configurar la base local.
- El backend pasa sus pruebas automatizadas.
- La compilación de React finaliza correctamente.
- No se guardan datos personales o clínicos reales en esta etapa.

## Límites de esta fase

No se crearán todavía fichas de residentes, registros asistenciales, escalas, perfiles familiares ni funciones de IA. Esos módulos requieren decisiones de producto, privacidad y revisión profesional registradas en Fase 0.
