# Reference — Graphviz Dark Pipeline (templates, paleta, ejemplos, Streamlit)

Doc oficial de atributos: https://graphviz.org/doc/info/attrs.html
Doc oficial de shapes: https://graphviz.org/docs/attrs/shape
Shapes disponibles: `box`, `ellipse`, `cylinder`, `note`, `diamond`, `parallelogram`, `record`
Styles de cluster: `filled`, `dashed`, `dotted`, `solid`, `rounded`, `bold`

> Usa Graphviz solo cuando el usuario lo pide o el diagrama va a embeberse en Streamlit (`st.graphviz_chart`). Para todo lo demás, Mermaid (`references/mermaid.md`).

---

## §1 — Paleta semántica dark (variante SOLO Streamlit)

> La paleta por defecto es la **canónica** de `paleta.md` (legible en claro y oscuro). Esta paleta dark de abajo es una **variante de alto contraste solo para Streamlit**, donde el fondo es siempre `#0B131E`. No la uses en README/docs/exports que puedan verse sobre blanco.

Fondo del grafo: `bgcolor="#0B131E"`.

| Rol | Borde cluster | Fill cluster | Nodos internos |
|---|---|---|---|
| **1. Datos Fuente** | `#999999` dashed | *(sin fill)* | cilindro `#2a2500` / `#f5c842` |
| **2. Procesamiento** | `#4dabf7` solid | `#091827` | `#1a3a5c` / `#4dabf7` |
| **3. Modelado Estadístico** | `#69db7c` solid | `#081a08` | `#0d2a10` / `#69db7c` |
| **4. Artefactos / Outputs** | `#da77f2` solid | `#140a22` | `#2a0d35` / `#da77f2` |
| **UI / render()** | `white` | `#1a1a3a` | ellipse único |

Variante rama de riesgo/robusto: borde `#ff6b6b`, fill cluster `#1a0808`, nodos `#3a1010`.

---

## §2 — Atributos globales

```dot
digraph Pipeline_Name {
    graph [rankdir=LR, bgcolor="#0B131E", fontname="Helvetica",
           pad=0.6, splines=curved, nodesep=0.5, ranksep=1.1];
    node [fontname="Helvetica", fontcolor="white", fontsize=8,
          style="filled,rounded", margin=0.18, penwidth=1.8];
    edge [fontcolor="#8aabcf", fontsize=7, color="#3a5a80", penwidth=1.3];
}
```

Añadir `compound=true` en `graph [...]` cuando existan ramas paralelas o edges que cruzan clusters.

---

## §3 — Tipos de aristas

```dot
// 1. Flujo principal de datos (sólida)
A -> B [label="datos transferidos", color="#3a5a80", fontcolor="#8aabcf", penwidth=1.3];

// 2. Generación de artefactos (dashed morado)
FN -> OUT [style=dashed, color="#9a47b2"];

// 3. Consumo en UI (dashed azul oscuro + etiqueta)
OUT -> UI [style=dashed, color="#5555aa", label="descripcion\nen UI"];

// 4. Metadatos / anotaciones opcionales (dotted gris, sin punta)
META -> NODE [style=dotted, arrowhead=none, color="#666666"];
```

---

## §4 — Templates de clusters (4 fases estándar)

