---
name: webapp-standards
description: Reglas exhaustivas de arquitectura para apps web híbridas Astro + Starlette (gateway) + Shiny for Python desplegables en ShinyApps.io/Posit sin romper el enrutamiento. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar la arquitectura de una app web (frontend estático + API + dashboard embebido), su gateway o su pipeline de build/deploy.
when_to_use: Al diseñar o revisar la arquitectura de una app web híbrida (SPA + API + dashboard), montar el gateway Starlette, definir el pipeline de compilación/despliegue a ShinyApps.io/Posit, o auditar rutas relativas y bundle de deploy.
allowed-tools: Read Grep Glob
---

# Estándares de Arquitectura Web (Astro + Starlette + Shiny)

Como agente de IA, DEBES cumplir estrictamente estas normativas al diseñar, implementar o revisar una app web híbrida del tipo "Agro-Stack": **Astro** (frontend estático), **Starlette** (backend/API gateway) y **Shiny for Python** (interactividad analítica embebida). Estas reglas destilan lecciones de despliegues reales en **ShinyApps.io/Posit Connect** y evitan los fallos de enrutamiento y de bundle que ese hosting provoca.

## Flujo

1. **Identifica el patrón.** Confirma que la app encaja en el patrón híbrido: frontend estático servido en `/`, API rápida en `/api`, dashboard interactivo montado en `/shiny`, todo detrás de un único entrypoint ASGI (`app.py`). Si el destino es ShinyApps.io/Posit, todas las reglas de este documento son obligatorias.
2. **Revisa/define la estructura de carpetas** (§2) y qué se commitea vs. qué es generado (`.gitignore` + `.rscignore`).
3. **Aplica la Regla de Oro del enrutamiento** (§3): SPA de una sola página, hash/client routing, rutas de recursos y `fetch` estrictamente relativas.
4. **Configura Astro** (§4) forzando `output: 'static'` y `inlineStylesheets: 'always'`; usa `pnpm`.
5. **Monta el gateway Starlette** (§5) respetando el orden de montaje (API → Shiny → Astro al final).
6. **Aplica las optimizaciones** (§6): API consolidada, pandas vectorizado, filtros bidireccionales.
7. **Prepara el bundle de deploy** (§7): `.rscignore` mínimo, build + inline JS + copia de estáticos + `rsconnect` vía `uv run`.
8. Ante cualquier duda de dependencias/versionado usa `uv` (Python) y `pnpm` (Node) según §8. Para el runbook de despliegue detallado, delega en la skill `shinyapps-deploy` cuando exista en el proyecto.

## 1. Reglas Generales e Idioma Mixto

- **Código en Inglés:** identificadores (variables, funciones, endpoints, componentes) DEBEN estar en inglés. Nada de abreviaturas crípticas (usa `dashboard_data`, NO `dd`).
- **Documentación en Español:** comentarios (`#`, `//`, `<!-- -->`) y docstrings/JSDoc DEBEN redactarse en español, en **presente activo** ("Este endpoint consolida...", NO "Se consolidó...").
- **Stack fijo:** **Starlette puro**, no FastAPI, como entrypoint de producción — ShinyApps.io/Posit tiene compatibilidad ASGI más estable con Starlette. FastAPI puede usarse solo como servidor de desarrollo local (`backend/main.py`), nunca como el `app.py` desplegado.

## 2. Estructura de Carpetas y Frontera Commit/Generado

Mantén esta estructura de referencia. Marca con `*` lo generado automáticamente, que **NO se commitea** (debe estar en `.gitignore` **y** en `.rscignore`):

