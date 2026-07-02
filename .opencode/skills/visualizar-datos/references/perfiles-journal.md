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
