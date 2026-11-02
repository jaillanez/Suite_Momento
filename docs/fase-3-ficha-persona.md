# Fase 3 — Ficha de la persona mayor

**Estado:** implementada el 02/11/2026 en el entorno local. Los campos y permisos son una propuesta de trabajo: deben revisarse con los profesionales y el equipo piloto antes de usar datos reales.

## Decisión de Jorge

El 02/11/2026 Jorge pidió que la ficha esté completa. Se implementaron todos los campos de la lista base; solo el nombre visible es obligatorio. Qué otros datos serán obligatorios lo definirá el equipo piloto con los profesionales.

## Contenido de la ficha

| Sección | Campos |
|---|---|
| Identificación | Nombre visible, cómo prefiere que le digan, nombres, apellidos, fecha de nacimiento, tipo y número de documento (DNI, CI, pasaporte u otro), género (como la persona lo indique), nacionalidad, idiomas, fecha de ingreso, habitación o cama, domicilio (cuidado domiciliario) |
| Cobertura | Obra social, prepaga o mutualista; número de afiliado; médico de cabecera y su teléfono |
| Salud y apoyos | Alergias, antecedentes relevantes, dieta y restricciones, movilidad y ayudas técnicas, audición/visión/comunicación, apoyos y cuidados especiales |
| Historia y preferencias | Historia de vida, gustos y preferencias, rutinas, creencias y prácticas espirituales |
| Contactos | Nombre, vínculo, teléfono, correo, notas; marca de contacto de emergencia (exige teléfono) y de referente legal o apoderado |

La sección de salud es **información de referencia**: no reemplaza la historia clínica, no son indicaciones y Momento no aplica reglas clínicas sobre esos datos.

## Permisos aplicados

| Acción | Encargado | Administrativo | Médico | Cuidador | Familia |
|---|---|---|---|---|---|
| Ver la ficha completa | Sí | Sí | Sí | Sí | No |
| Dar de alta una persona | Sí | Sí | No | No | No |
| Editar identificación, cobertura, historia y contactos | Sí | Sí | Sí | No | No |
| Editar salud y apoyos | Sí | No | Sí | No | No |
| Dar de baja (deja de aparecer; la ficha se conserva) | Sí | No | No | No | No |

Todo el personal ve solo las personas de los servicios que alcanza su vínculo. La familia no ve la ficha: su acceso sigue limitado a medicación, actividades y dietas según lo autorizado en Fase 2.

Cada consulta de la ficha, cada cambio (con los nombres de los campos modificados, nunca sus valores) y cada cambio de contactos queda en el registro de control.

## Pendiente de validar

- Qué campos son obligatorios y en qué momento (al ingreso o después).
- Si el cuidador debe poder agregar observaciones de historia y preferencias.
- Si algún campo de salud debe ocultarse a ciertos puestos.
- Carga de documentos (DNI escaneado, consentimientos, estudios): requiere definir almacenamiento de archivos y su protección.
- Requisitos legales de Argentina y Uruguay sobre datos de salud y consentimiento.

## Datos de demostración

El asistente de demo completa las 42 fichas con datos ficticios (fecha de nacimiento, documento, habitación, cobertura, médico de cabecera y un contacto de emergencia) y tres fichas con historia, preferencias y salud marcadas como "dato ficticio". Solo lo hace si ninguna ficha tiene datos cargados.
