---
name: rust-standards
description: Reglas exhaustivas de arquitectura, nomenclatura y documentación para Rust. CARGA ESTA HABILIDAD SIEMPRE que vayas a crear, editar o analizar archivos .rs o el Cargo.toml/Cargo.lock de un crate o workspace.
when_to_use: Al generar código Rust, refactorizar archivos .rs, realizar revisiones de código de crates, o estructurar módulos, manejo de errores, tests y documentación con rustdoc.
allowed-tools: Read Grep Glob
---

# Estándares de Arquitectura y Código Rust

Como agente de IA, DEBES cumplir estrictamente estas normativas de calidad (basadas en las **Rust API Guidelines**, `rustfmt` y `clippy`) al trabajar con archivos Rust (`.rs`) y con `Cargo.toml`.

## 1. Reglas Generales e Idioma Mixto
- **Código en Inglés:** Identificadores (variables, funciones, structs, enums, traits, módulos, constantes) DEBEN estar estrictamente en inglés. No uses abreviaturas crípticas (ej. usa `filtered_records`, NO `fr`).
- **Documentación en Español:** Todos los comentarios internos (`//`) y los doc comments (`///`, `//!`) DEBEN redactarse en español.
- **Tiempos Verbales:** Documenta siempre en **presente activo** (ej. "Esta función calcula...", NO "Se calculó...").

## 2. Nomenclatura Estricta (Rust API Guidelines)
- **Variables, Funciones y Métodos:** `snake_case` (ej. `image_processor`, `calculate_metrics()`). Las funciones, idealmente verbos.
- **Structs, Enums y Traits:** `UpperCamelCase` (ej. `DatabaseAuditor`, `VisionTransformer`, `Serialize`).
- **Constantes y `static`:** `UPPER_SNAKE_CASE` (ej. `MAX_RETRIES`, `DEFAULT_THRESHOLD`). Evita números mágicos hardcodeados.
- **Módulos, crates y archivos:** `snake_case` (ej. `mod image_io;` en `image_io.rs`). El nombre del archivo describe su contenido.
- **Variantes de enum y macros:** variantes en `UpperCamelCase`; macros declarativas en `snake_case!`. Los genéricos usan mayúsculas cortas (`T`, `K`, `V`).

## 3. Estructura de Crate / Workspace y Modularidad
Todo crate nuevo o modificado sigue una organización top-down y de responsabilidad única.

- **Layout del crate:** binario en `src/main.rs`, librería en `src/lib.rs`. La lógica reutilizable vive en la librería; el binario solo orquesta (`fn main()` delgado que llama a la API pública de `lib.rs`).
- **Módulos:** un submódulo por responsabilidad lógica, declarado con `mod nombre;` y definido en `src/nombre.rs` o `src/nombre/mod.rs` (o el estilo 2018: `src/nombre.rs` + carpeta `src/nombre/`). Expón la API pública explícitamente con `pub`/`pub(crate)`; mantén privado por defecto.
- **Workspaces:** para proyectos multi-crate usa un `Cargo.toml` raíz con `[workspace]` y `members = [...]`; comparte versiones vía `[workspace.dependencies]` para evitar divergencias. Un crate por dominio (ej. `core`, `cli`, `api`).
- **Orden top-down dentro de un `.rs`:** (1) `//!` doc comment de módulo/crate, (2) `use` agrupados y ordenados (std, luego crates de terceros, luego `crate::`/`super::`, separados por una línea en blanco), (3) constantes y `static`, (4) `struct`/`enum`/`trait` y sus `impl`, (5) funciones. Descompón toda función que asuma múltiples responsabilidades (lectura + transformación + persistencia) en funciones atómicas.
- **Cargo.toml:** dependencias con versiones acotadas; features mínimas necesarias (`default-features = false` cuando aplique). No dejes dependencias sin usar.

## 4. Manejo de Errores (`Result` y `?`)
- **Nada de `unwrap()`/`expect()` en código de producción:** reserva `unwrap`/`expect` para tests, prototipos o invariantes realmente imposibles (y ahí documenta el porqué en el `expect("...")`). En rutas normales, propaga con el operador `?`.
- **Tipo de retorno:** las funciones falibles devuelven `Result<T, E>`; usa `Option<T>` solo para ausencia legítima de valor, no para errores.
- **Errores propios:** define un enum de error por dominio (ej. con `thiserror` para librerías) e implementa `std::error::Error` + `Display`; en binarios/CLI usa `anyhow::Result` para agregación ergonómica. `panic!` solo ante estados irrecuperables o bugs de lógica, nunca para entrada inválida esperable.
- **Conversión:** implementa `From` para encadenar errores con `?`; evita `.map_err` verboso cuando `#[from]` (thiserror) o `From` resuelve la conversión.

