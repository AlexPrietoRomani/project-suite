---
name: generar-diagramas
description: Genera diagramas técnicamente precisos en Mermaid (por defecto) o Graphviz a partir del código real o de una especificación. Cubre todos los tipos — flowchart, sequence, class, state, erDiagram, gantt, pie, journey, quadrant, requirement, gitGraph, C4, mindmap, timeline, sankey, xychart, block, packet, kanban, architecture, radar, treemap. Úsalo cuando el usuario pida "haz un diagrama", "diagrama de la arquitectura", "diagrama ER de la base de datos", "diagrama de secuencia", "diagrama de estados", "flowchart", "mapa mental", "gantt", o quiera visualizar un pipeline/flujo/esquema. Por defecto usa Mermaid; usa Graphviz solo si el usuario lo pide o para embeber en Streamlit (st.graphviz_chart).
allowed-tools: Read Grep Bash(ls *) mcp__context7__resolve-library-id mcp__context7__query-docs WebSearch WebFetch
---

# Rol y Objetivo
Generas diagramas claros y **técnicamente precisos** a partir del código real del repo o de la especificación que da el usuario. Por defecto en **Mermaid**; en Graphviz solo cuando se pide o se va a embeber en Streamlit.

**REGLA DE ORO (As-Is):** cuando diagramas código existente, NO inventes ni supongas. Refleja la realidad: sin conexión en el código → sin flecha en el diagrama. Si el diagrama es conceptual (el usuario describe algo que aún no existe), eso es válido — solo no mezcles suposiciones con código real sin avisarlo.

Contexto / petición del usuario: `$ARGUMENTS`

> **Archivos de apoyo (carpeta `references/`, léelos solo si la tarea lo requiere):**
> - **Paleta canónica de colores (úsala SIEMPRE, legible en fondo claro y oscuro)** → `references/paleta.md`
> - Catálogo de tipos Mermaid y sintaxis → `references/mermaid.md`
> - Templates DOT, patrones y Streamlit (variante dark) → `references/graphviz.md`
> - Ejemplos reales completos del proyecto → `references/examples.md`

---

# 1. Elegir herramienta (Mermaid por defecto)

| Caso | Herramienta |
|---|---|
| **Cualquier diagrama, por defecto** | **Mermaid** |
| El usuario pide Graphviz / DOT explícitamente | **Graphviz** |
| Se va a embeber en **Streamlit** (`st.graphviz_chart`) | **Graphviz** (dark theme, ver §4) |
| Pipeline técnico DS con paleta semántica dark ya establecida en el proyecto | **Graphviz** (ver `references/graphviz.md` y `references/examples.md`) |

Si dudas, pregunta una sola cosa: "¿lo quieres en Mermaid (por defecto) o Graphviz?" — pero no bloquees: ante silencio, **Mermaid**.

---

# 2. Elegir el tipo de diagrama

Elige el tipo según lo que se quiere comunicar. Todos son Mermaid salvo que se indique Graphviz.

| Tipo (keyword Mermaid) | Para qué |
|---|---|
| **flowchart** / `graph` | Flujos, procesos, decisiones, pipelines ETL (el "normal", el más común) |
| **sequenceDiagram** | Interacciones temporales entre actores/servicios (APIs, auth, mensajes) |
| **classDiagram** | OOP: clases, atributos, métodos, herencia/composición |
| **stateDiagram-v2** | Máquinas de estado, ciclos de vida, transiciones |
| **erDiagram** | Esquema relacional de base de datos (entidad-relación, cardinalidades) |
| **journey** | User journey: pasos del usuario con puntuación de satisfacción |
| **gantt** | Cronogramas de proyecto, fases con fechas y dependencias |
| **pie** | Proporciones de un total |
| **quadrantChart** | Matriz 2×2 (priorización esfuerzo/impacto, etc.) |
| **requirementDiagram** | Requisitos y su trazabilidad / verificación |
| **gitGraph** | Ramas, commits, merges de git |
| **C4Context / C4Container / C4Component** | Arquitectura de software por niveles (modelo C4) |
| **mindmap** | Mapas mentales, lluvia de ideas jerárquica |
| **timeline** | Línea de tiempo cronológica de eventos |
| **sankey-beta** | Flujos con magnitud (energía, presupuesto, conversión) |
| **xychart-beta** | Gráfico x/y (barras y líneas) |
| **block-beta** | Diagramas de bloques con posicionamiento explícito |
| **packet-beta** | Estructura de paquetes de bytes/protocolos |
| **kanban** | Tableros kanban (columnas de tareas) |
| **architecture-beta** | Arquitectura de servicios/cloud con grupos e iconos |
| **radar** | Gráfico radar (comparar varias dimensiones) |
| **treemap** | Jerarquías representadas por área |

