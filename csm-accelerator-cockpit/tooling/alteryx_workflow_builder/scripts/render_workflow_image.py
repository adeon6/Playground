#!/usr/bin/env python3
"""Render an Alteryx workflow XML file into a PNG canvas preview.

This is a lightweight workflow-image re-creator inspired by the Imager macro.
It does not use Alteryx Designer to export the canvas. Instead, it:
1. Parses the workflow XML.
2. Reconstructs node geometry and container hierarchy.
3. Draws containers, text boxes, tools, annotations, and connectors with Pillow.

The output is a visual approximation meant for review and iteration.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


DEFAULT_TOOL_WIDTH = 42
DEFAULT_TOOL_HEIGHT = 36
CANVAS_PADDING = 140
CONTAINER_HEADER_HEIGHT = 20
CONTAINER_BORDER_WIDTH = 2
LABEL_TOP_GAP = 4
LABEL_LINE_HEIGHT = 12
DEFAULT_WRAP = 16
RIGHT_EDGE_VISUAL_INSET = 0
BOTTOM_EDGE_VISUAL_INSET = 0
POSITION_TOLERANCE = 12

TOOL_COLORS: dict[str, tuple[int, int, int]] = {
    "DbFileInput": (47, 156, 135),
    "DbFileOutput": (47, 156, 135),
    "TextInput": (47, 156, 135),
    "Formula": (28, 102, 184),
    "MultiFieldFormula": (28, 102, 184),
    "MultiRowFormula": (28, 102, 184),
    "Filter": (30, 123, 188),
    "Sort": (33, 123, 176),
    "Summarize": (34, 112, 180),
    "CrossTab": (214, 102, 31),
    "Transpose": (214, 102, 31),
    "Unique": (98, 74, 163),
    "Join": (98, 74, 163),
    "JoinMultiple": (98, 74, 163),
    "Union": (98, 74, 163),
    "Render": (189, 128, 35),
    "PortfolioComposerText": (189, 128, 35),
    "PortfolioComposerTable": (189, 128, 35),
    "PortfolioComposerRender": (189, 128, 35),
    "Action": (214, 102, 31),
    "ControlParam": (90, 90, 90),
    "DropDown": (73, 73, 73),
}


@dataclass
class Node:
    tool_id: str
    node_type: str
    x: float
    y: float
    width: float | None
    height: float | None
    annotation: str
    text: str
    level: int
    parent_id: str | None = None
    visible_label_lines: int = 0

    @property
    def draw_width(self) -> float:
        return self.width if self.width is not None else DEFAULT_TOOL_WIDTH

    @property
    def draw_height(self) -> float:
        return self.height if self.height is not None else DEFAULT_TOOL_HEIGHT

    @property
    def max_x(self) -> float:
        return self.x + self.draw_width

    @property
    def max_y(self) -> float:
        return self.y + self.draw_height

    @property
    def visible_max_y(self) -> float:
        label_height = 0
        if self.visible_label_lines > 0:
            label_height = LABEL_TOP_GAP + self.visible_label_lines * LABEL_LINE_HEIGHT
        return self.max_y + label_height


@dataclass
class Connection:
    origin_id: str
    destination_id: str
    is_wireless: bool


def parse_color(hex_or_name: str | None, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if not hex_or_name:
        return fallback
    value = hex_or_name.strip()
    if value.startswith("#") and len(value) == 7:
        try:
            return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            return fallback
    named = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        "grey": (128, 128, 128),
        "gray": (128, 128, 128),
        "yellow": (255, 248, 196),
    }
    return named.get(value.lower(), fallback)


def plugin_to_type(plugin: str) -> str:
    if not plugin:
        return "Macro"
    part = plugin.split(".")[-1]
    return part if len(part) >= 3 else plugin


def annotation_text(node: ET.Element) -> str:
    ann = node.find("./Properties/Annotation")
    if ann is None:
        return ""
    text = ann.findtext("AnnotationText")
    if text:
        return text.strip()
    default = ann.findtext("DefaultAnnotationText")
    return default.strip() if default else ""


def node_text(node: ET.Element, node_type: str) -> str:
    config = node.find("./Properties/Configuration")
    if config is None:
        return ""
    if node_type == "TextBox":
        text = config.findtext("Text")
        return text.strip() if text else ""
    if "Container" in node_type:
        caption = config.findtext("Caption")
        return caption.strip() if caption else ""
    return ""


def rect_inside(child: tuple[float, float, float, float], parent: tuple[float, float, float, float], tolerance: float = POSITION_TOLERANCE) -> bool:
    cx, cy, cw, ch = child
    px, py, pw, ph = parent
    return (
        cx >= px - tolerance
        and cy >= py - tolerance
        and cx + cw <= px + pw + tolerance
        and cy + ch <= py + ph + tolerance
    )


def effective_position(
    raw_x: float,
    raw_y: float,
    width: float | None,
    height: float | None,
    parent_rect: tuple[float, float, float, float] | None,
) -> tuple[float, float]:
    if parent_rect is None:
        return raw_x, raw_y

    px, py, pw, ph = parent_rect
    child_rect = (
        raw_x,
        raw_y,
        width if width is not None else DEFAULT_TOOL_WIDTH,
        height if height is not None else DEFAULT_TOOL_HEIGHT,
    )
    if rect_inside(child_rect, parent_rect):
        return raw_x, raw_y

    # Designer usually stores child node positions as absolute canvas coordinates,
    # even when they live under a Tool Container. Some generated or hand-edited
    # XML uses local container coordinates instead. Only offset when the child
    # position actually looks local to the parent container.
    looks_relative = (
        raw_x >= -POSITION_TOLERANCE
        and raw_y >= -POSITION_TOLERANCE
        and raw_x <= pw + POSITION_TOLERANCE
        and raw_y <= ph + POSITION_TOLERANCE
    )
    if looks_relative:
        return raw_x + px, raw_y + py
    return raw_x, raw_y


def parse_nodes(
    parent: ET.Element,
    level: int = 0,
    parent_rect: tuple[float, float, float, float] | None = None,
    parent_id: str | None = None,
) -> list[Node]:
    nodes: list[Node] = []
    for node in parent.findall("./Node"):
        gui = node.find("./GuiSettings")
        plugin = gui.attrib.get("Plugin", "") if gui is not None else ""
        node_type = plugin_to_type(plugin)
        pos = node.find("./GuiSettings/Position")
        raw_x = float(pos.attrib.get("x", "0")) if pos is not None else 0.0
        raw_y = float(pos.attrib.get("y", "0")) if pos is not None else 0.0
        width = float(pos.attrib["width"]) if pos is not None and "width" in pos.attrib else None
        height = float(pos.attrib["height"]) if pos is not None and "height" in pos.attrib else None
        x, y = effective_position(raw_x, raw_y, width, height, parent_rect)
        ann_text = annotation_text(node)
        text = node_text(node, node_type)
        label = ann_text or text or node_type
        wrap_width = max(8, int((width if width is not None else DEFAULT_TOOL_WIDTH) / 2.7)) if node_type == "TextBox" else DEFAULT_WRAP
        wrapped = wrap(label, wrap_width)
        lines = len(wrapped.splitlines()) if wrapped else 0
        nodes.append(
            Node(
                tool_id=node.attrib["ToolID"],
                node_type=node_type,
                x=x,
                y=y,
                width=width,
                height=height,
                annotation=ann_text,
                text=text,
                level=level,
                parent_id=parent_id,
                visible_label_lines=0 if ("Container" in node_type or node_type == "TextBox") else lines,
            )
        )
        child_nodes = node.find("./ChildNodes")
        if child_nodes is not None:
            child_rect = (
                x,
                y,
                width if width is not None else DEFAULT_TOOL_WIDTH,
                height if height is not None else DEFAULT_TOOL_HEIGHT,
            )
            nodes.extend(parse_nodes(child_nodes, level + 1, child_rect, node.attrib["ToolID"]))
    return nodes


def expand_container_bounds(nodes: list[Node], root_xml_node: ET.Element) -> None:
    node_map = {node.tool_id: node for node in nodes}
    child_map: dict[str, list[Node]] = {}
    margin_map: dict[str, float] = {}

    for node in nodes:
        if node.parent_id is not None:
            child_map.setdefault(node.parent_id, []).append(node)

    for node in nodes:
        if "Container" not in node.node_type:
            continue
        xml_node = root_xml_node.find(f".//Node[@ToolID='{node.tool_id}']")
        style = xml_node.find("./Properties/Configuration/Style") if xml_node is not None else None
        margin = float(style.attrib.get("Margin", "18")) if style is not None else 18.0
        margin_map[node.tool_id] = margin

    for node in sorted((n for n in nodes if "Container" in n.node_type), key=lambda n: n.level, reverse=True):
        children = child_map.get(node.tool_id, [])
        if not children:
            continue
        margin = margin_map.get(node.tool_id, 18.0)
        min_x = min(child.x for child in children) - margin
        max_x = max(child.max_x for child in children) + margin
        min_y = min(child.y for child in children) - (CONTAINER_HEADER_HEIGHT + margin)
        max_y = max(child.visible_max_y for child in children) + margin

        node.x = min(node.x, min_x)
        node.y = min(node.y, min_y)
        node.width = max(node.max_x, max_x) - node.x
        node.height = max(node.max_y, max_y) - node.y


def parse_connections(root: ET.Element) -> list[Connection]:
    connections: list[Connection] = []
    for con in root.findall(".//Connections/Connection"):
        origin = con.find("Origin")
        destination = con.find("Destination")
        if origin is None or destination is None:
            continue
        connections.append(
            Connection(
                origin_id=origin.attrib.get("ToolID", ""),
                destination_id=destination.attrib.get("ToolID", ""),
                is_wireless=con.attrib.get("Wireless", "False") == "True",
            )
        )
    return connections


def wrap(text: str, width: int) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def draw_polyline(draw: ImageDraw.ImageDraw, points: Iterable[tuple[float, float]], fill: tuple[int, int, int], width: int) -> None:
    pts = list(points)
    for start, end in zip(pts, pts[1:]):
        draw.line([start, end], fill=fill, width=width)


def connector_points(origin: Node, destination: Node) -> list[tuple[float, float]]:
    x1 = origin.x + DEFAULT_TOOL_WIDTH
    y1 = origin.y + DEFAULT_TOOL_HEIGHT / 2
    x2 = destination.x
    y2 = destination.y + DEFAULT_TOOL_HEIGHT / 2
    step = max(26, abs(x2 - x1) * 0.22)
    mid1 = x1 + step
    mid2 = x2 - step
    if mid2 < mid1:
        mid1 = x1 + 18
        mid2 = x2 - 18
    return [(x1, y1), (mid1, y1), (mid2, y2), (x2, y2)]


def load_workflow_root(path: Path) -> ET.Element:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag == "UserTelemetry":
        body = root.find("./Body/AlteryxDocument")
        if body is None:
            raise ValueError("UserTelemetry wrapper found, but AlteryxDocument body is missing.")
        return body
    if root.tag != "AlteryxDocument":
        nested = root.find(".//AlteryxDocument")
        if nested is None:
            raise ValueError(f"Unsupported root tag: {root.tag}")
        return nested
    return root


def canvas_size(nodes: list[Node]) -> tuple[int, int]:
    max_x = max((node.max_x for node in nodes), default=500)
    max_y = max((node.visible_max_y for node in nodes), default=300)
    return (int(max_x + CANVAS_PADDING), int(max_y + CANVAS_PADDING))


def draw_container(draw: ImageDraw.ImageDraw, node: Node, root_xml_node: ET.Element) -> None:
    xml_node = root_xml_node.find(f".//Node[@ToolID='{node.tool_id}']")
    style = xml_node.find("./Properties/Configuration/Style") if xml_node is not None else None
    fill = parse_color(style.attrib.get("FillColor") if style is not None else None, (226, 236, 246))
    border = parse_color(style.attrib.get("BorderColor") if style is not None else None, (91, 113, 138))
    text_color = parse_color(style.attrib.get("TextColor") if style is not None else None, (30, 30, 30))
    x1, y1, x2, y2 = node.x, node.y, node.max_x, node.max_y
    x2 += RIGHT_EDGE_VISUAL_INSET
    y2 += BOTTOM_EDGE_VISUAL_INSET
    draw.rectangle([x1, y1, x2, y2], fill=fill, outline=border, width=CONTAINER_BORDER_WIDTH)
    draw.line([(x1, y1 + CONTAINER_HEADER_HEIGHT), (x2, y1 + CONTAINER_HEADER_HEIGHT)], fill=border, width=1)
    draw.ellipse([x1 + 6, y1 + 4, x1 + 18, y1 + 16], fill=(40, 140, 230), outline=(255, 255, 255), width=1)
    caption = node.text or node.annotation or f"Container {node.tool_id}"
    caption_x = x1 + max(26, (x2 - x1 - len(caption) * 5) / 2)
    draw.text((caption_x, y1 + 3), caption, fill=text_color)


def draw_textbox(draw: ImageDraw.ImageDraw, node: Node, root_xml_node: ET.Element) -> None:
    xml_node = root_xml_node.find(f".//Node[@ToolID='{node.tool_id}']")
    config = xml_node.find("./Properties/Configuration") if xml_node is not None else None
    fill_node = config.find("FillColor") if config is not None else None
    text_node = config.find("TextColor") if config is not None else None
    fill = (
        (int(fill_node.attrib["r"]), int(fill_node.attrib["g"]), int(fill_node.attrib["b"]))
        if fill_node is not None and {"r", "g", "b"} <= set(fill_node.attrib)
        else parse_color(fill_node.attrib.get("name") if fill_node is not None else None, (255, 248, 196))
    )
    text_color = (
        (int(text_node.attrib["r"]), int(text_node.attrib["g"]), int(text_node.attrib["b"]))
        if text_node is not None and {"r", "g", "b"} <= set(text_node.attrib)
        else parse_color(text_node.attrib.get("name") if text_node is not None else None, (0, 0, 0))
    )
    draw.rounded_rectangle([node.x, node.y, node.max_x, node.max_y], radius=6, fill=fill, outline=(40, 40, 40), width=1)
    draw.multiline_text((node.x + 8, node.y + 8), wrap(node.text, max(18, int(node.draw_width / 7))), fill=text_color, spacing=2)


def tool_fill(node_type: str) -> tuple[int, int, int]:
    return TOOL_COLORS.get(node_type, (120, 120, 120))


def tool_abbrev(node_type: str) -> str:
    clean = node_type.replace("Alteryx", "").replace("PortfolioComposer", "")
    if len(clean) <= 4:
        return clean.upper()
    return "".join(ch for ch in clean if ch.isupper())[:4] or clean[:4].upper()


def draw_tool(draw: ImageDraw.ImageDraw, node: Node) -> None:
    fill = tool_fill(node.node_type)
    draw.rounded_rectangle([node.x, node.y, node.x + DEFAULT_TOOL_WIDTH, node.y + DEFAULT_TOOL_HEIGHT], radius=8, fill=fill, outline=(255, 255, 255), width=2)
    abbr = tool_abbrev(node.node_type)
    tx = node.x + 7
    ty = node.y + 10
    draw.text((tx, ty), abbr, fill=(255, 255, 255))
    label = node.annotation or node.text or node.node_type
    draw.multiline_text((node.x, node.y + DEFAULT_TOOL_HEIGHT + LABEL_TOP_GAP), wrap(label, DEFAULT_WRAP), fill=(0, 0, 0), spacing=1)


def render(workflow_path: Path, output_path: Path) -> None:
    root = load_workflow_root(workflow_path)
    nodes_root = root.find("./Nodes")
    if nodes_root is None:
        raise ValueError("Workflow has no Nodes section.")
    nodes = parse_nodes(nodes_root)
    expand_container_bounds(nodes, root)
    node_map = {node.tool_id: node for node in nodes}
    connections = parse_connections(root)

    width, height = canvas_size(nodes)
    image = Image.new("RGBA", (width, height), (245, 248, 251, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default()
        del font
    except Exception:
        pass

    version = root.attrib.get("yxmdVer", "")
    draw.text((width - 420, 8), workflow_path.name, fill=(150, 150, 150))
    if version:
        draw.text((width - 420, 22), f"Designer version: {version}", fill=(170, 170, 170))

    for level in sorted({node.level for node in nodes}):
        level_nodes = [n for n in nodes if n.level == level]
        # Always paint containers first, then text/tool contents on top of them.
        for node in [n for n in level_nodes if "Container" in n.node_type]:
            if "Container" in node.node_type:
                draw_container(draw, node, root)
        for node in [n for n in level_nodes if "Container" not in n.node_type]:
            if node.node_type == "TextBox":
                draw_textbox(draw, node, root)
            else:
                draw_tool(draw, node)

    for con in connections:
        origin = node_map.get(con.origin_id)
        destination = node_map.get(con.destination_id)
        if origin is None or destination is None:
            continue
        color = (165, 165, 165) if con.is_wireless else (60, 60, 60)
        draw_polyline(draw, connector_points(origin, destination), color, 2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an Alteryx workflow canvas preview to PNG.")
    parser.add_argument("workflow", help="Path to .yxmd/.yxmc/.yxwz file")
    parser.add_argument("--out", help="Output PNG path. Defaults next to the workflow.", default=None)
    args = parser.parse_args()

    workflow_path = Path(args.workflow).expanduser().resolve()
    if not workflow_path.exists():
        raise SystemExit(f"Workflow not found: {workflow_path}")

    output_path = Path(args.out).expanduser().resolve() if args.out else workflow_path.with_suffix(".png")
    render(workflow_path, output_path)
    print(f"Rendered {workflow_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
