# Momento — plan de trabajo por fases

**Estado al 26/10/2026:** Fase 0 y Fase 1 cerradas. Fase 2 en definición; todavía no se implementan autenticación ni permisos.  
**Propósito:** orientar al agente de IA y al equipo para avanzar en orden, conservar las decisiones y evitar construir funciones no validadas.

## Acuerdos del proyecto

- Producto nuevo, independiente del sistema de 2014.
- Debe contemplar residencias y cuidado domiciliario.
- Países iniciales: Argentina y Uruguay.
- La primera validación se realizará en una residencia.
- Tecnologías acordadas: Python, PostgreSQL y React.
- Desarrollo en Mac sin Docker.
- No se importarán código ni datos del sistema anterior sin una decisión explícita.
- El detalle de funcionalidades, perfiles y permisos se validará antes de implementar.

## Fase 0 — Descubrimiento de producto (cerrada)

**Objetivo:** entender las necesidades y procesos reales antes de fijar el alcance inicial.

**Trabajo:** relevar a la persona mayor, familiares, cuidadores, profesionales y responsables; documentar el recorrido actual en la residencia piloto y contemplar diferencias con el cuidado domiciliario; contrastar con la experiencia funcional documentada de Momento; distinguir problemas observados de ideas propuestas; identificar riesgos y decisiones legales pendientes.

**Resultado esperado:** problema prioritario validado, personas usuarias y responsabilidades, recorridos actuales, límites del producto y alcance de la primera versión con criterios de aceptación.

Los materiales compartidos agregan experiencia previa sobre ficha personal, evoluciones, evaluaciones, actividades, comunicación y capacitación. Se revisan como antecedentes, no como alcance aprobado.

Documentos: [Fase 0 — Descubrimiento y definición de Momento](fase-0-descubrimiento.md), [revisión de materiales compartidos](revision-materiales-compartidos.md) y [criterios iniciales de experiencia](criterios-iniciales-experiencia.md).

## Fase 1 — Base técnica y entorno local (cerrada)

**Objetivo:** preparar una base nueva, reproducible y fácil de desarrollar en la Mac.

**Trabajo:** conservar las versiones que ya están instaladas en la Mac; comprobar PostgreSQL local; crear el entorno virtual dentro del proyecto; ejecutar la API y la aplicación React existentes; configurar la conexión local y comprobar los servicios. Docker no forma parte del entorno acordado.

**Entorno ya informado por Jorge el 26/10/2026:** macOS 27.0.1 (arm64), Python 3.13.5, PostgreSQL 18.6, Node.js 22.18.0 y npm 11.5.2. Se usarán estas instalaciones para comenzar. No instalar otra versión global de Python ni modificar Xcode o Command Line Tools. El proyecto crea su entorno Python aislado en `backend/.venv`.

**Resultado alcanzado:** en la Mac de Jorge quedaron confirmados API y PostgreSQL con HTTP 200, 2 pruebas de backend aprobadas y compilación de React finalizada. El frontend estuvo activo y generó llamadas a las comprobaciones de salud. Se documentó la configuración reproducible. No se instalaron herramientas globales ni se modificaron Xcode/Command Line Tools.

## Fase 2 — Organizaciones, usuarios y acceso (definición en curso)

**Objetivo:** controlar quién puede acceder a cada institución, servicio y dato.\n\nBorrador de definición, con decisiones pendientes y sin alcance funcional aprobado: [Fase 2 — Organizaciones, usuarios y acceso](fase-2-organizaciones-usuarios-acceso.md).

**Trabajo:** definir organizaciones y ubicaciones; alta e invitación de usuarios; autenticación; permisos por rol y contexto; consentimiento/autorización cuando corresponda; trazabilidad de acciones sensibles.

**Decisiones confirmadas por Jorge:** una organización prestadora puede contener varias sedes o servicios; el piloto contempla personal, familias/personas de confianza y personas mayores; el acceso familiar lo autoriza el encargado de la residencia, un administrativo habilitado o el médico, y se limita a información de la persona vinculada sobre medicación, actividades y dietas.

**Pendiente de validar:** permisos concretos por rol, si la familia solo consulta o también interactúa, acceso individual de la persona mayor, pertenencia de usuarios a varias organizaciones o sedes, canales de invitación/recuperación, auditoría, acceso de emergencia y requisitos por país.

**Resultado esperado:** matriz de acceso acordada y comprobable antes de implementar autenticación o cargar datos reales.

## Fase 3 — Perfil y contexto de la persona mayor

**Objetivo:** reunir la información necesaria para personalizar y dar continuidad al cuidado.

**Posibles contenidos para validar:** identificación, contactos autorizados, preferencias, historia de vida, apoyos requeridos, documentos y antecedentes relevantes.

**Resultado esperado:** ficha inicial y reglas de acceso aprobadas. El alcance clínico y los datos obligatorios deberán definirse con profesionales y revisar su pertinencia legal.