> Sintaxis mínima (esqueleto) de cada tipo → `references/mermaid.md §A`. Los `-beta` pueden cambiar entre versiones: si vas a usar uno, **verifica su sintaxis con context7** (§3).

---

# 3. Verificar sintaxis con context7 (antes de adivinar)

No memorices ni inventes sintaxis dudosa. Cuando no estés seguro de la sintaxis de un tipo (sobre todo los `-beta`, `architecture`, `sankey`, `xychart`, `packet`, `radar`, `treemap`, o atributos de Graphviz), **consulta primero context7**; recurre a búsqueda web solo si context7 no lo cubre.

- **Mermaid** → `mcp__context7__query-docs` con `libraryId: /mermaid-js/mermaid` y una query específica (ej. "erDiagram relationship cardinality syntax", "architecture-beta groups and icons syntax").
- **Graphviz** → resuelve con `mcp__context7__resolve-library-id` (librería "Graphviz") o usa la doc oficial en `references/graphviz.md` (`graphviz.org/doc/info/attrs.html`).
- **Web** (`WebSearch`/`WebFetch`) → solo si context7 no devuelve lo necesario.

No consultes para lo trivial (un `flowchart` o `sequenceDiagram` básico que ya dominas). Consulta cuando una sintaxis poco común podría salir mal.

---

# 4. Estándar visual

**Colores: usa SIEMPRE la paleta canónica de `references/paleta.md`** (6 roles, legible en fondo negro y blanco). No inventes tonos por diagrama. Las flechas en neutro `#64748B`; nunca las dejes vacías: anota el dato que cruza (`[DataFrame]`, `[p-value]`, `[JSON]`).

- **Mermaid:** aplica la paleta con `classDef`/`style` (ver `paleta.md §M`). Para `erDiagram`, atributos/tipos reales y cardinalidades correctas (`||--o{`, etc.) — sintaxis en `references/mermaid.md §A`.
- **Graphviz:** aplica la paleta con `paleta.md §G`. **Excepción Streamlit** (`st.graphviz_chart`, fondo fijo `#0B131E`): puedes usar la variante dark de alto contraste de `references/graphviz.md §1`.

---

# 5. Integración Streamlit (modo Graphviz)

```python
with st.expander("📊 ¿Cómo se calculó esto? — Pipeline de datos", expanded=False):
    st.graphviz_chart("""
    digraph Pipeline {
        graph [rankdir=LR, bgcolor="#0B131E", ...];
        // ...
    }
    """, use_container_width=True)
    st.caption("Ejecutar: `python script.py --flags`")
```
**Strings Python:** usa `\\n` (doble backslash) en triple-quoted strings para newlines en labels DOT. Shapes validados en `st.graphviz_chart`: `box`, `ellipse`, `cylinder`, `note`, `diamond`.

---

# 6. Flujo de Trabajo
1. **Entender la fuente** → si es código real, léelo (funciones, archivos, flags, fórmulas, esquema de BD) y aplica la regla As-Is. Si es conceptual, parte de la descripción del usuario.
2. **Elegir herramienta** → Mermaid por defecto; Graphviz si se pide o es para Streamlit.
3. **Elegir tipo** → según qué se comunica (§2).
4. **Verificar sintaxis** → context7 si el tipo o atributo es dudoso (§3).
5. **Generar** → diagrama preciso, flechas anotadas, colores por rol si aporta. Para Mermaid usa `references/mermaid.md`; para pipelines DS dark / Streamlit usa `references/graphviz.md`.
6. **Reportar** → herramienta + tipo elegidos y, si auditaste código, los hallazgos clave que sustentan el diagrama. Para artefactos regenerables, incluye el comando CLI exacto.
