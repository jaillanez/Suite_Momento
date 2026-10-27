# Fase 2 — Organizaciones, usuarios y acceso

**Estado:** implementación en curso. Están acordados el modelo de organización, los grupos del piloto, las categorías de acceso familiar y el circuito general de solicitudes. El repositorio ya incluye autenticación de personal y protección inicial de rutas; todavía falta implementar la matriz completa de permisos, el acceso familiar y la bandeja persistente.  
**Propósito:** acordar cómo se organiza Momento y qué información puede consultar o modificar cada persona.

## Contexto confirmado

- Momento debe contemplar residencias y cuidado domiciliario.
- La primera validación del producto será en una residencia.
- Argentina y Uruguay son los países iniciales.
- La plataforma se construye desde cero; no se copian roles ni permisos del sistema anterior.
- La privacidad, la autorización y la trazabilidad deben formar parte del diseño desde el comienzo.

## Decisiones confirmadas por Jorge

Confirmadas el 26/10/2026:

1. **Organización:** representa al prestador de cuidado y puede contener varias sedes o servicios.
2. **Usuarios del piloto:** se contemplan personal, familiares/personas de confianza y personas mayores.
3. **Autorización familiar:** puede otorgarla el encargado de la residencia, un usuario administrativo habilitado o el médico.
4. **Alcance familiar:** se limita a información relacionada con la persona mayor vinculada y a los temas de medicación, actividades y dietas.
5. **Acciones familiares:** puede consultar la información autorizada, responder comunicaciones e iniciar solicitudes. No puede modificar indicaciones de medicación, dietas ni planes de actividades.
6. **Bandeja compartida:** las solicitudes y respuestas llegan primero a una bandeja compartida; solo el personal designado puede verla y gestionarla. El encargado designa a ese personal y asigna las solicitudes.

Jorge confirmó que la familia podrá consultar la información autorizada, responder comunicaciones e iniciar solicitudes relacionadas con medicación, actividades y dietas. La familia no podrá modificar indicaciones ni planes. Las comunicaciones y solicitudes ingresarán primero a una bandeja compartida de la residencia o servicio; solo el personal designado podrá verla y gestionarla. El encargado designa a ese personal y asigna cada solicitud.

## Modelo organizativo para diseñar

| Concepto | Definición de trabajo | Estado |
|---|---|---|
| Organización | Prestador que administra los servicios de cuidado | Confirmado |
| Sede o servicio | Residencia, sede física o equipo de atención domiciliaria dentro de una organización | Compatible con el modelo; alcance del piloto por precisar |
| Cuenta de usuario | Identidad de acceso de una persona | Propuesta técnica, pendiente de validar |
| Membresía | Vínculo de una cuenta con una organización, sede o equipo y sus permisos | Propuesta técnica, pendiente de validar |
| Autorización familiar | Permiso vinculado a una persona mayor, categorías autorizadas y acciones familiares | Categorías, autorizadores y acciones generales confirmados; vigencia y circuito de atención pendientes |
| Auditoría | Registro de accesos y cambios relevantes | Requisito del proyecto; eventos y retención por definir |

## Modelo conceptual de acceso para el piloto

La siguiente estructura traduce las decisiones confirmadas a conceptos de sistema. Es una propuesta funcional; aún no es un esquema de base de datos aprobado.

- **Organización** contiene una o más **sedes o servicios**.
- **Cuenta** identifica a una persona usuaria; el vínculo con una organización y sede se administra por separado.
- **Persona mayor** se vincula con su residencia o servicio de cuidado.
- **Autorización familiar** vincula una cuenta familiar con una persona mayor, incluye las categorías autorizadas (medicación, actividades y dietas), identifica quién la concedió y permite revocarla.
- **Acción permitida** (consultar, responder o iniciar una solicitud) debe quedar separada de la categoría de información. Jorge confirmó las categorías, quién puede autorizar y las acciones generales. La familia no modifica indicaciones ni planes.

### Flujo propuesto para autorizar a una familia

1. El encargado de la residencia, un administrativo habilitado o el médico selecciona a la persona mayor y al familiar/persona de confianza.
2. Quien autoriza selecciona una o más categorías: medicación, actividades y dietas.
3. El sistema registra quién autorizó, cuándo, para quién y qué categorías habilitó.
4. La autorización se puede revisar y revocar; al revocarla, deja de habilitar el acceso.
5. El acceso a otra persona o a otra categoría no autorizada se rechaza y queda sujeto a auditoría.

