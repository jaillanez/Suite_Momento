# Recorrido local de Momento con datos de ejemplo

El entorno de demostración usa una organización ficticia y nombres inventados. No cargues información de residentes reales en este escenario.

## Preparar los datos de prueba

Desde la carpeta del repositorio, aplicá las migraciones y ejecutá el asistente. No hace preguntas.

```sh
cd backend
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/python -m momento_api.bootstrap_demo
```

El asistente crea Residencia Los Aromos con 42 personas cuidadas, 18 cuidadores, 3 médicos, 1 administrativa y 31 familias, todos ficticios. Si la residencia ya existe, no borra ni reemplaza nada: solo agrega lo que falte.

## Usuarios de prueba

| Puesto | Correo | Contraseña | Qué ve |
|---|---|---|---|
| Encargado | encargado1@momento.com.ar | Encargado123 | Todo |
| Administrativo | administrativo1@momento.com.ar | Administrativo123 | Personas cuidadas y familias (puede autorizarlas) |
| Médico | medico1@momento.com.ar | Medico123 | Personas cuidadas, familias y bandeja |
| Cuidador | cuidador1@momento.com.ar | Cuidador123 | Personas cuidadas y bandeja |
| Familia | familia1@momento.com.ar | Familia123 | Su persona a cargo y sus consultas (elegir "Familias" al ingresar) |

El médico y el cuidador de prueba están designados para la bandeja. Además, Sofía Pereyra, Ramiro Costa y la Dra. Laura Méndez quedan designados, cada familia queda autorizada para medicación, actividades y dietas de una persona, y la bandeja tiene 4 solicitudes de ejemplo.

Estas contraseñas son solo para tu Mac. No las uses con datos reales ni en un servidor.

## Recorrer la aplicación

Iniciá los servicios en otra terminal:

```sh
bash scripts/iniciar-local.sh
```

Abrí http://127.0.0.1:5173. La pantalla de acceso tiene dos opciones: "Equipo de la residencia" y "Familias". El menú cambia según el puesto, y la API vuelve a validar cada acción. La sesión dura ocho horas y se revoca al salir.

El encargado también puede crear usuarios desde "Usuarios y vínculos": si completa correo y contraseña, la persona ya puede ingresar. La contraseña debe tener al menos 8 caracteres.

## Alcance

Los nombres y cantidades sirven para recorrer la experiencia local; no representan personas, turnos ni eventos reales. La agenda y el equipo del turno del dashboard siguen siendo ejemplos de interfaz. Las solicitudes, en cambio, se guardan en la base.

El cookie local no usa Secure por defecto porque el desarrollo corre por HTTP en localhost. En un despliegue con HTTPS, configurá MOMENTO_COOKIE_SECURE=true. La aplicación de esta rama es un entorno local de demostración: el asistente genera identidades ficticias y no habilita la operación con información real.
