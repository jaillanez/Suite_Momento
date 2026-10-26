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

Queda por precisar si el acceso familiar será solo de consulta o si también permitirá responder o iniciar solicitudes. La definición de acceso no habilita a familiares a modificar indicaciones de medicación, dietas o planes de actividades.

## Modelo organizativo para diseñar

| Concepto | Definición de trabajo | Estado |
|---|---|---|
| Organización | Prestador que administra los servicios de cuidado | Confirmado |
| Sede o servicio | Residencia, sede física o equipo de atención domiciliaria dentro de una organización | Compatible con el modelo; alcance del piloto por precisar |
| Cuenta de usuario | Identidad de acceso de una persona | Propuesta técnica, pendiente de validar |
| Membresía | Vínculo de una cuenta con una organización, sede o equipo y sus permisos | Propuesta técnica, pendiente de validar |
| Autorización familiar | Permiso vinculado a una persona mayor y a categorías de información definidas | Alcance y autorizadores confirmados; acciones y vigencia pendientes |
| Auditoría | Registro de accesos y cambios relevantes | Requisito del proyecto; eventos y retención por definir |

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

## Decisiones pendientes de Jorge y del equipo piloto

1. ¿El acceso familiar a medicación, actividades y dietas será solo de consulta, o permitirá responder o iniciar solicitudes? ¿Cuáles?
2. ¿Qué perfiles de personal se necesitan en la residencia piloto y qué diferencia de acceso tiene cada uno?
3. ¿La persona mayor tendrá una cuenta individual? ¿Qué alternativa se usará si necesita ayuda para acceder?
4. ¿Un usuario podrá pertenecer a varias organizaciones o sedes desde el piloto?
5. ¿La invitación y recuperación de acceso se harán por correo, teléfono, ambos u otro canal?
6. ¿Qué eventos deben quedar auditados y quién podrá revisar esos registros?
7. ¿Se necesita un acceso excepcional de emergencia? Si sí, ¿quién puede usarlo, en qué circunstancias y cómo se revisa después?

## Criterios de aceptación de la definición

La fase estará lista para implementar cuando:

- El alcance de organización, sedes y residencia piloto esté definido.
- La matriz de roles y permisos identifique cada acción y tipo de información.
- Las acciones familiares posibles dentro de medicación, actividades y dietas estén acordadas.
- Se definan los permisos y apoyos para la persona mayor.
- Los recorridos de invitación, cambio de permisos, revocación y baja estén acordados.
- Se definan auditoría, aislamiento entre organizaciones y reglas de revisión.
- Las preguntas legales o de consentimiento que afecten el diseño estén asignadas a revisión, sin suposiciones del agente.
- Jorge confirme el documento de alcance antes de implementar autenticación o permisos.

## Instrucción para el agente de IA

Hasta que estas decisiones se confirmen, el agente puede proponer alternativas, diagramar flujos y preparar casos de prueba con usuarios ficticios. No debe implementar un catálogo definitivo de roles, asumir consentimiento, crear cuentas reales ni habilitar acceso a información de personas mayores.