**Confirmado:** la familia puede consultar la información autorizada, responder comunicaciones e iniciar solicitudes. Estas ingresan primero a una bandeja compartida de la residencia o servicio y luego se asignan para su atención. La solicitud y la respuesta no cambian por sí mismas la medicación indicada, la dieta ni el plan de actividades.

**Pendiente:** definir qué estados o confirmaciones de recepción y avance verá la familia. La autorización familiar y la gestión de la bandeja son responsabilidades distintas: pueden autorizar el acceso familiar el encargado, un administrativo habilitado o el médico; la designación de quienes gestionan la bandeja y la asignación de solicitudes corresponden al encargado.

## Implementado en el repositorio

- Organizaciones, residencias/servicios, fichas mínimas de personas cuidadas y membresías de cuentas.
- Migraciones Alembic hasta autenticación, credenciales y sesiones.
- Login de personal con contraseñas derivadas mediante scrypt y sesión revocable en cookie HttpOnly; el logout revoca la sesión.
- Rutas de gestión protegidas para personal activo. El alcance de permisos todavía es preliminar; no equivale a la matriz funcional completa.
- El login de gestión rechaza cuentas familiares.
- Landing pública separada con un solo botón de acceso; navegación y dashboard dentro de la aplicación después del login.
- Dashboard con indicadores de personas cuidadas, cuidadores, médicos, familias y servicios consultados desde las APIs y la base local.
- Datos locales ficticios de residencia para pruebas. El bootstrap persiste membresías con claves explícitas y ahora incluye una prueba de regresión para el campo organization_id requerido.
- Vistas independientes de organizaciones, personas cuidadas, usuarios, bandeja y configuración.

## Límites actuales del código

- La bandeja sigue siendo una demostración en el navegador: las solicitudes y sus cambios no se guardan en PostgreSQL.
- La API y la pantalla para gestionar autorizaciones familiares aún no están conectadas; las cuentas familiares no pueden iniciar sesión.
- La designación del personal que puede acceder a la bandeja y la asignación de solicitudes todavía no están aplicadas de extremo a extremo.
- Agenda, guardias y actividad reciente contienen datos de muestra; no representan registros operativos guardados.
- No se debe exponer ni desplegar el entorno local hasta completar y probar permisos, auditoría y aislamiento entre organizaciones.

## Trabajo pendiente para cerrar Fase 2

1. Implementar permisos por organización y servicio, con pruebas de acceso permitido y denegado.
2. Implementar autorización familiar por persona, categoría y acciones acordadas, con otorgamiento y revocación.
3. Separar el acceso familiar del login de gestión y exponer solo información autorizada.
4. Persistir solicitudes y respuestas; hacer que el encargado designe al personal y asigne cada caso. Solo el encargado y el personal designado podrán ver y gestionar la bandeja según su alcance.
5. Registrar las acciones sensibles y comprobar el aislamiento entre organizaciones y servicios.
6. Acordar invitación, recuperación, baja de cuentas y reglas de auditoría antes del piloto.

## Grupos y roles candidatos

Los tres grupos generales del piloto están confirmados. Los roles exactos y sus permisos siguen abiertos:

| Grupo o rol candidato | Responsabilidad posible | Pendiente de definir |
|---|---|---|
| Encargado de residencia | Coordinar la operación y autorizar accesos familiares | Si administra también usuarios, equipos y otras sedes |
| Administrativo habilitado | Gestionar tareas administrativas y autorizaciones asignadas | Qué datos puede consultar y quién le concede la habilitación |
| Médico | Registrar o revisar información dentro de su competencia y autorizar acceso familiar | Alcance de acceso y acciones que puede realizar |
| Personal de cuidado | Consultar información necesaria y registrar tareas autorizadas | Diferencias entre cuidadores, enfermería y otros profesionales |
| Familiar o persona de confianza | Consultar información autorizada de la persona vinculada | Si puede responder, enviar solicitudes o solo consultar |
| Persona mayor | Usar las funciones propias que se definan para ella | Acceso individual, apoyos, representación y preferencias |

No se presupone que cada responsabilidad deba convertirse en un rol técnico independiente. Se debe validar con el equipo piloto.

## Reglas de acceso que debe resolver la definición

Se propone que cada permiso contemple:

