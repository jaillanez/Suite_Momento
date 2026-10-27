# Recorrido local de Momento con datos de ejemplo

El entorno de demostración usa una organización ficticia y nombres inventados. No cargues información de residentes reales en este escenario.

## Preparar la cuenta de acceso

Desde la carpeta del repositorio, aplicá la migración y ejecutá el asistente local. El asistente pide el correo y una contraseña nueva; la contraseña se guarda derivada con scrypt y nunca queda escrita en el repositorio.

```sh
cd backend
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/python -m momento_api.bootstrap_demo
```

La cuenta encargada se crea con el nombre Mariana López, dentro de Residencia Los Aromos. El asistente muestra el correo elegido y confirma que la contraseña no se guarda en texto legible. Si la contraseña y su confirmación no coinciden o no alcanzan 12 caracteres, podés volver a ingresarlas hasta tres veces. El conjunto incluye 42 personas cuidadas, 18 cuidadores, 3 profesionales médicos y 31 cuentas familiares con nombres ficticios. Solo la cuenta encargada recibe una contraseña en este asistente.

Para recorrer la pantalla, iniciá los servicios en otra terminal:

```sh
bash scripts/iniciar-local.sh
```

Abrí http://127.0.0.1:5173 e ingresá con el correo y la contraseña que configuraste. La API valida el acceso y emite una cookie de sesión HttpOnly, de ocho horas. Al salir, la sesión se revoca. La aplicación web de gestión acepta cuentas de personal con alcance de organización; las cuentas familiares no entran al panel de gestión. El panel solo habilita la gestión de organizaciones para personal con vínculo a nivel de organización; las rutas de servicio verifican que el vínculo de personal alcance ese servicio.

El escenario se crea una sola vez. Si ya existe Residencia Los Aromos, el asistente se detiene sin reemplazar ni borrar registros.

## Alcance

Los nombres y cantidades sirven para recorrer la experiencia local; no representan personas, turnos ni eventos reales. La agenda y las solicitudes visibles en la vista de demostración son ejemplos de interfaz y no forman parte de los registros guardados por el asistente.

El cookie local no usa Secure por defecto porque el desarrollo corre por HTTP en localhost. En un despliegue con HTTPS, configurá MOMENTO_COOKIE_SECURE=true. La aplicación de esta rama es un entorno local de demostración: el asistente genera identidades ficticias y no habilita la operación con información real.
