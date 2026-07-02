# Estándares de Documentación R (roxygen2)

## 1. Documentación de Funciones (roxygen2 en Español)
Todo bloque roxygen2 va inmediatamente **encima** de la definición de la función, con cada línea iniciada por `#'`. Documenta cada parámetro con `@param`, el retorno con `@returns` (forma preferida; `@return` sigue siendo válido) y, cuando aporte, un `@examples`.

```r
#' Extrae la latitud, longitud y precisión de los metadatos EXIF de una imagen.
#'
#' @param image_path character. Ruta absoluta o relativa al archivo de imagen.
#' @param confidence numeric. Umbral mínimo de confianza. Por defecto 0.8.
#'
#' @returns Una lista con los elementos `latitude`, `longitude` y `accuracy`.
#'   Devuelve una lista vacía si no se encuentran metadatos espaciales.
#'
#' @examples
#' extract_spatial_metadata("data/img_001.jpg", confidence = 0.9)
#'
#' @export
extract_spatial_metadata <- function(image_path, confidence = 0.8) {
  # ...
}
```

Notas:
- Como R no tiene type hints nativos, **declara el tipo esperado en la descripción de cada `@param`** (ej. `character`, `numeric`, `data.frame`, `logical`). Valida en runtime con `stopifnot()` o el paquete `checkmate` cuando el tipo sea crítico.
- Usa `@export` solo en funciones públicas de un paquete; omítelo en helpers internos.
- Tags útiles adicionales: `@inheritParams`, `@seealso`, `@importFrom paquete funcion`, `@keywords internal`.

## 2. Encabezado de Archivo (Obligatorio)
Todo archivo debe iniciar con este bloque de comentarios. Integra únicamente la **Opción Condicional** (A, B o C) que coincida con la naturaleza del archivo.

```r
# =============================================================================
# Archivo: <nombre_del_archivo.R>
# Fecha de modificación: <DD/MM/YYYY>
# Autor: <Nombre del Autor/Equipo>
#
# Descripción:
#   <Descripción detallada y activa de la lógica global presente.>
#
# Sustentación Científica: [Opcional]
#   <Justificación algorítmica/estadística. Formato APA / referencia a papers.>
#
# Acciones Principales:
#   - <Acción clave 1 ejecutada por el módulo.>
#
# Estructura Interna:
#   - `<nombre_funcion()>`: <Breve rol o responsabilidad.>
#
# Entradas / Dependencias:
#   - <Archivos, variables de entorno o recursos requeridos.>
#
# Salidas / Efectos:
#   - <Archivos, datos o estados que genera o modifica.>
#
# --- OPCIÓN A: EJECUTABLE (Rscript / scripts con main()) ---
# Ejecución:
#   Rscript <nombre_del_archivo.R> [--argumentos]
# Ejemplo de Uso:
#   Rscript <nombre_del_archivo.R> --input data/raw --response calibre
# Argumentos:
#   - <argumento_1>: <Tipo> - <Descripción detallada.>
#
# --- OPCIÓN B: MÓDULO DE UTILIDAD (funciones internas vía source()) ---
# Ejemplo de Integración:
#   source("R/<nombre_del_archivo>.R")
#   resultado <- <funcion_principal>(datos)
#
# --- OPCIÓN C: COMPONENTE DE UI / REPORTE (Shiny, R Markdown, plumber) ---
# Integración:
#   - Este archivo renderiza la vista/reporte de <Nombre_Componente>.
#   - Es invocado por <orquestador.R> mediante <funcion_de_render>().
# =============================================================================
```

## 3. Argumentos CLI (cuando aplica la Opción A)
Para scripts ejecutables con `Rscript`, parsea argumentos con `optparse` (legible y autodocumentado) en lugar de `commandArgs()` crudo:

```r
library(optparse)

option_list <- list(
  make_option("--input", type = "character", help = "Ruta a los datos de entrada."),
  make_option("--response", type = "character", help = "Variable respuesta a modelar.")
)
opts <- parse_args(OptionParser(option_list = option_list))
```
