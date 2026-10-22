#!/usr/bin/env annotations
#!/usr/bin/env python3
"""Compilador de documentos de arquitectura Markdown a visor HTML blueprint interactivo estilo Archify.

Este script analiza architecture.md (o cualquier archivo basado en plantilla_architecture.md),
extrae las secciones C4, Mapa Maestro, Flujos detallados, Invariantes, Despliegue y ADRs,
calcula el auto-layout jerárquico y ruteo ortogonal libre de colisiones,
y genera un visor HTML5 autocontenido y 100% offline.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Definición canónica de los 7 roles semánticos de Archify Blueprint
ARCHIFY_ROLES: Dict[str, Dict[str, str]] = {
    "frontend": {"color": "#06b6d4", "icon": "👤", "legend": "Frontend / Actor"},
    "backend": {"color": "#10b981", "icon": "⚙️", "legend": "Backend / Proceso"},
    "database": {"color": "#8b5cf6", "icon": "🗄️", "legend": "Base de Datos / Modelo"},
    "cloud": {"color": "#eab308", "icon": "☁️", "legend": "Cloud / Fuente"},
    "security": {"color": "#f43f5e", "icon": "🛡️", "legend": "Seguridad / Guardrail"},
    "message-bus": {"color": "#f97316", "icon": "📨", "legend": "Message Bus / Salida"},
    "external": {"color": "#64748b", "icon": "🌐", "legend": "Sistema Externo"},
}

# Mapeo de paleta canónica de project-suite (classDef) a roles de Archify
ROLE_MAP: Dict[str, str] = {
    "fuente": "cloud",
    "proc": "backend",
    "model": "database",
    "out": "message-bus",
    "riesgo": "security",
    "ui": "frontend",
    "frontend": "frontend",
    "backend": "backend",
    "database": "database",
    "cloud": "cloud",
    "security": "security",
    "message-bus": "message-bus",
    "external": "external",
}

DEFAULT_CARD_WIDTH = 250
DEFAULT_CARD_HEIGHT = 86
PADDING_BOUNDARY_X = 28
PADDING_BOUNDARY_Y_TOP = 34
PADDING_BOUNDARY_Y_BOTTOM = 22


def get_role_style(role_name: str) -> Dict[str, str]:
    """Obtiene los atributos visuales (color, icono, leyenda) para un rol semántico.

    Args:
        role_name: Nombre del rol o clase canónica.

    Returns:
        Diccionario con color, icon y legend.
    """
    canonical_role = ROLE_MAP.get(role_name.lower(), role_name.lower())
    return ARCHIFY_ROLES.get(canonical_role, ARCHIFY_ROLES["backend"])


@dataclasses.dataclass
class ComponentNode:
    """Representa una tarjeta de componente dentro del canvas blueprint."""
    id: str
    label: str
    sublabel: str = ""
    role: str = "backend"
    color: str = "#10b981"
    icon: str = "⚙️"
    subgraph_id: Optional[str] = None
    target_view_id: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    width: float = DEFAULT_CARD_WIDTH
    height: float = DEFAULT_CARD_HEIGHT


@dataclasses.dataclass
class BoundaryBox:
    """Representa un contenedor boundary punteado que agrupa componentes."""
    id: str
    label: str
    color: str = "#334155"
    parent_id: Optional[str] = None
    children: List[str] = dataclasses.field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclasses.dataclass
class ConnectionEdge:
    """Representa una conexión dirigida u ortogonal entre dos tarjetas."""
    from_node: str
    to_node: str
    label: str = ""
    arrow_type: str = "-->"
    dashed: bool = False
    bidirectional: bool = False
    thick: bool = False
    color: str = "#38bdf8"
    path: str = ""
    label_at: Optional[Dict[str, float]] = None


def infer_role_from_text(text: str, shape: str = "") -> str:
    """Infiere el rol semántico de un nodo a partir de su forma y palabras clave.

    Args:
        text: Texto combinado de título, subtítulo e ID del nodo.
        shape: Tipo de forma Mermaid (cylinder, rect, round, etc.).

    Returns:
        Nombre del rol semántico correspondiente a la paleta Archify.
    """
    low = text.lower()

    if shape == "cylinder" or any(k in low for k in ["db", "database", "sqlite", "postgres", "mysql", "tabla", "datos", "repo", "almacenamiento", "mode"]):
        return "database"
    if any(k in low for k in ["actor", "desarrollador", "user", "usuario", "cliente", "browser", "ui", "pantalla", "interfaz"]):
        return "frontend"
    if any(k in low for k in ["npm", "registry", "cloud", "cache", "s3", "bucket", "fuente", "api externa"]):
        return "cloud"
    if any(k in low for k in ["auth", "seguridad", "guard", "riesgo", "token", "validador"]):
        return "security"
    if any(k in low for k in ["cola", "queue", "kafka", "event", "mensaje", "out", "salida", "destino", "sesion"]):
        return "message-bus"
    if any(k in low for k in ["externo", "tercero", "remoto"]):
        return "external"

    return "backend"


def parse_mermaid_flowchart(code: str) -> Dict[str, Any]:
    """Analiza código fuente Mermaid de tipo flowchart/graph y produce el grafo blueprint.

    Args:
        code: Bloque de texto con código Mermaid flowchart o graph.

    Returns:
        Diccionario estructurado con direction, components, boundaries y connections.
    """
    lines = [ln.strip() for ln in code.strip().splitlines() if ln.strip()]
    direction = "LR"

    components_map: Dict[str, ComponentNode] = {}
    boundaries_map: Dict[str, BoundaryBox] = {}
    subgraph_stack: List[str] = []
    connections: List[ConnectionEdge] = []
    class_assignments: Dict[str, str] = {}
    inline_styles: Dict[str, Dict[str, str]] = {}

    for line in lines:
        if line.startswith("%%"):
            continue  # Salta comentarios Mermaid

        # Detección de encabezado de dirección
        header_match = re.match(r"^(flowchart|graph)\s+(TB|TD|LR|RL)", line, re.IGNORECASE)
        if header_match:
            raw_dir = header_match.group(2).upper()
            direction = "TB" if raw_dir in ("TB", "TD") else "LR"
            continue

        # Definición de classDef
        classdef_match = re.match(r"^classDef\s+([a-zA-Z0-9_-]+)\s+(.+)$", line)
        if classdef_match:
            continue

        # Asignación de clase global estilo: class A,B proc;
        class_match = re.match(r"^class\s+([a-zA-Z0-9_,-]+)\s+([a-zA-Z0-9_-]+);?$", line)
        if class_match:
            node_ids = [n.strip() for n in class_match.group(1).split(",")]
            cls_name = class_match.group(2).strip()
            for nid in node_ids:
                class_assignments[nid] = cls_name
            continue

        # Estilo inline: style ID fill:#...,stroke:#...
        style_match = re.match(r"^style\s+([a-zA-Z0-9_-]+)\s+(.+)$", line)
        if style_match:
            target_id = style_match.group(1)
            style_str = style_match.group(2)
            parsed_styles: Dict[str, str] = {}
            for item in style_str.split(","):
                if ":" in item:
                    k, v = item.split(":", 1)
                    parsed_styles[k.strip().lower()] = v.strip()
            inline_styles[target_id] = parsed_styles
            continue

        # Inicio de subgraph
        subgraph_match = re.match(
            r"^subgraph\s+([a-zA-Z0-9_-]+)(?:\[\"(.*?)\"\]|\[(.*?)\])?",
            line,
        )
        if subgraph_match:
            sg_id = subgraph_match.group(1)
            sg_label = subgraph_match.group(2) or subgraph_match.group(3) or sg_id
            parent_sg = subgraph_stack[-1] if subgraph_stack else None
            boundaries_map[sg_id] = BoundaryBox(
                id=sg_id,
                label=sg_label,
                parent_id=parent_sg,
            )
            subgraph_stack.append(sg_id)
            continue

        # Fin de subgraph
        if line == "end" or line.startswith("end "):
            if subgraph_stack:
                subgraph_stack.pop()
            continue

        # Detección de aristas y conexiones
        edge_match = re.search(
            r"([a-zA-Z0-9_]+)\s*(?:\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\})?\s*"
            r"(<-->|-->|-\.->|==>|--)\s*(?:\|\"?(.*?)\"?\|)?\s*"
            r"([a-zA-Z0-9_]+)",
            line,
        )
        if edge_match:
            u = edge_match.group(1)
            arrow_sym = edge_match.group(2)
            lbl = edge_match.group(3) or ""
            v = edge_match.group(4)

            dashed = "-." in arrow_sym
            bidir = arrow_sym == "<-->"
            thick = "==" in arrow_sym

            connections.append(
                ConnectionEdge(
                    from_node=u,
                    to_node=v,
                    label=lbl,
                    arrow_type=arrow_sym,
                    dashed=dashed,
                    bidirectional=bidir,
                    thick=thick,
                )
            )

        # Detección de nodos individuales o nodos presentes en la línea
        node_patterns = [
            (r'([a-zA-Z0-9_]+)\[\("(.*?)"\)\]', "cylinder"),
            (r'([a-zA-Z0-9_]+)\[\((.*?)\)\]', "cylinder"),
            (r'([a-zA-Z0-9_]+)\(\["(.*?)"\]\)', "round"),
            (r'([a-zA-Z0-9_]+)\(\[(.*?)\]\)', "round"),
            (r'([a-zA-Z0-9_]+)\(\("(.*?)"\)\)', "circle"),
            (r'([a-zA-Z0-9_]+)\(\((.*?)\)\)', "circle"),
            (r'([a-zA-Z0-9_]+)\{"(.*?)"\}', "diamond"),
            (r'([a-zA-Z0-9_]+)\{(.*?)\}', "diamond"),
            (r'([a-zA-Z0-9_]+)\["(.*?)"\]', "rect"),
            (r'([a-zA-Z0-9_]+)\[(.*?)\]', "rect"),
        ]

        for pattern, shape in node_patterns:
            for match in re.finditer(pattern, line):
                n_id = match.group(1)
                raw_text = match.group(2).replace("\\n", "\n").replace("<br/>", "\n").replace("<br>", "\n")
                lines_text = [t.strip() for t in raw_text.split("\n") if t.strip()]

                title = lines_text[0] if lines_text else n_id
                sub = " · ".join(lines_text[1:]) if len(lines_text) > 1 else ""

                current_sg = subgraph_stack[-1] if subgraph_stack else None

                # Verificación de clase :::clase
                cls_override = None
                class_suffix_match = re.search(rf"{n_id}(?:\[[^\]]*\])?:::([a-zA-Z0-9_-]+)", line)
                if class_suffix_match:
                    cls_override = class_suffix_match.group(1)

                role_key = cls_override or class_assignments.get(n_id)
                if role_key and role_key in ROLE_MAP:
                    canonical_role = ROLE_MAP[role_key]
                    role_style = ARCHIFY_ROLES[canonical_role]
                    role = canonical_role
                    color = role_style["color"]
                    icon = role_style["icon"]
                else:
                    role = infer_role_from_text(f"{n_id} {title} {sub} {current_sg or ''}", shape)
                    role_style = ARCHIFY_ROLES[role]
                    color = role_style["color"]
                    icon = role_style["icon"]

                if n_id not in components_map:
                    comp = ComponentNode(
                        id=n_id,
                        label=title,
                        sublabel=sub,
                        role=role,
                        color=color,
                        icon=icon,
                        subgraph_id=current_sg,
                    )
                    components_map[n_id] = comp
                    if current_sg and current_sg in boundaries_map:
                        boundaries_map[current_sg].children.append(n_id)

    # Inferencia de nodos implícitos no declarados explícitamente con corchetes
    for conn in connections:
        for nid in (conn.from_node, conn.to_node):
            if nid not in components_map:
                role = infer_role_from_text(nid)
                role_style = ARCHIFY_ROLES[role]
                components_map[nid] = ComponentNode(
                    id=nid,
                    label=nid,
                    role=role,
                    color=role_style["color"],
                    icon=role_style["icon"],
                )

    # Aplicación de estilos inline de subgrafos y nodos
    for target_id, styles in inline_styles.items():
        if target_id in boundaries_map:
            if "stroke" in styles:
                boundaries_map[target_id].color = styles["stroke"]
        elif target_id in components_map:
            if "stroke" in styles:
                components_map[target_id].color = styles["stroke"]

    return {
        "diagram_type": "flowchart",
        "direction": direction,
        "components": list(components_map.values()),
        "boundaries": list(boundaries_map.values()),
        "connections": connections,
    }


def parse_mermaid_sequence(code: str) -> Dict[str, Any]:
    """Analiza código Mermaid de diagramas de secuencia y extrae participantes, mensajes y bloques.

    Args:
        code: Bloque de texto con código sequenceDiagram.

    Returns:
        Diccionario estructurado con participants, messages y blocks condicionales.
    """
    lines = [ln.strip() for ln in code.strip().splitlines() if ln.strip()]

    participants_list: List[Dict[str, str]] = []
    seen_participants: Set[str] = set()
    messages_list: List[Dict[str, Any]] = []
    blocks_list: List[Dict[str, Any]] = []
    block_stack: List[Dict[str, Any]] = []

    for line in lines:
        if line.startswith("%%") or line.startswith("sequenceDiagram"):
            continue

        # Declaración explícita de participante: participant ID as Alias
        part_match = re.match(r"^participant\s+([a-zA-Z0-9_]+)(?:\s+as\s+(.+))?$", line)
        if part_match:
            pid = part_match.group(1)
            lbl = part_match.group(2) or pid
            if pid not in seen_participants:
                participants_list.append({"id": pid, "label": lbl})
                seen_participants.add(pid)
            continue

        # Bloques condicionales: alt / else / opt / loop
        cond_match = re.match(r"^(alt|else|opt|loop)\s*(.*)$", line)
        if cond_match:
            b_type = cond_match.group(1)
            b_cond = cond_match.group(2).strip()
            curr_msg_idx = len(messages_list)

            if b_type == "else" and block_stack:
                # Cierra el bloque anterior antes de abrir la rama alternativa
                prev_block = block_stack.pop()
                prev_block["endIdx"] = max(prev_block["startIdx"], curr_msg_idx - 1)
                blocks_list.append(prev_block)

            block_stack.append({
                "type": b_type,
                "condition": b_cond,
                "startIdx": curr_msg_idx,
            })
            continue

        if line == "end" or line.startswith("end "):
            if block_stack:
                closed_block = block_stack.pop()
                closed_block["endIdx"] = max(closed_block["startIdx"], len(messages_list) - 1)
                blocks_list.append(closed_block)
            continue

        # Mensajes entre participantes: A->>B: mensaje o B-->>A: respuesta
        # Nota: El orden de las flechas (-->> antes de ->>) es crítico para evitar falsas coincidencias
        msg_match = re.match(
            r"^([a-zA-Z0-9_]+)\s*(-->>|->>|-->|->)\s*([a-zA-Z0-9_]+)\s*:\s*(.+)$",
            line,
        )
        if msg_match:
            u = msg_match.group(1)
            arrow_sym = msg_match.group(2)
            v = msg_match.group(3)
            txt = msg_match.group(4).strip()

            for p in (u, v):
                if p not in seen_participants:
                    participants_list.append({"id": p, "label": p})
                    seen_participants.add(p)

            messages_list.append({
                "from": u,
                "to": v,
                "label": txt,
                "arrow": arrow_sym,
                "dashed": "--" in arrow_sym,
            })

    # Cierre de bloques remanentes en caso de sintaxis abierta
    while block_stack:
        rem_block = block_stack.pop()
        rem_block["endIdx"] = max(rem_block["startIdx"], len(messages_list) - 1)
        blocks_list.append(rem_block)

    return {
        "diagram_type": "sequence",
        "participants": participants_list,
        "messages": messages_list,
        "blocks": blocks_list,
    }


def parse_mermaid_state(code: str) -> Dict[str, Any]:
    """Analiza diagramas de estado simples y los traduce a formato de nodos y aristas blueprint.

    Args:
        code: Bloque de texto con diagrama stateDiagram o stateDiagram-v2.

    Returns:
        Diccionario estructurado con components y connections.
    """
    lines = [ln.strip() for ln in code.strip().splitlines() if ln.strip()]
    components_map: Dict[str, ComponentNode] = {}
    connections: List[ConnectionEdge] = []

    for line in lines:
        if line.startswith("%%") or line.startswith("stateDiagram"):
            continue

        trans_match = re.match(r"([a-zA-Z0-9_*\[\]]+)\s*-->\s*([a-zA-Z0-9_*\[\]]+)(?:\s*:\s*(.+))?", line)
        if trans_match:
            u = trans_match.group(1).replace("[*]", "Inicio")
            v = trans_match.group(2).replace("[*]", "Fin")
            lbl = trans_match.group(3) or ""

            for s_id in (u, v):
                if s_id not in components_map:
                    role = "frontend" if s_id == "Inicio" else ("message-bus" if s_id == "Fin" else "backend")
                    style = get_role_style(role)
                    components_map[s_id] = ComponentNode(
                        id=s_id,
                        label=s_id,
                        role=role,
                        color=style["color"],
                        icon=style["icon"],
                    )

            connections.append(
                ConnectionEdge(
                    from_node=u,
                    to_node=v,
                    label=lbl,
                )
            )

    return {
        "diagram_type": "flowchart",
        "direction": "LR",
        "components": list(components_map.values()),
        "boundaries": [],
        "connections": connections,
    }


def assign_layers_dag(
    node_ids: List[str],
    edges: List[Tuple[str, str]],
) -> Dict[str, int]:
    """Calcula las capas topológicas de un grafo dirigido rompiendo ciclos de forma determinista.

    Args:
        node_ids: Lista de identificadores únicos de nodos.
        edges: Lista de tuplas (nodo_origen, nodo_destino).

    Returns:
        Diccionario que asigna a cada identificador su índice entero de capa (0..K).
    """
    indeg = {n: 0 for n in node_ids}
    adj: Dict[str, List[str]] = {n: [] for n in node_ids}

    for u, v in edges:
        if u in adj and v in indeg and u != v:
            adj[u].append(v)
            indeg[v] += 1

    layers = {n: 0 for n in node_ids}
    queue = [n for n, d in indeg.items() if d == 0]
    if not queue and node_ids:
        queue = [node_ids[0]]

    visited: Set[str] = set()
    while queue:
        u = queue.pop(0)
        visited.add(u)
        for v in adj[u]:
            layers[v] = max(layers[v], layers[u] + 1)
            indeg[v] -= 1
            if indeg[v] <= 0 and v not in visited:
                queue.append(v)

    # Asigna capa por defecto a componentes disconexos o atrapados en ciclos
    for n in node_ids:
        if n not in visited:
            layers[n] = max(layers.values()) + 1 if layers else 0

    return layers


def compute_blueprint_layout(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula las coordenadas geométricas (x, y, w, h) para componentes, boundaries y conexiones.

    Garantiza matemáticamente cero colisiones entre tarjetas de componentes y encierra
    los boundaries con margen perimetral suficiente para su píldora superior.

    Args:
        graph_data: Diccionario producido por parse_mermaid_flowchart o similar.

    Returns:
        Diccionario enriquecido con dimensiones y coordenadas listas para SVG.
    """
    if graph_data.get("diagram_type") == "sequence":
        return graph_data  # Los diagramas de secuencia se maquetan por timeline dinámico

    components: List[ComponentNode] = graph_data.get("components", [])
    boundaries: List[BoundaryBox] = graph_data.get("boundaries", [])
    connections: List[ConnectionEdge] = graph_data.get("connections", [])
    direction: str = graph_data.get("direction", "LR")

    if not components:
        return graph_data

    node_ids = [c.id for c in components]
    edges = [(conn.from_node, conn.to_node) for conn in connections]

    layers_map = assign_layers_dag(node_ids, edges)

    # Agrupa componentes por capa
    layer_groups: Dict[int, List[ComponentNode]] = {}
    for comp in components:
        l_idx = layers_map.get(comp.id, 0)
        layer_groups.setdefault(l_idx, []).append(comp)

    col_width = 370.0
    row_height = 130.0
    margin_x = 80.0
    margin_y = 60.0

    comp_dict = {c.id: c for c in components}

    # Ordena nodos dentro de cada capa para agrupar los del mismo boundary
    for l_idx in sorted(layer_groups.keys()):
        group = layer_groups[l_idx]
        group.sort(key=lambda c: (c.subgraph_id or "", c.id))

        for row_idx, comp in enumerate(group):
            if direction == "TB":
                comp.x = margin_x + row_idx * (DEFAULT_CARD_WIDTH + 60.0)
                comp.y = margin_y + l_idx * row_height
            else:
                comp.x = margin_x + l_idx * col_width
                comp.y = margin_y + row_idx * row_height

            comp.width = DEFAULT_CARD_WIDTH
            comp.height = DEFAULT_CARD_HEIGHT

    # Dimensiona y posiciona cada boundary envolvente
    for b in boundaries:
        child_comps = [comp_dict[cid] for cid in b.children if cid in comp_dict]
        if not child_comps:
            continue

        min_x = min(c.x for c in child_comps)
        min_y = min(c.y for c in child_comps)
        max_x = max(c.x + c.width for c in child_comps)
        max_y = max(c.y + c.height for c in child_comps)

        b.x = min_x - PADDING_BOUNDARY_X
        b.y = min_y - PADDING_BOUNDARY_Y_TOP
        b.width = (max_x - min_x) + 2 * PADDING_BOUNDARY_X
        b.height = (max_y - min_y) + PADDING_BOUNDARY_Y_TOP + PADDING_BOUNDARY_Y_BOTTOM

    # Ruteo ortogonal de aristas y ubicación de etiquetas en píldora
    route_orthogonal_edges(comp_dict, connections, direction)

    return {
        "diagram_type": "flowchart",
        "direction": direction,
        "components": [dataclasses.asdict(c) for c in components],
        "boundaries": [dataclasses.asdict(b) for b in boundaries],
        "connections": [dataclasses.asdict(conn) for conn in connections],
    }


