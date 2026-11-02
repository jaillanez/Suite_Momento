# Escalas y antecedentes de la ficha

**Fuentes:** planilla "Escalas Momento Instituciones" y "apuntes MOMENTO 03/09/26" (revisión del sistema anterior), entregados por Jorge el 02/11/2026.
**Estado:** implementado en el entorno local. Las preguntas, opciones y puntajes se transcriben de la planilla; las diferencias están marcadas abajo y deben confirmarse con el equipo profesional.

## Qué se implementó

| Parte | Contenido | Quién la carga | Quién la ve |
|---|---|---|---|
| Datos generales | Sexo, lugar de nacimiento (país, provincia, localidad), nivel de instrucción y título, ocupación, estado civil, hijos, foto actual. "Cómo le gusta ser nombrado/a" se muestra destacado en la ficha | Encargado, administrativo, médico | Todo el personal del servicio |
| Antecedentes y datos de ingreso | Sentidos y movilidad, sueño y hábitos, antecedentes personales, estado cognitivo y funcional, datos de ingreso (peso, talla, IMC calculado, tensión arterial, ritmo cardíaco, plan farmacológico, reacciones adversas, resumen de estudios), antecedentes familiares, autonomía y tecnología | Encargado, médico | Todo el personal del servicio |
| Escalas | Barthel, Yesavage (GDS-15), Cuestionario de quejas cognitivas (CQC), ACE-III | Encargado, médico | Todo el personal del servicio |

La familia no ve nada de esto. Cada carga, consulta y borrado queda en el registro de control. Las evaluaciones no se editan: si hay un error, el encargado la borra y se carga de nuevo.

El puntaje lo calcula siempre el servidor (también la vista previa mientras se completa), para que lo que se ve y lo que se guarda coincidan. **El sistema no interpreta resultados**, salvo los rangos de Barthel que figuran en la planilla.

## Correcciones respecto de la planilla y del sistema anterior

1. **Barthel suma 100 como máximo.** La planilla da 15 a "Comer – Independiente", y con eso el total llega a 105, que es el error señalado en los apuntes. Se usa **10**, el valor del índice de Barthel estándar. **Confirmar con el equipo.**
2. **Barthel = 100** no figura en la tabla de rangos (llega a 91–99 "Mínima"). Se muestra como **"Independiente"**. **Confirmar.**
3. **ACE-III – frases:** "El flan tiene frutillas y frambuesas" y "La orquesta tocó y la audiencia la aplaudió".
4. **ACE-III – visoespacial:** diagrama **infinito** superpuesto en lugar de pentágonos; "**esfera**" del reloj en lugar de "cara".
5. **ACE-III – reconocimiento:** lo recordado en el recuerdo demorado suma automáticamente en reconocimiento y no se vuelve a preguntar. Nombre (Luis + Reynal) y calle (Pedro + Goyena) se acreditan solo si se recordaron ambas partes.
6. **Impresión:** el botón "Imprimir ficha" incluye antecedentes y escalas.
7. **Botones:** toda acción principal en violeta; "Cargar documento" con flecha de carga.

## Decisiones tomadas por el agente (revisar)

- **Restas seriadas:** cada resta cuenta si es 7 menos que la respuesta anterior (la primera, desde 100). Es la regla habitual del ACE-III; la planilla remite a una hoja "RESTAS" que no vino en el PDF.
- **Fluencia (palabras con P y animales):** el evaluador anota la cantidad de palabras y el **puntaje convertido (0 a 7)**, como indica la planilla ("lo realiza el evaluador solo"). La tabla de conversión (hoja "PALABRAS") no vino en el PDF; si la mandan, el sistema puede convertir solo.
- **Reconocimiento de voz** para fluencia: no se implementó (requiere un servicio externo). El evaluador carga los números a mano.
- **Fotos de dibujos** (escritura, infinito, cubo, reloj): se cargan como documento de la ficha; la escala solo guarda el puntaje.
- **Memoria retrógrada:** no se guardan nombres de presidentes ni del Papa (la planilla dice "Alberto Fernández", ya desactualizado); el evaluador marca si la respuesta es correcta al día de la evaluación.
- **"Lápiz y papel 1"** figura como #REF! en la planilla y no se incluyó; la comprensión se puntúa con las 3 órdenes de "Lápiz y papel 2".
- **Yesavage y CQC:** se muestran puntaje total y por dominio, sin puntos de corte (la planilla no los define).
- **Lectura irregular:** se respeta la grafía de la planilla ("Lassagna").

## Observación de los apuntes sin cambio de código

Los apuntes preguntan si en "Vivares Vanina" se cruzaron nombre y apellido. En Momento la ficha separa nombres y apellidos, y el nombre visible se carga aparte; conviene acordar con el equipo un formato único (por ejemplo, "Apellido, Nombre" en listados).
