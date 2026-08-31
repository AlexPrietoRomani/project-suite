#!/usr/bin/env python3
"""Herramienta del tablero de project-suite: resuelve las rutas del track activo,
mantiene el indice de un tablero partido en un archivo por Fase, y lleva/trae esos
documentos --que estan gitignorados-- entre el repo principal y una worktree.

Run: python scripts/tablero.py --indice | --verificar | --partir | --worktree FNN | --sync
Stdlib only.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ARCHIVO_TRACK = Path(".project-suite") / "track"
ORIGEN = ".project-suite-origen.json"

#: Los marcadores llevan `-tareas` a proposito y NO son genericos: un tablero habla de
#: sus propias herramientas, asi que su marcador tiene que ser distinto de cualquier
#: cadena citable adentro. Se buscan anclados a inicio de linea, segundo candado.
MARCA_INICIO = "<!-- indice-tareas:inicio -->"
MARCA_FIN = "<!-- indice-tareas:fin -->"

#: El calificador entre el numero y el guion no es opcional: `F21` y `F21 (reapertura)`
#: pueden convivir, y sin capturarlo la segunda Fase no casa y su contenido desaparece
#: del corte sin que nada falle.
PATRON_FASE = re.compile(r"^## \[([ X/])\] (?:Fase |F)(\d+)([^—]*)— (.+)$")
PATRON_SUBFASE = re.compile(r"^### \[([ X/])\] (SF\d+\.\d+) — (.+)$")

VACIAS = {"el", "la", "lo", "los", "las", "un", "una", "unos", "unas", "de", "del",
          "y", "o", "a", "en", "con", "por", "para", "que", "se", "su", "sus", "al",
          "es", "the", "of", "and", "to", "in", "for"}


# --- Track y rutas ---------------------------------------------------------------

def raiz_repo(inicio: Path = None) -> Path:
    """Sube desde `inicio` hasta el directorio que contiene .git."""
    d = (inicio or Path.cwd()).resolve()
    for cand in [d, *d.parents]:
        if (cand / ".git").exists():
            return cand
    return d


def tracks(raiz: Path) -> list:
    """Los tracks del repo: directorios bajo docs/plan/ que contienen plan_maestro.md.

    Vacio en layout plano (docs/plan/plan_maestro.md), que es el caso de un solo plan.
    """
    base = raiz / "docs" / "plan"
    if not base.is_dir():
        return []
    return sorted(d.name for d in base.iterdir() if (d / "plan_maestro.md").is_file())


def resolver_track(raiz: Path, pedido: str = None) -> str:
    """El track a usar, o None si el repo tiene layout plano.

    Orden: --track explicito > docs/plan/plan_maestro.md (plano) > .project-suite/track
    > el unico disponible. Con varios y sin activo valido, sale pidiendo /track.
    """
    disponibles = tracks(raiz)
    if pedido:
        if pedido not in disponibles:
            raise SystemExit(
                f"track '{pedido}' no existe. Disponibles: {', '.join(disponibles) or 'ninguno'}")
        return pedido
    if (raiz / "docs" / "plan" / "plan_maestro.md").is_file():
        return None
    if not disponibles:
        raise SystemExit(
            "no hay plan: falta docs/plan/plan_maestro.md o docs/plan/<track>/plan_maestro.md")
    try:
        activo = (raiz / ARCHIVO_TRACK).read_text(encoding="utf-8").strip()
    except OSError:
        activo = ""
    if activo in disponibles:
        return activo
    if len(disponibles) == 1:
        return disponibles[0]
    raise SystemExit(
        f"varios tracks y ninguno activo: {', '.join(disponibles)}. Elegi uno con /track <slug>")


def rutas(raiz: Path, track: str) -> dict:
    """Las tres rutas del track: plan maestro, tablero y carpeta de Fases."""
    sub = Path(track) if track else Path()
    return {
        "raiz": raiz,
        "track": track,
        "plan": raiz / "docs" / "plan" / sub / "plan_maestro.md",
        "tablero": raiz / "docs" / "task" / sub / "tareas.md",
        "fases": raiz / "docs" / "task" / sub / "fases",
    }


# --- Anclas, nombres de archivo e indice ------------------------------------------

def ancla_de_titulo(titulo: str) -> str:
    """El fragmento `#...` que GitHub genera para un encabezado.

    Minusculas, se cae todo lo que no sea alfanumerico, espacio, guion o guion bajo
    (los acentos SI sobreviven, como en GitHub), y los espacios pasan a guiones.
    """
    t = "".join(c for c in titulo.strip().lower() if c.isalnum() or c in " -_")
    return t.replace(" ", "-")


def nombre_de_archivo(numero: str, calificador: str, titulo: str) -> str:
    """El `FNN-slug.md` estable de una Fase."""
    slug = ancla_de_titulo(f"{calificador.strip()} {titulo}".strip())
    slug = slug.translate(str.maketrans("áéíóúüñ", "aeiouun")).strip("-")
    # Cuatro palabras significativas: el numero ya identifica, las palabras solo
    # recuerdan de que iba. Un nombre de 60 caracteres se corta en el explorador
    # justo donde empezaba a diferenciarse del vecino.
    palabras = [p for p in slug.split("-") if p and p not in VACIAS][:4]
    return f"F{int(numero):02d}-{'-'.join(palabras)}.md"


def entradas_de_las_fases(carpeta: Path) -> list:
    """Lee `fases/` y devuelve [(archivo, estado, etiqueta_fase, [(estado, etiqueta_sf)])]."""
    salida = []
    if not carpeta.is_dir():
        return salida
    for archivo in sorted(carpeta.glob("F*.md")):
        estado_fase = etiqueta_fase = None
        subfases = []
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            mf = PATRON_FASE.match(linea)
            if mf and etiqueta_fase is None:
                estado_fase = mf.group(1)
                etiqueta_fase = f"F{int(mf.group(2))}{mf.group(3).rstrip()} — {mf.group(4)}"
                continue
            ms = PATRON_SUBFASE.match(linea)
            if ms:
                subfases.append((ms.group(1), f"{ms.group(2)} — {ms.group(3)}"))
        if etiqueta_fase:
            salida.append((archivo.name, estado_fase, etiqueta_fase, subfases))
    return salida


def bloque_markdown(entradas: list) -> str:
    """El indice: la Fase enlaza a su archivo; la Sub fase, a su ancla dentro de el.

    El ancla sola (`#sf581-...`) solo resuelve dentro del documento donde vive, asi que
    partido el tablero el enlace tiene que ser `fases/F58-....md#sf581-...`.
    """
    lineas = [MARCA_INICIO, "",
              "> Una Fase por archivo, bajo [`fases/`](fases/). Regenerar con",
              "> `python scripts/tablero.py --indice`; `--verificar` avisa si quedo viejo.", ""]
    for archivo, estado, etiqueta, subfases in entradas:
        lineas.append(f"- [{estado}] [**{etiqueta}**](fases/{archivo})")
        for est_sf, etq_sf in subfases:
            lineas.append(f"  - [{est_sf}] [{etq_sf}](fases/{archivo}#{ancla_de_titulo(etq_sf)})")
    lineas += ["", MARCA_FIN]
    return "\n".join(lineas)


def _reemplazar_bloque(texto: str, bloque: str) -> str:
    """Sustituye el contenido entre marcadores, buscandolos anclados a inicio de linea."""
    ini = re.search(rf"^{re.escape(MARCA_INICIO)}$", texto, re.M)
    fin = re.search(rf"^{re.escape(MARCA_FIN)}$", texto, re.M)
    if not ini or not fin or fin.start() < ini.start():
        raise SystemExit(
            f"el tablero no tiene los marcadores {MARCA_INICIO} / {MARCA_FIN}: "
            "agregalos donde va el indice (ver templates/plantilla_tareas.md)")
    return texto[:ini.start()] + bloque + texto[fin.end():]


def escribir_indice(r: dict) -> bool:
    """Regenera el bloque del indice. True si cambio algo."""
    actual = r["tablero"].read_text(encoding="utf-8")
    nuevo = _reemplazar_bloque(actual, bloque_markdown(entradas_de_las_fases(r["fases"])))
    if nuevo == actual:
        return False
    r["tablero"].write_text(nuevo, encoding="utf-8")
    return True


def verificar_indice(r: dict) -> bool:
    """True si el indice esta al dia. No escribe."""
    actual = r["tablero"].read_text(encoding="utf-8")
    return _reemplazar_bloque(actual, bloque_markdown(entradas_de_las_fases(r["fases"]))) == actual


# --- Migracion de un tablero monolitico -------------------------------------------

def partir(r: dict) -> list:
    """Corta un tablero monolitico en un archivo por Fase y deja el tablero como portada.

    Escribe `tareas.md.bak` al lado antes de tocar nada.
    """
    texto = r["tablero"].read_text(encoding="utf-8")
    lineas = texto.splitlines(keepends=True)
    cortes = [(i, PATRON_FASE.match(l)) for i, l in enumerate(lineas) if PATRON_FASE.match(l)]
    if not cortes:
        raise SystemExit("no se encontro ninguna Fase (`## [ ] Fase N — ...`) en el tablero")

    r["tablero"].with_suffix(".md.bak").write_text(texto, encoding="utf-8")
    r["fases"].mkdir(parents=True, exist_ok=True)

    creados = []
    for orden, (inicio, m) in enumerate(cortes):
        fin = cortes[orden + 1][0] if orden + 1 < len(cortes) else len(lineas)
        destino = r["fases"] / nombre_de_archivo(m.group(2), m.group(3), m.group(4))
        if destino.exists():
            raise SystemExit(f"colision de nombres: {destino.name} ya existe")
        destino.write_text("".join(lineas[inicio:fin]).rstrip() + "\n", encoding="utf-8")
        creados.append(destino)

    portada = "".join(lineas[:cortes[0][0]]).rstrip() + "\n"
    r["tablero"].write_text(portada, encoding="utf-8")
    escribir_indice(r)
    return creados


# --- Worktree: llevar y traer los documentos ignorados ------------------------------

def sha256(p: Path) -> str:
    """Hash del contenido, o '' si el archivo no existe."""
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def archivos_de_la_fase(r: dict, fase: str) -> list:
    """Plan maestro, tablero y SOLO los archivos de esa Fase, relativos a la raiz."""
    prefijo = f"F{int(fase.lstrip('Ff')):02d}"
    seleccion = [r["plan"], r["tablero"], *sorted(r["fases"].glob(f"{prefijo}*.md"))]
    if len(seleccion) == 2:
        raise SystemExit(f"no hay ninguna Fase {prefijo} en {r['fases']}")
    return [p.relative_to(r["raiz"]) for p in seleccion if p.exists()]


def copiar_a_worktree(r: dict, worktree: Path, fase: str) -> list:
    """Copia los documentos ignorados que la Fase necesita y deja el registro de origen.

    git no los lleva --estan gitignorados a proposito--, asi que la copia es la unica via.
    """
    relativos = archivos_de_la_fase(r, fase)
    for rel in relativos:
        destino = worktree / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r["raiz"] / rel, destino)
    (worktree / ORIGEN).write_text(json.dumps({
        "track": r["track"],
        "raiz": str(r["raiz"]),
        "archivos": {rel.as_posix(): sha256(r["raiz"] / rel) for rel in relativos},
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return relativos


def sincronizar(worktree: Path, raiz: Path = None) -> tuple:
    """Copia worktree -> repo principal. Devuelve (aplicados, divergentes).

    Ante divergencia NO escribe: el caso frecuente es que main no se toco, y un merge de
    texto sobre un tablero de miles de lineas es donde se pierde trabajo en silencio.
    """
    registro_path = worktree / ORIGEN
    if not registro_path.exists():
        raise SystemExit(f"{worktree} no tiene {ORIGEN}: no fue creada con --worktree")
    registro = json.loads(registro_path.read_text(encoding="utf-8"))
    raiz = Path(raiz or registro["raiz"])

    aplicados, divergentes = [], []
    for rel, hash_origen in registro["archivos"].items():
        origen, destino = worktree / rel, raiz / rel
        if not origen.exists():
            continue
        hash_actual = sha256(destino)
        if hash_actual != hash_origen and hash_actual != sha256(origen):
            divergentes.append(rel)
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)
        registro["archivos"][rel] = sha256(destino)
        aplicados.append(rel)

    registro_path.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")
    return aplicados, divergentes


def crear_worktree(r: dict, fase: str) -> Path:
    """Crea rama y worktree para la Fase, y copia adentro los documentos del plan."""
    prefijo = f"F{int(fase.lstrip('Ff')):02d}"
    archivos = sorted(r["fases"].glob(f"{prefijo}*.md"))
    if not archivos:
        raise SystemExit(f"no hay ninguna Fase {prefijo} en {r['fases']}")
    nombre = archivos[0].stem
    destino = r["raiz"] / ".claude" / "worktrees" / nombre

    ignorado = subprocess.run(["git", "check-ignore", "-q", ".claude/worktrees/"],
                              cwd=r["raiz"]).returncode == 0
    if not ignorado:
        print("AVISO: .claude/worktrees/ no esta en .gitignore. Son repos embebidos y "
              "nunca deben llegar al indice -- agregalo antes de commitear.")

    subprocess.run(["git", "worktree", "add", "-b", f"fase/{nombre}", str(destino), "HEAD"],
                   cwd=r["raiz"], check=True)
    copiar_a_worktree(r, destino, fase)
    return destino


# --- CLI ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tablero de project-suite: track, indice y worktree.")
    ap.add_argument("--track", help="track a usar; por defecto, el activo")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rutas", action="store_true", help="imprime las rutas resueltas en JSON")
    g.add_argument("--tracks", action="store_true", help="lista los tracks del repo")
    g.add_argument("--indice", action="store_true", help="regenera el indice del tablero")
    g.add_argument("--verificar", action="store_true", help="sale 1 si el indice quedo viejo")
    g.add_argument("--partir", action="store_true", help="migra un tablero monolitico a fases/")
    g.add_argument("--worktree", metavar="FNN", help="crea rama y worktree para esa Fase")
    g.add_argument("--sync", action="store_true", help="copia worktree -> repo principal")
    a = ap.parse_args(argv)

    if a.sync:
        wt = Path.cwd().resolve()
        while not (wt / ORIGEN).exists() and wt != wt.parent:
            wt = wt.parent
        aplicados, divergentes = sincronizar(wt)
        for rel in aplicados:
            print(f"  sync  {rel}")
        for rel in divergentes:
            print(f"DIVERGE {rel}: cambio en el repo principal desde el copiado; no se piso.")
        return 1 if divergentes else 0

    raiz = raiz_repo()
    if a.tracks:
        for t in tracks(raiz) or ["(layout plano: un solo plan)"]:
            print(t)
        return 0

    r = rutas(raiz, resolver_track(raiz, a.track))
    if a.rutas:
        print(json.dumps({k: (str(v) if isinstance(v, Path) else v) for k, v in r.items()},
                         indent=2, ensure_ascii=False))
        return 0
    if a.indice:
        print("indice actualizado" if escribir_indice(r) else "indice ya estaba al dia")
        return 0
    if a.verificar:
        if verificar_indice(r):
            print("OK: indice al dia")
            return 0
        print(f"el indice de {r['tablero']} quedo viejo. Corre: python scripts/tablero.py --indice")
        return 1
    if a.partir:
        creados = partir(r)
        for p in creados:
            print(f"  creado  {p.relative_to(raiz)}")
        print(f"{len(creados)} Fases repartidas. Respaldo en {r['tablero'].name}.bak")
        return 0
    if a.worktree:
        destino = crear_worktree(r, a.worktree)
        print(f"worktree lista en {destino}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
