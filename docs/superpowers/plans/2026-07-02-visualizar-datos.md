# visualizar-datos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `visualizar-datos`, a new skill bundled in the `project-suite` plugin, for on-demand data visualization (static with journal profiles, or interactive via Plotly) during the construction of any project — distinct from `research-suite:graficar-datos`, which targets final document-bound report/article figures.

**Architecture:** A single `SKILL.md` (decision flow: static vs. interactive, per §1-2 of the spec) plus two `references/` files for progressive disclosure (journal profile specifics, web-integration specifics) — mirroring the existing pattern used by `redactar-informe/references/`, `generar-diagramas/references/`, `python-standards/references/` in this same codebase. Plus a one-line addition to the plugin validator's expected-skills set.

**Tech Stack:** Markdown (skill authoring, no executable code in the plugin itself — the skill *generates* Python/R/Plotly code for the target project, but the skill definition itself is prose), Python (`scripts/validate_plugin.py`, stdlib only).

**Spec:** `docs/superpowers/specs/2026-07-02-visualizar-datos-design.md` (this repo).

**Authoring convention** (matches every other skill in this repo — see `skills/graficar-datos/SKILL.md` in the sibling `research-suite` repo for the closest analog): YAML frontmatter with `name` (must equal the directory name), `description` (third person, states the CARGA-trigger), `when_to_use`, `allowed-tools`; body organized as numbered sections ending in a `## Flujo` and a closing rules/output section.

---

## File structure

```
project-suite/
└── skills/visualizar-datos/
    ├── SKILL.md
    └── references/
        ├── perfiles-journal.md
        └── interactivo-web.md
```

---

## Task 1: `skills/visualizar-datos/SKILL.md`

**Files:**
- Create: `skills/visualizar-datos/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
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
| Reporte/documento final, o el contexto no da ninguna senal | **Estatico** |
| Genuinamente ambiguo (ej. "grafica esto" sin mas contexto) | **Pregunta** cual de los dos quiere |

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
   - **Si hay Shiny:** Plotly nativo via `render.plotly`/`output_widget` -- un solo lenguaje (Python) de punta a punta.
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/visualizar-datos/SKILL.md
git commit -m "feat(skill): add visualizar-datos (on-demand data viz, static+interactive)"
```

---

## Task 2: `skills/visualizar-datos/references/perfiles-journal.md`

**Files:**
- Create: `skills/visualizar-datos/references/perfiles-journal.md`

- [ ] **Step 1: Write the file**

```markdown
# Perfiles de journal/publicacion — detalle

> Cargado desde `SKILL.md` §2 solo cuando la visualizacion estatica es para publicacion.

## Tamanos de figura estandar

| Perfil | Ancho | Cuando usarlo |
|---|---|---|
| Columna simple | ~89 mm (3.5 in) | Journals de dos columnas (Nature, Science, IEEE) |
| Columna doble / ancho completo | ~183 mm (7.2 in) | Figuras a todo el ancho de pagina |

## Tamano de fuente

- Etiquetas de ejes y ticks: **8-10 pt** (legible al tamano final de impresion).
- Titulo de la figura (si el journal lo permite dentro de la imagen, muchos lo excluyen y lo ponen en el pie de figura): igual rango, sin exceder 11 pt.

## Paneles multi-subplot con etiquetas A/B/C

**Matplotlib (Python):**

```python
import matplotlib.pyplot as plt
import string

fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))  # ancho completo, ~2 paneles
for ax, label in zip(axes, string.ascii_uppercase):
    ax.text(-0.1, 1.05, label, transform=ax.transAxes,
             fontsize=10, fontweight="bold", va="top", ha="right")
# ... plotear cada ax normalmente ...
fig.savefig("figura.pdf", bbox_inches="tight")   # vectorial, preferido para lineas
fig.savefig("figura.png", dpi=300, bbox_inches="tight")  # raster de respaldo
```

**ggplot2 + patchwork (R):**

```r
library(ggplot2)
library(patchwork)

