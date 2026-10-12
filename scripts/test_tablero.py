#!/usr/bin/env python3
"""Self-check de las funciones puras de tablero.py. Asserts planos, sin pytest.
Run: python scripts/test_tablero.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tablero import (  # noqa: E402
    MARCA_FIN,
    MARCA_INICIO,
    MARCA_FASE_FIN,
    MARCA_FASE_INICIO,
    ORIGEN,
    PATRON_FASE,
    actualizar_rollup,
    ancla_de_titulo,
    bloque_markdown,
    copiar_a_worktree,
    entradas_de_las_fases,
    escribir_indice,
    nombre_de_archivo,
    partir,
    resolver_track,
    rutas,
    sincronizar,
    tracks,
    verificar_indice,
)


def _repo(tmp, plano=True, con_tracks=()):
    raiz = Path(tmp)
    (raiz / ".git").mkdir()
    if plano:
        (raiz / "docs" / "plan").mkdir(parents=True)
        (raiz / "docs" / "plan" / "plan_maestro.md").write_text("x", encoding="utf-8")
        (raiz / "docs" / "task" / "fases").mkdir(parents=True)
        (raiz / "docs" / "task" / "tareas.md").write_text("x", encoding="utf-8")
    for t in con_tracks:
        d = raiz / "docs" / "plan" / t
        d.mkdir(parents=True)
        (d / "plan_maestro.md").write_text("x", encoding="utf-8")
        (raiz / "docs" / "task" / t / "fases").mkdir(parents=True)
    return raiz


# --- Task 1: resolución de track y rutas ---------------------------------------

def test_layout_plano_no_tiene_tracks():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        assert tracks(raiz) == []
        assert resolver_track(raiz) is None
        r = rutas(raiz, None)
        assert r["plan"] == raiz / "docs" / "plan" / "plan_maestro.md"
        assert r["tablero"] == raiz / "docs" / "task" / "tareas.md"
        assert r["fases"] == raiz / "docs" / "task" / "fases"


def test_track_unico_se_resuelve_solo():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=False, con_tracks=["cartilla_1065"])
        assert tracks(raiz) == ["cartilla_1065"]
        assert resolver_track(raiz) == "cartilla_1065"
        r = rutas(raiz, "cartilla_1065")
        assert r["tablero"] == raiz / "docs" / "task" / "cartilla_1065" / "tareas.md"


def test_varios_tracks_sin_activo_es_error():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=False, con_tracks=["a", "b"])
        assert tracks(raiz) == ["a", "b"]
        try:
            resolver_track(raiz)
        except SystemExit as e:
            assert "a, b" in str(e)
        else:
            raise AssertionError("debió salir pidiendo /track")


def test_activo_persistido_gana():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=False, con_tracks=["a", "b"])
        (raiz / ".project-suite").mkdir()
        (raiz / ".project-suite" / "track").write_text("b\n", encoding="utf-8")
        assert resolver_track(raiz) == "b"


def test_activo_invalido_cae_al_unico():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=False, con_tracks=["a"])
        (raiz / ".project-suite").mkdir()
        (raiz / ".project-suite" / "track").write_text("no-existe\n", encoding="utf-8")
        assert resolver_track(raiz) == "a"


# --- Task 2: anclas, nombres de archivo e índice --------------------------------

def test_ancla_replica_las_reglas_de_github():
    assert ancla_de_titulo("SF0.1 — Entorno y Estructura") == "sf01--entorno-y-estructura"
    assert ancla_de_titulo("SF2.2 — Maduración flor→azul") == "sf22--maduración-florazul"


def test_nombre_de_archivo_usa_dos_digitos_y_cuatro_palabras():
    # Dos dígitos: sin eso F10 se ordena antes que F2 en el explorador.
    assert nombre_de_archivo("2", "", "Base de Datos y Persistencia") == "F02-base-datos-persistencia.md"
    # Las vacías se filtran en TODO el título, no solo al arranque.
    assert nombre_de_archivo("56", "", "Lo que el Proyecto Afirma de Sí Mismo") == "F56-proyecto-afirma-si-mismo.md"


def test_nombre_de_archivo_conserva_el_calificador():
    # F21 y F21 (reapertura) conviven: sin el calificador la segunda pisa a la primera.
    a = nombre_de_archivo("21", " ", "El Flujo se Mira y se Corre")
    b = nombre_de_archivo("21", " (reapertura) ", "El Diagrama es la Interfaz")
    assert a != b
    assert b.startswith("F21-reapertura-")


def test_indice_enlaza_fase_y_subfases_limpias_sin_enlace():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        (raiz / "docs" / "task" / "fases" / "F00-setup-tooling-base.md").write_text(
            "## [X] Fase 0 — Setup, Tooling e Infraestructura Base\n"
            "\n"
            "### [X] SF0.1 — Entorno y Estructura\n"
            "\n"
            "### [ ] SF0.2 — Calidad de Código\n",
            encoding="utf-8",
        )
        bloque = bloque_markdown(entradas_de_las_fases(raiz / "docs" / "task" / "fases"))
        # Fase con enlace al archivo
        assert "[**F0 — Setup, Tooling e Infraestructura Base**](fases/F00-setup-tooling-base.md)" in bloque
        # Subfases indentadas limpias sin enlace
        assert "  - [X] SF0.1 — Entorno y Estructura" in bloque
        assert "  - [ ] SF0.2 — Calidad de Código" in bloque
        assert "#sf01" not in bloque


def test_los_marcadores_no_son_genericos():
    # En six_week reusar `<!-- indice:inicio -->` inyectó el índice en la línea 20 468,
    # porque una Acción del propio tablero citaba esa cadena.
    assert "indice-tareas" in MARCA_INICIO and "indice-tareas" in MARCA_FIN


# --- Task 3: --indice y --verificar ---------------------------------------------

def _tablero_con_marcadores(raiz):
    (raiz / "docs" / "task" / "fases" / "F00-setup-tooling-base.md").write_text(
        "## [ ] Fase 0 — Setup, Tooling e Infraestructura Base\n\n### [ ] SF0.1 — Entorno\n",
        encoding="utf-8")
    (raiz / "docs" / "task" / "tareas.md").write_text(
        "# Listado de Tareas\n\n## Índice\n\n"
        "<!-- indice-tareas:inicio -->\n<!-- indice-tareas:fin -->\n\n## Otra sección\n",
        encoding="utf-8")


def test_escribir_indice_solo_toca_el_bloque_marcado():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _tablero_con_marcadores(raiz)
        assert escribir_indice(rutas(raiz, None)) is True
        texto = (raiz / "docs" / "task" / "tareas.md").read_text(encoding="utf-8")
        assert texto.startswith("# Listado de Tareas")
        assert texto.rstrip().endswith("## Otra sección")
        assert "fases/F00-setup-tooling-base.md" in texto
        assert texto.count(MARCA_INICIO) == 1


def test_verificar_detecta_indice_viejo_y_luego_verde():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _tablero_con_marcadores(raiz)
        assert verificar_indice(rutas(raiz, None)) is False
        escribir_indice(rutas(raiz, None))
        assert verificar_indice(rutas(raiz, None)) is True


def test_escribir_indice_es_idempotente():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _tablero_con_marcadores(raiz)
        escribir_indice(rutas(raiz, None))
        primero = (raiz / "docs" / "task" / "tareas.md").read_text(encoding="utf-8")
        assert escribir_indice(rutas(raiz, None)) is False
        assert (raiz / "docs" / "task" / "tareas.md").read_text(encoding="utf-8") == primero


# --- Task 4: --partir ------------------------------------------------------------

TABLERO_MONOLITICO = """# Listado de Tareas