```dot
// ── CLUSTER 1: Datos Fuente ──────────────────────────────
subgraph cluster_sources {
    label="1. DATOS FUENTE";
    style=dashed; color="#999999"; fontcolor="#CCCCCC"; fontsize=10;
    RAW [label="archivo.parquet\\ncol1 | col2 | col3\\ncol4 | col5",
         shape=cylinder, fillcolor="#2a2500", color="#f5c842"];
}

// ── CLUSTER 2: Procesamiento / Ingeniería de Variables ───
subgraph cluster_processing {
    label="2. NOMBRE DEL PROCESO\\nnombre_script.py";
    style=filled; fillcolor="#091827"; color="#4dabf7";
    fontcolor="#74c0fc"; fontsize=10;
    FN_A [label="nombre_funcion()\\nDetalle proceso o formula\\nParametros: clave=valor",
          shape=box, fillcolor="#1a3a5c", color="#4dabf7"];
    ARTIFACT [label="output_intermedio.parquet\\nDescripcion breve",
              shape=note, fillcolor="#050e1a", color="#74c0fc"];
    FN_A -> ARTIFACT;
}

// ── CLUSTER 3: Modelado Estadístico ─────────────────────
subgraph cluster_modeling {
    label="3. MODELADO ESTADISTICO\\nnombre_script.py";
    style=filled; fillcolor="#081a08"; color="#69db7c";
    fontcolor="#a9e34b"; fontsize=10;
    FN_B [label="fit_model()\\nY_ij = mu + beta*X_i + u_j + e_ij\\nUmbrales: param > valor",
          shape=box, fillcolor="#0d2a10", color="#69db7c"];
    FN_C [label="compute_metric()\\nMetrica = formula\\n<0.10 irrelevante | >0.50 dominante",
          shape=box, fillcolor="#0d2a10", color="#69db7c"];
    FN_B -> FN_C;
}

// ── CLUSTER 4: Artefactos de Salida ─────────────────────
subgraph cluster_outputs {
    label="4. ARTEFACTOS DE SALIDA";
    style=filled; fillcolor="#140a22"; color="#da77f2";
    fontcolor="#cc5de8"; fontsize=10;
    OUT_A [label="output_a.csv\\ncol1 | col2 | col3",
           shape=note, fillcolor="#2a0d35", color="#da77f2"];
    OUT_B [label="output_b.png\\nDescripcion del grafico",
           shape=note, fillcolor="#2a0d35", color="#da77f2"];
}

// ── Nodo UI (fuera de clusters) ──────────────────────────
UI [label="render()\\nnombre_subtab.py",
    shape=ellipse, fillcolor="#1a1a3a", color="white", penwidth=2.5];
```

Variante rama de riesgo/robusto (LMM Robusto, outliers, validación alternativa):
```dot
subgraph cluster_robust {
    label="3. LMM ROBUSTO — script.R";
    style=filled; fillcolor="#1a0808"; color="#ff6b6b";
    fontcolor="#ff9999"; fontsize=10;
    FN_ROB [label="funcion()\\nDetalle\\nUmbral de decision",
            shape=box, fillcolor="#3a1010", color="#ff6b6b"];
}
```

---

## §5 — Patrones de arquitectura

| Patrón | Estructura | Cuándo usarlo |
|---|---|---|
| **A. Lineal** | FUENTE → PROC → MODEL → OUT → UI | Un script, un flujo |
| **B. Ramas Paralelas** | FUENTE → {RAMA_1, RAMA_2} → OUT | Comparación de modelos (estándar vs robusto) |
| **C. Fan-out Estadístico** | FUENTE → MODELO → {MÉTRICA_1, MÉTRICA_2, ...} | Un modelo genera N métricas (ICC, Wald, CLD) |
| **D. Modelos Anidados** | FUENTE → {MOD_A, MOD_B} → TEST → FDR → OUT | LRT, comparación AIC |

Usa `compound=true` cuando hay ramas paralelas (Patrones B y D).

Label de cada nodo estadístico, en este orden:
```
"nombre_funcion() — Titulo\nFormula: expresion\nParametro clave\nInterpretacion o umbral"
```
Artefactos (`shape=note`):
```
"nombre_archivo.csv\ncol1 | col2 | col3"
"nombre_plot.png\nDescripcion de lo que muestra"
```

---

## §6 — Notas de compatibilidad
- `splines=curved` requiere graphviz >= 2.30
- `style="filled,rounded"` combina relleno y esquinas redondeadas en nodos
- En Python triple-quoted strings: usar `\\n` (doble backslash) para newlines en labels DOT
- `compound=true` es necesario para edges que cruzan clusters (Patrones B y D)
- Shapes validados en `st.graphviz_chart`: `box`, `ellipse`, `cylinder`, `note`, `diamond`

---

## §7 — Integración Streamlit

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

---
## §8 — Ejemplos reales completos

Los ejemplos extensos extraídos del proyecto (fan-out estadístico en Streamlit, orquestador multi-fuente) viven en `examples.md` para no inflar esta referencia:
- **Ejemplo 1** — Fan-out estadístico (Patrón C) en `st.graphviz_chart`.
- **Ejemplo 2** — Orquestador (múltiples fuentes → múltiples sub-análisis).

Patrón B (ramas paralelas) → `subtab_g6_0_outliers_q2.py`; Patrón D (LRT anidado) → `subtab_g6_0_interacciones_q4.py`.
