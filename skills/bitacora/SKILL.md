---
name: bitacora
description: Registra incidentes/bugs/refactors en docs/logs/log.md con formato forense (sintoma -> hipotesis -> causa raiz -> resolucion -> verificacion -> lecciones). CARGA cuando se resuelve un error, se documenta un incidente, o antes de depurar (consultar el log primero).
when_to_use: Ante cualquier bug/bloqueo resuelto, o para consultar incidentes previos.
allowed-tools: Read Grep Glob Write Edit
---

# Bitácora de Incidencias

Mantiene `docs/logs/log.md`: un registro forense y cronológico de bugs, bloqueos y refactors resueltos. Es memoria del proyecto para no reincidir en el mismo error y para acelerar el diagnóstico consultando incidentes previos antes de depurar de cero.

## Flujo

1. **Asegura el archivo.** Comprueba si existe `docs/logs/log.md` (`Glob`/`Read`). Si no existe, créalo copiando literalmente `templates/plantilla_log.md` como semilla (con su bloque "[Plantilla Vacía - Copiar para Nuevas Entradas]" y el ejemplo de referencia) y reemplaza `[Nombre del Proyecto]` en el título por el nombre real del proyecto. Si el directorio `docs/logs/` no existe, créalo al escribir el archivo.

2. **Consulta primero (obligatorio ante un error).** Antes de diagnosticar un bug nuevo, busca en `docs/logs/log.md` una entrada previa que coincida por síntoma, componente afectado, traza de error o mensaje (`Grep` sobre síntomas/logs, `Read` de las entradas candidatas). Si encuentras una coincidencia, parte de su causa raíz y sus lecciones aprendidas en lugar de empezar de cero, y dilo explícitamente al usuario.

3. **Redacta la entrada nueva.** Reúne la evidencia real del incidente resuelto (síntoma observado, hipótesis validadas/descartadas, causa raíz técnica, cambios aplicados con archivos tocados, verificación con pruebas/mediciones, y lecciones accionables). Usa fecha absoluta `YYYY-MM-DD` (hoy) en el encabezado, junto al título corto del incidente y los componentes afectados.

4. **Inserta al principio.** Agrega la entrada al **inicio** de la sección de incidentes (orden cronológico inverso: lo más reciente primero), justo antes de las entradas ya existentes. Usa `Edit` para insertar sin borrar el bloque de plantilla vacía, el ejemplo de referencia ni las entradas anteriores.

5. **Cierra.** Confirma la ruta de la entrada escrita y, si la causa raíz revela un cambio de contrato (DB/API/arquitectura), sugiere actualizar los docs con `especificar` o correr `auditar-coherencia`.

## Reglas / Salida

- **Formato forense fijo.** Toda entrada usa las 6 secciones del template `templates/plantilla_log.md`, en este orden y con estos títulos:
  1. `### 1. Síntoma Observado / Reporte` — qué falló, entorno (Local/Staging/Producción) y traza de error o payload fallido en bloque de código.
  2. `### 2. Hipótesis de Diagnóstico` — teorías numeradas, cada una con su resultado (Descartada porque… / Confirmada mediante…).
  3. `### 3. Causa Raíz` — explicación técnica **real** del porqué (condición de carrera, desalineación de contrato de API, concurrencia en DB, timeout en llamada síncrona, etc.). Nunca una causa genérica ni especulativa cuando ya se resolvió.
  4. `### 4. Resolución e Implementación` — pasos exactos y archivos editados/refactorizados; incluye diff de referencia cuando aporte.
  5. `### 5. Verificación y Mediciones` — pruebas ejecutadas que certifican la resolución sin regresiones; incluye tiempos/telemetría antes/después si aplica.
  6. `### 6. Lecciones Aprendidas (Retroalimentación)` — guardarraíles accionables para evitar la reincidencia (validaciones, reintentos con backoff, circuit breakers, invariantes de escritura, etc.).
- **Encabezado de entrada:** `## YYYY-MM-DD — [Título corto] — [Componentes Afectados]` con fecha absoluta (nunca "hoy"/"ayer" ni relativa).
- **Consulta antes de diagnosticar:** ante un error, primero se busca en el log; solo si no hay coincidencia se diagnostica desde cero.
- **No borra historia:** las entradas se acumulan; nunca se sobrescriben ni se reordena el archivo salvo para insertar la nueva entrada al principio. Se conservan el bloque de plantilla vacía y el ejemplo de referencia del template.
- **Sin secciones en blanco ni placeholders:** cada una de las 6 secciones debe tener contenido real del incidente; nada de "TBD"/"TODO"/marcadores del template sin rellenar.
- **Salida:** el archivo `docs/logs/log.md` actualizado (o creado desde `templates/plantilla_log.md`) con la nueva entrada al principio, más un resumen breve al usuario de qué se registró y qué lección clave quedó anotada.