```
proyecto/
├── app.py                  # Entrypoint ASGI de producción (Starlette)
├── requirements.txt        # Dependencias Python de producción
├── .env                    # Secretos locales (NO commitear) *
├── .env.example            # Plantilla de variables (SÍ commitear)
├── .gitignore
├── .rscignore              # Exclusiones para ShinyApps.io/Posit (crítico)
├── backend/
│   ├── main.py             # Servidor de desarrollo local (FastAPI/uvicorn)
│   ├── engine.py           # Lógica de negocio (KPIs, cálculos, filtros)
│   ├── dashboard.py        # App Shiny for Python
│   ├── static/             # HTML/CSS compilado de Astro (NO commitear) *
│   └── data/               # Datos fuente de producción
├── frontend/
│   ├── src/pages/index.astro   # ÚNICA página (SPA)
│   ├── public/                 # Activos estáticos
│   ├── dist/                   # Build (NO commitear) *
│   ├── node_modules/           # (NO commitear) *
│   ├── astro.config.mjs
│   ├── package.json
│   ├── pnpm-lock.yaml          # (SÍ commitear)
│   └── pnpm-workspace.yaml     # (SÍ commitear)
├── scripts/inline_js.py    # Post-procesador de JS para ShinyApps.io
└── test/                   # Tests del backend (test_api.py, test_engine.py)
```

- **Lockfiles SÍ se commitean:** `pnpm-lock.yaml`, `pnpm-workspace.yaml`. `node_modules/`, `dist/`, `backend/static/` y `.venv/` NO.
- **Datos:** commitea los pequeños y de negocio (`config_excepciones.csv`, ajustes manuales); ignora los CSV/artefactos grandes y regenerables.

## 3. Regla de Oro del Enrutamiento (Aprendizaje Crítico)

ShinyApps.io/Posit asigna una URL con un slug de *worker* dinámico (`/_w_1234abcd/`). El enrutamiento dinámico de Astro (múltiples páginas o SSR) rompe contra ese proxy: navegar a `/dashboard/` da **404** y recargar pierde la sesión del worker. DEBES:

- **SPA de una sola página:** todo el frontend es `index.astro`. NADA de páginas físicas múltiples ni Server-Side Rendering.
- **Navegación por estado de cliente o Hash Routing:** cambia de vista con estado (Vanilla JS / React / Svelte) o con hash (`/#dashboard`); la URL física **nunca** cambia para el servidor.
- **Rutas estrictamente relativas:** todo enlace, `src`, `<iframe>` y `fetch` usa rutas relativas — `./api/dashboard`, `./shiny/`, NO `/api/dashboard` ni `/shiny/`. Una barra inicial `/` rompe el proxy en producción.

## 4. Frontend Astro

- `astro.config.mjs`: `output: 'static'` (SPA/SSG, nunca SSR para este hosting).
- `build.inlineStylesheets: 'always'` — el CSS va inline; evita las rutas rotas `/_astro/` en ShinyApps.io.
- **TypeScript estricto** en el frontend; para reglas finas de `.ts`/`.tsx` sigue la skill `ts-standards`, y para `.astro` (islands, estructura de componentes, deploy SPA) la skill `astro-standards`.
- Gestor de paquetes: **pnpm** (vía corepack), no npm — evita *phantom dependencies* y comparte store.
- Proxy de desarrollo en `vite.server.proxy`: reenvía `/api` y `/shiny` (con `ws: true`) a `http://localhost:8000` para replicar el gateway en local.

## 5. Backend y API Gateway (Starlette)

`app.py` es el único servicio expuesto en producción. El **orden de montaje es obligatorio**:

1. `Route(...)` de la API primero (`/api/status`, `/api/dashboard`, `/api/filters`).
2. `Mount("/shiny", app=shiny_dashboard_app)` — el dashboard Shiny en un subdirectorio.
3. `Mount("/", app=StaticFiles(directory="backend/static", html=True))` — Astro en la raíz **SIEMPRE al final**; un `Mount("/")` prematuro captura todas las rutas y deja API/Shiny inaccesibles.

- Endpoints `async` que retornan `JSONResponse`.
- El dashboard Shiny se consume desde `index.astro` con un `<iframe src="./shiny/">` (ruta relativa, §3).
- Las reglas de código Python del backend (nomenclatura, docstrings, arquitectura top-down) se rigen por la skill `python-standards`.

## 6. Optimizaciones Críticas (Rendimiento y UX)

