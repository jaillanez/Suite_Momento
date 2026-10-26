# Instrucciones para agentes de IA

## Contexto del producto

Momento es un producto nuevo para el cuidado de personas mayores en residencias y domicilios, con Argentina y Uruguay como mercados iniciales. El repositorio no debe tratarse como una continuación técnica del sistema antiguo.

## Reglas de trabajo

1. No copiar ni reutilizar código, estructura, base de datos, pantallas o arquitectura del sistema viejo.
2. Usar los materiales históricos solo para extraer necesidades, problemas y aprendizajes; diferenciar hechos confirmados de propuestas.
3. No inventar reglas clínicas, legales, operativas ni comerciales. Marcar dudas y pedir validación antes de convertirlas en comportamiento del producto.
4. No tomar decisiones de producto relevantes por cuenta propia. Presentar opciones y explicar sus consecuencias.
5. Mantener documentación clara y en español, salvo nombres técnicos y convenciones del código.
6. La IA no debe diagnosticar, prescribir, modificar indicaciones clínicas ni enviar información sensible a terceros sin autorización explícita.
7. Proteger datos personales y de salud desde el diseño. Aplicar acceso por rol y organización cuando se defina el modelo.
8. Mantener el desarrollo local sin Docker. Stack acordado: Python, PostgreSQL y React. Validar las versiones al configurar el entorno.
9. No instalar, actualizar ni eliminar Xcode o Command Line Tools; esta Mac también se usa para otros proyectos.
10. No agregar servicios, dependencias o infraestructura sin una necesidad identificada.
11. Antes de modificar archivos, revisar el estado del repositorio. Al terminar, resumir cambios, comprobaciones y decisiones pendientes.

## Forma de avanzar

- Documentar visión, personas, procesos y alcance antes de construir funcionalidades.
- Trabajar en entregas pequeñas y revisables.
- No considerar una idea de los documentos de referencia como requisito aprobado automáticamente.
- No publicar, desplegar, migrar datos ni conectar el sistema nuevo con el anterior sin autorización explícita.
