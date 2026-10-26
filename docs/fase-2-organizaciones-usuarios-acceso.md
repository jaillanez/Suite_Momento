# Fase 2 — Organizaciones, usuarios y acceso

**Estado:** definición en curso. Jorge confirmó el modelo de organización, los grupos de usuarios del piloto y quién autoriza el acceso familiar. Faltan reglas operativas antes de implementar autenticación y permisos.  
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

## Primera entrega técnica de Fase 2

**Comprobada localmente por Jorge el 26/10/2026:** pasaron 9 pruebas del backend; Alembic registró `0002_care_workflow_statuses (head)` en PostgreSQL; `npm run build` completó correctamente.

- Modelos SQLAlchemy `Organization` y `CareUnit`.
- Tipos de servicio iniciales: residencia y cuidado domiciliario.
- Migración Alembic reversible que crea `organizations` y `care_units`.
- API y pantalla local para crear y consultar organizaciones y sus servicios.
- Configuración por servicio de nombres, orden, activación y visibilidad familiar de los estados de seguimiento.
- Estados iniciales: recibida, asignada, en atención, respondida y cerrada.
- Validación de tipo de servicio, nombre y país (AR/UY).
- Pruebas con SQLite en memoria; usan datos ficticios.
- Modelos base `UserAccount` y `OrganizationMembership` para personal, familia y persona mayor, con alcance opcional por servicio; `0003_user_memberships` está preparada para verificación local.
- Modelo `CareRecipient` con nombre visible únicamente y `FamilyAuthorization` por categoría y acción; registra familiar, autorizador y revocación.
- `0004_care_recipients_family_authorizations` está preparada para verificación local.
- Las tablas no tienen inicio de sesión, credenciales ni endpoints de acceso; `role_label` es descriptivo y no concede permisos.
- No se crean datos reales ni solicitudes de personas mayores.

**Límite de seguridad:** los endpoints de escritura actuales son un andamiaje local para comprobar el flujo. La API se inicia enlazada a `127.0.0.1`; no se debe exponer ni desplegar hasta definir autenticación, autorización y auditoría. La migración se aplica manualmente y no al iniciar el servidor. `0002` agrega la configuración de estados; `0003` agrega identidades y membresías, sin exponerlas por API hasta definir autenticación y autorización.

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

## Criterios de aceptación de la definición

La fase estará lista para implementar cuando:

- El alcance de organización, sedes y residencia piloto esté definido.
- La matriz de roles y permisos identifique cada acción y tipo de información.
- El circuito de recepción, asignación y respuesta de solicitudes familiares esté acordado.
- Se definan los permisos y apoyos para la persona mayor.
- Los recorridos de invitación, cambio de permisos, revocación y baja estén acordados.
- Se definan auditoría, aislamiento entre organizaciones y reglas de revisión.
- Las preguntas legales o de consentimiento que afecten el diseño estén asignadas a revisión, sin suposiciones del agente.
- Jorge confirme el documento de alcance antes de implementar autenticación o permisos.

## Instrucción para el agente de IA

Hasta que estas decisiones se confirmen, el agente puede proponer alternativas, diagramar flujos y preparar casos de prueba con usuarios ficticios. No debe implementar un catálogo definitivo de roles, asumir consentimiento, crear cuentas reales ni habilitar acceso a información de personas mayores.
