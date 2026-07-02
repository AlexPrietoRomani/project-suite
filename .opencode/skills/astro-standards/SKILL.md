---
name: astro-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y despliegue para Astro. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .astro.
when_to_use: Al generar componentes/páginas Astro, refactorizar archivos .astro, revisar código de un frontend Astro, o preparar el build para un despliegue tipo ShinyApps.io/Posit Connect.
allowed-tools: Read Grep Glob
---

# Estándares de Arquitectura y Código Astro

Como agente de IA, DEBES cumplir estrictamente estas normativas de calidad al trabajar con archivos Astro (`.astro`) y su configuración (`astro.config.mjs`, `package.json`, `tsconfig.json`). Las reglas de despliegue SPA/rutas relativas/CSS inline son **obligatorias** cuando el frontend se sirve detrás de un gateway tipo ShinyApps.io o Posit Connect (arquitectura Astro + Starlette + Shiny).

## Flujo
1. **Detecta el tipo de salida objetivo:** si el proyecto se despliega detrás de un worker con slug dinámico (ShinyApps.io/Posit Connect), aplica el modo **SPA estricto** (§4). Para un hosting estático clásico (Netlify, Vercel static, GitHub Pages) puedes usar SSG multipágina normal, pero mantén las demás reglas.
2. **Verifica la config** (`astro.config.mjs`): `output`, `build.inlineStylesheets`, y el `proxy` de Vite para `/api` y `/shiny` en desarrollo (§4, §5).
3. **Estructura los componentes** con frontmatter arriba, template abajo, e islas (`client:*`) solo donde haga falta interactividad (§2, §3).
4. **Audita rutas:** todo enlace, `import` de activo y `fetch` debe ser **estrictamente relativo** cuando el destino sea ShinyApps.io (§4).
5. **Confirma el gestor de paquetes:** `pnpm` (con `corepack`), lockfile `pnpm-lock.yaml` commiteado (§6).

## 1. Reglas Generales e Idioma Mixto
- **Código en Inglés:** Identificadores (variables, funciones, props, componentes) DEBEN estar estrictamente en inglés. Nada de abreviaturas crípticas (usa `filteredRows`, NO `fr`).
- **Documentación en Español:** Todos los comentarios internos (`//`, `/* */`, `<!-- -->`) DEBEN redactarse en español.
- **Tiempos Verbales:** Documenta en **presente activo** (ej. "Este componente renderiza...", NO "Se renderizó...").
- **TypeScript estricto:** El proyecto usa `tsconfig.json` con el preset **`strict`** de Astro. Prohibido `any`; tipa las `props` de cada componente con `interface Props`.

## 2. Nomenclatura Estricta
- **Componentes y páginas:** `PascalCase.astro` para componentes reutilizables (ej. `KpiCard.astro`, `GanttChart.astro`); las páginas en `src/pages/` van en `kebab-case` o `index.astro`. En modo SPA existe **una sola página** física: `src/pages/index.astro`.
- **Variables y funciones (dentro del frontmatter):** `camelCase` (ej. `dashboardData`, `fetchDashboard()`).
- **Constantes y globales:** `UPPER_SNAKE_CASE` (ej. `API_BASE`, `POLL_INTERVAL_MS`). Evita valores mágicos hardcodeados.
- **CSS/clases:** `kebab-case` en clases (`kpi-card`), o usa estilos `<style>` scoped por componente (comportamiento por defecto de Astro).

## 3. Estructura del Componente e Islas de Interactividad
- **Dos zonas claras:** el **frontmatter** (`---` … `---`) arriba contiene el código del lado servidor (imports, fetch de datos en build, tipado de `Props`); debajo va el **template** (HTML/JSX-like). No mezcles lógica pesada en el template.
- **Astro es HTML por defecto (zero-JS):** No envíes JavaScript al cliente salvo que un fragmento requiera interactividad real.
- **Islas (`client:*`):** Marca la hidratación solo en los componentes interactivos:
  - `client:load` para lo crítico visible al inicio (ej. el panel de filtros).
  - `client:visible` para lo que se hidrata al entrar en viewport (ej. gráficos secundarios).
  - `client:idle` para interactividad no urgente.
  - Nunca hidrates un componente puramente estático.
- **Composición:** un componente = una responsabilidad. Extrae `KpiCard`, `FilterBar`, `GanttChart` en `src/components/` en lugar de un `index.astro` monolítico.
- **Estado de cliente:** la navegación entre vistas se maneja con **estado de cliente** (Vanilla JS / framework de isla) o **Hash Routing** (`/#dashboard`), nunca con páginas físicas nuevas (ver §4).

