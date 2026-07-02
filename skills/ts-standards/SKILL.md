---
name: ts-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y documentación para TypeScript/Node. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .ts o .tsx.
when_to_use: Al generar código TypeScript, refactorizar archivos .ts/.tsx, realizar revisiones de código, o estructurar módulos, tipos y tests en proyectos Node/pnpm.
allowed-tools: Read Grep Glob
---

# Estándares de Arquitectura y Código TypeScript/Node

Como agente de IA, DEBES cumplir estrictamente estas normativas de calidad al trabajar con archivos TypeScript (`.ts`, `.tsx`). Se basan en el `tsconfig` estricto oficial, ESLint + Prettier y las convenciones idiomáticas del ecosistema Node/pnpm.

## Flujo
1. Antes de escribir, identifica el `tsconfig.json` y el `package.json` del proyecto: confirma que el modo estricto está activo y detecta el runner de tests (Vitest o Jest) y el gestor de paquetes (`pnpm`).
2. Aplica las reglas de idioma, nomenclatura, tipado y estructura de módulos de las secciones 1–6 al generar o refactorizar código.
3. Materializa los tests junto al código según la sección 7 y verifica que lint/format pasan sin warnings (sección 8) antes de dar la tarea por cerrada.

## 1. Reglas Generales e Idioma Mixto
- **Código en Inglés:** Identificadores (variables, funciones, clases, métodos, argumentos, tipos, interfaces, enums) DEBEN estar estrictamente en inglés. No uses abreviaturas crípticas (ej. usa `filteredRows`, NO `fr`).
- **Documentación en Español:** Todos los comentarios internos (`//`) y bloques TSDoc/JSDoc (`/** */`) DEBEN redactarse en español.
- **Tiempos Verbales:** Documenta siempre en **presente activo** (ej. "Esta función calcula...", NO "Se calculó...").

## 2. Nomenclatura Estricta
- **Variables, funciones y métodos:** `camelCase` (ej. `imageProcessor`, `calculateMetrics()`). Las funciones, idealmente verbos.
- **Clases, tipos, interfaces y enums:** `PascalCase` (ej. `DatabaseAuditor`, `UserProfile`, `HttpStatus`). No uses el prefijo `I` en interfaces (`UserProfile`, NO `IUserProfile`).
- **Constantes de módulo:** `UPPER_SNAKE_CASE` (ej. `MAX_RETRIES`, `DEFAULT_THRESHOLD`). Evita números mágicos hardcodeados.
- **Archivos:** `kebab-case.ts` para módulos (ej. `fit-models.ts`); componentes React en `PascalCase.tsx` (ej. `UserCard.tsx`). Un nombre que describa su contenido.
- **Miembros privados:** usa el modificador `private` de la clase; reserva el prefijo `#` para campos privados reales del lenguaje cuando lo necesites.

## 3. Configuración Estricta y Tipado (`tsconfig`)
- **Modo estricto obligatorio:** `"strict": true` en `tsconfig.json`. Activa además `noUncheckedIndexedAccess`, `noImplicitOverride` y `exactOptionalPropertyTypes` cuando el proyecto lo permita.
- **Prohibido `any`:** NUNCA introduzcas `any` (explícito ni implícito). Si el tipo es genuinamente desconocido, usa `unknown` y estrecha con guards. Un `any` puntual e inevitable se justifica en comentario y se aísla con `// eslint-disable-next-line`.
- **`type` vs `interface`:** usa `interface` para formas de objeto extensibles y contratos públicos; usa `type` para uniones, intersecciones, tuplas y utilidades.
- **Inmutabilidad:** prefiere `readonly` y `as const` para datos que no mutan; declara con `const` salvo que necesites reasignar.
- **Sin no-null asertivo gratuito:** evita `!` (non-null assertion); estrecha con checks explícitos u `optional chaining` (`?.`) y `nullish coalescing` (`??`).

