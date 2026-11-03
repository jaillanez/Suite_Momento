# Fase 4 — Registro del cuidado y entrega de turno

**Estado:** primera entrega implementada el 03/11/2026 en el entorno local, con pruebas automáticas. Falta validarla con el equipo piloto. Las decisiones marcadas abajo las tomó el agente con criterios razonables y se pueden cambiar.

## Qué se implementó

| Parte | Qué hace | Quién |
|---|---|---|
| Registro diario | Nota breve sobre una persona: tipo (alimentación, higiene, descanso, ánimo, actividad, salud, incidente, otro), qué pasó, si es importante para el próximo turno y, opcionalmente, la hora si pasó antes | Todo el personal del servicio |
| Pendientes | Algo que hay que hacer, del servicio o de una persona, con fecha opcional. Pasa de turno en turno hasta que alguien lo marca como hecho | Crear y resolver: todo el personal. Cancelar: quien lo creó o el encargado |
| Entrega de turno | Pantalla "Turno y registros": lo importante desde el turno anterior, los pendientes abiertos, lo registrado en el turno actual y en el anterior | Todo el personal del servicio |
| Ficha de la persona | Sección "Registro diario" con los últimos 7 días y sus pendientes | Todo el personal del servicio |

- **Los registros no se editan.** Si hay un error, quien lo cargó o el encargado lo anula con un motivo. Queda visible tachado en la ficha y desaparece de la entrega de turno.
- **La familia no ve estos registros.** Qué se comparte con la familia es parte de la Fase 5.
- Cada carga, anulación y consulta queda en el registro de control. El registro de control guarda el tipo de nota, pero no su texto.
- Momento no interpreta los registros. El formulario recuerda que ante una urgencia se sigue el protocolo de la residencia.

## Decisiones del agente (revisar con el piloto)

Los valores están en `backend/src/momento_api/care_log.py`, al comienzo del archivo.

| Decisión | Valor actual | Parámetro |
|---|---|---|
| Turnos | Mañana 6 a 14, Tarde 14 a 22, Noche 22 a 6, iguales para todos los servicios | `SHIFTS` |
| Zona horaria | Argentina (Buenos Aires) o Uruguay (Montevideo), según el país del servicio | `TIMEZONES` |
| Carga retroactiva | Hasta 7 días hacia atrás; no se aceptan horas futuras | `MAX_BACKDATE_DAYS` |
| Tipos de registro | Los 8 de la tabla de arriba | `CARE_ENTRY_CATEGORIES` en `models.py` (requiere migración) |
| Incidentes | Siempre se marcan como importantes | `create_entry` |

## Fuera de esta entrega

- **Medicación:** requiere validar con el equipo cómo se indica, quién administra y cómo se registra una omisión. No se implementó.
- Plan de cuidado por persona, tareas programadas que se repiten, recordatorios y registro por voz: siguen como propuestas de los documentos.
- Escalamiento automático de incidentes (avisos a la encargada o a la familia): requiere definir responsables y canales.

## Preguntas para el piloto

1. ¿Los turnos son de 8 horas (mañana, tarde, noche) o de 12? ¿Cambian según el servicio?
2. ¿Qué tipos de registro usan hoy en el cuaderno o planilla de novedades?
3. ¿Quién tiene que enterarse de un incidente y cómo se avisa hoy?