1. **API consolidada:** un único endpoint integral `/api/dashboard` que devuelve KPIs + tabla + gantt en un solo JSON. NO hagas múltiples fetch separados desde el frontend; reduce la latencia de red.
2. **Pandas vectorizado:** prohibido iterar filas (`iterrows`, `apply` por fila) para lógica de negocio. Usa `np.where`, `.isin`, `.str.contains` y `groupby` por llave para responder en milisegundos con miles de registros.
3. **Filtros bidireccionales en cascada:** `/api/filters` recibe el estado de *todos* los filtros y devuelve solo opciones compatibles; en el frontend, además de comboboxes, las tarjetas de KPI actúan como filtros al hacer clic.

## 7. Bundle y Pipeline de Despliegue

`.rscignore` es **crítico**: sin él, `rsconnect` incluye `frontend/`, `node_modules/`, `notebooks/`, `docs/`, `test/`, `scripts/` y `.venv/` en el bundle, lo que ralentiza el deploy y puede causar **checksum mismatch**. Contenido mínimo obligatorio:

```
frontend/
frontend/*
node_modules/
node_modules/*
notebooks/
notebooks/*
docs/
docs/*
test/
test/*
scripts/
scripts/*
.venv/
venv/
data/output/
.env
```

Pipeline unificado (build → inline → copia → deploy), en PowerShell:

```powershell
cd frontend; pnpm run build; cd ..
uv run python scripts/inline_js.py            # inyecta JS inline, corrige favicon (evita /_astro/ roto)
xcopy /E /Y frontend\dist\* backend\static\   # estáticos al backend
uv run python -c "from rsconnect.main import cli; cli()" deploy shiny . --entrypoint app:app --name TU_USUARIO --app-id TU_APP_ID
```

El servidor remoto debe ver a Starlette (`app:app`) como entrypoint. Para el pre-vuelo (build + `requirements.txt` sincronizado + secretos) y el diagnóstico de suspensiones/fallos del free-tier, delega en la skill `shinyapps-deploy` cuando exista en el proyecto.

## 8. Dependencias y Versionado

| Herramienta      | Recomendado                 | Notas                                                        |
|------------------|-----------------------------|--------------------------------------------------------------|
| Gestor Python    | `uv`                        | 10-100x más rápido que `pip`; resolución determinista.       |
| Gestor Node.js   | `pnpm` (corepack)           | Evita *phantom deps*; store compartido.                      |
| Python target    | 3.11+                       | En 3.13 usa `numpy>=2.1.0` (hay wheels; `1.26.x` no compila).|
| uvicorn dev      | `--reload-exclude ".venv"`  | Evita reinicios infinitos en Windows.                        |

`requirements.txt` de producción incluye al menos: `starlette>=0.45.0`, `shiny>=1.2.0`, `uvicorn>=0.34.0`, `pandas>=2.2.0`, `numpy>=2.1.0`, `plotly>=6.0.0`, `rsconnect-python>=1.28.0` (`fastapi` solo si se usa el server de dev local).

## Reglas / Salida

- **Debe:** garantizar SPA de una sola página, rutas relativas en todo recurso/`fetch`, CSS inline, orden de montaje API→Shiny→Astro, API consolidada `/api/dashboard`, pandas vectorizado, y `.rscignore` completo antes de cualquier deploy.
- **No debe:** usar SSR/páginas múltiples en Astro, rutas absolutas con `/` inicial, `Mount("/")` antes de la API/Shiny, iterar filas de DataFrames para lógica, ni dejar `frontend/`/`node_modules/`/`.venv/` fuera del `.rscignore`. No es una skill de ejecución: no despliega — reporta divergencias y remite a `shinyapps-deploy` para el runbook.
- **Cruces:** código Python → `python-standards`; `.ts`/`.tsx` → `ts-standards`; `.astro` → `astro-standards`; diagramas de arquitectura → `generar-diagramas`; deploy a ShinyApps.io → `shinyapps-deploy` (cuando exista en el proyecto; no viene con este plugin). Los flujos y el bundle de deploy documentados aquí deben quedar reflejados en `docs/architecture/architecture.md` (plantilla `templates/plantilla_architecture.md`) y la guía de arranque en `docs/ejecucion.md` (plantilla `templates/plantilla_ejecucion.md`).