## 4. Regla de Oro — SPA + Rutas Relativas (despliegue ShinyApps.io/Posit Connect)
Al desplegar detrás de un gateway Starlette en ShinyApps.io, el servidor asigna una URL con un *slug* de worker dinámico (ej. `/_w_1234abcd/`). El enrutamiento dinámico o multipágina de Astro **rompe** (404 al navegar o recargar, pérdida de sesión del worker). Por eso:

- **SPA obligatorio:** una sola página física, `src/pages/index.astro`. **Prohibido** el enrutamiento dinámico de Astro y el SSR para este despliegue.
- **Navegación por estado o Hash Routing:** cambia de vista con estado de cliente o `/#dashboard`; la URL física NUNCA debe cambiar para el servidor.
- **Rutas estrictamente relativas:** todo enlace, activo (`img`, `script`), `import` de estático y `fetch` debe ser relativo (`./api/dashboard`, `./shiny/`), **nunca** absoluto (`/api/dashboard`). Las rutas absolutas colisionan con el slug del worker.
- **`iframe` de Shiny relativo:** incrusta el dashboard con `<iframe src="./shiny/" …>`, no con `/shiny/`.

```javascript
// astro.config.mjs — modo SPA para ShinyApps.io/Posit Connect
import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'static',              // SSG puro; NADA de SSR ni adaptadores server
  build: {
    inlineStylesheets: 'always', // CSS inline: evita rutas /_astro/ rotas en el worker
  },
  vite: {
    server: {
      proxy: {
        '/api':   { target: 'http://localhost:8000', changeOrigin: true },
        '/shiny': { target: 'http://localhost:8000', changeOrigin: true, ws: true },
      },
    },
  },
});
```

## 5. CSS Inline y Activos
- **`inlineStylesheets: 'always'`** es obligatorio en el despliegue ShinyApps.io: incrusta el CSS en el `<head>` en lugar de emitir `/_astro/*.css`, cuyas rutas absolutas se rompen bajo el slug del worker.
- **Post-proceso de JS:** si el build emite `<script>` externos con rutas absolutas, deben inyectarse inline (ej. un `scripts/inline_js.py` en la fase de build) para el mismo motivo. Ver la guía `docs/ejecucion.md` del proyecto y la skill `webapp-standards`.
- **Estilos scoped:** prefiere `<style>` scoped por componente; usa estilos globales solo para tokens/reset.
- **Activos estáticos:** favicon e imágenes en `public/`; referencia siempre relativa (`./favicon.svg`).

## 6. Gestor de Paquetes y Tooling
- **`pnpm` (no `npm`):** evita *phantom dependencies* y comparte store. Habilítalo con `corepack enable && corepack prepare pnpm@latest --activate`.
- **Lockfile:** commitea `pnpm-lock.yaml` (y `pnpm-workspace.yaml` si aplica); NO commitees `node_modules/` ni `dist/`.
- **Scaffold:** `pnpm create astro@latest frontend` → *Empty project*, TypeScript **Strict**. Tras instalar, `pnpm approve-builds` para binarios (`esbuild`, `sharp`).
- **Build:** `pnpm run build` genera `frontend/dist/`, que luego se copia a `backend/static/` para que Starlette lo sirva en `/`.

## Reglas / Salida
- **Debe:** aplicar SPA estricto + rutas relativas + `inlineStylesheets: 'always'` en cualquier proyecto con despliegue ShinyApps.io/Posit Connect; tipar props con TS strict; usar islas `client:*` solo donde haya interactividad; usar `pnpm`.
- **No debe:** introducir páginas físicas múltiples, SSR/adaptadores server, rutas absolutas (`/api`, `/_astro/…`), ni `any` en TypeScript, cuando el destino sea el gateway Starlette.
- **Cruces:** para la arquitectura completa Astro + Starlette + Shiny (gateway, endpoint consolidado `/api/dashboard`, `.rscignore`, `uv`), consulta la skill `webapp-standards`. La guía de arranque/despliegue vive en `docs/ejecucion.md` (skill `ejecucion`). Para el backend Python asociado, aplica `python-standards`.
- **Salida:** este skill es guía normativa (no genera archivos); reporta las violaciones detectadas y la corrección concreta por archivo `.astro`/config.
