# Momento

Plataforma nueva para acompañar y organizar el cuidado de personas mayores en residencias y domicilios, inicialmente orientada a Argentina y Uruguay.

Este repositorio comienza como un proyecto nuevo. El sistema anterior de 2014 es solo una referencia histórica: no se reutiliza su código, arquitectura ni base de datos.

## Estado actual

Primera base técnica en construcción: API Python, comprobación de PostgreSQL y aplicación React. La pantalla actual es de desarrollo y no registra datos de personas.

## Tecnologías

- API: Python y FastAPI.
- Base de datos: PostgreSQL.
- Aplicación web: React, TypeScript y Vite.
- Desarrollo local en Mac, sin Docker.
- La aplicación móvil con Capacitor y la landing pública son decisiones para fases posteriores.

## Ejecutar localmente en Mac

Después de actualizar el repositorio, desde su carpeta ejecuta:

    bash scripts/iniciar-local.sh

El script crea el entorno virtual dentro del proyecto, prepara dependencias y arranca API y web. No instala ni actualiza Python, Homebrew, Xcode o Command Line Tools. Presiona Control+C para detener ambos servicios.

Abre http://127.0.0.1:5173. La API estará en http://127.0.0.1:8000. PostgreSQL aparecerá pendiente hasta configurar una base local.

## Documentación

- docs/vision.md
- docs/fase-0-descubrimiento.md
- docs/plan-de-fases.md
- backend/README.md
- frontend/README.md
- AGENTS.md

No cargar datos personales o clínicos reales en esta base de desarrollo.
