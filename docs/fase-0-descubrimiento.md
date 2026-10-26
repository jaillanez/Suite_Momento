# Fase 0 — Descubrimiento y definición de Momento

**Estado:** cerrada por decisión de Jorge el 26/10/2026.  
**Alcance del cierre:** habilita comenzar la base técnica. Las preguntas que siguen sin evidencia quedan pendientes de validación antes de aprobar funcionalidades o el alcance del MVP.

**Proyecto:** Momento  
**Repositorio:** `jaillanez/Suite_Momento`

## Objetivo de esta fase

Acordar qué problema debe resolver Momento, para quién y en qué situaciones. El resultado será una definición de producto validable antes de fijar procesos clínicos, permisos, pantallas o arquitectura detallada.

Esta fase no parte del código ni del modelo de datos del sistema anterior. El software de 2014 y los documentos/capturas asociados son fuentes históricas para detectar necesidades y problemas; no son especificaciones aprobadas.

## Decisiones confirmadas por Jorge

- Momento será un producto nuevo, desarrollado desde cero.
- Debe contemplar cuidado en residencias y en domicilios.
- Se considera a todas las personas que participan en el cuidado; el detalle de perfiles y permisos está pendiente.
- Mercados iniciales: Argentina y Uruguay.
- Tecnologías elegidas: Python, PostgreSQL y React.
- Desarrollo local en Mac, sin Docker.
- El primer contexto para validar será una residencia. El cuidado domiciliario debe quedar contemplado en el diseño.
- El repositorio de trabajo es `jaillanez/Suite_Momento`.

## Cómo leer lo que sigue

- **Confirmado:** decisión expresada por Jorge.
- **Hipótesis:** idea sugerida por los materiales o por el análisis, pendiente de validación.
- **Pendiente:** todavía no hay decisión suficiente para construirla.

## Materiales compartidos y cómo se interpretan

Se revisaron los documentos de Momento, las capturas de interfaces y las notas de experiencia que Jorge compartió. El inventario y la síntesis se encuentran en [revisión de materiales compartidos](revision-materiales-compartidos.md).

El informe técnico de una etapa previa registra como áreas exploradas la ficha personal, los registros profesionales con información privada y compartida, las evaluaciones, los pedidos a familiares, las actividades planificadas, la comunicación institucional, la aplicación móvil para familiares y la capacitación del personal. Estas experiencias deben servir para preguntar y validar; no se supone que estén implementadas hoy ni se trasladan automáticamente al producto nuevo.

Las capturas muestran interfaces anteriores de gestión institucional y una aplicación móvil. Sirven para reconocer el contexto y conversar sobre problemas observables; no son diseños a copiar ni confirman que sus flujos fueran satisfactorios.

Las propuestas tituladas Red de Cuidados, Portal del Cuidador, Navegación Geriátrica, Interfaces Intuitivas y Diseño Esqueuomórfico incluyen ideas generadas para explorar. Se consideran hipótesis. Las métricas promocionales incluidas allí, las funciones de vigilancia con sensores o cámaras y el análisis automático de voz o emociones no tienen evidencia suficiente para transformarse en compromisos.

Las notas de revisión de septiembre de 2026 registran problemas concretos de la experiencia previa, como la jerarquía de acciones, la localización de escalas, la carga de estudios y la presentación o puntuación de algunos elementos. Cada observación necesita comprobarse en su contexto antes de convertirse en una regla del nuevo sistema.

## Problema que queremos entender

Los materiales apuntan a posibles dificultades en la continuidad del cuidado, la coordinación entre personas, el registro de novedades, la comunicación con familiares y la facilidad de uso para personas mayores y cuidadores.

Son hipótesis, no hallazgos confirmados para todos los centros o domicilios. La fase debe comprobar cuáles ocurren en el contexto piloto, con qué frecuencia y qué consecuencias tienen.

## Personas y contextos a relevar

La lista identifica participantes a entrevistar; no constituye todavía el diseño definitivo de roles y permisos.

| Participante | Qué necesitamos comprender |
|---|---|
| Persona mayor | Preferencias, autonomía, participación, barreras y formas deseadas de comunicación |
| Familia o persona de confianza | Necesidades de información, participación, privacidad y comunicación |
| Cuidador/a | Rutina real, registros, traspasos, interrupciones y carga administrativa |
| Enfermería y profesionales de salud | Información necesaria, límites de responsabilidad y coordinación |
| Coordinación o dirección de residencia | Organización, supervisión, incidentes y necesidades operativas |
| Persona que brinda cuidado domiciliario | Visitas, coordinación con familia/profesionales y continuidad entre visitas |

