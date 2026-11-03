# Fase 5 — Comunicación con la familia

**Estado:** primera entrega implementada el 03/11/2026 en el entorno local, con pruebas automáticas. Falta validarla con el equipo piloto. Las opciones por defecto las eligió el agente y cada servicio las puede cambiar.

## Qué se implementó: novedades para la familia

| Parte | Qué hace | Quién |
|---|---|---|
| Publicar una novedad | Texto breve para la familia sobre una persona. Se escribe desde la ficha ("Novedades para la familia" → "+ Novedad") o desde un registro del día ("Compartir con la familia"), que copia el texto para revisarlo antes de publicar | Los puestos habilitados en el servicio (por defecto, todo el personal) |
| Retirar una novedad | La familia deja de verla. Queda en la ficha tachada, con el motivo | Quien la publicó o el encargado |
| Ver novedades | Sección "Novedades" en el portal de familias, con la persona, la fecha y el puesto de quien publicó | Familiares con el permiso «Novedades» para esa persona |
| Aviso a la familia | La campana del portal familiar avisa cuando hay una novedad nueva | Configurable por servicio (por defecto, sí) |

## Fotos (03/11/2026)

- Una novedad puede llevar **una foto** (JPG o PNG, hasta 5 MB).
- Solo si la persona tiene registrado su **consentimiento de imagen**: quién lo dio (la persona o su representante) y la fecha. Lo registran o quitan el encargado, un administrativo o el médico, desde la ficha → "Novedades para la familia". Se recomienda guardar el consentimiento firmado en Documentos con el tipo «Consentimiento».
- Quien publica debe confirmar que **en la foto no aparecen otras personas, o que también dieron su consentimiento**.
- Si se quita el consentimiento, o el servicio deja de permitir fotos, la familia **deja de ver las fotos ya publicadas**; el texto de la novedad sigue visible.
- Las fotos se guardan en el disco del servidor, como los documentos de la ficha, y solo se entregan a quien tiene permiso. No se guardan en el navegador.
- Momento no decide qué vale como consentimiento válido: eso lo define la residencia según la normativa de cada país.

## Reglas de privacidad

- **Nada del registro diario llega solo a la familia.** Siempre hay una persona del equipo que escribe o revisa el texto y decide publicarlo. Al compartir un registro se copia el texto; la familia nunca ve el registro original, su tipo ni quién lo cargó.
- **"Novedades" es un permiso más**, igual que Medicación, Actividades y Dietas. Lo otorga el encargado, un administrativo o el médico en "Usuarios y vínculos". Si nadie lo tiene, no se puede publicar (para no escribir algo que nadie lee).
- Si se revoca el permiso o se retira la novedad, la familia deja de verla, y también desaparece su aviso.
- A la familia se le muestra **el puesto** de quien publicó (por ejemplo, "Cuidador/a"), no su nombre.
- Las novedades no se editan. Si hay un error, se retiran con motivo y se publica otra.
- Publicar, retirar y consultar quedan en el registro de control. El registro guarda cuántos familiares podían leerla, no el texto.
- La familia también puede hacer consultas con el tema «Novedades» desde "Nueva consulta"; llegan a la bandeja como las demás.

## Configuración por servicio

En "Organizaciones" → cada servicio → "Registro diario y turnos" → "Novedades para la familia":

| Opción | Valor por defecto | Alternativas |
|---|---|---|
| Quién puede publicar | Encargado, administrativo, médico y cuidador | Cualquier combinación de puestos, o nadie |
| Avisar a la familia en Momento | Sí | No |
| Permitir fotos | Sí (y además cada persona necesita su consentimiento de imagen) | No |

Los valores por defecto están en `backend/src/momento_api/care_settings.py` (`DEFAULTS`).

## Para validar con el piloto

- ¿Está bien que los cuidadores publiquen directamente, o la residencia prefiere que lo haga solo el encargado? (Se cambia en la configuración, sin programar.)
- ¿Mostrar el nombre de quien publica en vez del puesto?
- ¿Qué documento usa la residencia como consentimiento de imagen y quién puede firmarlo?
- ¿Hace falta un aviso por correo a la familia además del aviso en Momento? (Hoy no existe; el correo no llevaría el texto.)

## Fuera de esta entrega

- **Mensajes en ambos sentidos (chat):** hoy la familia escribe por "Nueva consulta" y el equipo responde desde la bandeja.
- Notificaciones push: llegan con la app móvil (Fase 7), que usará las mismas rutas de avisos (`/api/family/notifications`).