p1 <- ggplot(datos1, aes(x, y)) + geom_line() + theme_minimal(base_size = 9)
p2 <- ggplot(datos2, aes(x, y)) + geom_point() + theme_minimal(base_size = 9)

figura <- (p1 + p2) + plot_annotation(tag_levels = "A")
ggsave("figura.pdf", figura, width = 183, height = 90, units = "mm")
ggsave("figura.png", figura, width = 183, height = 90, units = "mm", dpi = 300)
```

## Exportacion

- **Preferido:** vectorial (PDF o EPS) para lineas/texto -- evita artefactos de re-rasterizado al tamano final de impresion.
- **Respaldo:** PNG a 300 dpi cuando el journal exige raster o para previsualizacion rapida.
- Mismo estandar de paleta colorblind-safe y datos reales que el resto de la skill (`SKILL.md` §4).
```

- [ ] **Step 2: Commit**

```bash
git add skills/visualizar-datos/references/perfiles-journal.md
git commit -m "docs(skill): add perfiles-journal reference for visualizar-datos"
```

---

## Task 3: `skills/visualizar-datos/references/interactivo-web.md`

**Files:**
- Create: `skills/visualizar-datos/references/interactivo-web.md`

- [ ] **Step 1: Write the file**

```markdown
# Interactivo en apps web — detalle

> Cargado desde `SKILL.md` §3 solo cuando el modo es interactivo (Plotly) y el destino es una app web.

## Deteccion: ¿el proyecto usa Shiny for Python?

Busca cualquiera de estas senales (coherente con `webapp-standards`):
- `shiny` como dependencia en `requirements.txt` o `pyproject.toml`.
- Un entrypoint tipo `backend/dashboard.py` (el patron que `webapp-standards` documenta para la app Shiny).

## Si hay Shiny: Plotly nativo

Shiny for Python renderiza Plotly sin JS adicional via `shinywidgets`:

```python
# backend/dashboard.py (o el modulo de dashboard existente)
from shiny import ui
from shinywidgets import output_widget, render_widget
import plotly.express as px

app_ui = ui.page_fluid(
    output_widget("mi_grafico"),
)

def server(input, output, session):
    @render_widget
    def mi_grafico():
        fig = px.scatter(datos, x="x", y="y", color="categoria",
                          color_discrete_sequence=px.colors.qualitative.Safe)
        return fig
```

Un solo lenguaje (Python) de punta a punta -- ni bundling de JS aparte ni una segunda cadena de build.

## Si NO hay Shiny: Plotly.js standalone

Genera un archivo HTML/JS embebible que corre en cualquier frontend (Astro, React, HTML estatico), sin asumir un backend especifico:

```python
import plotly.express as px

fig = px.line(datos, x="fecha", y="valor", color="serie",
               color_discrete_sequence=px.colors.qualitative.Safe)

# Standalone completo (abre solo, con su propio <html>)
fig.write_html("grafico.html")

# O snippet embebible dentro de una pagina existente (usa el CDN de plotly.js,
# no duplica la libreria si la pagina ya la carga en otro punto)
snippet = fig.to_html(full_html=False, include_plotlyjs="cdn")
```

Para incrustar `snippet` en una pagina Astro: pegarlo dentro de un bloque `<Fragment set:html={snippet} />` o el equivalente segun el framework del proyecto.

## Estandares comunes

Igual que el modo estatico (`SKILL.md` §4): datos reales, paleta colorblind-safe (`px.colors.qualitative.Safe`), respeta `python-standards`/`webapp-standards` si existen en el proyecto.
```

- [ ] **Step 2: Commit**

```bash
git add skills/visualizar-datos/references/interactivo-web.md
git commit -m "docs(skill): add interactivo-web reference for visualizar-datos"
```

---

## Task 4: Register the skill in the validator

**Files:**
- Modify: `scripts/validate_plugin.py`

