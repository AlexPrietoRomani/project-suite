# [Nombre del Proyecto] - Plan Maestro de Implementación

> **Propósito.** Este documento sirve como una guía estructural, metódica y exhaustiva para construir el proyecto descrito en los documentos de arquitectura de software o requerimientos iniciales. Su diseño obliga a desglosar el esfuerzo en **Fases** temáticas, subdivididas en **Sub fases** y **Tareas**, asegurando un desarrollo iterativo, reproducible e integrado.
>
> **Persistencia:** Indicar qué motores de bases de datos se emplearán en entornos de desarrollo local y producción.
>
> **Tooling:** Lenguajes, gestores de paquetes y de dependencias principales (ej. Python/uv, Node/pnpm, Go/mod).
>
> **Cómo leer este documento:** Instrucciones sobre cómo debe consumirse este plan. Este archivo es la fuente primaria a partir de la cual se derivan tableros Kanban o listados de tareas detallados (ej. `tareas.md` o Jira).
> - Cada **Fase** resuelve un macro-problema y tiene objetivos de alto nivel.
> - Cada Fase se divide en **Sub fases** (micro objetivos).
> - Cada Sub fase se divide en **Tareas** (micro procesos).
> - En este Plan Maestro **solo se llega hasta el nivel de Tarea** (las acciones atómicas se definen en el documento de tareas diario).
> - **Regla de Oro de Calidad:** Cada Fase, Sub fase y Tarea debe especificar claramente sus **Tests Unitarios** y **Tests de Simulación de Usuario** (comportamiento/E2E/integración que valide el flujo desde la perspectiva del usuario final).

