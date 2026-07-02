# Reference — Mermaid (catálogo, sintaxis y ejemplo)

Doc oficial vía context7: `libraryId: /mermaid-js/mermaid`. Si una sintaxis no está aquí o es `-beta`, consúltala con `mcp__context7__query-docs` antes de generar.

---

## §A — Catálogo de tipos (esqueletos mínimos)

Cada bloque empieza con su keyword. Para detalle/atributos avanzados → context7.

```mermaid
flowchart LR
  A[Inicio] -->|DataFrame| B{¿Válido?}
  B -->|sí| C[Procesar]
  B -->|no| D[Descartar]
```
```mermaid
sequenceDiagram
  participant U as Usuario
  participant API
  U->>API: POST /login
  API-->>U: 200 + token
```
```mermaid
classDiagram
  class Modelo {
    +DataFrame datos
    +fit() void
  }
  Modelo <|-- ModeloMixto
```
```mermaid
stateDiagram-v2
  [*] --> Pendiente
  Pendiente --> Procesando: start()
  Procesando --> [*]: done
```
```mermaid
erDiagram
  PRODUCTOR ||--o{ LOTE : tiene
  LOTE ||--|{ BAYA : contiene
  BAYA {
    int id_baya PK
    float diametro_px
    string stage
  }
```
```mermaid
journey
  title Flujo del analista
  section Cargar
    Subir datos: 4: Analista
    Validar: 3: Analista
```
```mermaid
gantt
  title Fases
  dateFormat YYYY-MM-DD
  section Datos
  Ingesta :a1, 2026-01-01, 7d
  Limpieza :after a1, 5d
```
```mermaid
pie title Distribución
  "A" : 40
  "B" : 60
```
```mermaid
quadrantChart
  title Priorización
  x-axis Bajo esfuerzo --> Alto esfuerzo
  y-axis Bajo impacto --> Alto impacto
  "Tarea 1": [0.3, 0.7]
```
```mermaid
gitGraph
  commit
  branch feature
  checkout feature
  commit
  checkout main
  merge feature
```
```mermaid
mindmap
  root((Proyecto))
    Datos
      Ingesta
      Limpieza
    Modelos
```
```mermaid
timeline
  title Hitos
  2026-01 : Kickoff
  2026-03 : v1 release
```
```mermaid
C4Context
  title Sistema
  Person(user, "Usuario")
  System(sys, "App")
  Rel(user, sys, "usa")
```

**Beta / verificar con context7 antes de usar:** `sankey-beta`, `xychart-beta`, `block-beta`, `packet-beta`, `architecture-beta`, `radar`, `treemap`, `requirementDiagram`, `kanban`. Su sintaxis cambia entre versiones de Mermaid.

**Cardinalidades erDiagram:** `||` uno-exacto · `o{` cero-o-muchos · `|{` uno-o-muchos · `o|` cero-o-uno. Ej: `A ||--o{ B : etiqueta`.

---

## §B — Estándar visual Mermaid

- En `flowchart`, **nunca dejes flechas vacías**: anota el dato que cruza (`[DataFrame]`, `[p-value]`, `[JSON]`).
- **Colores: usa SIEMPRE la paleta canónica** (`paleta.md`) vía `classDef`/`style`. No inventes tonos por diagrama. Se lee igual en fondo claro y oscuro.
- En `erDiagram`: usa los atributos y tipos reales del esquema y cardinalidades correctas.

> Ejemplo completo de flowchart para README con la paleta canónica → `examples.md` (Ejemplo 3).
