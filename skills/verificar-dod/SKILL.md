---
name: verificar-dod
description: Gate de Definition-of-Done por Tarea: corre los tests declarados (con cobertura vs umbral), lint/format sin warnings, y confirma que cambios de DB/env quedaron documentados (diseno_db.md/.env.example/architecture.md). Reporta pass/fail por item de DoD antes de marcar [X] o commitear. CARGA al cerrar una tarea.
when_to_use: Antes de marcar una Tarea como [X] o de commitear su trabajo.
allowed-tools: Read Grep Glob Bash Skill
---

# verificar-dod — Gate de Definition of Done por Tarea

Ejecuta el Definition of Done (DoD) de una Tarea del Plan Maestro y reporta pass/fail por cada item. Es el guardián que habilita (o bloquea) el `[X]` de la Tarea y el commit posterior. No commitea ni marca checkboxes por su cuenta: verifica y decide.

## Flujo

1. **Entrada.** Recibe un ID de Tarea (ej. `T1.1.1`) o toma la Tarea del contexto actual. Localiza su definición en `docs/task/tareas.md` y en `docs/plan/plan_maestro.md` (macro-objetivo, Entregable, Criterios de Aceptación, y sus bloques `Test Unitario` + `Test de Simulación de Usuario`). Lee el **Apéndice A — Definition of Done (DoD) Global** del `plan_maestro.md` (derivado de `templates/plantilla_plan.md`), que fija los 5 requerimientos innegociables.

2. **Item 1 — Tests unitarios + simulación de usuario en verde.** Delega en la skill `testear` (Skill tool) para materializar/correr los dos niveles obligatorios de la Tarea. Confirma que **todos** los tests declarados en los bloques `Test Unitario` y `Test de Simulación de Usuario` corren y pasan, y que cubren casos óptimos y de error.

3. **Item 2 — Cobertura ≥ umbral de referencia.** Ejecuta el runner con reporte de cobertura del stack detectado (ej. `pytest --cov`, `vitest --coverage`, `jest --coverage`, `covr` en R, `cargo tarpaulin`/`cargo llvm-cov` en Rust). Compara el porcentaje contra el umbral de referencia declarado en las Convenciones/Estrategia de Pruebas del `plan_maestro.md`. Si el plan no fija un umbral explícito, lo señala como faltante en vez de asumir uno.

4. **Item 3 — Tests limpios en local (y CI si existe).** Verifica que la suite corre limpia en local (sin tests saltados o marcados como esperados-fallando sin justificación). Si el repo tiene configuración de CI (`.github/workflows/`, `.gitlab-ci.yml`, etc.), confirma que el pipeline de tests está definido y no está silenciado; si no hay CI, lo indica como "no aplica / no configurado" sin marcarlo como fallo.

5. **Item 4 — Lint/format con 0 warnings.** Corre los linters y formateadores del stack (ej. `ruff`/`black` en Python, `eslint`/`prettier` en TS/JS, `lintr`/`styler` en R, `clippy`/`rustfmt` en Rust, según los `*-standards` aplicables). Exige **0 warnings** y ninguna exclusión artificial (`# noqa`, `eslint-disable`, `#[allow(...)]`) sin justificación registrada.

6. **Item 5 — Cambios de DB/env documentados.** Si la Tarea tocó esquema de datos o variables de entorno, verifica que quedaron reflejados: nuevas tablas/columnas/índices/migraciones en `docs/db/diseno_db.md` (diccionario de tablas, ER, matriz de accesos), nuevas variables en `.env.example`, y flujos/scripts/ADRs afectados en `docs/architecture/architecture.md`. Detecta drift comparando lo declarado en los docs contra los archivos reales de migración/DDL/config; ante divergencias sugiere invocar `auditar-coherencia` para el análisis profundo.

7. **Veredicto.** Consolida el resultado por item y decide si la Tarea puede cerrarse.

## Reglas / Salida

- **Reporta pass/fail por cada uno de los 5 items del DoD** (Apéndice A del plan), con evidencia concreta: comando ejecutado, salida relevante, porcentaje de cobertura vs umbral, y ruta del doc actualizado. Nada de "todo OK" genérico.
- **Si cualquier item falla, NO habilita el `[X]`** de la Tarea y enumera exactamente qué falta para pasar el gate (ej. "cobertura 71% < umbral 80%", "3 warnings de ruff en `src/logic/pricing.py`", "columna `orders.discount_pct` no está en `diseno_db.md`").
- **No commitea.** El commit es responsabilidad de la skill `semantic-commit`; `verificar-dod` es el gate previo. Tampoco marca checkboxes: el `[X]` lo aplica `construir` (o el usuario) **solo** tras un veredicto verde.
- **No inventa criterios.** Se ciñe al DoD del `plan_maestro.md`; si un item no es determinable (ej. no hay umbral de cobertura definido, o no hay CI), lo declara como faltante/no-aplica en lugar de aprobarlo o inventarlo.
- **Terminal state:** entrega el reporte pass/fail. En verde, sugiere marcar la Tarea `[X]` (vía `construir`) y continuar con `semantic-commit`. En rojo, entrega la lista accionable de bloqueos y, si hay drift docs↔código, deriva a `auditar-coherencia`; ante un bloqueo recurrente, sugiere registrar el incidente con `bitacora`.
