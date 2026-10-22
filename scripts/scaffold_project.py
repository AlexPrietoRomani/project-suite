"""
Archivo: scaffold_project.py
Fecha de modificación: 22/10/2026
Autor: Antigravity

Descripción:
Compilador y generador determinista de scaffolding para proyectos spec-driven.
Crea la estructura física de directorios (docs/, .project-suite/), copia e interpola
las 7 plantillas documentales canónicas, genera los archivos de reglas operativas
(CLAUDE.md y/o AGENTS.md), configura .gitignore con base en el stack técnico y la
política de versionado de artefactos de trabajo, y compila los visores HTML interactivos
compañeros (architecture.html, diseno_db.html) e índices de bitácora y tablero.

Acciones Principales:
    - `copy_doc_templates`: Crea carpetas canónicas e instancia las 7 plantillas Markdown.
    - `render_rules_files`: Genera CLAUDE.md y/o AGENTS.md sustituyendo metadatos de autoría.
    - `build_gitignore_content`: Ensambla reglas .gitignore para stack y artefactos locales.
    - `scaffold_project`: Orquestador integral de inicialización y compilación de companions.
    - `build_argument_parser`: Parser de interfaz de línea de comandos (CLI).
    - `main`: Punto de entrada CLI con soporte de salida en texto o JSON estructurado.

Estructura Interna:
    - Constantes: `REQUIRED_DIRECTORIES`, `TEMPLATE_MAPPING`, `STACK_IGNORES`, `WORKING_FILES_IGNORES`.
    - Funciones de generación: `build_gitignore_content`, `render_rules_files`, `copy_doc_templates`.
    - Función orquestadora: `scaffold_project`.
    - CLI: `build_argument_parser`, `main`.

Entradas / Dependencias:
    - Plantillas Markdown en `templates/` y `templates/generated/rules-body.tmpl.md`.
    - Plantillas HTML de visores en `templates/html/`.
    - Módulos auxiliares: `render_db_html`, `render_arch_html`, `log_index`, `tablero`.
    - Biblioteca estándar de Python: `argparse`, `json`, `pathlib`, `re`, `sys`, `typing`.

Salidas / Efectos:
    - Estructura `docs/` poblada con las 7 especificaciones iniciales.
    - Archivos de reglas `CLAUDE.md` y/o `AGENTS.md`.
    - Archivo de configuración de disciplina `.project-suite/mode`.
    - Archivo de exclusiones `.gitignore`.
    - Visores HTML interactivos `diseno_db.html` y `architecture.html`.
    - Sincronización de índices en `docs/logs/log.md` y `docs/task/tareas.md`.

Ejecución:
    python scripts/scaffold_project.py --target <dir> --name <nombre> [opciones]

Ejemplo de Uso:
    python scripts/scaffold_project.py --target ./mi-sistema --name "MiSistema" --lang es --stack python,astro
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

# Raíz canónica del plugin project-suite
ROOT = Path(__file__).resolve().parent.parent

# Asegurar disponibilidad de scripts hermanos en sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import log_index  # noqa: E402
import render_arch_html  # noqa: E402
import render_db_html  # noqa: E402
import tablero  # noqa: E402


REQUIRED_DIRECTORIES: tuple[str, ...] = (
    "docs",
    "docs/architecture",
    "docs/db",
    "docs/plan",
    "docs/task/fases",
    "docs/logs",
    ".project-suite",
)

TEMPLATE_MAPPING: dict[str, str] = {
    "plantilla_description_proyecto.md": "description_proyecto.md",
    "plantilla_architecture.md": "architecture/architecture.md",
    "plantilla_db.md": "db/diseno_db.md",
    "plantilla_plan.md": "plan/plan_maestro.md",
    "plantilla_tareas.md": "task/tareas.md",
    "plantilla_ejecucion.md": "ejecucion.md",
    "plantilla_log.md": "logs/log.md",
}

STACK_IGNORES: dict[str, list[str]] = {
    "python": [
        "# Python",
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        ".venv/",
        "venv/",
        "env/",
        "dist/",
        "build/",
        "*.egg-info/",
        ".pytest_cache/",
        ".coverage",
        "htmlcov/",
    ],
    "node": [
        "# Node / TypeScript / Astro",
        "node_modules/",
        "dist/",
        ".next/",
        ".expo/",
        ".astro/",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
        ".pnpm-debug.log*",
    ],
    "r": [
        "# R",
        ".Rhistory",
        ".RData",
        ".Ruserdata",
        "*-Ex.R",
        "/*.tar.gz",
    ],
    "rust": [
        "# Rust",
        "target/",
        "**/*.rs.bk",
    ],
}

WORKING_FILES_IGNORES: list[str] = [
    "# Archivos de trabajo locales (project-suite)",
    "docs/task/",
    "docs/plan/",
    "docs/logs/",
    "CLAUDE.md",
    "AGENTS.md",
    ".project-suite/",
]

BASE_IGNORES: list[str] = [
    "# Entorno y secretos",
    ".env",
    ".env.local",
    ".env.*.local",
]


def _normalize_stack_name(name: str) -> str | None:
    """
    Normaliza el nombre o alias de una tecnología a la clave canónica del stack.

    Args:
        name (str): Nombre o alias ingresado para el stack técnico.

    Returns:
        str | None: Clave canónica ('python', 'node', 'r', 'rust') o None si no coincide.
    """
    cleaned = name.strip().lower()
    if cleaned in ("python", "py"):
        return "python"
    if cleaned in ("node", "ts", "typescript", "astro", "js", "javascript"):
        return "node"
    if cleaned in ("r", "rmd"):
        return "r"
    if cleaned in ("rust", "rs"):
        return "rust"
    return None


def build_gitignore_content(
    stack: list[str] | None = None,
    version_work: str = "no",
) -> str:
    """
    Construye el contenido determinista para el archivo .gitignore.

    Args:
        stack (list[str] | None, opcional): Lista de stacks detectados o seleccionados.
        version_work (str, opcional): Política de versionado de archivos de trabajo ('no' o 'yes').

    Returns:
        str: Contenido formateado de reglas .gitignore.
    """
    sections: list[list[str]] = []

    # Bloque base inmutable de variables de entorno
    sections.append(BASE_IGNORES)

    # Identificación y desduplicación de tecnologías de stack
    matched_stacks: set[str] = set()
    if stack:
        for item in stack:
            # Soporta tanto elementos separados por coma como elementos individuales
            for sub_item in item.split(","):
                norm = _normalize_stack_name(sub_item)
                if norm:
                    matched_stacks.add(norm)

    # Orden canónico de inclusión de stacks
    for key in ("python", "node", "r", "rust"):
        if key in matched_stacks and key in STACK_IGNORES:
            sections.append(STACK_IGNORES[key])

    # Inclusión condicional de archivos de trabajo locales si no se versionan
    is_versioned = version_work.strip().lower() in ("yes", "true", "1")
    if not is_versioned:
        sections.append(WORKING_FILES_IGNORES)

    # Enlace de bloques con doble salto de línea
    rendered_blocks = ["\n".join(sec) for sec in sections]
    return "\n\n".join(rendered_blocks).strip() + "\n"


def render_rules_files(
    target_dir: Path,
    project_name: str,
    doc_lang: str = "es",
    rules_target: str = "both",
    author_name: str = "Developer",
    author_email: str = "dev@example.com",
    coauthor_policy: str = "active_model",
    plugin_root: Path = ROOT,
) -> list[Path]:
    """
    Genera los archivos de reglas operativas CLAUDE.md y/o AGENTS.md.

    Args:
        target_dir (Path): Directorio raíz del proyecto destino.
        project_name (str): Nombre representativo del proyecto.
        doc_lang (str, opcional): Idioma principal de documentación ('es' o 'en').
        rules_target (str, opcional): Destino de las reglas ('both', 'claude', 'agents').
        author_name (str, opcional): Nombre del autor principal.
        author_email (str, opcional): Correo electrónico del autor.
        coauthor_policy (str, opcional): Política de coautoría para LLM.
        plugin_root (Path, opcional): Raíz del plugin donde residen las plantillas.

    Returns:
        list[Path]: Rutas absolutas o relativas de los archivos de reglas generados.

    Raises:
        FileNotFoundError: Si no se encuentra rules-body.tmpl.md.
        ValueError: Si el destino `rules_target` no es reconocido.
    """
    template_path = plugin_root / "templates" / "generated" / "rules-body.tmpl.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Plantilla de reglas no encontrada en: {template_path}")

    body_tmpl = template_path.read_text(encoding="utf-8")

    # Sustitución de marcadores de posición canónicos
    body = (
        body_tmpl.replace("{{PROJECT_NAME}}", project_name)
        .replace("{{DOC_LANG}}", doc_lang)
        .replace("{{AUTHOR_NAME}}", author_name)
        .replace("{{AUTHOR_EMAIL}}", author_email)
        .replace("{{COAUTHOR_POLICY}}", coauthor_policy)
    )

    norm_target = rules_target.strip().lower()
    if norm_target not in ("both", "claude", "agents"):
        raise ValueError(
            f"rules_target no reconocido: {rules_target}. Use 'both', 'claude' o 'agents'."
        )

    created_paths: list[Path] = []
    target_dir.mkdir(parents=True, exist_ok=True)

    # Generación de CLAUDE.md según especificación de commands/init.md
    if norm_target in ("both", "claude"):
        claude_content = (
            f"# {project_name} — Agent operating rules (Claude Code)\n\n"
            f"> Spec-driven project. Docs are the source of truth. Doc language: {doc_lang}.\n\n"
            f"{body}"
        )
        claude_file = target_dir / "CLAUDE.md"
        claude_file.write_text(claude_content, encoding="utf-8")
        created_paths.append(claude_file)

    # Generación de AGENTS.md según especificación de commands/init.md
    if norm_target in ("both", "agents"):
        agents_content = (
            f"# {project_name} — Agent operating rules (opencode / AGENTS.md standard)\n\n"
            f"> Spec-driven project. Docs are the source of truth. Doc language: {doc_lang}.\n\n"
            f"{body}"
        )
        agents_file = target_dir / "AGENTS.md"
        agents_file.write_text(agents_content, encoding="utf-8")
        created_paths.append(agents_file)

    return created_paths


def copy_doc_templates(
    target_dir: Path,
    project_name: str,
    plugin_root: Path = ROOT,
    overwrite: bool = False,
) -> list[Path]:
    """
    Crea la estructura de carpetas y copia las 7 plantillas base de documentación.

    Args:
        target_dir (Path): Directorio destino del proyecto.
        project_name (str): Nombre del proyecto para sustituir en los títulos.
        plugin_root (Path, opcional): Raíz del plugin project-suite.
        overwrite (bool, opcional): Si es True sobrescribe archivos existentes.

    Returns:
        list[Path]: Lista de rutas de los archivos de plantilla creados o preservados.

    Raises:
        FileNotFoundError: Si alguna de las plantillas de origen no existe.
    """
    # Materialización previa de todas las carpetas requeridas
    for rel_dir in REQUIRED_DIRECTORIES:
        (target_dir / rel_dir).mkdir(parents=True, exist_ok=True)

    templates_dir = plugin_root / "templates"
    created_paths: list[Path] = []

    for tmpl_name, rel_dest in TEMPLATE_MAPPING.items():
        src_path = templates_dir / tmpl_name
        if not src_path.exists():
            raise FileNotFoundError(f"Plantilla documental requerida no encontrada: {src_path}")

        dest_path = target_dir / "docs" / rel_dest
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists() and not overwrite:
            # Preserva el archivo existente si no se solicitó sobrescritura
            created_paths.append(dest_path)
            continue

        raw_content = src_path.read_text(encoding="utf-8")
        # Sustituye marcador genérico de nombre del proyecto en títulos y cuerpo
        interpolated = re.sub(r"\[Nombre del [Pp]royecto\]", project_name, raw_content)
        interpolated = re.sub(r"\(app_estaciones_chile\)", f"({project_name})", interpolated)
        dest_path.write_text(interpolated, encoding="utf-8")
        created_paths.append(dest_path)

    return created_paths


def scaffold_project(
    target_dir: Path,
    project_name: str,
    doc_lang: str = "es",
    rules_target: str = "both",
    author_name: str = "Developer",
    author_email: str = "dev@example.com",
    coauthor_policy: str = "active_model",
    version_work: str = "no",
    stack: list[str] | None = None,
    mode: str = "estricto",
    compile_companions: bool = True,
    overwrite: bool = False,
    plugin_root: Path = ROOT,
) -> dict[str, Any]:
    """
    Orquesta el scaffolding determinista completo de un proyecto spec-driven.

    Args:
        target_dir (Path): Directorio raíz destino donde se creará el proyecto.
        project_name (str): Nombre del proyecto.
        doc_lang (str, opcional): Idioma de documentación ('es' o 'en').
        rules_target (str, opcional): Archivos de reglas ('both', 'claude', 'agents').
        author_name (str, opcional): Nombre del autor principal.
        author_email (str, opcional): Correo del autor principal.
        coauthor_policy (str, opcional): Política de coautoría para LLM.
        version_work (str, opcional): Si versiona archivos de trabajo ('no' o 'yes').
        stack (list[str] | None, opcional): Lista de tecnologías base del proyecto.
        mode (str, opcional): Modo inicial de disciplina ('estricto', 'relajado', 'off').
        compile_companions (bool, opcional): Si compila visores HTML e índices.
        overwrite (bool, opcional): Si sobrescribe archivos existentes.
        plugin_root (Path, opcional): Raíz del plugin project-suite.

    Returns:
        dict[str, Any]: Resumen estructurado de todos los artefactos creados.
    """
    resolved_target = Path(target_dir).resolve()
    resolved_target.mkdir(parents=True, exist_ok=True)

    # 1. Copia de plantillas documentales base
    docs_created = copy_doc_templates(
        target_dir=resolved_target,
        project_name=project_name,
        plugin_root=plugin_root,
        overwrite=overwrite,
    )

    # 2. Generación de archivos de reglas operativas
    rules_created = render_rules_files(
        target_dir=resolved_target,
        project_name=project_name,
        doc_lang=doc_lang,
        rules_target=rules_target,
        author_name=author_name,
        author_email=author_email,
        coauthor_policy=coauthor_policy,
        plugin_root=plugin_root,
    )

    # 3. Escritura del modo de disciplina inicial en .project-suite/mode
    mode_dir = resolved_target / ".project-suite"
    mode_dir.mkdir(parents=True, exist_ok=True)
    mode_file = mode_dir / "mode"
    mode_file.write_text(f"{mode.strip()}\n", encoding="utf-8")

    # 4. Creación o actualización de .gitignore
    gitignore_file = resolved_target / ".gitignore"
    desired_gitignore = build_gitignore_content(stack=stack, version_work=version_work)
    if gitignore_file.exists() and not overwrite:
        existing_lines = gitignore_file.read_text(encoding="utf-8").splitlines()
        existing_set = set(line.strip() for line in existing_lines if line.strip())
        new_lines_to_add: list[str] = []
        for line in desired_gitignore.splitlines():
            stripped = line.strip()
            # Conservar encabezados y agregar únicamente reglas inexistentes
            if stripped.startswith("#") or (stripped and stripped not in existing_set):
                new_lines_to_add.append(line)
        if new_lines_to_add:
            merged_content = (
                "\n".join(existing_lines).rstrip()
                + "\n\n"
                + "\n".join(new_lines_to_add).strip()
                + "\n"
            )
            gitignore_file.write_text(merged_content, encoding="utf-8")
    else:
        gitignore_file.write_text(desired_gitignore, encoding="utf-8")

    # 5. Compilación determinista de visores HTML compañeros e índices
    companions_created: list[Path] = []
    if compile_companions:
        # Compilación de visor diseno_db.html
        db_md_file = resolved_target / "docs" / "db" / "diseno_db.md"
        db_html_file = resolved_target / "docs" / "db" / "diseno_db.html"
        db_template = plugin_root / "templates" / "html" / "db_viewer.html"
        if db_md_file.exists() and db_template.exists():
            db_content = db_md_file.read_text(encoding="utf-8")
            db_data = render_db_html.parse_db_markdown(db_content)
            db_data["title"] = f"Diseño de Base de Datos — {project_name}"
            db_sha = render_db_html.compute_content_hash(db_content)
            rendered_db = render_db_html.render_html(db_data, db_sha, template_path=db_template)
            db_html_file.write_text(rendered_db, encoding="utf-8")
            companions_created.append(db_html_file)

        # Compilación de visor architecture.html
        arch_md_file = resolved_target / "docs" / "architecture" / "architecture.md"
        arch_html_file = resolved_target / "docs" / "architecture" / "architecture.html"
        arch_template = plugin_root / "templates" / "html" / "arch_viewer.html"
        if arch_md_file.exists() and arch_template.exists():
            rendered_arch, _ = render_arch_html.compile_architecture_to_html(
                arch_md_file, arch_template
            )
            arch_html_file.write_text(rendered_arch, encoding="utf-8")
            companions_created.append(arch_html_file)

        # Sincronización del índice de lecciones transferibles en log.md
        log_md_file = resolved_target / "docs" / "logs" / "log.md"
        if log_md_file.exists():
            log_index.update_log_index(log_md_file, check_only=False)

        # Inicialización del índice de tablero en tareas.md para sincronía inmediata
        plan_file = resolved_target / "docs" / "plan" / "plan_maestro.md"
        tablero_file = resolved_target / "docs" / "task" / "tareas.md"
        fases_dir = resolved_target / "docs" / "task" / "fases"
        if tablero_file.exists():
            tablero_context = {
                "raiz": resolved_target,
                "track": None,
                "plan": plan_file,
                "tablero": tablero_file,
                "fases": fases_dir,
            }
            tablero.escribir_indice(tablero_context)

    return {
        "target_dir": str(resolved_target),
        "project_name": project_name,
        "doc_lang": doc_lang,
        "rules_target": rules_target,
        "docs": [str(p) for p in docs_created],
        "rules": [str(p) for p in rules_created],
        "mode_file": str(mode_file),
        "gitignore": str(gitignore_file),
        "companions": [str(p) for p in companions_created],
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Construye el analizador de argumentos de línea de comandos.

    Returns:
        argparse.ArgumentParser: Parser configurado para CLI.
    """
    parser = argparse.ArgumentParser(
        description="Scaffolder determinista para proyectos spec-driven de project-suite."
    )
    parser.add_argument(
        "--target",
        "-t",
        default=".",
        help="Directorio destino del scaffolding (por defecto: directorio actual).",
    )
    parser.add_argument(
        "--name",
        "-n",
        default=None,
        help="Nombre representativo del proyecto (por defecto: nombre del directorio destino).",
    )
    parser.add_argument(
        "--lang",
        "-l",
        choices=["es", "en"],
        default="es",
        help="Idioma de la documentación técnica (por defecto: es).",
    )
    parser.add_argument(
        "--rules",
        "-r",
        choices=["both", "claude", "agents"],
        default="both",
        help="Archivos de reglas operativas a generar (por defecto: both).",
    )
    parser.add_argument(
        "--author-name",
        default="Developer",
        help="Nombre del autor para documentación y commits (por defecto: Developer).",
    )
    parser.add_argument(
        "--author-email",
        default="dev@example.com",
        help="Correo electrónico del autor (por defecto: dev@example.com).",
    )
    parser.add_argument(
        "--coauthor-policy",
        default="active_model",
        help="Política de coautoría para el LLM (por defecto: active_model).",
    )
    parser.add_argument(
        "--version-work",
        choices=["no", "yes"],
        default="no",
        help="Si se versionan archivos de trabajo locales en git (por defecto: no).",
    )
    parser.add_argument(
        "--stack",
        "-s",
        default=None,
        help="Tecnologías del stack separadas por coma (ej. python,astro,rust).",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["estricto", "relajado", "off"],
        default="estricto",
        help="Modo de recordatorio disciplinario inicial (por defecto: estricto).",
    )
    parser.add_argument(
        "--no-companions",
        action="store_true",
        help="Omite la compilación inicial de visores HTML compañeros e índices.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe archivos preexistentes en el destino.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el resultado estructurado en formato JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Punto de entrada de línea de comandos para el scaffolding de proyectos.

    Args:
        argv (list[str] | None, opcional): Lista de argumentos pasados al CLI.

    Returns:
        int: Código de salida (0 para éxito, 1 para error).
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    target_path = Path(args.target).resolve()
    project_name = args.name or target_path.name
    if not project_name or project_name == ".":
        project_name = "Proyecto"

    stack_list: list[str] = []
    if args.stack:
        stack_list = [item.strip() for item in args.stack.split(",") if item.strip()]

    try:
        result = scaffold_project(
            target_dir=target_path,
            project_name=project_name,
            doc_lang=args.lang,
            rules_target=args.rules,
            author_name=args.author_name,
            author_email=args.author_email,
            coauthor_policy=args.coauthor_policy,
            version_work=args.version_work,
            stack=stack_list,
            mode=args.mode,
            compile_companions=not args.no_companions,
            overwrite=args.overwrite,
            plugin_root=ROOT,
        )

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Scaffolding completado exitosamente en: {target_path}")
            print(f"- Proyecto: {project_name} (idioma: {args.lang})")
            print(f"- Documentos base creados: {len(result['docs'])}")
            print(f"- Reglas generadas: {', '.join(Path(p).name for p in result['rules'])}")
            print(f"- Visores HTML y compañeros: {len(result['companions'])}")
            print(f"- Modo configurado: {args.mode}")
        return 0
    except Exception as exc:
        print(f"Error durante el scaffolding del proyecto: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
