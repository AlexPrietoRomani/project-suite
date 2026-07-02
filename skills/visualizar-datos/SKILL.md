---
name: visualizar-datos
description: Genera visualizaciones de datos on-demand durante el desarrollo de cualquier proyecto (ETL, ciencia de datos, apps web) -- estaticas (matplotlib/seaborn/ggplot2, con perfiles de journal) o interactivas (Plotly, nativo via Shiny o standalone). CARGA ESTA HABILIDAD cuando el usuario pida graficar, visualizar, explorar o depurar datos durante la construccion de un proyecto. NO uses esta skill para la figura final de un reporte/articulo -- para eso existe research-suite:graficar-datos.
when_to_use: Exploracion o depuracion de datos en un pipeline ETL o de ciencia de datos; generar un chart o dashboard interactivo para una app web; cualquier visualizacion de datos que no sea la figura final de un documento.
allowed-tools: Read Grep Write Edit Bash Skill mcp__context7__resolve-library-id mcp__context7__query-docs
---

# Visualizar datos (matplotlib / seaborn / ggplot2 / Plotly)

Visualizacion de datos **on-demand**, durante el proceso de construir, depurar o monitorear cualquier proyecto -- no la figura final de un documento (esa es `research-suite:graficar-datos`). Toda visualizacion se hace con **codigo**, nunca con generadores de imagen por IA.

## 0. REGLA DURA: datos = codigo

Una grafica de datos sale siempre de los datos reales via un script reproducible. **Nunca** inventes numeros ni uses un generador de imagen por IA para representar datos.

## 1. Elige el modo: estatico o interactivo

| Contexto de la peticion | Modo |
|---|---|
| Explorar o depurar datos durante desarrollo (salida de un paso ETL, celda de notebook, pipeline en construccion) | **Interactivo** |
| Chart o dashboard embebido en una app o frontend (independiente de si el proyecto esta en desarrollo o ya en produccion) | **Interactivo** |
| Reporte o documento final con contexto claro de que es para eso (aunque no de mas detalle) | **Estatico** |
| Peticion sin ninguna senal de formato (ej. "grafica esto" a secas, sin mencionar documento, app ni exploracion) | **Pregunta** cual de los dos quiere |

## 2. Modo estatico (matplotlib / seaborn / ggplot2)

| Lenguaje del proyecto | Libreria |
|---|---|
| **Python** | **matplotlib** (base) y **seaborn** (estadistico, por defecto para datos tabulares) |
| **R** | **ggplot2** |

Elige el tipo de grafica segun el dato:

| Quieres mostrar... | Grafica |
|---|---|
| Comparar categorias | barras |
| Evolucion en el tiempo | lineas / serie temporal |
| Relacion entre dos variables | dispersion (scatter) |
| Distribucion de una variable | histograma / densidad / boxplot / violin |
| Correlacion entre muchas variables | heatmap de correlacion |
| Proporciones de un total | barras apiladas (evita pie salvo pocas categorias) |

Si la visualizacion es para **publicacion/journal** (tamanos de figura, fuentes, paneles multi-subplot, exportacion vectorial), carga [references/perfiles-journal.md](references/perfiles-journal.md) -- progressive disclosure, solo cuando aplique.

## 3. Modo interactivo (Plotly)

1. Detecta si el proyecto usa el stack Shiny for Python (`webapp-standards`): busca `shiny` en `requirements.txt`/`pyproject.toml`, o un entrypoint tipo `backend/dashboard.py`.
2. Carga [references/interactivo-web.md](references/interactivo-web.md) para los detalles de integracion:
   - **Si hay Shiny:** Plotly nativo via `render_widget`/`output_widget` -- un solo lenguaje (Python) de punta a punta.
   - **Si no hay Shiny:** Plotly.js standalone (HTML/JS embebible) para cualquier frontend (Astro, React, estatico).

## 4. Estandares comunes (ambos modos)

- **Datos reales o nada:** nunca inventes numeros. Si faltan datos, pidelos o marca el placeholder pendiente.
- Titulo claro, ejes etiquetados **con unidades**, leyenda solo si aporta.
- Paleta accesible (colorblind-safe: `seaborn.set_palette("colorblind")` / `scale_*_viridis` en ggplot2 / `plotly.express` con `color_discrete_sequence=px.colors.qualitative.Safe`).
- Codigo en ingles, comentarios/documentacion en espanol. Respeta los estandares del proyecto: si existen las skills `python-standards`, `r-standards` o `webapp-standards`, **cargalas** y aplica su nomenclatura, docstrings/roxygen2 y estructura.

## 5. Verifica sintaxis con context7

Para argumentos finos de seaborn/matplotlib/Plotly poco usados, o capas/escalas de ggplot2, confirma con el MCP **context7** (`/mwaskom/seaborn`, `/matplotlib/matplotlib`, `/plotly/plotly.py`, `/tidyverse/ggplot2`) antes de adivinar. No consultes lo trivial.

## 6. Flujo

1. Identifica el contexto de la peticion y elige modo (§1).
2. Identifica los datos (de donde salen, formato) y el tipo de grafica si es estatico (§2), o el objetivo interactivo si es Plotly (§3).
3. Si aplica un perfil de journal o integracion web, carga el `references/` correspondiente.
4. Escribe el script reproducible que lee los datos y produce la figura/chart, exportandola a archivo (estatico) o al destino correcto (Shiny/HTML standalone).
5. Verifica que corre (Bash) si los datos estan disponibles.
6. Devuelve la ruta del archivo o la referencia de integracion (ej. donde quedo montado el `output_widget` de Shiny).

## Reglas / Salida

- Si la peticion es claramente sobre la **figura final de un documento** (resolver un placeholder `[FIGURA: ...]` en un informe/articulo/analisis de mercado), no uses esta skill: deriva a `research-suite:graficar-datos`.
- Si la peticion es sobre una **figura de proceso/metodologia pulida** (no datos), deriva a `research-suite:generar-figuras` (paperbanana).
- Si la peticion es un **diagrama de flujo/arquitectura/esquema** (no datos), deriva a `generar-diagramas` (Mermaid/Graphviz).
- Salida esperada: el script/codigo reproducible + la figura o integracion resultante, nunca solo una descripcion de como se veria.