## Índice
2. [Stack Tecnológico Definitivo](#2-stack-tecnologico-definitivo)
3. [Estructura Objetivo del Repositorio](#3-estructura-objetivo-del-repositorio)
4. [Datos de Referencia (Fixtures)](#4-datos-de-referencia-fixtures)
5. [Estrategia, Selección y Diseño de Base de Datos](#5-estrategia-seleccion-y-diseno-de-base-de-datos)
6. [Fases de Ejecución (Plan Maestro)](#6-fases-de-ejecucion-plan-maestro)
7. [Apéndices](#7-apendices)

---

## 1. Convenciones y Nomenclatura

Reglas claras sobre el "idioma ubicuo" (Ubiquitous Language) y los estándares sintácticos que rigen el proyecto, con el fin de evitar la ambigüedad semántica:

- **Terminología de Negocio:** Define cómo llamar a los conceptos centrales.
- **Identificadores y Código:** Reglas claras para nombrar variables, clases y módulos.
- **Reglas Arquitectónicas de Diseño:** (ej. Idempotencia requerida, inmutabilidad, Single Responsibility Principle).
- **Convenciones Operativas:** (ej. Manejo del estado, reglas de formato, uso de debouncers, logs centralizados).

---

## 2. Stack Tecnológico Definitivo

Tabla matriz de las herramientas de tecnología elegidas para el proyecto.

| Capa / Dominio                  | Tecnología Preferida (Framework/Lib)    | Versión Sugerida | Justificación / Notas Técnicas                                                                                                   |
| ------------------------------- | --------------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Lenguaje Core Backend           | [Ej: Python / TypeScript / Go]          | [Versión]        | [Motivo de elección, compatibilidad de versión, dependencias estrictas]                                                          |
| Gestor de Paquetes              | [Ej: uv / pnpm / poetry]                | [Versión]        | [Ventajas de performance, manejo de dependencias fantasma, determinismo de lockfiles]                                            |
| API / Host Framework            | [Ej: FastAPI, Express, Nest, Starlette] | [Versión]        | [Razones de rendimiento, ecosistema, soporte asíncrono o requisitos del servidor en producción]                                  |
| ORM / Query Builder             | [Ej: SQLAlchemy, Prisma, Drizzle]       | [Versión]        | [Justificación sobre mantenibilidad, soporte de bases de datos objetivo (SQLite/Postgres)]                                       |
| Base de Datos (Cloud / Dev)     | [Ej: PostgreSQL / SQLite]               | [Versión]        | [Decisiones de DB local vs cloud, migraciones, soporte de transaction poolers, etc.]                                             |
| Framework UI / Frontend         | [Ej: Astro, Next.js, Shiny, Svelte]     | [Versión]        | [Justificación de patrones de renderizado: SPA, SSR, SSG]                                                                        |
| Styling / Design System         | [Ej: Tailwind CSS]                      | [Versión]        | [Menciones de paleta de colores corporativos o tokens estándar]                                                                  |
| Testing Suite                   | [Ej: pytest, Jest, Playwright]          | [Versión]        | [Tipos de testing implementados: unitario, E2E, basado en propiedades (property-based)]                                          |

---

## 3. Estructura Objetivo del Repositorio

Diagrama de árbol (`tree`) representativo de la arquitectura final esperada.

```text
nombre-del-repositorio/
│
├── pyproject.toml / package.json  # Manifiestos, dependencias y reglas de build
├── .env.example                   # Variables de entorno esenciales (plantilla)
├── README.md                      # Instrucciones de arranque e introducción
│
├── src/                           # Código fuente del proyecto
│   ├── api/                       # Capa de transporte y endpoints
│   ├── core/domain/               # Reglas puras del negocio y esquemas/tipos
│   ├── logic/                     # Casos de uso (sin I/O ni dependencias externas)
│   ├── db/                        # Migraciones, Modelos ORM, Repositorios
│   └── ui/                        # Frontend y vistas
│
├── tests/                         # Pruebas integrales de la aplicación
│   ├── unit/                      # Pruebas unitarias
│   ├── integration/               # Pruebas de integración
│   └── e2e/                       # Pruebas de simulación del usuario (Playwright/Cypress)
```

---

## 4. Datos de Referencia (Fixtures)

Espacio destinado a establecer la *verdad fundamental* matemática o de contenido del proyecto, esencial para el "Golden Testing".

**Escenario / Inputs Canónicos:**
| Variable de Entrada | Rango o Valor Ejemplo |
| ------------------- | --------------------- |
| Dato Clave 1        | 100                   |

**Salidas Esperadas (Golden Data):**
Valores numéricos, objetos resultantes, o comportamientos concretos e inequívocos que el sistema *debe* generar a partir de los inputs canónicos.

---

## 5. Estrategia, Selección y Diseño de Base de Datos

El diseño y modelado de la persistencia de datos debe ser el paso inicial previo a la codificación de la base de datos, y debe documentarse de forma detallada en un archivo dedicado (ej. `docs/db/diseno_db.md`) utilizando la `plantilla_db.md`.

Este proceso metodológico consta de:

1.  **Origen de Requisitos:** El diseño parte obligatoriamente del documento de especificación funcional y flujos de negocio (`docs/description_proyecto.md`).
2.  **Criterios de Elección del Motor:**
    - **Relacional (SQL):** Se prefiere cuando el negocio exige integridad transaccional estricta (ACID), existen relaciones complejas o jerárquicas entre entidades, o requerimientos de consultas SQL agregadas y Joins (ej. PostgreSQL, SQLite).
    - **No-Relacional (NoSQL/Documental):** Se prefiere cuando el esquema es altamente dinámico, los datos son semiestructurados o en formato JSON anidado y no hay relaciones rígidas transversales, o se requiere almacenar documentos aislados de alta velocidad (ej. MongoDB, DynamoDB).
    - **Decisión Documentada:** Justificar la elección en el Stack Tecnológico y registrar cualquier implicación (ej. Pooling de conexiones, sincronización remota).
3.  **Proceso de Construcción del Esquema:**
    - **Modelado Visual (Mermaid `erDiagram`):** Mapear gráficamente las entidades principales, atributos clave (PK, FK), y la cardinalidad de sus relaciones.
    - **Diccionario de Tablas/Colecciones:** Detalle de columnas/campos, tipos de datos, restricciones (unicidad, nulidad), índices requeridos y valores por defecto.
    - **Matriz de Accesos:** Mapear qué módulos/servicios de la aplicación realizan operaciones de lectura/escritura en cada recurso.
    - **Sistema de Migraciones:** Elegir y configurar una herramienta para el versionado de base de datos (ej. Alembic, Prisma, Flyway) que permita aplicar y revertir cambios reproduciblemente en todos los entornos.
4.  **Derivación de Tareas:** Del documento de diseño de DB resultante se generarán directamente las sub fases y tareas en `tareas.md` (Fase de Base de Datos y Persistencia).

---

## 6. Fases de Ejecución (Plan Maestro)

---

### Fase 0 — [Nombre de la Fase: Setup, Tooling e Infraestructura Base]

- **Macro-objetivo:** [Descripción general de lo que se logrará en esta fase. Ej: Configurar monorepo inicializable y reproducible, linters, formateadores y la suite de pruebas básica].
- **Entregable global de la Fase:** Entorno de desarrollo levantado con verificación de calidad automatizada en CI/CD.
- **Criterio de Aceptación (AC) global de la Fase:**
  - [ ] El comando de instalación limpia descarga y configura todas las dependencias sin fallos.
  - [ ] La ejecución del linter/formatter retorna código de salida exitoso.
- **Estrategia de Pruebas de la Fase:**
  - **Tests Unitarios:** Verificación de configs, scripts de setup y pre-commits.
  - **Tests de Simulación de Usuario:** Simulación en CI/CD del despliegue del entorno y arranque de servicios en puerto local con verificación de ping de salud.

#### Sub fase 0.1 — Inicialización de Entornos y Dependencias
- **Micro objetivo:** Disponer de los gestores de paquetes y dependencias base instaladas y listas para su uso.
- **Entregables:** Archivos manifest y lockfiles correctos (`pyproject.toml`, `package.json`, etc.).
- **Estrategia de Pruebas de la Sub fase:**
  - **Tests Unitarios:** Verificadores de consistencia en el esquema de dependencias.
  - **Tests de Simulación de Usuario:** Script que clona el repo en un entorno limpio e instala/levanta el entorno de manera interactiva.

##### T0.1.1 — Configuración del Manifiesto y Paquetes Core (Micro proceso)
- **Objetivo de la Tarea:** Inicializar los archivos de configuración del proyecto y agregar librerías de producción.
- **Entregable:** Archivos de dependencias configurados.
- **Criterios de Aceptación (AC):**
  - [ ] Archivos de dependencias compilables.
  - [ ] No existen dependencias rotas o incompatibilidades en el árbol.
- **Tests de la Tarea:**
  - **Test Unitario:** Test que valida la lectura del archivo de configuración.
  - **Test de Simulación de Usuario:** Comando de consola que valida que la instalación de paquetes se ejecuta y se integra correctamente con el interprete local.

##### T0.1.2 — Creación de la Estructura de Directorios Base (Micro proceso)
- **Objetivo de la Tarea:** Crear las carpetas de arquitectura y archivos `.env.example`.
- **Entregable:** Estructura física en disco del repositorio.
- **Criterios de Aceptación (AC):**
  - [ ] Las rutas de importación base funcionan sin referencias rotas.
- **Tests de la Tarea:**
  - **Test Unitario:** Script que verifica que todas las carpetas obligatorias y módulos base existan en el sistema de archivos.
  - **Test de Simulación de Usuario:** Verificación de importación de módulos vacíos simulando el arranque de la app.

#### Sub fase 0.2 — Setup de Herramientas de Calidad de Código
- **Micro objetivo:** Implementar herramientas automatizadas de análisis estático, estilo y pruebas.
- **Entregables:** Archivos de configuración de formateadores y linters en la raíz.
- **Estrategia de Pruebas de la Sub fase:**
  - **Tests Unitarios:** Verificación de la sintaxis y carga de las configuraciones de linters.
  - **Tests de Simulación de Usuario:** Ejecución de comandos de formateo sobre un archivo mock desordenado para validar auto-corrección.

##### T0.2.1 — Configuración de Linters, Formateadores y Pre-commit (Micro proceso)
- **Objetivo de la Tarea:** Activar linters y configurar hooks de pre-commit para prevenir commits corruptos o fuera del estándar.
- **Entregable:** `.pre-commit-config.yaml` y reglas de linter activas.
- **Criterios de Aceptación (AC):**
  - [ ] Los commits no permitidos por formato son rechazados automáticamente.
- **Tests de la Tarea:**
  - **Test Unitario:** Ejecución de linters sobre el código para certificar 0 errores.
  - **Test de Simulación de Usuario:** Simulación de un commit fallido (con errores de formato) para verificar que el hook detenga la acción.

---

### Fase 1 — [Nombre de la Fase: Modelado de Dominio y Core de Negocio]

- **Macro-objetivo:** [Descripción general. Ej: Definir e implementar las estructuras de tipos, clases de dominio, validadores y lógica pura del negocio aislada de dependencias externas].
- **Entregable global de la Fase:** Módulos de dominio e inmutables listos para su integración.
- **Criterio de Aceptación (AC) global de la Fase:**
  - [ ] El modelo lógico permite instanciarse y validarse contra los esquemas de negocio.
- **Estrategia de Pruebas de la Fase:**
  - **Tests Unitarios:** Suite de pruebas unitarias sobre todos los constructores y métodos lógicos.
  - **Tests de Simulación de Usuario:** Orquestación de flujos de negocio simulados pasando payloads complejos y validando respuestas contra el Golden Data.

#### Sub fase 1.1 — Definición de Tipos y Enums Core
- **Micro objetivo:** Declarar los tipos de datos primitivos y categorizaciones del negocio.
- **Entregables:** Módulos de definición de tipos aislados.
- **Estrategia de Pruebas de la Sub fase:**
  - **Tests Unitarios:** Validación de mapeos y parseadores de Enums.
  - **Tests de Simulación de Usuario:** Flujo de entrada de datos de usuario simulando la selección de opciones de dropdowns/filtros para asegurar que correspondan con los tipos válidos.

##### T1.1.1 — Creación de Esquemas e Invariantes de Datos (Micro proceso)
- **Objetivo de la Tarea:** Modelar las entidades principales garantizando la integridad de datos durante la instanciación.
- **Entregable:** Clases de dominio con validación de tipo y valor.
- **Criterios de Aceptación (AC):**
  - [ ] Datos incorrectos disparan excepciones capturables.
- **Tests de la Tarea:**
  - **Test Unitario:** Pruebas unitarias pasando valores nulos, negativos o fuera de rango.
  - **Test de Simulación de Usuario:** Simulación de carga de un formulario inválido en la UI y verificación de que las invariantes impidan la creación del objeto.

---

## 7. Apéndices

### Apéndice A — Definition of Done (DoD) Global

Toda **Tarea** debe cumplir estos requerimientos innegociables para considerarse finalizada:
1. El código cuenta con **Tests Unitarios** que cubren casos óptimos y de error (cobertura mínima de referencia).
2. Se han implementado **Tests de Simulación de Usuario** que emulan la interacción real/E2E con ese micro proceso.
3. Las pruebas automatizadas corren de forma limpia y exitosa en local y CI/CD.
4. Linters y formateadores pasan sin warnings o exclusiones artificiales.
5. Los cambios en bases de datos o variables de entorno están documentados.
