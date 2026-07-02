# Listado de Tareas — [Nombre del Proyecto]

> **Fuentes de contexto obligatorias:**
> - Spec funcional/lógico: [`docs/description_proyecto.md`](../description_proyecto.md) (o equivalente).
> - Plan maestro (Fases, Sub fases y arquitectura): [`docs/plan/plan_maestro.md`](../plan/plan_maestro.md) (o equivalente).
> - Diseño de Base de Datos: [`docs/db/diseno_db.md`](../db/diseno_db.md) (o equivalente, basado en `plantilla_db.md`).
>
> **Persistencia y Aprendizaje de Errores (Bitácora de Incidentes):**
> - **Consulta Obligatoria:** Ante cualquier complicación, error recurrente o bloqueo durante el desarrollo de una tarea, el desarrollador (o agente de IA) debe revisar obligatoriamente [`docs/log.md`](../log.md) (basado en `plantilla_log.md`) para verificar si el incidente ya fue resuelto previamente.
> - **Mapeo de Nuevos Errores:** Si el error no ha sido documentado, se debe abrir un apartado en `docs/log.md` describiendo detalladamente los síntomas y el contexto.
> - **Registro de Solución:** Una vez resuelto, se debe registrar el diagnóstico de causa raíz y la solución implementada para consolidar el conocimiento y evitar reincidir en el mismo error.
>
> **Convenciones de Checkboxes:**
> - `[ ]` Pendiente
> - `[/]` En progreso / En revisión
> - `[X]` Completado
> - **Invariante de progreso:** Una Tarea solo se marca completada (`[X]`) si todas sus Acciones asociadas están en `[X]` y sus Criterios de Aceptación y Tests pasan de forma limpia. Una Sub fase se completa si todas sus Tareas lo están, y una Fase se completa si todas sus Sub fases lo están.
>
> **Convenciones de Identificadores (IDs):**
> - **Fase:** `F{n}` — ej. `F1`
> - **Sub fase:** `SF{f}.{n}` — ej. `SF1.1`
> - **Tarea:** `T{f}.{sf}.{n}` — ej. `T1.1.2` (Fase 1, Sub fase 1, Tarea 2)
> - **Acción:** `A{f}.{sf}.{t}.{n}` — ej. `A1.1.2.3` (Fase 1, Sub fase 1, Tarea 2, Acción 3)
>
> **Regla Maestra de Calidad:** Cada Fase, Sub fase, Tarea y Acción debe detallar y ejecutar obligatoriamente **Tests Unitarios** (aislados del sistema) y **Tests de Simulación de Usuario** (comportamiento/E2E/integración que replique la experiencia del usuario interactuando con el entregable). Una Tarea solo se marca completada si todas sus Acciones están en `[X]` y sus AC se cumplen; una Fase solo se marca completada si todas sus sub Fases lo están.
>
> **Estructura obligatoria de cada Tarea (didáctica y reproducible):** además de Objetivo / Entregable / AC / Tests, **toda Tarea debe incluir** dos bloques que la hagan autoexplicativa:
> - **🧠 Explicación:** qué es cada parte y *por qué* se hace así (concepto + decisión de diseño), en lenguaje claro para cualquier desarrollador o agente de IA.
> - **💡 Cómo hacerlo (ejemplo):** uno o más bloques de **código o comandos reales y adaptables** (con el lenguaje correcto: ` ```python `, ` ```bash `, ` ```sql `, ` ```yaml `, etc.) que muestren cómo implementar la Tarea.
>
> Coloca ambos bloques entre el **Entregable** y los **AC/Tests**. Si una Tarea repite un patrón ya ejemplificado, puedes **referenciar** la Tarea/documento donde está el ejemplo en vez de duplicarlo. Las Tareas de ejemplo de esta plantilla (T0.1.1, T1.1.1 y T2.1.1) muestran el formato a seguir.

---

## Índice de Fases y Sub fases

