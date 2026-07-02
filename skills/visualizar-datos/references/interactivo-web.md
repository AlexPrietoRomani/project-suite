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
