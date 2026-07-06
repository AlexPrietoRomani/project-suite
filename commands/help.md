---
description: "Muestra ayuda rapida de todos los comandos y skills de project-suite."
argument-hint: ""
allowed-tools: Read
---

# /help — Referencia rapida de project-suite

Muestra la lista de comandos y skills disponibles, con una linea de que hace cada uno.

## Comandos

| Comando | Que hace |
|---|---|
| `/init [idea]` | Arranca un proyecto: entrevista de diseno, genera docs/, escribe CLAUDE.md/AGENTS.md, arma .gitignore. |
| `/nueva-fase [cambio]` | Gate spec-driven: evalua si un cambio amerita una nueva Fase y la redacta ANTES de codear. |
| `/modo [estricto/relajado/off]` | Cambia o consulta la intensidad del recordatorio ambiental. |
| `/review [commit]` | Revisa el diff actual contra el plan: detecta codigo sin planificar o que contradice la spec. |
| `/audit` | Audita TODO el repo contra architecture.md y diseno_db.md: detecta drift global. |
| `/help` | Esta ayuda. |

## Skills (por dominio)

**Documentacion:** `especificar`, `planificar`, `ejecucion`, `bitacora`

**Loop de calidad:** `construir`, `testear`, `verificar-dod`, `auditar-coherencia`

**Estándares:** `python-standards`, `ts-standards`, `rust-standards`, `astro-standards`, `sql-standards`, `r-standards`, `webapp-standards`

**Empaquetadas:** `generar-diagramas`, `semantic-commit`, `pull-request`, `caveman`, `visualizar-datos`

## Flujo tipico

```
/init [idea]  →  /nueva-fase [cambio]  →  construir  →  /review  →  semantic-commit  →  pull-request
```

## Modos

- **estricto** (default): antes de codear cualquier cambio, corre `/nueva-fase`. Sin verde en `verificar-dod`, no hay `[X]`.
- **relajado**: para cambios grandes considera `/nueva-fase`. `verificar-dod` es opcional pero recomendado.
- **off**: sin recordatorios. Los comandos siguen disponibles.

Cambia con `/modo [nivel]`.