def route_orthogonal_edges(
    comp_dict: Dict[str, ComponentNode],
    connections: List[ConnectionEdge],
    direction: str = "LR",
) -> None:
    """Traza los caminos SVG ortogonales con esquinas redondeadas y posiciona las píldoras de texto.

    Args:
        comp_dict: Diccionario de componentes indexados por su identificador.
        connections: Lista de conexiones que serán enriquecidas con 'path' y 'label_at'.
        direction: Dirección general del diagrama ('LR' o 'TB').
    """
    radius = 8.0

    for conn in connections:
        u = comp_dict.get(conn.from_node)
        v = comp_dict.get(conn.to_node)

        if not u or not v:
            continue

        if direction == "LR":
            # Conexión regular izquierda a derecha
            x1 = u.x + u.width
            y1 = u.y + u.height / 2.0
            x2 = v.x
            y2 = v.y + v.height / 2.0

            if x2 >= x1:
                # Conexión hacia adelante
                mid_x = (x1 + x2) / 2.0
                if abs(y1 - y2) < 2.0:
                    conn.path = f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}"
                    conn.label_at = {"x": mid_x, "y": y1}
                else:
                    dir_y = 1.0 if y2 > y1 else -1.0
                    conn.path = (
                        f"M {x1:.1f} {y1:.1f} "
                        f"L {mid_x - radius:.1f} {y1:.1f} "
                        f"Q {mid_x:.1f} {y1:.1f} {mid_x:.1f} {y1 + dir_y * radius:.1f} "
                        f"L {mid_x:.1f} {y2 - dir_y * radius:.1f} "
                        f"Q {mid_x:.1f} {y2:.1f} {mid_x + radius:.1f} {y2:.1f} "
                        f"L {x2:.1f} {y2:.1f}"
                    )
                    conn.label_at = {"x": mid_x, "y": (y1 + y2) / 2.0}
            else:
                # Conexión hacia atrás o en bucle
                loop_y = max(u.y + u.height, v.y + v.height) + 36.0
                conn.path = (
                    f"M {u.x + u.width / 2.0:.1f} {u.y + u.height:.1f} "
                    f"L {u.x + u.width / 2.0:.1f} {loop_y:.1f} "
                    f"L {v.x + v.width / 2.0:.1f} {loop_y:.1f} "
                    f"L {v.x + v.width / 2.0:.1f} {v.y + v.height:.1f}"
                )
                conn.label_at = {"x": (u.x + v.x) / 2.0, "y": loop_y}
        else:
            # Conexión arriba hacia abajo (TB)
            x1 = u.x + u.width / 2.0
            y1 = u.y + u.height
            x2 = v.x + v.width / 2.0
            y2 = v.y

            if y2 >= y1:
                mid_y = (y1 + y2) / 2.0
                if abs(x1 - x2) < 2.0:
                    conn.path = f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}"
                    conn.label_at = {"x": x1, "y": mid_y}
                else:
                    dir_x = 1.0 if x2 > x1 else -1.0
                    conn.path = (
                        f"M {x1:.1f} {y1:.1f} "
                        f"L {x1:.1f} {mid_y - radius:.1f} "
                        f"Q {x1:.1f} {mid_y:.1f} {x1 + dir_x * radius:.1f} {mid_y:.1f} "
                        f"L {x2 - dir_x * radius:.1f} {mid_y:.1f} "
                        f"Q {x2:.1f} {mid_y:.1f} {x2:.1f} {mid_y + radius:.1f} "
                        f"L {x2:.1f} {y2:.1f}"
                    )
                    conn.label_at = {"x": (x1 + x2) / 2.0, "y": mid_y}
            else:
                loop_x = max(u.x + u.width, v.x + v.width) + 40.0
                conn.path = (
                    f"M {u.x + u.width:.1f} {u.y + u.height / 2.0:.1f} "
                    f"L {loop_x:.1f} {u.y + u.height / 2.0:.1f} "
                    f"L {loop_x:.1f} {v.y + v.height / 2.0:.1f} "
                    f"L {v.x + v.width:.1f} {v.y + v.height / 2.0:.1f}"
                )
                conn.label_at = {"x": loop_x, "y": (u.y + v.y) / 2.0}