## Recorridos que debemos conocer

Estos recorridos son una guía de relevamiento. No definen todavía cómo funcionará el producto.

### Residencia piloto

- Ingreso y actualización de información relevante de la persona.
- Organización y registro del cuidado diario.
- Comunicación de novedades y asuntos pendientes entre turnos.
- Coordinación entre cuidadores, profesionales y responsables.
- Comunicación con familiares.
- Manejo y seguimiento de incidentes, cambios o situaciones que requieren atención.

### Cuidado domiciliario

- Organización del cuidado entre visitas y personas involucradas.
- Registro de lo ocurrido y de asuntos que requieren seguimiento.
- Coordinación entre familia, cuidadores y profesionales.
- Comunicación ante cambios o necesidades de asistencia.

## Líneas de producto para validar

Los documentos de referencia sugieren explorar:

- Información y preferencias de la persona mayor.
- Registro del cuidado y seguimiento.
- Continuidad entre turnos o entre visitas.
- Coordinación del equipo.
- Comunicación con la familia.
- Interfaz accesible para la persona mayor.
- Capacitación y recursos de apoyo para cuidadores.
- Asistencia de IA con revisión humana.

Ninguna línea queda aprobada como funcionalidad hasta conocer el proceso real, quién la necesita, qué datos involucra y qué riesgos presenta.

## Principios de producto

1. Respetar dignidad, autonomía, privacidad y preferencias de la persona mayor.
2. Facilitar el cuidado y la comunicación sin convertir el sistema en una herramienta de vigilancia punitiva.
3. Registrar información comprensible, pertinente y útil para la continuidad.
4. Dar acceso a información según una autorización clara y el rol de cada persona.
5. Mantener decisiones clínicas bajo responsabilidad de profesionales habilitados.
6. La IA puede resumir, organizar o sugerir; no diagnostica, prescribe ni reemplaza el criterio profesional.
7. Diseñar para distintas capacidades visuales, motoras, cognitivas y niveles de experiencia digital.
8. Adaptar la solución a las diferencias operativas y normativas de Argentina y Uruguay, una vez identificadas.

## Preguntas abiertas

### Producto y alcance

- ¿Qué necesidad es más urgente para la residencia piloto?
- ¿Quién será responsable de usar y mantener cada tipo de información?
- ¿Qué información necesita conocer la familia y quién autoriza su acceso?
- ¿Qué desea hacer directamente la persona mayor dentro del sistema?
- ¿Qué procesos deben funcionar con conectividad limitada?
- ¿Qué capacidades pertenecen al producto base y cuáles dependen de cada organización?

### Cuidado y seguridad

- ¿Qué registros son asistenciales, administrativos o de comunicación?
- ¿Qué situaciones requieren aviso inmediato y a quién?
- ¿Qué acciones deben quedar registradas con autor y fecha?
- ¿Cómo se corrige un registro sin perder trazabilidad?
- ¿Qué funciones requieren intervención de un profesional de salud?
- ¿Qué información no debería registrarse en la plataforma?

### Países y privacidad

- ¿Qué obligaciones legales y de protección de datos aplican en Argentina y Uruguay?
- ¿Dónde se alojarán los datos y qué transferencias internacionales serían necesarias?
- ¿Cuáles serán los plazos de conservación, exportación y eliminación?
- ¿Qué consentimiento o autorización se requiere para cada uso?

### Tecnología y operación

- ¿Qué dispositivos se usan en el piloto y quién los administra?
- ¿Qué funciones necesitan aplicación móvil y cuáles pueden operar en web?
- ¿Qué comunicaciones externas e integraciones son realmente necesarias?
- ¿Qué conocimientos, herramientas y versiones están disponibles en la Mac de desarrollo?

## Criterio de salida de la Fase 0

La fase podrá considerarse lista para diseñar la primera versión cuando exista:

- Un problema prioritario validado con participantes del contexto piloto.
- Personas usuarias y responsabilidades descritas.
- Recorridos actuales documentados para residencia y cuidado domiciliario.
- Alcance inicial separado de las ideas futuras.
- Reglas y riesgos que requieren validación profesional o legal identificados.
- Decisiones pendientes visibles, con responsable de resolverlas.
- Criterios de aceptación redactados en lenguaje verificable.

## Próximo paso

Relevar el recorrido actual en una residencia piloto y contrastarlo con cuidadores, coordinación, profesionales, familiares y, cuando sea posible, personas mayores. Después se consolidarán hallazgos, alcance inicial y criterios de aceptación.

No registrar datos identificables o clínicos reales de residentes en este repositorio.