- [ ] **Step 1: Add `"visualizar-datos"` to `EXPECTED_SKILLS`**

Find:
```python
EXPECTED_SKILLS = {
    "especificar", "planificar", "bitacora", "ejecucion",
    "testear", "verificar-dod", "auditar-coherencia", "construir",
    "rust-standards", "astro-standards", "sql-standards", "ts-standards", "webapp-standards",
    "generar-diagramas", "semantic-commit", "pull-request", "caveman",
    "python-standards", "r-standards"}
```
Replace with:
```python
EXPECTED_SKILLS = {
    "especificar", "planificar", "bitacora", "ejecucion",
    "testear", "verificar-dod", "auditar-coherencia", "construir",
    "rust-standards", "astro-standards", "sql-standards", "ts-standards", "webapp-standards",
    "generar-diagramas", "semantic-commit", "pull-request", "caveman",
    "python-standards", "r-standards", "visualizar-datos"}
```

- [ ] **Step 2: Run the validator**

Run: `python scripts/validate_plugin.py`
Expected: `OK: 20 skills, templates complete, config valid.` (20, not 19 — the new skill is now counted)

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_plugin.py
git commit -m "test: add visualizar-datos to EXPECTED_SKILLS"
```

---

## Task 5: opencode sync + final verification

**Files:**
- None created/modified directly — this task runs the existing sync script and verifies its output.

- [ ] **Step 1: Regenerate the opencode mirror**

Run: `python scripts/sync_opencode.py`
Expected: `opencode sync OK: 20 skills, 3 commands, mcp=['codegraphcontext']`

- [ ] **Step 2: Confirm the new skill mirrored correctly**

Run: `diff -r skills/visualizar-datos .opencode/skills/visualizar-datos`
Expected: no output (byte-identical directory copy)

- [ ] **Step 3: Full validator + hook test suite re-run (regression check)**

Run: `python scripts/validate_plugin.py`
Expected: `OK: 20 skills, templates complete, config valid.`

Run: `npm test`
Expected: `pass 32` (unaffected by this change — no hooks/ files touched)

- [ ] **Step 4: Commit whatever the sync produced**

```bash
git add .opencode/skills/visualizar-datos
git commit -m "chore(opencode): mirror visualizar-datos skill"
```

- [ ] **Step 5: Confirm clean working tree**

Run: `git status --short`
Expected: empty output

---

## Self-review notes

**Spec coverage:**
- §1 scope (in/out) → `SKILL.md`'s "Reglas / Salida" closing section (Task 1) explicitly derives to `graficar-datos`/`generar-figuras`/`generar-diagramas` for out-of-scope asks.
- §2 mode selection → `SKILL.md` §1 decision table (Task 1).
- §3 journal profiles → `references/perfiles-journal.md` (Task 2), exact figures/fonts/panel-label code matching the spec's table verbatim.
- §4 web integration → `references/interactivo-web.md` (Task 3), Shiny-native vs. standalone Plotly.js, matching the spec's decision exactly.
- §5 file structure → matches exactly (Task 1-3 file paths).
- §6 integration (validator, sync, init.md) → Task 4 (validator), Task 5 (sync confirms no `init.md`/`sync_opencode.py` code change needed since the mirror is generic).
- §7 `graficar-datos` reaffirmation → already done as a companion change in the `research-suite` repo (separate commit, not part of this plan's tasks since it's a different repository).
- §8 testing → no automated test applicable (skill = prose); Task 5's validator run is the applicable check.
- §9 non-goals → respected: no new MCP, no `commands/init.md` change, no merge with `graficar-datos`.

**Placeholder scan:** none — every file's full content is given verbatim in each task.

**Type/name consistency check:** skill directory name `visualizar-datos` matches the `name:` frontmatter field (Task 1) and the `EXPECTED_SKILLS` entry (Task 4) exactly. Reference file links in `SKILL.md` (`references/perfiles-journal.md`, `references/interactivo-web.md`) match the exact filenames created in Tasks 2-3.