def parse_markdown_table(table_lines: List[str]) -> List[Dict[str, str]]:
    """Convierte una tabla Markdown en una lista de diccionarios con sus columnas.

    Args:
        table_lines: Lista de líneas pertenecientes a la tabla Markdown.

    Returns:
        Lista de filas con nombres de columna normalizados.
    """
    if len(table_lines) < 2:
        return []

    headers = [h.strip() for h in table_lines[0].strip("|").split("|")]
    rows: List[Dict[str, str]] = []

    for line in table_lines[2:]:
        if not line.strip() or not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) >= len(headers):
            row_dict = {headers[i]: cols[i] for i in range(len(headers))}
            rows.append(row_dict)

    return rows


def parse_architecture_markdown(md_text: str) -> Dict[str, Any]:
    """Extrae la estructura integral de architecture.md para alimentar el visor blueprint.

    Args:
        md_text: Texto completo del documento architecture.md.

    Returns:
        Diccionario con metadatos, vistas calculadas, índice de flujos, ADRs y search index.
    """
    lines = md_text.splitlines()

    # Extracción de título del documento
    title = "Arquitectura del Sistema"
    for line in lines:
        if line.startswith("# "):
            title = line.lstrip("# ").strip()
            break

    # Extracción de subtítulo / resumen inicial
    subtitle = ""
    for line in lines:
        if line.startswith("> "):
            subtitle = line.lstrip("> ").strip()
            break

    views: List[Dict[str, Any]] = []
    flows_index: List[Dict[str, Any]] = []
    adrs_list: List[Dict[str, Any]] = []
    search_index: List[Dict[str, Any]] = []

    # Partición del documento en secciones Markdown de primer y segundo nivel
    section_pattern = re.compile(r"^##\s+(.+)$")
    sections: List[Tuple[str, List[str]]] = []
    current_title = "Cabecera"
    current_lines: List[str] = []

    for line in lines:
        m = section_pattern.match(line)
        if m:
            sections.append((current_title, current_lines))
            current_title = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections.append((current_title, current_lines))

    # Helper para extraer bloques de código Mermaid en una sección
    def extract_mermaid_blocks(sec_lines: List[str]) -> List[Tuple[str, str]]:
        blocks = []
        inside = False
        buf = []
        for l in sec_lines:
            if l.startswith("```mermaid"):
                inside = True
                buf = []
            elif inside and l.startswith("```"):
                inside = False
                raw_code = "\n".join(buf).strip()
                first_word = raw_code.split()[0].lower() if raw_code else ""
                blocks.append((first_word, raw_code))
            elif inside:
                buf.append(l)
        return blocks

    total_invariants = 0
    master_map_rows: List[Dict[str, str]] = []

    for sec_name, sec_lines in sections:
        sec_text = "\n".join(sec_lines)
        mermaid_blocks = extract_mermaid_blocks(sec_lines)

        # 1. C4 Contexto
        if "C4 – Nivel Contexto" in sec_name or "Nivel Contexto" in sec_name:
            if mermaid_blocks:
                kind, code = mermaid_blocks[0]
                graph_data = parse_mermaid_flowchart(code)
                layout_data = compute_blueprint_layout(graph_data)
                view_obj = {
                    "id": "c4-contexto",
                    "name": "C4 Contexto",
                    "description": "Visión macro de actores humanos y sistemas externos",
                    **layout_data,
                }
                views.append(view_obj)

        # 2. C4 Contenedor
        elif "C4 – Nivel Contenedor" in sec_name or "Nivel Contenedor" in sec_name:
            if mermaid_blocks:
                kind, code = mermaid_blocks[0]
                graph_data = parse_mermaid_flowchart(code)
                layout_data = compute_blueprint_layout(graph_data)
                view_obj = {
                    "id": "c4-contenedor",
                    "name": "C4 Contenedor",
                    "description": "Componentes lógicos y módulos internos del sistema",
                    **layout_data,
                }
                views.append(view_obj)

        # 3. Mapa Maestro de Flujos
        elif "mapa maestro" in sec_name.lower():
            table_lines = [l for l in sec_lines if "|" in l]
            master_map_rows = parse_markdown_table(table_lines)

            # Si contiene diagrama Mermaid explícito, se procesa
            if mermaid_blocks:
                kind, code = mermaid_blocks[0]
                graph_data = parse_mermaid_flowchart(code)
            else:
                # Síntesis automática del grafo blueprint para el Mapa Maestro
                components: List[ComponentNode] = []
                connections: List[ConnectionEdge] = []

                for row in master_map_rows:
                    f_num = row.get("#", "").strip() or str(len(components) + 1)
                    f_name = row.get("Flujo", "").strip()
                    f_in = row.get("Entrada", "").strip()
                    f_proc = row.get("Proceso", "").strip()
                    f_out = row.get("Salida", "").strip()

                    f_node_id = f"flow_{f_num}"
                    in_node_id = f"in_{f_num}"
                    out_node_id = f"out_{f_num}"

                    # Tarjeta central del Flujo (con drill-down enlazado)
                    components.append(
                        ComponentNode(
                            id=f_node_id,
                            label=f"Flujo {f_num}: {f_name}",
                            sublabel=f_proc,
                            role="backend",
                            color="#10b981",
                            icon="⚙️",
                            target_view_id=f"flow-{f_num}",
                        )
                    )

                    # Tarjeta de Entrada
                    components.append(
                        ComponentNode(
                            id=in_node_id,
                            label=f"Entrada ({f_num})",
                            sublabel=f_in,
                            role="cloud",
                            color="#eab308",
                            icon="☁️",
                        )
                    )

                    # Tarjeta de Salida
                    components.append(
                        ComponentNode(
                            id=out_node_id,
                            label=f"Salida ({f_num})",
                            sublabel=f_out,
                            role="message-bus",
                            color="#f97316",
                            icon="📨",
                        )
                    )

                    connections.append(ConnectionEdge(from_node=in_node_id, to_node=f_node_id, label="dispara"))
                    connections.append(ConnectionEdge(from_node=f_node_id, to_node=out_node_id, label="produce"))

                graph_data = {
                    "diagram_type": "flowchart",
                    "direction": "LR",
                    "components": components,
                    "boundaries": [],
                    "connections": connections,
                }

            layout_data = compute_blueprint_layout(graph_data)
            view_obj = {
                "id": "mapa-maestro",
                "name": "Mapa Maestro de Flujos",
                "description": "Encadenamiento global de todos los flujos de datos",
                **layout_data,
            }
            views.append(view_obj)

        # 4. Flujos individuales (§3..§N)
        elif re.search(r"Flujo\s+(\d+)", sec_name, re.IGNORECASE):
            flow_num_match = re.search(r"Flujo\s+(\d+)", sec_name, re.IGNORECASE)
            f_num = flow_num_match.group(1) if flow_num_match else str(len(flows_index) + 1)
            view_id = f"flow-{f_num}"

            # Extracción de pipeline 'Entrada → Proceso → Salida'
            pipeline_match = re.search(r"\*\*Entrada\s*→\s*Proceso\s*→\s*Salida:\*\*\s*(.+)", sec_text)
            pipeline_desc = pipeline_match.group(1).strip() if pipeline_match else ""

            # Extracción de scripts asociados
            scripts_found: List[str] = []
            script_match = re.search(r"Scripts?:\s*(.+)", sec_text, re.IGNORECASE)
            if script_match:
                raw_scripts = script_match.group(1)
                for code_tag in re.findall(r"`([^`]+)`", raw_scripts):
                    scripts_found.append(code_tag)

            # Extracción de tabla de reglas e invariantes
            invariants_list: List[Dict[str, str]] = []
            invariants_table_lines = []
            capturing_table = False
            for l in sec_lines:
                if "Reglas e invariantes" in l or "Invariantes" in l:
                    capturing_table = True
                    continue
                if capturing_table:
                    if l.startswith("##") and not l.startswith("###"):
                        break
                    if "|" in l:
                        invariants_table_lines.append(l)

            if invariants_table_lines:
                raw_inv_table = parse_markdown_table(invariants_table_lines)
                for row in raw_inv_table:
                    rule_name = row.get("Regla", "") or row.get("Invariante", "")
                    rule_desc = row.get("Descripción", "") or row.get("Detalle", "")
                    if rule_name:
                        invariants_list.append({"name": rule_name, "description": rule_desc})
                        total_invariants += 1

            # Procesamiento de diagrama Mermaid o síntesis de pipeline visual
            if mermaid_blocks:
                kind, code = mermaid_blocks[0]
                if kind == "sequencediagram":
                    graph_data = parse_mermaid_sequence(code)
                    layout_data = graph_data
                elif kind in ("statediagram", "statediagram-v2"):
                    graph_data = parse_mermaid_state(code)
                    layout_data = compute_blueprint_layout(graph_data)
                else:
                    graph_data = parse_mermaid_flowchart(code)
                    layout_data = compute_blueprint_layout(graph_data)
            else:
                # Síntesis visual de pipeline Entrada -> Proceso -> Salida
                comp_in = ComponentNode(
                    id=f"f{f_num}_in",
                    label="Entrada",
                    sublabel=pipeline_desc.split("→")[0].strip() if "→" in pipeline_desc else "Inicio",
                    role="cloud",
                    color=ARCHIFY_ROLES["cloud"]["color"],
                    icon=ARCHIFY_ROLES["cloud"]["icon"],
                )
                comp_proc = ComponentNode(
                    id=f"f{f_num}_proc",
                    label=sec_name.split("—")[-1].strip(),
                    sublabel=", ".join(scripts_found) if scripts_found else "Lógica interna",
                    role="backend",
                    color=ARCHIFY_ROLES["backend"]["color"],
                    icon=ARCHIFY_ROLES["backend"]["icon"],
                )
                comp_out = ComponentNode(
                    id=f"f{f_num}_out",
                    label="Salida",
                    sublabel=pipeline_desc.split("→")[-1].strip() if "→" in pipeline_desc else "Fin",
                    role="message-bus",
                    color=ARCHIFY_ROLES["message-bus"]["color"],
                    icon=ARCHIFY_ROLES["message-bus"]["icon"],
                )
                conns = [
                    ConnectionEdge(from_node=comp_in.id, to_node=comp_proc.id, label="procesa"),
                    ConnectionEdge(from_node=comp_proc.id, to_node=comp_out.id, label="emite"),
                ]
                synth_data = {
                    "diagram_type": "flowchart",
                    "direction": "LR",
                    "components": [comp_in, comp_proc, comp_out],
                    "boundaries": [],
                    "connections": conns,
                }
                layout_data = compute_blueprint_layout(synth_data)

            view_obj = {
                "id": view_id,
                "name": f"Flujo {f_num}",
                "full_title": sec_name,
                "is_flow": True,
                "flow_number": int(f_num) if f_num.isdigit() else 0,
                "description": pipeline_desc,
                "scripts": scripts_found,
                "invariants": invariants_list,
                "flow_meta": {
                    "pipeline": pipeline_desc,
                    "scripts": scripts_found,
                    "invariants": invariants_list,
                },
                **layout_data,
            }
            views.append(view_obj)

            flows_index.append({
                "id": view_id,
                "number": f_num,
                "name": sec_name,
                "pipeline": pipeline_desc,
                "scripts": scripts_found,
                "invariants_count": len(invariants_list),
            })

        # 5. Arquitectura de despliegue
        elif "despliegue" in sec_name.lower():
            if mermaid_blocks:
                kind, code = mermaid_blocks[0]
                graph_data = parse_mermaid_flowchart(code)
                layout_data = compute_blueprint_layout(graph_data)
                view_obj = {
                    "id": "despliegue",
                    "name": "Despliegue",
                    "description": "Distribución física, caché y empaquetado",
                    **layout_data,
                }
                views.append(view_obj)

        # 6. Decisiones Arquitectónicas (ADRs)
        elif "decisiones" in sec_name.lower() or "adrs" in sec_name.lower():
            table_lines = [l for l in sec_lines if "|" in l]
            adrs_raw = parse_markdown_table(table_lines)
            for row in adrs_raw:
                decision = row.get("Decisión Tomada", "") or row.get("Decisión", "")
                alt = row.get("Alternativa Descartada", "") or row.get("Alternativa", "")
                rationale = row.get("Razón Principal", "") or row.get("Motivo", "")
                if decision:
                    adrs_list.append({
                        "decision": decision,
                        "alternative": alt,
                        "rationale": rationale,
                    })

    # Asegura que todos los flujos de la tabla del Mapa Maestro tengan su vista
    for row in master_map_rows:
        f_num = row.get("#", "").strip()
        if not f_num:
            continue
        view_id = f"flow-{f_num}"
        if not any(v.get("id") == view_id for v in views):
            f_name = row.get("Flujo", "").strip()
            f_in = row.get("Entrada", "").strip()
            f_proc = row.get("Proceso", "").strip()
            f_out = row.get("Salida", "").strip()
            pipeline_desc = f"{f_in} → {f_proc} → {f_out}"

            comp_in = ComponentNode(
                id=f"f{f_num}_in",
                label="Entrada",
                sublabel=f_in,
                role="cloud",
                color=ARCHIFY_ROLES["cloud"]["color"],
                icon=ARCHIFY_ROLES["cloud"]["icon"],
            )
            comp_proc = ComponentNode(
                id=f"f{f_num}_proc",
                label=f"Flujo {f_num}: {f_name}",
                sublabel=f_proc,
                role="backend",
                color=ARCHIFY_ROLES["backend"]["color"],
                icon=ARCHIFY_ROLES["backend"]["icon"],
            )
            comp_out = ComponentNode(
                id=f"f{f_num}_out",
                label="Salida",
                sublabel=f_out,
                role="message-bus",
                color=ARCHIFY_ROLES["message-bus"]["color"],
                icon=ARCHIFY_ROLES["message-bus"]["icon"],
            )
            conns = [
                ConnectionEdge(from_node=comp_in.id, to_node=comp_proc.id, label="dispara"),
                ConnectionEdge(from_node=comp_proc.id, to_node=comp_out.id, label="produce"),
            ]
            synth_data = {
                "diagram_type": "flowchart",
                "direction": "LR",
                "components": [comp_in, comp_proc, comp_out],
                "boundaries": [],
                "connections": conns,
            }
            layout_data = compute_blueprint_layout(synth_data)

            view_obj = {
                "id": view_id,
                "name": f"Flujo {f_num}",
                "full_title": f"Flujo {f_num} — {f_name}",
                "is_flow": True,
                "flow_number": int(f_num) if f_num.isdigit() else 0,
                "description": pipeline_desc,
                "scripts": [],
                "invariants": [],
                "flow_meta": {
                    "pipeline": pipeline_desc,
                    "scripts": [],
                    "invariants": [],
                },
                **layout_data,
            }
            views.append(view_obj)

            flows_index.append({
                "id": view_id,
                "number": f_num,
                "name": f"Flujo {f_num} — {f_name}",
                "pipeline": pipeline_desc,
                "scripts": [],
                "invariants_count": 0,
            })

    # Si se registraron ADRs, se agrega la vista de ADRs en la navegación
    if adrs_list:
        views.append({
            "id": "adrs",
            "name": "ADRs",
            "description": "Registro de Decisiones Arquitectónicas tomadas y descartadas",
            "diagram_type": "adrs_table",
            "badge": str(len(adrs_list)),
            "components": [],
            "boundaries": [],
            "connections": [],
        })

    # Ordena flujos en flows_index de forma ascendente
    flows_index.sort(key=lambda f: int(f["number"]) if str(f["number"]).isdigit() else 999)

    # Construcción del índice global de búsqueda instantánea (Ctrl+K)
    for v in views:
        search_index.append({
            "id": f"view-{v['id']}",
            "title": v.get("name", ""),
            "subtitle": v.get("description", "Vista de arquitectura"),
            "category": "vista",
            "targetViewId": v["id"],
        })

        for comp in v.get("components", []):
            search_index.append({
                "id": f"comp-{comp.get('id', '')}",
                "title": comp.get("label", ""),
                "subtitle": f"{comp.get('sublabel', '')} · {v.get('name', '')}",
                "category": "componente",
                "targetViewId": v["id"],
                "nodeId": comp.get("id"),
            })

        for s in v.get("scripts", []):
            search_index.append({
                "id": f"script-{s}",
                "title": s,
                "subtitle": f"Script de {v.get('name', '')}",
                "category": "script",
                "targetViewId": v["id"],
            })

        for inv in v.get("invariants", []):
            search_index.append({
                "id": f"inv-{inv.get('name', '')}",
                "title": inv.get("name", ""),
                "subtitle": f"{inv.get('description', '')} · {v.get('name', '')}",
                "category": "invariante",
                "targetViewId": v["id"],
            })

    for adr in adrs_list:
        search_index.append({
            "id": f"adr-{adr['decision'][:30]}",
            "title": adr["decision"],
            "subtitle": adr["rationale"],
            "category": "adr",
            "targetViewId": "adrs",
        })

    total_components = sum(len(v.get("components", [])) for v in views)

    meta = {
        "title": title,
        "subtitle": subtitle,
        "flows_count": len(flows_index),
        "components_count": total_components,
        "invariants_count": total_invariants,
        "adrs_count": len(adrs_list),
    }

    return {
        "meta": meta,
        "views": views,
        "flows_index": flows_index,
        "adrs": adrs_list,
        "search_index": search_index,
    }


