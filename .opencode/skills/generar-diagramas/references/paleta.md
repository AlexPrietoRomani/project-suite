# Reference — Paleta canónica (usar SIEMPRE)

Una sola paleta para todos los diagramas, elegida para que **se lea igual de bien sobre fondo negro y sobre fondo blanco**. Los rellenos son tonos medios saturados (visibles en ambos fondos), el borde es una variante más oscura del mismo color, y el color de texto se fija por relleno para mantener contraste AA.

> Regla: no inventes colores nuevos por diagrama. Usa estos 6 roles. Si un rol no aplica, omítelo, no lo sustituyas por otro tono.

## Roles y hex

| Rol | Relleno (fill) | Borde (stroke) | Texto | Emoji |
|---|---|---|---|---|
| **Datos / Fuente** | `#EAB308` | `#A16207` | `#1F2937` (oscuro) | 🛢️ |
| **Procesamiento / Ingeniería** | `#3B82F6` | `#1D4ED8` | `#FFFFFF` | ⚙️ |
| **Modelado / Análisis** | `#22C55E` | `#15803D` | `#06310F` (oscuro) | 📊 |
| **Artefactos / Outputs** | `#8B5CF6` | `#6D28D9` | `#FFFFFF` | 📦 |
| **Riesgo / Robusto / Alerta** | `#EF4444` | `#B91C1C` | `#FFFFFF` | 🔴 |
| **UI / Entrada-salida** | `#64748B` | `#334155` | `#FFFFFF` | 🖥️ |

Por qué funciona en ambos fondos: ninguno de los rellenos es casi-negro ni casi-blanco, así que el nodo siempre destaca contra negro **y** contra blanco; el borde más oscuro lo separa del fondo blanco, y el texto fijado por relleno mantiene legibilidad.

Las flechas/aristas en tono neutro `#64748B` (borde `#334155`) se ven en ambos fondos; nunca uses gris claro (`#CCC`) ni gris muy oscuro.

---

## §M — Aplicar en Mermaid (`classDef`)

Pega este bloque y asigna clases con `:::rol` o `class A,B rol;`:

```mermaid
flowchart LR
  A[Datos]:::fuente --> B[Procesar]:::proc --> C[Modelo]:::model
  C --> D[(Output)]:::out
  C --> E[Validación]:::riesgo
  D --> F[UI]:::ui

  classDef fuente fill:#EAB308,stroke:#A16207,color:#1F2937;
  classDef proc   fill:#3B82F6,stroke:#1D4ED8,color:#FFFFFF;
  classDef model  fill:#22C55E,stroke:#15803D,color:#06310F;
  classDef out    fill:#8B5CF6,stroke:#6D28D9,color:#FFFFFF;
  classDef riesgo fill:#EF4444,stroke:#B91C1C,color:#FFFFFF;
  classDef ui     fill:#64748B,stroke:#334155,color:#FFFFFF;
```

Para `subgraph`, aplica `style NOMBRE fill:#...,stroke:#...,color:#...` con los mismos hex.

---

## §G — Aplicar en Graphviz

Define defaults y úsalos por nodo. Sirve con `bgcolor` claro u oscuro:

```dot
digraph G {
  graph [bgcolor="transparent"];   // o "#0B131E" en Streamlit; la paleta se ve en ambos
  node  [style="filled,rounded", fontname="Helvetica", penwidth=1.8];
  edge  [color="#334155", fontcolor="#64748B"];

  DATOS [label="archivo.parquet", shape=cylinder, fillcolor="#EAB308", color="#A16207", fontcolor="#1F2937"];
  PROC  [label="funcion()",        shape=box,      fillcolor="#3B82F6", color="#1D4ED8", fontcolor="#FFFFFF"];
  MODEL [label="fit_model()",      shape=box,      fillcolor="#22C55E", color="#15803D", fontcolor="#06310F"];
  OUT   [label="salida.csv",       shape=note,     fillcolor="#8B5CF6", color="#6D28D9", fontcolor="#FFFFFF"];
  RISK  [label="validacion",       shape=box,      fillcolor="#EF4444", color="#B91C1C", fontcolor="#FFFFFF"];
  UI    [label="render()",         shape=ellipse,  fillcolor="#64748B", color="#334155", fontcolor="#FFFFFF"];
}
```

> **Variante Streamlit dark** (solo cuando el fondo es siempre `#0B131E`): existe una paleta dark de alto contraste en `graphviz.md §1`. Úsala únicamente dentro de `st.graphviz_chart`; para todo lo demás (README, docs, exports que pueden verse en claro u oscuro) usa esta paleta canónica.
