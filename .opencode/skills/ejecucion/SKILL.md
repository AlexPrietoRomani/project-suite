---
name: ejecucion
description: Genera docs/ejecucion.md: guia de arranque, entorno, variables, ejecucion por tipo de proyecto, despliegue y troubleshooting. CARGA cuando el usuario quiera documentar como levantar, correr o desplegar el proyecto.
when_to_use: Al cerrar el setup o antes de entregar/desplegar.
allowed-tools: Read Grep Glob Write Edit
---

# Ejecución — Guía de arranque, ejecución y despliegue

Genera `docs/ejecucion.md`: el documento operativo que dice cómo levantar el entorno, correr el proyecto según su tipo, desplegarlo y salir de los problemas típicos. Es la puerta de entrada de cualquiera que herede el repo.

## Flujo

1. **Detecta el stack y el tipo de proyecto.** Inspecciona el repo antes de escribir: busca señales con Glob/Grep — `app.py` + `shiny run` (Shiny), `app.py` + `streamlit run` (Streamlit), backend (`FastAPI`/`Flask`/`uvicorn`) + carpeta de UI (React/Vue/Astro/SPA), proyecto Node/estático sin backend, notebooks/scripts de análisis sin UI, o scripts secuenciales de ETL/pipeline. También mira el gestor de dependencias real: `pyproject.toml`/`uv.lock` (uv), `environment.yml`/`requirements.txt` (conda/pip), `pnpm-lock.yaml`/`package.json` (pnpm/npm).
2. **Reconfirma el mapeo tipo → secciones.** El template define seis tipos y qué secciones exige cada uno (§1, §2, §3, §4A–§4F, §5). Marca con `[X]` el tipo detectado en la tabla "Identifica tu tipo de proyecto" y ajusta las secciones obligatorias a ese tipo.
3. **Copia la estructura del template** `templates/plantilla_ejecucion.md` y rellena con los datos reales del repo: versiones mínimas de software (§1.1), credenciales/accesos (§1.2), el bloque del gestor de entorno que corresponda (§2A conda / §2B uv, o el equivalente Node), variables `.env` con descripción y dónde obtenerlas (§3).
4. **Escribe la sección de ejecución del tipo detectado** (§4A–§4F) con los comandos, puertos y checklist de verificación reales. Para pipelines/ETL, completa la tabla de dependencias entre pasos (entrada → salida → depende de).
5. **Escribe el despliegue** (§5A ShinyApps.io / §5B Streamlit Cloud / §5C Docker o servidor propio) solo si el proyecto se despliega, con los comandos concretos del target real.
6. **Completa el troubleshooting** (§6) con las causas y soluciones que apliquen al stack; conserva las filas genéricas útiles y añade las específicas del proyecto.
7. **Poda.** Borra los bloques de tipos de proyecto, gestores de entorno y targets de despliegue que NO apliquen — es una regla dura de las plantillas. El documento final no debe contener secciones de tipos ajenos ni placeholders `[...]` sin resolver.
8. **Escribe** el resultado en `docs/ejecucion.md`.

## Reglas / Salida

- **Salida única:** `docs/ejecucion.md`, derivado de `templates/plantilla_ejecucion.md`, con solo las secciones que aplican al tipo de proyecto detectado.
- **Idioma:** genera el documento en el idioma del proyecto (`userConfig.default_doc_language`); mantén en inglés/tal cual los nombres de comandos, rutas, variables y etiquetas.
- **Poda obligatoria:** un solo tipo de proyecto marcado en la tabla selectora; elimina los bloques `§4`/`§5` y el gestor de entorno (`§2A`/`§2B`) que no correspondan. Ninguna sección en blanco, ningún `[placeholder]` sin sustituir.
- **Trampas Windows (solo si el stack es Python):** incluye lo que documenta el template — usa `python -m <paquete>` en vez del binario `<paquete>.exe` para evitar bloqueos de **AppLocker** (aplica a `shiny`, `streamlit`, `uvicorn`, `rsconnect`); en **OneDrive** crea el venv fuera del repo sincronizado (`$env:UV_PROJECT_ENVIRONMENT` antes de `uv venv`) para evitar conflictos de lock; y el patrón `conda run -n <entorno>` para invocar scripts sin activar en automatización/CI. En stacks no-Python omite estas trampas.
- **Fidelidad al repo:** comandos, puertos, nombres de entorno y variables deben reflejar el proyecto real (los que detectaste en el paso 1), no valores de ejemplo del template.
- **Terminal state:** deja `docs/ejecucion.md` escrito y consistente con `docs/architecture/architecture.md` (bundle de despliegue) y `docs/db/diseno_db.md` (dependencias de datos del pipeline) cuando existan. Sugiere `auditar-coherencia` si el setup cambió respecto a lo documentado.