def compile_architecture_to_html(
    input_path: Path,
    template_path: Path,
) -> Tuple[str, str]:
    """Compila el documento Markdown en un archivo HTML interactivo.

    Args:
        input_path: Ruta al archivo Markdown fuente.
        template_path: Ruta a la plantilla HTML base.

    Returns:
        Tupla con (contenido_html_final, sha256_del_markdown).
    """
    md_content = input_path.read_text(encoding="utf-8")
    md_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()

    parsed_data = parse_architecture_markdown(md_content)
    json_str = json.dumps(parsed_data, ensure_ascii=False, indent=2)

    template_content = template_path.read_text(encoding="utf-8")

    # Inyección de datos JSON en la plantilla HTML
    data_script_block = (
        f'<!-- ARCH_DATA_START -->\n'
        f'  <script id="arch-data" type="application/json">\n{json_str}\n  </script>\n'
        f'  <!-- ARCH_DATA_END -->'
    )

    injected_html = re.sub(
        r"<!-- ARCH_DATA_START -->.*?<!-- ARCH_DATA_END -->",
        data_script_block,
        template_content,
        flags=re.DOTALL,
    )

    # Estampa de hash SHA-256 en la cabecera del documento
    final_html = f"<!-- source-sha256: {md_hash} -->\n" + injected_html
    return final_html, md_hash


