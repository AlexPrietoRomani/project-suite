---
name: testear
description: Materializa y corre los dos niveles de test obligatorios de una Tarea/Sub fase (unitario + simulacion de usuario) leyendo el plan y los Golden Data. Detecta el runner (pytest/Jest/Vitest/testthat/cargo test) y E2E (Playwright), escribe los tests y reporta pass/fail por AC. CARGA cuando haya que crear o correr los tests de una tarea.
when_to_use: Durante construir, o cuando el usuario pida escribir/correr los tests de una tarea del plan.
allowed-tools: Read Grep Glob Write Edit Bash Skill
---

# Testear — materializar y correr los tests obligatorios de una Tarea

Escribe y ejecuta los **dos niveles de test obligatorios** de una Tarea o Sub fase (Test Unitario + Test de Simulación de Usuario) tal como los declara el Plan Maestro, y reporta el resultado mapeado a cada Criterio de Aceptación (AC). No marca checkboxes ni commitea: solo prueba y reporta.

## Flujo

1. **Identifica el objetivo.** La entrada es un **ID de Tarea/Sub fase** (ej. `T1.1.1`, `SF2.1`) o el contexto de trabajo actual. Si no se te da un ID y el contexto es ambiguo, pídelo antes de continuar.
2. **Lee la especificación de los tests.** Abre `docs/task/tareas.md` y `docs/plan/plan_maestro.md` y localiza, para ese ID, los bloques **"Test Unitario"** y **"Test de Simulación de Usuario"**, junto con el **Objetivo**, el **Entregable** y los **AC** de la Tarea (y sus bloques 🧠 Explicación / 💡 Cómo hacerlo si existen).
3. **Lee los Golden Data.** Consulta la sección **§4 "Datos de Referencia (Fixtures)"** de `docs/plan/plan_maestro.md`: los Inputs Canónicos y las Salidas Esperadas (Golden Data) son la fuente de verdad para los asserts. No inventes valores esperados.
4. **Detecta stack y runner.** Inspecciona el repo (manifiestos y archivos) para elegir el runner correcto:
   - `pyproject.toml`/`.py` → **pytest**
   - `package.json` → **Vitest** o **Jest** (según el que declare el manifiesto)
   - `DESCRIPTION`/`.R`/`.Rmd` → **testthat**
   - `Cargo.toml`/`.rs` → **cargo test** (`#[cfg(test)]` + `tests/`)
   - App web/UI con simulación de usuario → **Playwright** para el nivel E2E.
5. **Escribe los archivos de test** siguiendo la convención de `templates/plantilla_plan.md` §3 (Estructura Objetivo):
   - Test Unitario → `tests/unit/` (aislado del sistema, sin I/O externo).
   - Test de integración → `tests/integration/`.
   - Test de Simulación de Usuario / E2E → `tests/e2e/` (Playwright para web; para no-web, un test de comportamiento que emule el flujo del usuario final).
   Nombra y estructura los archivos según la convención de cada stack; respeta los `*-standards` del lenguaje al escribir el código de test.
6. **Corre los tests** con el comando del runner detectado vía `Bash` (ej. `pytest -q`, `pnpm vitest run`, `npx playwright test`, `Rscript -e 'testthat::test_dir("tests")'`, `cargo test`).
7. **Reporta pass/fail mapeado a cada AC** de la Tarea (ver Salida).

## Reglas / Salida

- **Dos niveles siempre.** Toda Tarea/Sub fase exige Test Unitario **y** Test de Simulación de Usuario (Regla Maestra de Calidad de `plantilla_tareas.md` y Apéndice A de `plantilla_plan.md`). Si el plan declara ambos, materializa ambos.
- **Asserts anclados al Golden Data.** Las salidas esperadas provienen de §4 del plan. **Si falta Golden Data** para un assert verificable, dilo explícitamente en el reporte (marca ese AC como "no verificable: falta Golden Data") en vez de inventar valores esperados o escribir un assert trivial.
- **Mapeo AC → test → resultado.** Devuelve una tabla o lista que, por cada AC de la Tarea, indique el/los test(s) que lo cubren y su estado `PASS`/`FAIL` (con el mensaje de error real si falla). Si un AC no queda cubierto por ningún test, márcalo como **descubierto**.
- **No marca checkboxes.** `testear` nunca cambia `[ ]`→`[X]` en `tareas.md` ni commitea: esa decisión es de `verificar-dod` (gate de DoD) y `construir` (que marca el roll-up); el commit lo hace `semantic-commit`.
- **Cumple los estándares del lenguaje.** Al escribir código de test, aplica el estándar por tipo de archivo (`python-standards`, `r-standards`, `rust-standards`, `astro-standards`, `sql-standards`, `ts-standards`, `webapp-standards`) vía la herramienta `Skill`.
- **Salida final:** los archivos de test escritos en `tests/unit|integration|e2e`, la salida del runner, y el reporte pass/fail por AC. Si todo pasa, sugiere continuar con `verificar-dod`; si algo falla, indica qué test y por qué (y recuerda que un bloqueo recurrente debe consultarse/registrarse con `bitacora`).
