# Fase 3 — Ficha de la persona mayor

**Estado:** implementada el 02/11/2026 en el entorno local, con datos obligatorios, notas del equipo y documentos adjuntos. Los campos y permisos son una propuesta de trabajo: deben revisarse con los profesionales y el equipo piloto antes de usar datos reales.

## Decisión de Jorge

El 02/11/2026 Jorge pidió que la ficha esté completa. Se implementaron todos los campos de la lista base; solo el nombre visible es obligatorio. Qué otros datos serán obligatorios lo definirá el equipo piloto con los profesionales.

## Contenido de la ficha

| Sección | Campos |
|---|---|
| Datos generales | Nombre visible, cómo le gusta ser nombrado/a, sexo, lugar de nacimiento, nivel de instrucción, ocupación, estado civil, hijos, foto, nombres, apellidos, fecha de nacimiento, tipo y número de documento (DNI, CI, pasaporte u otro), nacionalidad, idiomas, fecha de ingreso, habitación o cama, domicilio (cuidado domiciliario) |
| Cobertura | Obra social, prepaga o mutualista; número de afiliado; médico de cabecera y su teléfono |
| Salud y apoyos | Alergias, antecedentes relevantes, dieta y restricciones, movilidad y ayudas técnicas, audición/visión/comunicación, apoyos y cuidados especiales |
| Historia y preferencias | Historia de vida, gustos y preferencias, rutinas, creencias y prácticas espirituales |
| Contactos | Nombre, vínculo, teléfono, correo, notas; marca de contacto de emergencia (exige teléfono) y de referente legal o apoderado |

La sección de salud es **información de referencia**: no reemplaza la historia clínica, no son indicaciones y Momento no aplica reglas clínicas sobre esos datos.

## Antecedentes y escalas

Los antecedentes, datos de ingreso y escalas (Barthel, Yesavage, CQC y ACE-III) siguen la planilla del equipo. Detalle, correcciones y dudas en [Escalas y antecedentes](escalas.md).

## Datos obligatorios (confirmado por Jorge el 02/11/2026)

Nombre, fecha de nacimiento, documento, fecha de ingreso, habitación (o domicilio en cuidado domiciliario) y al menos un contacto de emergencia.

No bloquean el guardado: se puede dar de alta a una persona con datos parciales. La ficha muestra "Ficha incompleta" con la lista de lo que falta, y el listado marca a las personas con ficha incompleta.

## Permisos aplicados

| Acción | Encargado | Administrativo | Médico | Cuidador | Familia |
|---|---|---|---|---|---|
| Ver la ficha completa | Sí | Sí | Sí | Sí | No |
| Dar de alta una persona | Sí | Sí | No | No | No |
| Editar identificación, cobertura y contactos | Sí | Sí | Sí | No | No |
| Editar historia de vida y preferencias | Sí | Sí | Sí | Sí | No |
| Editar salud y apoyos | Sí | No | Sí | No | No |
| Dar de baja (deja de aparecer; la ficha se conserva) | Sí | No | No | No | No |
| Ver y descargar documentos | Sí | Sí | Sí | Sí | No |
| Subir y borrar documentos | Sí | Sí | No | No | No |

Todo el personal ve solo las personas de los servicios que alcanza su vínculo. La familia no ve la ficha: su acceso sigue limitado a medicación, actividades y dietas según lo autorizado en Fase 2.

Cada consulta de la ficha, cada cambio (con los nombres de los campos modificados, nunca sus valores) y cada cambio de contactos queda en el registro de control.

## Documentos adjuntos

- Tipos: documento de identidad, consentimiento, estudio o informe, otro.
- Formatos: PDF, JPG o PNG, hasta 10 MB. Se verifica que el contenido coincida con el formato declarado.
- Se guardan en el disco de la Mac (`backend/storage/documents`, excluido de Git; se puede cambiar con `MOMENTO_DOCUMENTS_DIR`). El nombre interno lo genera el sistema; el nombre original solo se muestra.
- Subida, descarga y borrado quedan en el registro de control.
- No se agregó ninguna dependencia ni servicio externo: el archivo se envía directo en la solicitud.

## Pendiente de validar

- Si algún campo de salud debe ocultarse a ciertos puestos.
- Dónde se guardarán los documentos fuera del entorno local (copias de respaldo, cifrado) y cuánto tiempo se conservan.
- Requisitos legales de Argentina y Uruguay sobre datos de salud y consentimiento.

## Datos de demostración

El asistente de demo completa las 42 fichas con datos ficticios (fecha de nacimiento, documento, habitación, cobertura, médico de cabecera y un contacto de emergencia) y tres fichas con historia, preferencias y salud marcadas como "dato ficticio". Solo lo hace si ninguna ficha tiene datos cargados.
