---
name: frontend-standards
description: Estándares modernos de arquitectura Frontend, componentes, gestión de estado, accesibilidad (a11y), feedback visual y rendimiento. CARGA cuando diseñes, implementes o refactorices interfaces de usuario y componentes web.
when_to_use: Al crear o editar interfaces web, componentes de UI, hooks/composables, stores de estado cliente/servidor o tests E2E y de componentes.
allowed-tools: Read Grep Glob Write Edit
---

# Estándares de Arquitectura e Ingeniería Frontend

Como agente de IA, DEBES cumplir rigurosamente estos estándares de diseño e ingeniería frontend al construir, modificar o auditar interfaces de usuario. Se basan en principios de arquitectura limpia para el cliente, separación de responsabilidades, accesibilidad (a11y) y Core Web Vitals.

## Flujo de Trabajo
1. **Inspección de Contexto:** Antes de crear componentes, identifica el framework (React, Vue, Svelte, Astro, Solid), el motor de estilos (Tailwind, CSS Modules, Styled Components) y el gestor de estado remoto/local.
2. **Separación de Lógica y Presentación:** Desacopla la lógica de negocio, side-effects y mutaciones de la capa de renderizado visual.
3. **Manejo de Estados de UI:** Asegura que toda vista o componente asíncrono contemple los 4 estados canónicos (Loading/Skeleton, Error, Empty, Success).
4. **Accesibilidad y Semántica:** Emplea etiquetas HTML semánticas y contratos de accesibilidad antes de recurrir a contenedores genéricos `<div>`.
5. **Verificación y Pruebas:** Aplica pruebas de componentes (Testing Library/Vitest) y pruebas de simulación de usuario (Playwright) antes de dar la tarea por completada.

---

## 1. Arquitectura y Separación de Responsabilidades

- **Componentes de Presentación (*Dumb / UI*):** 
  - Solo reciben props y emiten eventos/callbacks.
  - No realizan llamadas directas a APIs ni acceden a stores globales complejos.
  - Son predecibles, testeables y altamente reutilizables.
- **Componentes Contenedores (*Smart / Feature*):** 
  - Conectan la UI con hooks, stores o servicios.
  - Orquestan el ciclo de vida y la composición de componentes de presentación.
- **Custom Hooks / Composables:**
  - Toda lógica que maneje efectos secundarios, cálculos derivados o sincronización con APIs DEBE encapsularse en custom hooks/composables dedicados (ej. `useUserPermissions()`, `useDebounceSearch()`).

---

## 2. Gestión de Estado: Servidor vs. Cliente

- **Estado de Servidor (*Server Cache / Remote State*):**
  - Datos obtenidos por API/red pertenecen a herramientas de caché remota (ej. TanStack Query, SWR, RTK Query, Nuxt `useFetch`).
  - NUNCA dupliques datos del servidor en estados locales (`useState`/`ref`) a menos que requieran edición en borrador independiente.
- **Estado de Cliente UI (*Local / Global Client State*):**
  - Modales abiertos, pestañas activas, temas visuales o preferencias de vista.
  - Usa stores ligeros y modulares (Zustand, Pinia, Nanostores) o estado local según el alcance necesario.
- **Estado de Formularios:**
  - Validaciones síncronas/asíncronas controladas con librerías de esquemas tipados (Zod, Valibot) y gestores de formularios (React Hook Form, Formik, VeeValidate).

---

## 3. Los 4 Estados Obligatorios de UI

Ningún componente o pantalla que consuma datos asíncronos puede pasar a producción sin implementar explícitamente:
1. **Estado de Carga (*Loading / Skeleton*):** Usa esqueletos (*skeletons*) con las dimensiones aproximadas del contenido final para evitar saltos de diseño (CLS).
2. **Estado de Error (*Error State*):** Mensaje comprensible para el usuario, sin tecnicismos ni stacktraces visibles, con un botón o mecanismo claro de reintento (*Retry*).
3. **Estado Vacío (*Empty State*):** Si la lista o resultado tiene 0 elementos, muestra una ilustración o icono sutil, una explicación clara y una llamada a la acción (*Call to Action*, ej. "Crear primer registro").
4. **Estado Exitoso (*Success / Data Display*):** Visualización clara de los datos cargados.

---

## 4. Accesibilidad (a11y) y HTML Semántico

- **HTML Semántico Obligatorio:** Usa `<main>`, `<header>`, `<footer>`, `<nav>`, `<aside>`, `<section>`, `<article>`, `<button>` y `<input>` en lugar de construir botones o enlaces con `<div onClick="...">`.
- **Navegación por Teclado:** Todo elemento interactivo debe ser alcanzable con `Tab`, operable con `Enter` y `Space`, y mantener un indicador de foco visible (`focus-visible`).
- **Atributos ARIA:** Usa ARIA solo cuando el HTML nativo no proporcione la semántica requerida (`aria-expanded`, `aria-controls`, `aria-label`, `role="alert"`).
- **Contraste y Escala:** Relación mínima de contraste de 4.5:1 para texto normal (WCAG AA). Los tamaños de fuente y targets táctiles deben ser de mínimo 44x44px en móviles.

---

## 5. Rendimiento y Core Web Vitals

- **Largest Contentful Paint (LCP):** Optimiza imágenes críticas con formatos modernos (WebP/AVIF), atributos `fetchpriority="high"` y dimensiones explícitas `width` y `height`.
- **Cumulative Layout Shift (CLS):** Reserva espacio con `aspect-ratio` o contenedores de tamaño fijo para imágenes, anuncios y banners dinámicos.
- **Interaction to Next Paint (INP):** Evita bloquear el hilo principal. Aplica *debouncing* o *throttling* en inputs de búsqueda y eventos de scroll/resize.
- **Code-Splitting Dinámico:** Carga diferida (*lazy loading*) de rutas secundarias, modales pesados o bibliotecas de gráficos/mapas mediante `dynamic import()` o `React.lazy()`.

---

## 6. Convenciones de Nomenclatura y Archivos

- **Componentes:** `PascalCase.tsx` / `PascalCase.vue` (ej. `UserProfileCard.tsx`).
- **Hooks:** `usePascalCase.ts` o `useCamelCase.ts` (ej. `useDebounce.ts`, `useAuthSession.ts`).
- **Utilidades y Servicios:** `kebab-case.ts` (ej. `format-currency.ts`, `api-client.ts`).
- **Estilos:** Colocados junto al componente (`UserProfileCard.module.css`) o vía utilidades atómicas.

---

## 7. Referencias Canónicas y Herramientas del Ecosistema

- **shadcn/ui (Arquitectura de Componentes y Estilizado):**
  - Adopta el principio de componentes accesibles desacoplados: primitivas sin estilos (Radix UI) combinadas con utilidades atómicas (Tailwind CSS) mediante utilidades como `cn()` (`clsx` + `tailwind-merge`).
  - Emplea el patrón `asChild` para composición de elementos interactivos sin añadir wrappers `<div>` innecesarios.
  - Sigue una paleta de tokens semánticos configurables (`--background`, `--primary`, `--muted`, `--destructive`).
- **awesome-cursorrules (Reglas de Diseño y Frameworks Modernos):**
  - Aplica convenciones probadas de la comunidad para React/Vue/Svelte/Astro y Tailwind CSS: props inmutables, componentes puros y minimización de re-renders.
- **mcp-playwright (Testing, Rendering e Inspección Visual):**
  - Para pruebas de simulación de usuario y validación visual, apóyate en el servidor MCP de Playwright o el runner local para verificar navegación, formularios, estados de carga y capturas visuales en tiempo real.