## Fase 4 — Organización y registro del cuidado

**Objetivo:** apoyar el cuidado cotidiano y facilitar la continuidad entre personas y turnos.

**Posibles capacidades para validar:** plan de cuidado, tareas, registros breves, observaciones, eventos relevantes, pendientes y entrega de turno. El registro por voz, recordatorios y medicación son propuestas de los documentos, todavía sujetas a validación operativa y clínica.

**Resultado esperado:** flujos de cuidado acordados, responsables identificados, trazabilidad de cambios y manejo claro de errores y situaciones que requieren escalamiento.

## Fase 5 — Comunicación con familia y personas de confianza

**Objetivo:** compartir información autorizada y mantener un canal claro con el equipo.

**Posibles capacidades para validar:** novedades, mensajes, fotografías/actividades, solicitudes y avisos. No todo dato asistencial debe publicarse automáticamente en un diario familiar; cada tipo de información requiere autorización y reglas de publicación.

**Resultado esperado:** permisos y contenidos visibles aprobados, canales y responsables definidos y protección de privacidad verificada.

## Fase 6 — Experiencia directa para la persona mayor

**Objetivo:** permitir una interacción simple, accesible y elegida por la persona.

**Posibles capacidades para validar:** contactos, mensajes, fotos, álbum de recuerdos, lectura en voz alta y solicitud de ayuda. Las llamadas de emergencia o asistencia deben diseñarse y probarse con un protocolo real; no se presentarán como atendidas automáticamente.

**Resultado esperado:** prototipo probado con usuarios representativos, rutas simples y medidas de accesibilidad acordadas.

## Fase 7 — Aplicación móvil

**Objetivo:** ofrecer las tareas móviles que realmente necesiten cuidadores, familiares o personas mayores.

**Recomendación de arquitectura:** empezar por una aplicación web React adaptable. Evaluar Capacitor para empaquetarla como aplicación iOS/Android cuando los flujos web estén validados y se conozcan las necesidades nativas. No mantener dos productos independientes si la misma aplicación web cubre los usos.

**Resultado esperado:** decisión documentada sobre dispositivo, funciones nativas, permisos, publicación y conectividad antes de generar aplicaciones de tiendas.

## Fase 8 — Asistencia con inteligencia artificial

**Objetivo:** reducir tareas repetitivas sin transferir a la IA decisiones clínicas o responsabilidades humanas.

**Posibles usos para validar:** organizar notas, resumir novedades, preparar borradores de comunicación y facilitar búsqueda de información autorizada.

**Límites:** no diagnosticar, prescribir, cambiar indicaciones ni marcar una alerta como resuelta sin intervención humana. Definir revisión, fuentes, registro de uso, protección de datos y mecanismo para corregir resultados antes de habilitar cada función.

**Resultado esperado:** caso de uso acotado, prueba con información ficticia o anonimizada, revisión humana obligatoria y criterios de seguridad aprobados.

## Fase 9 — Preparación operativa y ampliación

**Objetivo:** comprobar que el producto puede sostenerse antes de ampliar su uso.

**Trabajo:** pruebas funcionales y de accesibilidad; revisión de seguridad; copias y restauración; monitoreo; soporte; exportación y eliminación de datos; análisis de obligaciones aplicables en Argentina y Uruguay; evaluación del piloto y correcciones.

**Resultado esperado:** decisión documentada sobre continuidad y ampliación, basada en evidencia del piloto.

## Landing pública

La landing institucional es un componente separado de la plataforma de cuidado. WordPress con el tema Astra puede servir si el equipo necesita editar textos y campañas por su cuenta. Se debe confirmar quién mantendrá el contenido, el dominio y el alojamiento antes de decidir si se construye con Astra o con React.

## Criterios para el agente de IA en todas las fases

- Leer primero la documentación del repositorio y respetar acuerdos confirmados.
- Separar hechos, propuestas, dudas y decisiones.
- No inventar procesos asistenciales ni requisitos legales.
- Antes de implementar, describir cambio, impacto en datos/permisos y comprobaciones.
- Usar información ficticia o anonimizada en desarrollo y pruebas.
- Mantener cambios pequeños y revisables; no publicar ni desplegar sin autorización.
- Registrar decisiones técnicas y funcionales relevantes en el repositorio.
- No adelantar fases que dependan de decisiones o validaciones pendientes.

## Referencias de versiones consultadas

- [Python 3.15.2 — versión estable](https://www.python.org/downloads/release/python-3152/)
- [Fórmula de Python 3.15 en Homebrew](https://formulae.brew.sh/formula/python%403.15)
- [Política oficial de versiones PostgreSQL](https://www.postgresql.org/support/versioning/)
- [PostgreSQL 19 RC 1 — aviso oficial; todavía release candidate](https://www.postgresql.org/about/news/postgresql-19-rc-1-released-3409/)
