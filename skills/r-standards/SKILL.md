---
name: r-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y documentación para R. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .R, .r o .Rmd.
when_to_use: Al generar código R, refactorizar archivos .R/.Rmd, realizar revisiones de código de scripts de R, o estructurar funciones, paquetes y documentación roxygen2.
allowed-tools: Read Grep
---

# Estándares de Arquitectura y Código R

Como agente de IA, DEBES cumplir estrictamente estas normativas de calidad (basadas en el **tidyverse style guide** y **roxygen2**) al trabajar con archivos R (`.R`, `.r`, `.Rmd`).

## 1. Reglas Generales e Idioma Mixto
- **Código en Inglés:** Identificadores (variables, funciones, argumentos, constantes) DEBEN estar estrictamente en inglés. No uses abreviaturas crípticas (ej. usa `filtered_data`, NO `fd`).
- **Documentación en Español:** Todos los comentarios (`#`) y bloques roxygen2 (`#'`) DEBEN redactarse en español.
- **Tiempos Verbales:** Documenta siempre en **presente activo** (ej. "Esta función calcula...", NO "Se calculó...").

## 2. Nomenclatura Estricta (tidyverse)
- **Variables y Funciones:** `snake_case` (ej. `image_processor`, `calculate_metrics()`). Las funciones, idealmente verbos.
- **Nada de puntos en nombres:** Evita `.` en nombres de objetos/funciones (`calc.mean`) — el punto está reservado para métodos S3 (`print.miclase`).
- **Clases:** S4 y R6 en `UpperCamelCase` (ej. `DatabaseAuditor`); métodos S3 como `generico.clase`.
- **Constantes y Globales:** `UPPER_SNAKE_CASE` (ej. `MAX_RETRIES`, `DEFAULT_THRESHOLD`). Evita números mágicos hardcodeados.
- **Archivos:** `snake_case.R`, nombre que describa su contenido (ej. `fit_models.R`).

## 3. Sintaxis y Estilo (tidyverse)
- **Asignación:** usa `<-`, NO `=`, para asignar (`x <- 5`). Reserva `=` para argumentos de funciones.
- **Espaciado:** espacios alrededor de operadores binarios (`x + 1`, `y <- 2`) y después de comas; sin espacio antes de `(` en llamadas.
- **Pipe:** encadena con `|>` (nativo) o `%>%` (magrittr); un paso por línea, indentado.
- **Líneas:** máximo ~80 caracteres. Llaves `{` al final de la línea, `}` en su propia línea.

## 4. Comentarios Internos (`#`)
- **El Porqué, no el Qué:** El código limpio se explica solo. Usa comentarios inline solo para decisiones técnicas complejas, fundamentos matemáticos o *workarounds* temporales.
- **Alineación:** mínimo dos espacios antes de un comentario inline en la misma línea.
- **Mala práctica:** `x <- x + 1  # Incrementa x en 1` (explica el qué).
- **Buena práctica:** `Sys.sleep(2)  # Pausa necesaria para no exceder el rate-limit de la API` (explica el porqué).

## 5. Recursos Detallados y Plantillas Obligatorias
Consulta dinámicamente según sea necesario:
- Para la organización top-down del archivo y modularidad: Ver [references/architecture.md](references/architecture.md)
- Para plantillas exactas de roxygen2 (funciones) y encabezado de archivo: Ver [references/documentation.md](references/documentation.md)