## 5. Comentarios y Documentación (rustdoc)
- **El Porqué, no el Qué (`//`):** el código limpio se explica solo. Usa comentarios inline solo para decisiones técnicas complejas, fundamentos matemáticos o *workarounds* temporales.
  - **Mala práctica:** `x += 1; // Incrementa x en 1` (explica el qué).
  - **Buena práctica:** `std::thread::sleep(d); // Pausa necesaria para no exceder el rate-limit de la API` (explica el porqué).
- **Doc comments obligatorios:** todo elemento público (`pub fn`, `pub struct`, `pub trait`, `pub enum`, módulos expuestos) lleva `///` inmediatamente encima; el crate/módulo lleva `//!` al inicio del archivo. Redacción en español, presente activo.
- **Plantilla de doc comment para funciones públicas:**

```rust
/// Extrae la latitud, longitud y precisión de los metadatos EXIF de una imagen.
///
/// # Arguments
/// * `image_path` - Ruta al archivo de imagen.
/// * `confidence` - Umbral mínimo de confianza (0.0–1.0).
///
/// # Returns
/// `Ok(SpatialMetadata)` con la posición; `Err(MetadataError)` si no hay datos espaciales.
///
/// # Errors
/// Devuelve `MetadataError::NotFound` si el archivo no existe o carece de EXIF.
///
/// # Examples
/// ```
/// let meta = extract_spatial_metadata("foto.jpg", 0.8)?;
/// assert!(meta.latitude.is_finite());
/// ```
pub fn extract_spatial_metadata(image_path: &str, confidence: f64) -> Result<SpatialMetadata, MetadataError> {
    // ...
}
```

- **Ejemplos ejecutables:** los bloques ```` ```rust ```` de los doc comments se compilan y corren con `cargo test`; manténlos válidos. Documenta las secciones `# Panics`, `# Errors` y `# Safety` (esta última obligatoria en todo `unsafe fn`) cuando apliquen.

## 6. Tests (`#[cfg(test)]` + `tests/`)
- **Tests unitarios:** en el mismo archivo del código, dentro de un módulo `#[cfg(test)] mod tests { use super::*; ... }`, con funciones `#[test]`. Prueban lógica interna y detalles privados.
- **Tests de integración:** en el directorio `tests/` en la raíz del crate (cada archivo es su propio crate y solo ve la API pública). Prueban el comportamiento observable del crate como caja negra.
- **Doc-tests:** los `# Examples` sirven como tests vivos de la API pública; cuéntalos como parte de la cobertura.
- **Regla:** todo `pub` con lógica no trivial tiene al menos un test; los asserts se basan en Golden Data real, nunca en valores inventados. Usa `assert_eq!`/`assert!` con mensajes claros.

## 7. Toolchain, Lints y Edición
- **Formato:** `cargo fmt` (rustfmt) es la única fuente de verdad de estilo; el código se commitea ya formateado, sin diffs de formato pendientes.
- **Lints:** `cargo clippy` debe pasar **sin warnings**. Trata los warnings de clippy como errores en el gate de calidad (ej. `#![deny(clippy::all)]` o `cargo clippy -- -D warnings` en CI). No silencies lints con `#[allow(...)]` sin justificar el porqué en un comentario.
- **Edición pinada:** fija la `edition` explícitamente en `Cargo.toml` (ej. `edition = "2021"`); no dependas del default implícito. Fija también `rust-version` (MSRV) cuando el crate tenga consumidores.
- **`unsafe`:** evítalo salvo necesidad real; si aparece, aíslalo, documenta el invariante en `// SAFETY:` y en el doc comment `# Safety`, y minimiza su superficie.

## 8. Integración con project-suite
- Este estándar se aplica automáticamente a archivos `.rs` durante la construcción por subagentes (ver la skill `construir`); cada Tarea que toque Rust DEBE cumplirlo antes de pasar el gate `verificar-dod`.
- Los tests obligatorios (unitario + simulación de usuario) declarados en `docs/plan/plan_maestro.md` y `docs/task/tareas.md` se materializan y corren con la skill `testear` usando `cargo test` como runner.
