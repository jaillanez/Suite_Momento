# Fase 1 — Base técnica local

**Estado:** cerrada en la Mac de Jorge el 26/10/2026. API, PostgreSQL, pruebas de backend y compilación de React verificados.  
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

La pantalla web continúa siendo una base de desarrollo y no registra residentes, historias clínicas ni actividades. El servidor Vite estuvo activo y la API recibió llamadas de salud desde el entorno web.

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

## Conexión local de PostgreSQL

PostgreSQL está activo y conectado a la API en el entorno local de Jorge. La API registra respuestas HTTP 200 tanto en `/api/health` como en `/api/health/database`.

La configuración local se guarda en `backend/.env`, excluido de Git. No compartir ni subir ese archivo.

## Criterios de verificación

- El script inicia ambos servicios y se detiene con Control+C.
- La web carga y muestra la marca Momento.
- `/api/health` responde HTTP 200. **Confirmado por Jorge en su Mac.**
- `/api/health/database` responde HTTP 200. **Confirmado por Jorge en su Mac.**
- Las pruebas del backend finalizan correctamente: **2 pasaron**.
- La compilación de React finaliza correctamente después de agregar la declaración de tipos de Vite. **Confirmado por Jorge en su Mac.**
- No se guardan datos personales o clínicos reales en esta etapa.

## Límites de esta fase

No se crearán todavía fichas de residentes, registros asistenciales, escalas, perfiles familiares ni funciones de IA. Esos módulos requieren decisiones de producto, privacidad y revisión profesional registradas en Fase 0.