## 4. Comentarios Internos (`//`) y TSDoc
- **El Porqué, no el Qué:** El código tipado se explica solo. Usa comentarios inline solo para decisiones técnicas complejas, fundamentos matemáticos o *workarounds* temporales.
- **Alineación:** mínimo dos espacios antes de un comentario inline en la misma línea de código.
- **Mala práctica:** `x = x + 1  // Incrementa x en 1` (explica el qué).
- **Buena práctica:** `await sleep(2000)  // Pausa necesaria para no exceder el rate-limit de la API` (explica el porqué).
- **TSDoc:** documenta las funciones y tipos exportados con bloques `/** */` (`@param`, `@returns`, `@throws`); el tipado ya cubre los tipos, así que la descripción explica el propósito, no repite las firmas.

## 5. Estructura de Módulos e Imports
- **Módulos ES:** usa `import`/`export` (ESM), NO `require`. Prefiere named exports; reserva `export default` para el punto de entrada único de un componente o módulo.
- **Sin barriles ciegos:** evita `index.ts` que reexporten todo si generan ciclos; importa desde la ruta concreta.
- **Orden de imports:** primero built-ins de Node y librerías externas, luego imports internos por alias/ruta; sin imports sin usar (los detecta ESLint).
- **Frontera de tipos:** usa `import type { ... }` para importar solo tipos, de modo que se eliminen en compilación.
- **Organización top-down:** en cada archivo, primero imports, luego constantes/tipos, después la función/símbolo principal exportado y por último los helpers privados que este usa.

## 6. Manejo de Errores y Asincronía
- **`async`/`await`:** modela la asincronía con `async`/`await` y tipa el retorno como `Promise<T>`; evita cadenas largas de `.then()`.
- **Errores tipados:** en el `catch (error)` el error es `unknown`; estrecha (`instanceof Error`) antes de acceder a `.message`. Lanza `Error` (o subclases propias), nunca strings.
- **Sin promesas huérfanas:** toda promesa se espera (`await`) o se maneja explícitamente; no dejes rechazos sin capturar.

## 7. Testing Obligatorio (Vitest / Jest)
- **Runner:** usa **Vitest** por defecto en proyectos nuevos (o **Jest** si el proyecto ya lo tiene). Detecta cuál está configurado en `package.json` antes de escribir tests.
- **Ubicación:** coloca los tests en `*.test.ts` junto al código o bajo `tests/`, según la convención del repo. Sigue Arrange–Act–Assert y nombra los `describe`/`it` en español describiendo el comportamiento.
- **Cobertura de AC:** cada Criterio de Aceptación de una Tarea del plan tiene al menos un test que lo verifica. Para los tests obligatorios (unitario + simulación de usuario) y el gate de cierre, delega en las skills `testear` y `verificar-dod`.

## 8. Tooling y Gestor de Paquetes
- **pnpm:** usa `pnpm` como gestor de paquetes (`pnpm install`, `pnpm add`, `pnpm run <script>`). No mezcles con `npm`/`yarn` ni comitees `package-lock.json`/`yarn.lock`; el lockfile canónico es `pnpm-lock.yaml`.
- **ESLint + Prettier:** el código debe pasar ESLint (con `@typescript-eslint`) y Prettier **sin warnings**. Prettier gobierna el formato (comillas, comas colgantes, ancho de línea ~100); ESLint gobierna las reglas de calidad. No desactives reglas de forma masiva.
- **Scripts estándar:** expón `build`, `lint`, `format`, `test` en `package.json`. La compilación (`tsc --noEmit` o el bundler) no debe emitir errores de tipos.

## 9. Cruces con otros estándares
- Para componentes de UI en el framework Astro, respeta además la skill `astro-standards` (`.astro` usa TS estricto y las mismas reglas de tipado de este documento).
- Para la arquitectura completa de una app web (gateway, rutas relativas, endpoints consolidados), respeta la skill `webapp-standards`.
