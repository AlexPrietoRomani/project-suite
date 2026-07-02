# Estructura y Modularidad de Archivos R

Todo script o módulo `.R` nuevo o modificado debe seguir una organización lógica secuencial top-down:

## Flujo de Organización Secuencial
1. **Encabezado del Archivo:** Bloque de comentarios informativo del ciclo de vida y alcance del archivo (ver plantilla en `documentation.md`).
2. **Carga de Dependencias:** Agrupadas y ordenadas, separando cada bloque por una única línea en blanco:
   - Librerías base / del sistema (ej. `library(stats)`, `library(utils)`).
   - Paquetes de terceros (ej. `library(dplyr)`, `library(lme4)`).
   - Módulos locales del proyecto vía `source()` (ej. `source("R/utils_io.R")`).
   - Prefiere `library()` al inicio; evita `require()` salvo para chequeo condicional. No uses `install.packages()` dentro de scripts de análisis.
3. **Variables Globales / Constantes:** Configuraciones fijas del archivo si no se externalizan a un `config.R` (en `UPPER_SNAKE_CASE`).
4. **Funciones Modulares:** Estructuras que apliquen el principio de Responsabilidad Única. Si una función asume múltiples responsabilidades (ej. lectura, transformación y persistencia), DEBE descomponerse en funciones atómicas independientes.
5. **Bloque de Entrada Principal:** Encapsula toda la lógica de ejecución en una función `main()` y protégela para que no corra al hacer `source()`:

```r
main <- function() {
  # Toda la lógica de ejecución del script vive aquí.
}

if (sys.nframe() == 0L) {
  main()
}
```

`sys.nframe() == 0L` es verdadero solo cuando el archivo se ejecuta directamente (ej. `Rscript script.R`), no cuando se carga con `source()` desde otro archivo. Es el equivalente en R del `if __name__ == "__main__"` de Python.

## Notas sobre paquetes (estructura formal)
Si el código forma parte de un paquete R (no un script suelto):
- Las funciones van en `R/`, una responsabilidad lógica por archivo.
- La documentación se genera con roxygen2 (`devtools::document()`), no se edita `man/` a mano.
- Dependencias declaradas en `DESCRIPTION` (`Imports`/`Suggests`), referenciadas como `paquete::funcion()` dentro del código del paquete (no `library()`).
