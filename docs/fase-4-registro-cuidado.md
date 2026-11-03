# Fase 4 — Registro del cuidado y entrega de turno

**Estado:** primera entrega implementada el 03/11/2026 en el entorno local, con pruebas automáticas. Falta validarla con el equipo piloto. Las decisiones marcadas abajo las tomó el agente con criterios razonables y se pueden cambiar.

## Qué se implementó

| Parte | Qué hace | Quién |
|---|---|---|
| Registro diario | Nota breve sobre una persona: tipo (alimentación, higiene, descanso, ánimo, actividad, salud, incidente, otro), qué pasó, si es importante para el próximo turno y, opcionalmente, la hora si pasó antes | Todo el personal del servicio |
| Pendientes | Algo que hay que hacer, del servicio o de una persona, con fecha opcional. Pasa de turno en turno hasta que alguien lo marca como hecho | Crear y resolver: todo el personal. Cancelar: quien lo creó o el encargado |
| Entrega de turno | Pantalla "Turno y registros": lo importante desde el turno anterior, los pendientes abiertos, lo registrado en el turno actual y en el anterior | Todo el personal del servicio |
| Ficha de la persona | Sección "Registro diario" con los últimos 7 días y sus pendientes | Todo el personal del servicio |

- **Los registros no se editan.** Si hay un error, quien lo cargó o el encargado lo anula con un motivo. **Un incidente solo lo anula el encargado**, para que nadie pueda retirar solo un incidente propio. Queda visible tachado en la ficha y desaparece de la entrega de turno.
- **La familia no ve estos registros.** Para compartir algo, alguien del equipo publica una novedad revisando el texto (ver [Fase 5](fase-5-comunicacion-familia.md)).
- Cada carga, anulación y consulta queda en el registro de control. El registro de control guarda el tipo de nota, pero no su texto.
- Momento no interpreta los registros. El formulario recuerda que ante una urgencia se sigue el protocolo de la residencia.

## Configuración por servicio

Cada residencia o servicio domiciliario decide cómo trabaja. Lo configura el **encargado de la organización** en "Organizaciones" → cada servicio → "Registro diario y turnos". Los cambios se aplican desde ese momento y quedan en el registro de control. Si un servicio no cambia nada, usa los valores por defecto.

| Opción | Valor por defecto | Alternativas |
|---|---|---|
| Turnos | 3 de 8 h: Mañana 6, Tarde 14, Noche 22 | 2 de 12 h (Día 8, Noche 20) o de 1 a 6 turnos con nombre y hora a elección |
| Tipos de novedad | Los 8 habilitados: alimentación, higiene, descanso, ánimo, actividad, salud, incidente, otro | Desactivar los que no se usan y cambiarles el nombre. "Incidente" siempre queda activo y con su nombre, porque de él dependen los avisos |
| Registros olvidados | Hasta 7 días hacia atrás | De 0 (solo en el momento) a 31 días |
| Incidente importante | Siempre se marca como importante | Que lo decida quien registra |
| Quién anula un incidente | Solo el encargado | También quien lo cargó |
| Aviso de incidentes en Momento | Al encargado | Cualquier combinación de puestos, o nadie |
| Además, aviso por correo | No | Sí (a los mismos puestos) |

Otras reglas:
- **Avisos en Momento:** aparecen en la campana de la barra superior, con el nombre de la persona y quién lo cargó. Lo que pasó se lee en "Turno y registros", al que lleva el aviso. La web consulta cada minuto. Los avisos se guardan en el servidor (`/api/notifications`), así la **app móvil de la Fase 7 usará los mismos avisos** y podrá sumar notificaciones push. Cada persona ve solo sus avisos, y solo mientras siga como personal activo del servicio del aviso: si la desactivan o la pasan a otro servicio, deja de verlos.
- **Aviso por correo (opcional):** solo dice que hubo un incidente en el servicio, sin nombre ni detalle. El correo real requiere configurar el servidor de correo (ver Fase 2).
- Quien registra el incidente no recibe aviso.
- Cualquiera del servicio puede marcar un pendiente como hecho, y queda guardado quién fue y su nota. Cancelarlo es solo de quien lo creó o del encargado.
- La zona horaria sale del país del servicio (Argentina o Uruguay).

Los valores por defecto están en `backend/src/momento_api/care_settings.py` (`DEFAULTS`).

## Fuera de esta entrega

- **Medicación:** requiere validar con el equipo cómo se indica, quién administra y cómo se registra una omisión. No se implementó.
- Plan de cuidado por persona, tareas programadas que se repiten, recordatorios y registro por voz: siguen como propuestas de los documentos.
- Escalamiento automático de incidentes (avisos a la encargada o a la familia): requiere definir responsables y canales.

## Preguntas para el piloto

Ya no bloquean el desarrollo: cada servicio las responde en su configuración. Conviene igual revisarlas con el piloto para elegir buenos valores por defecto.
