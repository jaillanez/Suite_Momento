# Fase 2 — Organizaciones, usuarios y acceso

**Estado:** borrador de definición. No representa decisiones aprobadas ni autoriza implementar autenticación o permisos todavía.  
**Propósito:** acordar cómo se organiza Momento y qué información puede consultar o modificar cada persona.

## Contexto confirmado

- Momento debe contemplar residencias y cuidado domiciliario.
- La primera validación del producto será en una residencia.
- Argentina y Uruguay son los países iniciales.
- La plataforma se construye desde cero; no se copian roles ni permisos del software anterior.
- La privacidad, la autorización y la trazabilidad deben formar parte del diseño desde el comienzo.

## Alcance de esta fase

Definir reglas, recorridos y criterios verificables para:

1. Crear y administrar una organización prestadora.
2. Representar una o más residencias, sedes o servicios domiciliarios.
3. Invitar, activar, suspender y retirar usuarios.
4. Asociar una cuenta con una organización y, cuando corresponda, con una sede o equipo.
5. Definir acceso a personas mayores según rol, contexto y autorización.
6. Registrar cambios de acceso y acciones sensibles.

La base técnica de la Fase 1 queda cerrada. Esta fase no incorpora todavía información de residentes ni módulos asistenciales.

## Conceptos candidatos para validar

Estos nombres sirven para conversar; no son un modelo de datos aprobado:

- **Organización:** entidad que presta o administra el servicio de cuidado.
- **Sede o servicio:** residencia, sede física, equipo o servicio domiciliario dentro de la organización.
- **Cuenta de usuario:** identidad de acceso de una persona.
- **Vínculo con organización:** participación de una cuenta en una organización, con uno o más roles.
- **Vínculo con persona mayor:** autorización para acceder a información de una persona específica.
- **Invitación:** proceso para incorporar a un usuario con alcance y vencimiento definidos.
- **Registro de auditoría:** evidencia de accesos y cambios relevantes.

## Roles candidatos

La siguiente lista es una hipótesis inicial. La separación entre funciones se debe validar con el equipo de la residencia piloto:

| Candidato | Responsabilidad posible | Decisiones pendientes |
|---|---|---|
| Titular o administrador de organización | Configurar la organización y administrar accesos | Si existe un titular separado del administrador |
| Coordinación de servicio | Coordinar equipos, sedes y operación cotidiana | Qué datos asistenciales puede ver o cambiar |
| Personal de cuidado | Consultar información necesaria y registrar tareas autorizadas | Diferencias entre cuidadores, enfermería y otros profesionales |
| Profesional de salud | Consultar o registrar información dentro de su competencia | Qué profesiones existen y qué registros requiere cada una |
| Familiar o persona de confianza | Consultar y aportar información autorizada | Qué puede ver, enviar, descargar o solicitar |
| Persona mayor | Consultar información propia y usar funciones que elija | Capacidades, apoyos, representación y preferencias de acceso |

No se presupone que todas estas cuentas deban existir en la primera versión.

## Reglas de acceso que debe resolver la definición

El permiso no debería depender solamente del nombre del rol. Se propone evaluar en conjunto:

- La organización a la que pertenece la cuenta.
- La sede, servicio o equipo desde el que actúa.
- El vínculo autorizado con la persona mayor.
- El tipo de información y la acción solicitada: consultar, crear, modificar, compartir o exportar.
- El estado vigente de la cuenta y de la autorización.
- La finalidad operativa del acceso, cuando corresponda.

Las reglas concretas y sus excepciones quedan pendientes de validación.

## Recorridos que deberán acordarse

- Alta inicial de una organización y su primera sede o servicio.
- Invitación y activación de un integrante del equipo.
- Invitación de un familiar o persona de confianza para una persona determinada.
- Aceptación, rechazo, vencimiento y reenvío de invitaciones.
- Cambio de rol, sede o equipo.
- Suspensión o baja de una cuenta y revocación de sus autorizaciones.
- Usuario que trabaja con más de una organización.
- Recuperación de acceso y cambio de datos de contacto.
- Revisión de quién consultó o modificó información sensible.

## Requisitos iniciales de seguridad y privacidad

- Aislar los datos de cada organización y comprobar ese aislamiento con pruebas.
- Aplicar el principio de menor acceso necesario.
- Denegar por defecto los accesos sin autorización explícita.
- Revocar el acceso cuando vence o se retira una membresía o autorización.
- Proteger credenciales y sesiones; no registrar contraseñas en bitácoras.
- Registrar actor, acción, fecha, contexto y resultado de operaciones sensibles.
- Evitar mostrar datos personales en mensajes de error y registros técnicos.
- Probar permisos con cuentas y datos ficticios.
- Definir por separado los requisitos aplicables en Argentina y Uruguay con asesoramiento adecuado; este documento no constituye una interpretación legal.

## Decisiones pendientes de Jorge y del equipo piloto

1. ¿La primera organización representa una residencia individual o una entidad que puede tener varias residencias?
2. ¿Qué tipos de personal deben distinguirse desde el comienzo y cuáles podrían compartir permisos?
3. ¿Qué información puede consultar cada familiar y quién autoriza ese acceso?
4. ¿La persona mayor tendrá una cuenta propia desde la primera versión, podrá elegirla, o el equipo necesita relevar primero sus capacidades y preferencias?
5. ¿Un usuario podrá pertenecer a varias organizaciones o sedes?
6. ¿La invitación y recuperación de acceso se harán por correo, teléfono, ambos u otro canal?
7. ¿Qué acciones sensibles necesitan quedar auditadas para el piloto?
8. ¿Se necesita un acceso excepcional de emergencia? Si sí, quién puede usarlo, en qué circunstancias y cómo se revisa después.

## Criterios de aceptación de la definición

La fase estará lista para implementar cuando:

- El equipo piloto confirme los tipos de organización, sedes y servicios que usará.
- La matriz de roles y permisos identifique cada acción y cada tipo de información.
- Los recorridos de invitación, cambio de rol y baja estén acordados.
- Las reglas de acceso familiar y de la persona mayor estén explícitas.
- Se definan revocación, auditoría y aislamiento entre organizaciones.
- Las preguntas legales o de consentimiento que afecten el diseño estén asignadas a revisión, sin suposiciones del agente.
- Jorge confirme el documento de alcance antes de abrir el trabajo de implementación.

## Instrucción para el agente de IA

Hasta que estas decisiones se confirmen, el agente puede proponer alternativas, diagramar flujos y preparar casos de prueba con usuarios ficticios. No debe implementar un catálogo definitivo de roles, asumir consentimiento, crear cuentas reales ni habilitar acceso a información de personas mayores.