def verify_html_sync(input_path: Path, output_path: Path) -> bool:
    """Verifica si el archivo HTML está sincronizado con el hash SHA-256 del Markdown fuente.

    Args:
        input_path: Ruta al archivo Markdown fuente.
        output_path: Ruta al archivo HTML generado.

    Returns:
        True si los hashes coinciden, False si hay drift o el archivo no existe.
    """
    if not input_path.exists() or not output_path.exists():
        return False

    md_content = input_path.read_text(encoding="utf-8")
    current_hash = hashlib.sha256(md_content.encode("utf-8")).hexdigest()

    html_content = output_path.read_text(encoding="utf-8")
    hash_match = re.search(r"<!-- source-sha256:\s*([a-f0-9]{64})\s*-->", html_content)

    if not hash_match:
        return False

    return hash_match.group(1) == current_hash


def main() -> int:
    """Punto de entrada de línea de comandos para el compilador de arquitectura HTML."""
    parser = argparse.ArgumentParser(
        description="Compila docs/architecture/architecture.md en docs/architecture/architecture.html estilo Archify Blueprint."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="docs/architecture/architecture.md",
        help="Ruta al archivo Markdown de arquitectura (default: docs/architecture/architecture.md)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="docs/architecture/architecture.html",
        help="Ruta al archivo HTML de salida (default: docs/architecture/architecture.html)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica la sincronía entre el Markdown y el HTML generado sin modificar archivos.",
    )

    args = parser.parse_args()

    input_file = Path(args.input).resolve()
    output_file = Path(args.output).resolve()

    if not input_file.exists():
        print(f"ERROR: Archivo de entrada no encontrado: {input_file}", file=sys.stderr)
        return 1

    if args.check:
        is_synced = verify_html_sync(input_file, output_file)
        if is_synced:
            print(f"OK: {output_file.name} sincronizado con {input_file.name}")
            return 0
        else:
            print(
                f"DRIFT: {output_file.name} desincronizado o ausente respecto a {input_file.name}. Ejecute render_arch_html.py para regenerarlo.",
                file=sys.stderr,
            )
            return 1

    # Resolución de ruta a la plantilla HTML
    repo_root = Path(__file__).resolve().parent.parent
    template_file = repo_root / "templates" / "html" / "arch_viewer.html"

    if not template_file.exists():
        print(f"ERROR: Plantilla HTML no encontrada en: {template_file}", file=sys.stderr)
        return 1

    output_file.parent.mkdir(parents=True, exist_ok=True)
    html_out, md_hash = compile_architecture_to_html(input_file, template_file)
    output_file.write_text(html_out, encoding="utf-8")

    print(f"OK: Generado {output_file} exitosamente (source-sha256: {md_hash[:12]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