- [ ] [Fase 0 — Setup e Infraestructura Base](#fase-0--setup-e-infraestructura-base)
  - [ ] [Sub fase 0.1 — Inicialización de Entornos](#sub-fase-01--inicializacion-de-entornos)
- [ ] [Fase 1 — Modelado de Dominio y Core de Negocio](#fase-1--modelado-de-dominio-y-core-de-negocio)
  - [ ] [Sub fase 1.1 — Tipos y Validación de Datos](#sub-fase-11--tipos-y-validacion-de-datos)
- [ ] [Fase 2 — Base de Datos y Persistencia](#fase-2--base-de-datos-y-persistencia)
  - [ ] [Sub fase 2.1 — Modelado Físico y Migraciones](#sub-fase-21--modelado-fisico-y-migraciones)

---

## [ ] Fase 0 — Setup e Infraestructura Base (Macro-objetivos)

- **Objetivo:** [Descripción general de la Fase. Ej: Dejar el repositorio inicializado con tooling ejecutable de manera reproducible y controles de calidad activos].
- **Entregable global:** Entorno de desarrollo Docker/Local operativo y configurado con linter y testing suites.
- **AC global de la Fase:**
  - [ ] El comando de instalación limpia configura todas las dependencias.
  - [ ] Los scripts de calidad (linting/format) pasan con 0 advertencias.
- **Tests de la Fase:**
  - **Test Unitario:** Validación de la carga de manifiestos y dependencias cruzadas.
  - **Test de Simulación de Usuario:** Clonado limpio e instalación del entorno mediante comandos, verificando que los servicios arranquen y respondan ping de saludo en local.

---

### [ ] SF0.1 — Inicialización de Entornos (Micro objetivo)

- **Objetivo:** [Descripción de la Sub fase. Ej: Configurar los gestores de paquetes principales, dependencias base y la estructura de carpetas física de la aplicación].
- **Entregable:** Archivos de dependencias bloqueados y árbol de carpetas creado.
- **AC de la Sub fase:**
  - [ ] Los paquetes se resuelven sin conflictos de versiones.
- **Tests de la Sub fase:**
  - **Test Unitario:** Ejecución de chequeos de integridad estáticos sobre el lockfile.
  - **Test de Simulación de Usuario:** Script que inicializa el entorno de desarrollo simulando la primera experiencia de un desarrollador en el equipo.

#### [ ] T0.1.1 — Configuración del Manifiesto y Paquetes Core (Micro proceso)
- **Objetivo de la Tarea:** Inicializar los archivos de paquetes (`package.json`, `pyproject.toml`, etc.) y sus dependencias estrictas.
- **Entregable:** Archivos manifest y lockfiles correctos en la raíz.

> **🧠 Explicación:** [Explica qué es cada componente y por qué se eligió así. Ej: el *gestor de paquetes* garantiza instalaciones reproducibles y rápidas; el *manifiesto* (`pyproject.toml`/`package.json`) declara **qué** dependencias necesitamos, y el *lockfile* congela **las versiones exactas** para que el entorno sea idéntico en local, CI y producción. Se separan dependencias de producción de las de desarrollo (tests, linter).]

> **💡 Cómo hacerlo (ejemplo):**
> ```bash
> # Ejemplo con Python + uv (adaptar al gestor del stack: pnpm, poetry, go mod, etc.)
> uv init mi-proyecto && cd mi-proyecto
> uv add fastapi "uvicorn[standard]"      # dependencias de producción
> uv add --dev pytest ruff                # dependencias de desarrollo
> uv sync                                  # resuelve e instala -> genera el lockfile
> ```

- **AC de la Tarea:**
  - [ ] Comando de instalación instala las dependencias sin fallar.
- **Tests de la Tarea:**
  - **Test Unitario:** Comprobar la existencia y validez sintáctica de los archivos.
  - **Test de Simulación de Usuario:** Comando de instalación automatizado ejecutado y verificado en un contenedor de pruebas.

##### [ ] A0.1.1.1 — Crear archivos manifiesto de dependencias (Mínimo por hacer)
- **Objetivo:** Inicializar físicamente los archivos de configuración y definir dependencias clave.
- **Input:** Sistema de archivos del repositorio y stack técnico definido.
- **Output:** Archivos `pyproject.toml` o `package.json` en disco.
- **Proceso:**
  1. [Paso 1. Inicializar mediante CLI, ej: `npm init` o `poetry init`].
  2. [Paso 2. Agregar dependencias en el manifest].
- **Tests:**
  - **Test Unitario:** Test que valida que los archivos JSON/TOML son sintácticamente válidos.
  - **Test de Simulación de Usuario:** Comando de parseo de dependencias de la CLI que valida que el manifiesto es legible y ejecutable por el gestor de paquetes.
- **AC:** Los manifiestos contienen las dependencias exactas del stack tecnológico y se leen correctamente.

##### [ ] A0.1.1.2 — Generar el archivo de bloqueo de dependencias (Mínimo por hacer)
- **Objetivo:** Bloquear las versiones exactas para garantizar reproducibilidad.
- **Input:** Archivos manifiesto generados en A0.1.1.1.
- **Output:** Archivos lock (`pnpm-lock.yaml`, `poetry.lock`, `uv.lock`).
- **Proceso:**
  - Ejecutar el comando de instalación del gestor elegido para resolver y generar el lockfile.
- **Tests:**
  - **Test Unitario:** Chequeo automático de integridad de firma del lockfile.
  - **Test de Simulación de Usuario:** Ejecución de un comando de instalación en modo offline/freeze y verificación de que se utilicen solo las dependencias bloqueadas.
- **AC:** Lockfile generado en la raíz sin advertencias de versiones en conflicto.

---

## [ ] Fase 1 — Modelado de Dominio y Core de Negocio (Macro-objetivos)

- **Objetivo:** [Descripción de la Fase. Ej: Definir el modelo de dominio lógico, sus tipos de datos primitivos e invariantes de negocio aislados de frameworks].
- **Entregable global:** Librería o directorio de modelos y validadores inmutables de dominio.
- **AC global de la Fase:**
  - [ ] Todas las clases del dominio permiten ser instanciadas y validan sus reglas de negocio al nacer.
- **Tests de la Fase:**
  - **Test Unitario:** Suite de pruebas unitarias sobre constructores y métodos.
  - **Test de Simulación de Usuario:** Ingesta de un payload complejo simulado y comprobación de que el modelo de dominio calcula las variables derivadas correctamente según las reglas de negocio.

---

### [ ] SF1.1 — Tipos y Validación de Datos (Micro objetivo)

- **Objetivo:** [Descripción de la Sub fase. Ej: Implementar los Enums, tipos de datos primitivos y clases de datos con validaciones].
- **Entregable:** Módulos de tipos y esquemas de validación de datos.
- **AC de la Sub fase:**
  - [ ] Los esquemas impiden el paso de datos corruptos al dominio core.
- **Tests de la Sub fase:**
  - **Test Unitario:** Suite de pruebas sobre validadores de tipos básicos.
  - **Test de Simulación de Usuario:** Simulación de una interfaz de ingreso de datos donde se introducen tipos incorrectos y se verifica que los validadores intercepten y expliquen los errores.

#### [ ] T1.1.1 — Modelado de Entidades Core con Invariantes (Micro proceso)
- **Objetivo de la Tarea:** Definir las clases y estructuras de datos principales garantizando sus restricciones lógicas.
- **Entregable:** Archivos de clases con validadores de rango y restricciones.

> **🧠 Explicación:** [Explica el rol del modelado de dominio. Ej: los esquemas validan y documentan el "contrato" de datos en los límites del sistema; un validador rechaza valores imposibles **antes** de que contaminen la lógica de negocio o la base de datos. Define las invariantes que toda entidad debe cumplir al nacer.]

> **💡 Cómo hacerlo (ejemplo):**
> ```python
> # Ejemplo con Pydantic (adaptar al lenguaje/librería del stack)
> from pydantic import BaseModel, Field, field_validator
>
> class EntidadCore(BaseModel):
>     codigo: str = Field(min_length=1)
>     valor: float = Field(ge=0)            # invariante: no negativos
>
>     @field_validator("codigo")
>     @classmethod
>     def _normaliza(cls, v: str) -> str:
>         if not v.strip():
>             raise ValueError("codigo no puede estar vacío")
>         return v.strip().upper()           # canonicalización
> ```

- **AC de la Tarea:**
  - [ ] Intentos de asignación de datos inválidos disparan excepciones de negocio controladas.
- **Tests de la Tarea:**
  - **Test Unitario:** Pruebas unitarias de frontera (valores límite, nulos, vacíos).
  - **Test de Simulación de Usuario:** Simulación de la carga de un formulario inválido en la UI de usuario y confirmación de que la validación impida la propagación a la base de datos.

##### [ ] A1.1.1.1 — Crear clases de dominio inmutables (Mínimo por hacer)
- **Objetivo:** Definir las propiedades y tipos de las entidades base.
- **Input:** Estructura del modelo relacional/documental.
- **Output:** Archivos de código fuente con las clases de dominio.
- **Proceso:**
  - Escribir la definición de clases y decoradores de tipado de acuerdo a las convenciones.
- **Tests:**
  - **Test Unitario:** Instanciación básica de clases verificando tipos de retorno de atributos.
  - **Test de Simulación de Usuario:** Simular la conversión de las clases a diccionarios/JSON para transferir datos a la capa del cliente.
- **AC:** Las entidades exponen de forma pública sus atributos requeridos y respetan los nombres de la convención sintáctica.

##### [ ] A1.1.1.2 — Agregar validaciones de rango e integridad (Mínimo por hacer)
- **Objetivo:** Asegurar que los datos instanciados cumplan con las reglas y rangos lógicos del negocio.
- **Input:** Clases de dominio de A1.1.1.1 y reglas de validación.
- **Output:** Métodos de validación o esquemas de validación integrados en las clases.
- **Proceso:**
  - Implementar lógica que compruebe límites de rangos, valores permitidos y nulidad.
- **Tests:**
  - **Test Unitario:** Pasar valores fuera de rango y verificar el lanzamiento de excepciones.
  - **Test de Simulación de Usuario:** Flujo de entrada de datos simulando el envío de datos de usuario con campos obligatorios vacíos y verificación de que se reciba el mensaje de error adecuado.
- **AC:** Valores inválidos arrojan errores descriptivos y valores válidos se instancian correctamente.

---

## [ ] Fase 2 — Base de Datos y Persistencia (Macro-objetivos)

- **Objetivo:** Implementar la base de datos física, sus tablas/colecciones, constraints, índices y el sistema de migraciones conforme al diseño detallado.
- **Entregable global:** Base de datos instanciada en entorno local/test con migraciones aplicadas correctamente.
- **AC global de la Fase:**
  - [ ] El comando de migración se ejecuta sin errores y levanta la estructura esperada en una base de datos vacía.
- **Tests de la Fase:**
  - **Test Unitario:** Validación de la carga de esquemas y tests de conexión del Pool.
  - **Test de Simulación de Usuario:** Creación de un registro, lectura, modificación y eliminación (CRUD) simulando la carga de datos del flujo de negocio.
- **Referencias:** [`docs/db/diseno_db.md`](../db/diseno_db.md) (derivado de `plantilla_db.md`).

---

### [ ] SF2.1 — Modelado Físico y Migraciones (Micro objetivo)

- **Objetivo:** Crear los archivos de migración y la configuración del motor de persistencia.
- **Entregables:** Scripts de migración de base de datos e inicialización de esquemas.
- **AC de la Sub fase:**
  - [ ] Se puede aplicar y revertir la migración sin dejar huérfanos o corrupción.
- **Tests de la Sub fase:**
  - **Test Unitario:** Script que comprueba que la versión actual de la migración coincide con el estado del ORM/esquema físico.
  - **Test de Simulación de Usuario:** Script automatizado que aplica la migración, inserta fixtures de datos canónicos, valida tipos y revierte la migración en un entorno aislado.

#### [ ] T2.1.1 — Implementación del Esquema Físico y Constraints (Micro proceso)
- **Objetivo de la Tarea:** Definir las tablas/colecciones con sus llaves primarias, foráneas y checks de integridad.
- **Entregable:** Archivos de definición de tablas o modelos ORM.

> **🧠 Explicación:** [Explica la estrategia de persistencia. Ej: las migraciones son SQL/DDL **versionado** que se aplica en orden y de forma **idempotente** (`if not exists`) en cualquier entorno; los índices aceleran las consultas frecuentes y los `constraints` (PK/FK/CHECK) garantizan la integridad. Nunca se altera el esquema a mano en producción.]

> **💡 Cómo hacerlo (ejemplo):**
> ```sql
> -- Ejemplo de migración inicial (adaptar al motor: PostgreSQL, SQLite, etc.)
> create table if not exists entidades_core (
>   id          uuid primary key default gen_random_uuid(),
>   usuario_id  uuid not null references usuarios(id) on delete cascade,
>   codigo      text not null,
>   valor       numeric not null check (valor >= 0),
>   created_at  timestamptz default now(),
>   constraint uq_codigo unique (codigo)
> );
> create index if not exists idx_core_codigo on entidades_core (codigo);
> ```
> ```bash
> # Aplicar de forma reproducible (ej. con la CLI del ORM o psql)
> alembic upgrade head        # o: psql "$DATABASE_URL" -f migrations/0001_init.sql
> ```

- **AC de la Tarea:**
  - [ ] Los modelos mapean exactamente al diccionario de datos en `diseno_db.md`.
- **Tests de la Tarea:**
  - **Test Unitario:** Instanciar modelos y validar tipos.
  - **Test de Simulación de Usuario:** Simulación de inserciones con FK inválidas para validar que el motor de base de datos dispare el error de integridad correspondiente.

##### [ ] A2.1.1.1 — Generar la migración inicial del esquema (Mínimo por hacer)
- **Objetivo:** Crear el script de migración SQL o NoSQL para inicializar las tablas principales descritas en `diseno_db.md`.
- **Input:** Diccionario de datos y diagrama ERD en `docs/db/diseno_db.md`.
- **Output:** Archivo de migración (ej. `.sql` o script de ORM).
- **Proceso:**
  1. Escribir el script SQL DDL o generar la migración a través de la herramienta CLI del ORM (ej. `alembic revision --autogenerate`).
- **Tests:**
  - **Test Unitario:** Ejecución en seco (dry-run) del script DDL para validar sintaxis SQL.
  - **Test de Simulación de Usuario:** Aplicar la migración sobre una base de datos limpia de pruebas y verificar la existencia de las tablas mediante introspección.
- **AC:** Tablas creadas con tipos de datos y constraints coincidentes al 100% con `diseno_db.md`.
