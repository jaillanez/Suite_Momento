# Visión de producto Momento

## Qué queremos construir

Momento es una plataforma nueva para acompañar y organizar el cuidado de personas mayores en residencias y domicilios. Busca conectar a la persona mayor con su familia, cuidadores, profesionales y la organización que coordina la atención, manteniendo a la persona y su historia en el centro.

El producto parte desde cero en código, arquitectura y datos. La experiencia acumulada de Momento y los materiales compartidos aportan conocimiento funcional y de marca; no obligan a reproducir pantallas, procesos o decisiones técnicas anteriores.

## Propósito

Facilitar un cuidado más cercano, coordinado y comprensible. La tecnología debe ayudar a sostener los vínculos y la continuidad del cuidado, y reducir fricciones para quienes cuidan. No debe reemplazar el trato humano ni trasladar decisiones profesionales a un sistema automático.

## Líneas de producto que surgen de los antecedentes

Estas líneas orientan el descubrimiento. Todavía deben contrastarse con el equipo y con las personas usuarias de la nueva plataforma.

1. **Conocer a la persona.** Reunir información pertinente sobre preferencias, apoyos y aspectos de su historia que ayuden a personalizar el cuidado.
2. **Dar continuidad al cuidado.** Facilitar que quienes participan registren novedades y comprendan qué ocurrió y qué queda pendiente entre turnos o visitas.
3. **Coordinar actividades y equipos.** Explorar la planificación de actividades, la comunicación interna y el seguimiento de asuntos que requieren coordinación.
4. **Mantener informada a la familia.** Ofrecer una comunicación clara sobre la información que la organización autorizó compartir. Los registros profesionales privados no deben publicarse automáticamente.
5. **Acompañar a quienes cuidan.** Considerar recursos de formación y apoyo, además de herramientas operativas que no conviertan el sistema en una herramienta de control punitivo.
6. **Facilitar la participación de la persona mayor.** Evaluar una experiencia propia, sencilla y accesible, siempre según el interés y las preferencias de cada persona.

## Aprendizajes documentados, no compromisos de producto

Un informe técnico de una etapa previa de Momento describe una ficha personal, evoluciones profesionales cronológicas con información diferenciada, evaluaciones, pedidos a familiares, planificación de actividades, comunicación institucional y una aplicación móvil orientada al vínculo con las familias. También documenta un programa de capacitación para equipos de residencias.

Estos antecedentes muestran áreas de trabajo ya exploradas por el equipo. No confirman que cada función siga siendo necesaria, que su implementación anterior esté vigente o que deba conservarse con el mismo flujo.

## Decisiones confirmadas

- El proyecto actual es un desarrollo nuevo e independiente.
- Debe contemplar residencias y cuidado domiciliario.
- Los mercados iniciales son Argentina y Uruguay.
- El primer contexto para validar será una residencia; el diseño también debe considerar el cuidado en domicilio.
- El stack elegido es Python, PostgreSQL y React.
- El desarrollo local se hará en Mac, sin Docker.
- La identidad visual de referencia está en los materiales de Momento compartidos. Su versión vigente debe confirmarse con el equipo.

## Principios

- Respetar dignidad, autonomía, privacidad, preferencias y participación de la persona mayor.
- Diseñar para el trabajo real de cuidadores, familiares y profesionales, sin presumir que todos usan la plataforma de la misma manera.
- Diferenciar datos asistenciales, de coordinación y de comunicación; definir quién puede ver cada uno antes de implementar.
- Registrar autoría y cambios de forma comprensible cuando el dato sea relevante para la continuidad.
- Mantener las decisiones clínicas bajo responsabilidad de profesionales habilitados.
- La IA, si se incorpora, debe tener un propósito acotado, explicar su aporte y quedar bajo revisión humana. No diagnostica, prescribe ni modifica indicaciones.
- Diseñar con accesibilidad y probar las pantallas con personas usuarias diversas.

## Límites por definir

Todavía no están aprobados los módulos de la primera versión, los roles y permisos detallados, los datos clínicos necesarios, los avisos a familiares, las escalas, las integraciones, el uso de IA, la operación sin conectividad ni las obligaciones legales específicas en Argentina y Uruguay.

Las ideas de monitoreo por cámaras o sensores, reconocimiento de emociones, generación automática de informes clínicos y métricas de impacto promocionales no forman parte del alcance aprobado.

## Próximo trabajo

Usar los antecedentes para preparar entrevistas y observación en la residencia piloto. Documentar cómo se trabaja actualmente, qué dificultades se repiten y qué información necesita cada participante. Con esa evidencia se definirá el alcance inicial, los límites de acceso y los criterios de aceptación.