- Organización, sede o servicio de la cuenta.
- Vínculo con la persona mayor.
- Categoría de información y acción: consultar, crear, modificar, compartir o exportar.
- Estado y vigencia de la cuenta, membresía y autorización.
- Responsable que concedió, modificó o retiró el permiso.

Para familiares, el alcance inicial confirmado es la información vinculada a medicación, actividades y dietas de la persona autorizada. La visibilidad de cada registro debe ser explícita; no se debe compartir automáticamente el resto de la información asistencial.

## Recorridos que deberán acordarse

- Alta inicial de una organización y de la residencia piloto.
- Incorporación de personal, familias/personas de confianza y personas mayores.
- Autorización familiar por persona y por categoría de información.
- Aceptación, rechazo, vencimiento, modificación y revocación de autorizaciones.
- Cambio de función, sede o equipo del personal.
- Suspensión o baja de una cuenta.
- Recuperación de acceso y cambio de datos de contacto.
- Revisión de quién consultó o modificó información sensible.

## Requisitos iniciales de seguridad y privacidad

- Aislar los datos de cada organización y comprobar ese aislamiento con pruebas.
- Aplicar el principio de menor acceso necesario y denegar accesos no autorizados.
- Revocar el acceso cuando vence o se retira una membresía o autorización.
- Proteger credenciales y sesiones; no registrar contraseñas en bitácoras.
- Registrar actor, acción, fecha, contexto y resultado de operaciones sensibles.
- Evitar mostrar datos personales en mensajes de error y registros técnicos.
- Probar permisos con cuentas y datos ficticios.
- Definir por separado los requisitos aplicables en Argentina y Uruguay con asesoramiento adecuado; este documento no constituye una interpretación legal.
- No habilitar un acceso excepcional de emergencia sin procedimiento, responsables, auditoría y revisión aprobados.

**Configuración inicial propuesta del seguimiento familiar**  
Para avanzar sin convertir estos nombres en reglas rígidas, cada servicio podrá configurar los estados habilitados, sus etiquetas y cuáles ve la familia. Valores iniciales propuestos:

| Estado interno | Evento inicial propuesto | Visibilidad familiar |
|---|---|---|
| Recibida | Se crea al enviar la solicitud | Sí |
| Asignada | El encargado la asigna a personal designado | Sí |
| En atención | La persona asignada indica que comenzó a gestionarla | Sí |
| Respondida | El personal designado registra una respuesta | Sí |
| Cerrada | El responsable marca la solicitud como finalizada | Sí |

La familia verá el estado y la respuesta compartida, no notas internas ni datos personales del trabajador asignado. Estos son valores iniciales editables por servicio; no se fijan plazos de respuesta. La configuración definitiva se revisará antes del piloto.

## Decisiones pendientes de Jorge y del equipo piloto

Los siguientes aspectos quedan como parámetros por definir y configurar con el equipo piloto; no bloquean la estructura actual ni se tomarán como reglas clínicas:

- Perfiles de personal y permisos por organización o servicio.
- Cuenta individual de la persona mayor y apoyos para acceder.
- Pertenencia de una persona a varias organizaciones o sedes.
- Canales de invitación y recuperación de acceso.
- Eventos de auditoría, responsables de revisión y retención.
- Acceso excepcional de emergencia; deshabilitado por defecto hasta definir y revisar su procedimiento.

## Criterios de aceptación para cerrar la fase

La fase estará lista para validación del piloto cuando:

- El alcance de organización, sedes y residencia piloto esté definido.
- La matriz de roles y permisos identifique cada acción y tipo de información.
- El circuito de recepción, asignación y respuesta de solicitudes familiares esté acordado.
- Se definan los permisos y apoyos para la persona mayor.
- Los recorridos de invitación, cambio de permisos, revocación y baja estén acordados.
- Se definan auditoría, aislamiento entre organizaciones y reglas de revisión.
- Las preguntas legales o de consentimiento que afecten el diseño estén asignadas a revisión, sin suposiciones del agente.
- Los permisos implementados tengan pruebas automatizadas y revisión con el equipo piloto.

## Instrucción para el agente de IA

No inventar reglas asistenciales ni legales. Implementar únicamente las decisiones confirmadas; marcar propuestas y decisiones pendientes en la documentación. Usar cuentas y personas ficticias en desarrollo. No habilitar acceso familiar ni desplegar la plataforma antes de probar autorización, revocación, aislamiento y trazabilidad.
