# `visualizar-datos` — Design Spec

> Status: **approved for planning** · Date: 2026-07-02 · Author: AlexPrietoRomani

## 0. Purpose

Add a new skill, `visualizar-datos`, bundled in the `project-suite` plugin, for **on-demand data visualization during the process of building any project** — ETL pipelines, data science exploration/debugging, or web apps. This is deliberately distinct from `research-suite:graficar-datos`, which targets **final academic/report figures** (technical reports, scientific articles, market analyses) destined for `.md`/`.tex` documents, alongside `generar-figuras` (paperbanana) for process/methodology illustrations.

**Why two skills, not one:** the two live in different plugins with different lifecycles. `research-suite:graficar-datos` is invoked during document authoring (`redactar-informe`'s flow), producing a figure that becomes part of a finished document. `project-suite:visualizar-datos` is invoked during construction/debugging of a project scaffolded by `project-suite` (`construir`, `testear`, ad-hoc requests), producing a chart that helps understand data *right now* — often throwaway, often interactive, not necessarily destined for any document at all.

## 1. Scope

**In scope:**
- Static charts (matplotlib/seaborn Python, ggplot2 R) with **publication/journal profiles**: standard figure widths, font sizing, multi-panel layouts with A/B/C labels, vector export.
- Interactive charts (Plotly), with project-aware output target: native Plotly rendering inside a Shiny for Python app (if the project uses the `webapp-standards` stack) or a standalone embeddable Plotly.js HTML/JS snippet otherwise.
- Mode selection (static vs. interactive) inferred from the request's context, asking only when genuinely ambiguous.
- Reuse of `graficar-datos`'s already-validated doctrine: real data only, colorblind-safe palettes, reproducible code, respects `python-standards`/`r-standards`, context7 for fine-grained API verification.

**Out of scope:**
- Anything covered by `generar-figuras` (paperbanana) — polished process/methodology illustrations for publication. This skill never generates images via AI.
- Document-authoring flow integration (`[FIGURA: ...]` placeholders, `redactar-informe`) — that's `research-suite:graficar-datos`'s territory.
- Diagrams of flow/process/architecture — that's `generar-diagramas` (Mermaid/Graphviz), already bundled in project-suite.

## 2. Mode selection: static vs. interactive

Inferred from the request's context, not asked by default:
- **Interactive (Plotly)** when the ask is about exploring, debugging, or monitoring data during development (an ETL step's output, a notebook cell, a data science exploratory question, "muéstrame cómo se ve esto").
- **Static** when the ask is about a final report/document, or the context gives no clear signal either way.
- **Ask explicitly** only when the request is genuinely ambiguous between the two (e.g., "grafica esto" with no other context at all).

## 3. Static mode — journal/publication profiles

New capability beyond what `graficar-datos` already has. Concrete parameters:

| Profile | Width | Notes |
|---|---|---|
| Single column | ~89 mm (3.5 in) | Common for two-column journals (Nature, Science, IEEE) |
| Double column / full width | ~183 mm (7.2 in) | Full-width figures |
| Font size (axis/tick labels) | 8–10 pt | Print-legible at final size |
| Multi-panel | Subplot grid, bold A/B/C/D labels top-left of each panel | Matplotlib `fig.text`/`ax.text` or `patchwork`/`cowplot` in R |
| Export formats | PDF/EPS (vector, preferred for line art) + PNG @ 300 dpi (raster fallback) | Vector avoids re-rasterization artifacts at print size |

Same colorblind-safe-palette and real-data-only rules as `graficar-datos` apply here.

## 4. Interactive mode — web integration

- **Detect** whether the current project uses the Shiny for Python stack (per `webapp-standards`, already in project-suite — look for `shiny` in dependencies / `backend/dashboard.py`-style entrypoint).
  - **If Shiny is present:** generate Plotly figures rendered natively through Shiny's `render.plotly`/`output_widget` — no separate JS bundling, one language (Python) end to end.
  - **If Shiny is absent:** generate a standalone Plotly.js HTML/JS snippet (`fig.write_html(...)` or the Plotly.js equivalent) that can be embedded in any frontend (Astro, React, static HTML) without assuming a specific backend.
- Both paths produce genuinely interactive output (zoom, hover, filter) — this is the capability `graficar-datos` explicitly lacks today.

## 5. File structure

```
project-suite/skills/visualizar-datos/
├── SKILL.md                       # main flow: mode-selection decision table, static/interactive steps
└── references/
    ├── perfiles-journal.md        # §3 detail: exact figure-size/font/panel-label specifics per profile
    └── interactivo-web.md         # §4 detail: Shiny-native vs. Plotly.js decision + code snippets
```

Progressive disclosure matches the existing pattern in this codebase (`redactar-informe/references/`, `generar-diagramas/references/`, `python-standards/references/`) — `SKILL.md` stays a decision-and-flow document; the reference files hold the copy-pasteable specifics loaded only when that branch is taken.

## 6. Integration with the rest of project-suite

- Bundled alongside `python-standards`, `r-standards`, `webapp-standards` — same tier as those, not a "core doc" skill (`especificar`/`planificar`/etc.) or a "loop-closer" (`testear`/`verificar-dod`/`auditar-coherencia`).
- `scripts/validate_plugin.py`: add `"visualizar-datos"` to `EXPECTED_SKILLS`.
- `scripts/sync_opencode.py`: no change needed — it mirrors `skills/*/SKILL.md` generically with no hardcoded skill list, so the new skill is picked up automatically on the next `sync_opencode.py` run.
- `commands/init.md`/`CLAUDE.md` rules body: no change required — the per-file-type standards list (`.py`→python-standards, etc.) doesn't need a `visualizar-datos` entry since it's invoked by request/context, not by file extension, same as `generar-diagramas`.

## 7. Reaffirming `research-suite:graficar-datos`'s scope (companion change, different repo)

To avoid confusion between the two skills, `research-suite/skills/graficar-datos/SKILL.md` gets a scope-clarification edit (not a redesign): an explicit note that it is for **document-bound, final report/article figures** (feeding `redactar-informe`'s `[FIGURA: ...]` placeholders), and a pointer to `project-suite:visualizar-datos` for on-demand/interactive/process-time visualization needs. No functional change to `graficar-datos` itself — this is a documentation clarification, tracked and committed separately in the `research-suite` repo.

## 8. Testing

This is a skill (markdown instructions to an agent), not executable code — no automated test suite applies, consistent with how `graficar-datos`, `generar-diagramas`, and the other instruction-only skills in this codebase are (correctly) untested by `node --test`/`pytest`. Verification is: `scripts/validate_plugin.py` confirms the skill exists with correct frontmatter (`name` matches directory, `description` present), and a manual smoke invocation (ask for one static chart and one interactive chart against sample data) during/after implementation.

## 9. Non-goals

- No AI-generated images for data (same hard rule as `graficar-datos` — data visualization is always code-generated from real data).
- No new MCP servers.
- No changes to `commands/init.md`'s per-file-type standards table.
- No attempt to unify or deduplicate with `graficar-datos` into one cross-plugin skill — they serve different lifecycles and live in different plugins by design (§0).

## 10. Open questions

None blocking.