## Índice de Fases y Sub fases

<!-- indice-tareas:inicio -->
<!-- indice-tareas:fin -->

---

## [X] Fase 0 — Setup y Tooling

### [X] SF0.1 — Entorno

Contenido cero.

## [ ] F21 (reapertura) — El Diagrama es la Interfaz

### [ ] SF21.1 — Lo que la pantalla dice

Contenido veintiuno.
"""


def test_partir_reparte_las_fases_y_deja_respaldo():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        (raiz / "docs" / "task" / "tareas.md").write_text(TABLERO_MONOLITICO, encoding="utf-8")
        creados = partir(rutas(raiz, None))
        assert len(creados) == 2, creados
        nombres = sorted(p.name for p in creados)
        assert nombres[0] == "F00-setup-tooling.md"
        assert nombres[1].startswith("F21-reapertura-")
        assert "Contenido veintiuno." in creados[1].read_text(encoding="utf-8")
        # El respaldo importa: la operación mueve miles de líneas y un error no se
        # nota hasta que alguien busca una Tarea que ya no está.
        assert (raiz / "docs" / "task" / "tareas.md.bak").exists()
        portada = (raiz / "docs" / "task" / "tareas.md").read_text(encoding="utf-8")
        assert "Contenido cero." not in portada
        assert "fases/F00-setup-tooling.md" in portada


def test_partir_no_pierde_ninguna_fase():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        (raiz / "docs" / "task" / "tareas.md").write_text(TABLERO_MONOLITICO, encoding="utf-8")
        esperadas = sum(1 for l in TABLERO_MONOLITICO.splitlines() if PATRON_FASE.match(l))
        assert len(partir(rutas(raiz, None))) == esperadas


# --- Task 5: --worktree y --sync --------------------------------------------------

def _con_fase(raiz):
    (raiz / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md").write_text(
        "## [ ] Fase 7 — App de Trazabilidad\n\n### [ ] SF7.1 — Registro\n", encoding="utf-8")
    (raiz / "docs" / "task" / "fases" / "F08-otra-fase-cualquiera.md").write_text(
        "## [ ] Fase 8 — Otra\n", encoding="utf-8")


def test_copiar_lleva_solo_la_fase_pedida():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas"
        wt.mkdir(parents=True)
        copiados = copiar_a_worktree(rutas(raiz, None), wt, "F07")
        assert (wt / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md").exists()
        # Una worktree que trabaja una Fase no debe cargar las otras.
        assert not (wt / "docs" / "task" / "fases" / "F08-otra-fase-cualquiera.md").exists()
        assert (wt / "docs" / "task" / "tareas.md").exists()
        assert (wt / "docs" / "plan" / "plan_maestro.md").exists()
        origen = json.loads((wt / ORIGEN).read_text(encoding="utf-8"))
        assert len(origen["archivos"]) == len(copiados)


def test_sync_devuelve_los_cambios_cuando_main_no_se_movio():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas"
        wt.mkdir(parents=True)
        copiar_a_worktree(rutas(raiz, None), wt, "F07")
        fase_wt = wt / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md"
        fase_wt.write_text(fase_wt.read_text(encoding="utf-8").replace("[ ] SF7.1", "[X] SF7.1"),
                           encoding="utf-8")
        aplicados, divergentes = sincronizar(wt, raiz)
        assert divergentes == []
        assert "[X] SF7.1" in (raiz / "docs" / "task" / "fases" /
                               "F07-app-trazabilidad-perillas.md").read_text(encoding="utf-8")


def test_sync_no_pisa_si_main_cambio():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas"
        wt.mkdir(parents=True)
        copiar_a_worktree(rutas(raiz, None), wt, "F07")
        fase_main = raiz / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md"
        fase_main.write_text("## [ ] Fase 7 — App de Trazabilidad\n\nEditado en main.\n",
                             encoding="utf-8")
        fase_wt = wt / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md"
        fase_wt.write_text("## [ ] Fase 7 — App de Trazabilidad\n\nEditado en la worktree.\n",
                           encoding="utf-8")
        aplicados, divergentes = sincronizar(wt, raiz)
        assert len(divergentes) == 1
        assert "Editado en main." in fase_main.read_text(encoding="utf-8")


def test_sync_segunda_corrida_no_reporta_falsa_divergencia():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas"
        wt.mkdir(parents=True)
        copiar_a_worktree(rutas(raiz, None), wt, "F07")
        fase_wt = wt / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md"
        fase_wt.write_text(fase_wt.read_text(encoding="utf-8") + "\nprimera vuelta\n", encoding="utf-8")
        sincronizar(wt, raiz)
        fase_wt.write_text(fase_wt.read_text(encoding="utf-8") + "segunda vuelta\n", encoding="utf-8")
        aplicados, divergentes = sincronizar(wt, raiz)
        assert divergentes == []
        assert "segunda vuelta" in (raiz / "docs" / "task" / "fases" /
                                    "F07-app-trazabilidad-perillas.md").read_text(encoding="utf-8")


def test_actualizar_rollup_acciones_a_tarea_y_subfase_y_fase():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        fase_p = raiz / "docs" / "task" / "fases" / "F01-prueba-rollup.md"
        fase_p.write_text(
            "## [ ] Fase 1 — Setup Base\n\n"
            "### [ ] SF1.1 — Subfase A\n\n"
            "#### [ ] T1.1.1 — Tarea 1\n"
            "  - [X] A1.1.1.1 — Paso uno\n"
            "  - [X] A1.1.1.2 — Paso dos\n\n"
            "#### [ ] T1.1.2 — Tarea 2\n"
            "  - [X] A1.1.2.1 — Paso unico\n\n"
            "### [ ] SF1.2 — Subfase B\n\n"
            "#### [ ] T1.2.1 — Tarea 3\n"
            "  - [ ] A1.2.1.1 — Pendiente\n",
            encoding="utf-8",
        )
        cambio = actualizar_rollup(fase_p)
        assert cambio is True
        contenido = fase_p.read_text(encoding="utf-8")
        # T1.1.1 con todas sus acciones [X] pasa a [X]
        assert "#### [X] T1.1.1 — Tarea 1" in contenido
        # T1.1.2 con su accion [X] pasa a [X]
        assert "#### [X] T1.1.2 — Tarea 2" in contenido
        # SF1.1 con todas sus tareas [X] pasa a [X]
        assert "### [X] SF1.1 — Subfase A" in contenido
        # SF1.2 con tarea pendiente permanece [ ]
        assert "### [ ] SF1.2 — Subfase B" in contenido
        # Fase 1 con SF1.1 [X] y SF1.2 [ ] pasa a progreso [/]
        assert "## [/] Fase 1 — Setup Base" in contenido
        # Genera el bloque de indice de la Fase
        assert MARCA_FASE_INICIO in contenido
        assert "- [X] SF1.1 — Subfase A" in contenido
        assert "  - [X] T1.1.1 — Tarea 1" in contenido


def test_copiar_worktree_con_subfase_y_scope():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas-sf7-1"
        wt.mkdir(parents=True)
        copiados = copiar_a_worktree(rutas(raiz, None), wt, "SF7.1")
        assert (wt / "docs" / "task" / "fases" / "F07-app-trazabilidad-perillas.md").exists()
        assert not (wt / "docs" / "task" / "fases" / "F08-otra-fase-cualquiera.md").exists()
        origen = json.loads((wt / ORIGEN).read_text(encoding="utf-8"))
        assert origen["scope"]["subfase"] == "SF7.1"
        assert origen["scope"]["fase"] == "F07"


def test_sincronizar_bloquea_fases_fuera_de_scope():
    with tempfile.TemporaryDirectory() as tmp:
        raiz = _repo(tmp, plano=True)
        _con_fase(raiz)
        wt = raiz / ".claude" / "worktrees" / "F07-app-trazabilidad-perillas-sf7-1"
        wt.mkdir(parents=True)
        copiar_a_worktree(rutas(raiz, None), wt, "SF7.1")
        # Simular que en la worktree se creó/modificó un archivo de otra Fase
        otra_fase = wt / "docs" / "task" / "fases" / "F08-fase-no-autorizada.md"
        otra_fase.write_text("## [ ] Fase 8", encoding="utf-8")
        try:
            sincronizar(wt, raiz)
            assert False, "debe fallar con SystemExit por violacion de scope"
        except SystemExit as e:
            assert "CAMBIO BLOQUEADO" in str(e)


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if nombre.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok  {nombre}")
            except AssertionError as e:
                fallos += 1
                print(f"FAIL  {nombre}: {e}")
    print("OK" if not fallos else f"{fallos} fallo(s)")
    sys.exit(1 if fallos else 0)
