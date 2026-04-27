#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

DEFAULT_TEXTBOX_FONT = 14.0
DEFAULT_ANNOT_FONT = 14.0
LINE_HEIGHT_MULT = 1.25
TEXT_PAD_X = 10.0
TEXT_PAD_Y = 10.0
CONTAINMENT_MARGIN = 4.0
BORDER_BAND = 3.0
DEFAULT_TOOL_WIDTH = 36.0
DEFAULT_TOOL_HEIGHT = 36.0
POSITION_TOLERANCE = 12.0
TEXTBOX_PLUGIN = 'AlteryxGuiToolkit.TextBox.TextBox'
TOOL_CONTAINER_PLUGIN = 'AlteryxGuiToolkit.ToolContainer.ToolContainer'

FORBIDDEN_VISIBLE_TOKEN_RE = re.compile(r"\bobj\b", re.IGNORECASE)
FORBIDDEN_LINE_END_WORDS = {"or", "and", "the", "a", "an"}
VISIBLE_TEXT_XPATHS = (
    "./Properties/Configuration/Text",
    "./Properties/Annotation/AnnotationText",
    "./Properties/Annotation/DefaultAnnotationText",
)

CHECK_IMPLEMENTATION = {
    "R-MACRO-001": "check_macro_integrity",
    "R-MACRO-002": "check_macro_integrity",
    "R-MACRO-003": "check_macro_integrity",
    "R-COMP-001C": "check_header_hierarchy",
    "R-COMP-001D": "check_header_hierarchy",
    "R-COMP-009A": "check_contextual_containers",
    "R-LAYOUT-001": "check_layout_containment",
    "R-LAYOUT-002": "check_layout_containment",
    "R-LAYOUT-003": "check_layout_containment",
    "R-LAYOUT-008": "check_layout_containment",
    "R-LAYOUT-009": "check_layout_containment",
    "R-LAYOUT-011": "check_layout_containment",
    "R-ANN-001": "check_layout_containment",
    "R-ANN-002": "check_layout_containment",
    "R-TEXT-001": "check_text_hygiene",
    "R-TEXT-002": "check_text_hygiene",
    "R-NAME-001": "check_naming",
    "R-NAME-002": "check_naming",
    "R-CONFIG-001": "check_configuration",
    "R-CONFIG-003": "check_configuration",
    "R-CONFIG-002": "check_structure",
}


@dataclass
class Violation:
    file: str
    rule: str
    mistake_id: str
    element_id: str
    severity: str
    description: str


@dataclass
class WorkflowContext:
    path: Path
    root: ET.Element


@dataclass
class LayoutNode:
    node: ET.Element
    tool_id: str
    plugin: str
    x: float
    y: float
    width: float
    height: float
    parent_tool_id: str | None
    depth: int

    @property
    def rect(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)


def as_float(v: str | None, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default


def split_lines(text: str) -> List[str]:
    return [""] if not text else text.split("\n")


def estimate_line_width(line: str, font_size: float) -> float:
    # Conservative estimator (slightly overestimates)
    width = 0.0
    for ch in line:
        o = ord(ch)
        if ch.isspace():
            width += font_size * 0.36
        elif 0x4E00 <= o <= 0x9FFF or 0x3040 <= o <= 0x30FF or 0xAC00 <= o <= 0xD7AF:
            width += font_size * 1.05
        elif ch.isupper():
            width += font_size * 0.75
        elif ch.isdigit():
            width += font_size * 0.68
        elif ch in '-_/\\.':
            width += font_size * 0.52
        else:
            width += font_size * 0.64
    return width + 4.0


def text_rect(text: str, x: float, y: float, font_size: float) -> Tuple[float, float, float, float]:
    lines = split_lines(text)
    max_width = max((estimate_line_width(l, font_size) for l in lines), default=1.0)
    width = max(1.0, max_width)
    height = max(1.0, len(lines) * font_size * LINE_HEIGHT_MULT)
    return (x, y, width, height)


def rect_inside(inner: Tuple[float, float, float, float], outer: Tuple[float, float, float, float], margin: float) -> bool:
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return (
        ix >= ox + margin and
        iy >= oy + margin and
        ix + iw <= ox + ow - margin and
        iy + ih <= oy + oh - margin
    )


def rect_intersects(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def border_band_rects(rect: Tuple[float, float, float, float], band: float) -> List[Tuple[float, float, float, float]]:
    x, y, w, h = rect
    return [
        (x, y, w, band),
        (x, y + h - band, w, band),
        (x, y, band, h),
        (x + w - band, y, band, h),
    ]


def rect_inside_loose(inner: Tuple[float, float, float, float], outer: Tuple[float, float, float, float], tolerance: float = POSITION_TOLERANCE) -> bool:
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return (
        ix >= ox - tolerance and
        iy >= oy - tolerance and
        ix + iw <= ox + ow + tolerance and
        iy + ih <= oy + oh + tolerance
    )


def has_non_printable_chars(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if code in (0xFFFD, 0xFFFC):
            return True
        if code < 32 and ch not in ("\n", "\r", "\t"):
            return True
    return False


def kit_slug_from_path(path: Path) -> str:
    parts = list(path.parts)
    lower = [p.lower() for p in parts]
    if "office_of_finance_ai_starter_kits" in lower:
        idx = lower.index("office_of_finance_ai_starter_kits")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def starter_kit_group(path: Path) -> str:
    parts = list(path.parts)
    lower = [p.lower() for p in parts]
    if "office_of_finance_ai_starter_kits" in lower:
        idx = lower.index("office_of_finance_ai_starter_kits")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return path.parent.name


def is_managed_portfolio_workflow(path: Path) -> bool:
    lower = [p.lower() for p in path.parts]
    return "office_of_finance_ai_starter_kits" in lower or "starter_kits" in lower


def collect_visible_text_fields(root: ET.Element) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for node in iter_workflow_nodes(root):
        tid = node.get('ToolID') or ''
        for xp in VISIBLE_TEXT_XPATHS:
            elem = node.find(xp)
            if elem is None or elem.text is None:
                continue
            out.append((tid, xp, elem.text))
    return out


def iter_workflow_nodes(root: ET.Element) -> List[ET.Element]:
    out: List[ET.Element] = []

    def walk(node: ET.Element) -> None:
        out.append(node)
        for child in node.findall('./ChildNodes/Node'):
            walk(child)

    for node in root.findall('./Nodes/Node'):
        walk(node)
    return out


def effective_position(
    raw_x: float,
    raw_y: float,
    width: float,
    height: float,
    parent_rect: Tuple[float, float, float, float] | None,
) -> Tuple[float, float]:
    if parent_rect is None:
        return raw_x, raw_y
    child_rect = (raw_x, raw_y, width, height)
    if rect_inside_loose(child_rect, parent_rect):
        return raw_x, raw_y
    return raw_x + parent_rect[0], raw_y + parent_rect[1]


def collect_layout_nodes(root: ET.Element) -> List[LayoutNode]:
    out: List[LayoutNode] = []

    def walk(parent: ET.Element, owner_rect: Tuple[float, float, float, float] | None, owner_id: str | None, depth: int) -> None:
        for node in parent.findall('./Node'):
            gs = node.find('./GuiSettings')
            plugin = gs.get('Plugin', '') if gs is not None else ''
            pos = gs.find('./Position') if gs is not None else None
            raw_x = as_float(pos.get('x') if pos is not None else None)
            raw_y = as_float(pos.get('y') if pos is not None else None)
            width = as_float(pos.get('width') if pos is not None else None, DEFAULT_TOOL_WIDTH)
            height = as_float(pos.get('height') if pos is not None else None, DEFAULT_TOOL_HEIGHT)
            x, y = effective_position(raw_x, raw_y, width, height, owner_rect)
            layout = LayoutNode(
                node=node,
                tool_id=node.get('ToolID') or '',
                plugin=plugin,
                x=x,
                y=y,
                width=width,
                height=height,
                parent_tool_id=owner_id,
                depth=depth,
            )
            out.append(layout)
            child_nodes = node.find('./ChildNodes')
            if child_nodes is not None:
                walk(child_nodes, layout.rect, layout.tool_id, depth + 1)

    nodes_root = root.find('./Nodes')
    if nodes_root is not None:
        walk(nodes_root, None, None, 0)
    return out


def textbox_text(node: ET.Element) -> str:
    return (node.findtext('./Properties/Configuration/Text') or '').strip()


def textbox_font_size(node: ET.Element) -> float:
    font = node.find('./Properties/Configuration/Font')
    return as_float(font.get('size') if font is not None else None, DEFAULT_TEXTBOX_FONT)


def textbox_fill_is_visible(node: ET.Element) -> bool:
    fill = node.find('./Properties/Configuration/FillColor')
    if fill is None:
        return False

    if {'r', 'g', 'b'} <= set(fill.attrib):
        try:
            rgb = tuple(int(fill.attrib[k]) for k in ('r', 'g', 'b'))
        except Exception:
            return False
        return not all(channel >= 248 for channel in rgb)

    name = (fill.get('name') or '').strip().lower()
    return name not in {'', 'white', 'transparent', 'none'}


def discover_workflows(paths: Sequence[str], dirs: Sequence[str], file_lists: Sequence[str]) -> List[Path]:
    found: List[Path] = []

    for wf in paths:
        p = Path(wf)
        if p.is_dir():
            found.extend(sorted(p.rglob('*.yxmd')))
        elif p.suffix.lower() == '.yxmd' and p.exists():
            found.append(p)

    for d in dirs:
        dp = Path(d)
        if dp.exists():
            found.extend(sorted(dp.rglob('*.yxmd')))

    for fl in file_lists:
        fp = Path(fl)
        if not fp.exists():
            continue
        for line in fp.read_text(encoding='utf-8', errors='ignore').splitlines():
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            p = Path(s)
            if p.exists() and p.suffix.lower() == '.yxmd':
                found.append(p)

    uniq: Dict[str, Path] = {}
    for p in found:
        rp = p.resolve()
        uniq[str(rp)] = rp
    return [uniq[k] for k in sorted(uniq.keys())]


def make_violation(path: Path, rule: str, mistake_id: str, element_id: str, severity: str, description: str) -> Violation:
    return Violation(file=str(path), rule=rule, mistake_id=mistake_id, element_id=element_id, severity=severity, description=description)


def load_plugins_in_order(root: ET.Element) -> List[str]:
    rows: List[Tuple[int, str]] = []
    for n in iter_workflow_nodes(root):
        tid_raw = n.get('ToolID') or '0'
        try:
            tid = int(tid_raw)
        except Exception:
            tid = 0
        gs = n.find('./GuiSettings')
        plugin = gs.get('Plugin', '') if gs is not None else ''
        rows.append((tid, plugin))
    rows.sort(key=lambda t: t[0])
    return [r[1] for r in rows]


def load_structure_baselines(skill_dir: Path) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    files = {
        '01': skill_dir / 'golden' / 'workflow_01.yxmd',
        '02': skill_dir / 'golden' / 'workflow_02.yxmd',
        'base': skill_dir / 'templates' / 'base.yxmd',
    }
    for k, p in files.items():
        try:
            if p.exists():
                out[k] = load_plugins_in_order(ET.parse(p).getroot())
        except Exception:
            continue
    return out


def check_macro_integrity(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    expected_slug = kit_slug_from_path(ctx.path).lower()

    for node in iter_workflow_nodes(ctx.root):
        tid = node.get('ToolID') or ''
        eng = node.find('./EngineSettings')
        macro = '' if eng is None else (eng.get('Macro') or '').strip()
        if not macro:
            continue

        if re.match(r'^[A-Za-z]:\\', macro) or macro.startswith('\\') or macro.startswith('/'):
            out.append(make_violation(ctx.path, 'R-MACRO-001', 'M-MACRO-002', tid, 'critical', f'Absolute/UNC/rooted macro path: {macro}'))
            continue

        if '..\\..\\..\\..\\' in macro or '../../../../../' in macro:
            out.append(make_violation(ctx.path, 'R-MACRO-002', 'M-MACRO-002', tid, 'major', f'Forbidden macro path escape depth: {macro}'))

        if expected_slug != 'unknown':
            m = re.search(r'Starter Kits\\([^\\]+)\\Macros', macro, flags=re.IGNORECASE)
            if m and m.group(1).lower() != expected_slug:
                out.append(make_violation(ctx.path, 'R-MACRO-003', 'M-MACRO-001', tid, 'critical', f'Macro root mismatch expected={expected_slug} got={m.group(1)} path={macro}'))

        if 'accounting_automation' in macro.lower() and expected_slug not in ('unknown', 'accounting_automation'):
            out.append(make_violation(ctx.path, 'R-MACRO-002', 'M-MACRO-001', tid, 'major', f'Forbidden macro token for this kit: {macro}'))

    return out


def collect_comment_boxes(root: ET.Element) -> List[dict]:
    layout_by_id = {layout.tool_id: layout for layout in collect_layout_nodes(root)}
    boxes: List[dict] = []
    for node in iter_workflow_nodes(root):
        gs = node.find('./GuiSettings')
        if gs is None or gs.get('Plugin') != 'AlteryxGuiToolkit.TextBox.TextBox':
            continue
        layout = layout_by_id.get(node.get('ToolID') or '')
        if layout is None:
            continue
        cfg = node.find('./Properties/Configuration')
        shape = ''
        if cfg is not None:
            sh = cfg.find('./Shape')
            shape = sh.get('shape') if sh is not None and sh.get('shape') else ''
        rect = layout.rect
        boxes.append({'id': node.get('ToolID') or '', 'shape': shape, 'rect': rect, 'node': node})
    return boxes


def collect_container_boxes(root: ET.Element) -> List[dict]:
    boxes: List[dict] = []
    for layout in collect_layout_nodes(root):
        if layout.plugin != TOOL_CONTAINER_PLUGIN:
            continue
        boxes.append(
            {
                'id': layout.tool_id,
                'shape': 'container',
                'rect': layout.rect,
                'node': layout.node,
                'depth': layout.depth,
                'parent_tool_id': layout.parent_tool_id,
            }
        )
    return boxes


def is_actual_tool_plugin(plugin: str) -> bool:
    return plugin not in (TEXTBOX_PLUGIN, TOOL_CONTAINER_PLUGIN)


def container_context_label(node: ET.Element) -> str:
    cfg = node.find('./Properties/Configuration')
    ann = node.find('./Properties/Annotation')
    caption = '' if cfg is None else (cfg.findtext('./Caption') or '').strip()
    annotation = '' if ann is None else ((ann.findtext('./AnnotationText') or ann.findtext('./DefaultAnnotationText') or '').strip())
    return caption or annotation


def is_ancestor(ancestor_id: str, child_id: str, by_id: Dict[str, LayoutNode]) -> bool:
    current = by_id.get(child_id)
    seen = set()
    while current is not None and current.parent_tool_id and current.parent_tool_id not in seen:
        if current.parent_tool_id == ancestor_id:
            return True
        seen.add(current.parent_tool_id)
        current = by_id.get(current.parent_tool_id)
    return False


def owner_section_for_tool(tool_x: float, tool_y: float, section_boxes: List[dict]) -> dict | None:
    tool_center = (tool_x + 18.0, tool_y + 18.0)
    owner = None
    area_best = float('inf')
    for b in section_boxes:
        bx, by, bw, bh = b['rect']
        if bx <= tool_center[0] <= bx + bw and by <= tool_center[1] <= by + bh:
            area = bw * bh
            if area < area_best:
                area_best = area
                owner = b
    return owner


def check_header_hierarchy(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    header_boxes = [
        layout for layout in collect_layout_nodes(ctx.root)
        if layout.depth == 0 and layout.plugin == TEXTBOX_PLUGIN and textbox_text(layout.node)
    ]
    if len(header_boxes) < 2:
        return out

    top_y = min(layout.y for layout in header_boxes)
    header_boxes = [layout for layout in header_boxes if layout.y <= top_y + 220.0]
    if len(header_boxes) < 2:
        return out

    title = max(
        header_boxes,
        key=lambda layout: (textbox_font_size(layout.node), -layout.y, len(textbox_text(layout.node))),
    )
    if textbox_font_size(title.node) < 14.0:
        return out

    if title.y > top_y + 2.0:
        out.append(
            make_violation(
                ctx.path,
                'R-COMP-001C',
                'M-COMP-002',
                title.tool_id,
                'major',
                f'Primary title textbox {title.tool_id} is not the top-most header element',
            )
        )

    title_bottom = title.y + title.height
    for layout in header_boxes:
        if layout.tool_id == title.tool_id:
            continue
        if layout.y < title_bottom - 2.0:
            out.append(
                make_violation(
                    ctx.path,
                    'R-COMP-001C',
                    'M-COMP-002',
                    layout.tool_id,
                    'major',
                    f'Header textbox {layout.tool_id} is not placed below the primary title textbox {title.tool_id}',
                )
            )
        if not textbox_fill_is_visible(layout.node):
            out.append(
                make_violation(
                    ctx.path,
                    'R-COMP-001D',
                    'M-COMP-003',
                    layout.tool_id,
                    'major',
                    f'Header textbox {layout.tool_id} lacks a visible intentional fill style',
                )
            )

    return out


def check_contextual_containers(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    layout_nodes = collect_layout_nodes(ctx.root)
    layout_by_id = {layout.tool_id: layout for layout in layout_nodes}

    for layout in layout_nodes:
        if not is_actual_tool_plugin(layout.plugin):
            continue

        current = layout
        seen: set[str] = set()
        found_context = False
        while current.parent_tool_id and current.parent_tool_id not in seen:
            seen.add(current.parent_tool_id)
            parent = layout_by_id.get(current.parent_tool_id)
            if parent is None:
                break
            if parent.plugin == TOOL_CONTAINER_PLUGIN and container_context_label(parent.node):
                found_context = True
                break
            current = parent

        if not found_context:
            out.append(
                make_violation(
                    ctx.path,
                    'R-COMP-009A',
                    'M-COMP-001',
                    layout.tool_id,
                    'major',
                    f'Tool {layout.tool_id} is not enclosed by a clearly titled Tool Container',
                )
            )

    return out


def check_layout_containment(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    layout_nodes = collect_layout_nodes(ctx.root)
    layout_by_id = {layout.tool_id: layout for layout in layout_nodes}
    comment_boxes = collect_comment_boxes(ctx.root)
    container_boxes = collect_container_boxes(ctx.root)
    boxes = comment_boxes + container_boxes
    section_boxes = [b for b in comment_boxes if b['shape'] == '0' and b['rect'][2] >= 200 and b['rect'][3] >= 120]
    section_boxes.extend(container_boxes)

    # Textbox/comment text containment
    for b in comment_boxes:
        cfg = b['node'].find('./Properties/Configuration')
        if cfg is None:
            continue
        text = (cfg.findtext('./Text') or '').strip()
        if not text:
            continue
        font = cfg.find('./Font')
        fs = as_float(font.get('size') if font is not None else None, DEFAULT_TEXTBOX_FONT)
        bx, by, _, _ = b['rect']
        tr = text_rect(text, bx + TEXT_PAD_X, by + TEXT_PAD_Y, fs)

        if not rect_inside(tr, b['rect'], CONTAINMENT_MARGIN):
            out.append(make_violation(ctx.path, 'R-LAYOUT-002', 'M-LAYOUT-002', b['id'], 'major', f'Text not contained in box {b["id"]}: text_rect={tr} box_rect={b["rect"]}'))

        for band in border_band_rects(b['rect'], BORDER_BAND):
            if rect_intersects(tr, band):
                out.append(make_violation(ctx.path, 'R-LAYOUT-003', 'M-LAYOUT-002', b['id'], 'major', f'Text intersects border band in box {b["id"]}: text_rect={tr} box_rect={b["rect"]}'))
                break

    # Tool annotation containment
    for layout in layout_nodes:
        tid = layout.tool_id
        gs = layout.node.find('./GuiSettings')
        if gs is None or gs.get('Plugin') in (TEXTBOX_PLUGIN, TOOL_CONTAINER_PLUGIN):
            continue
        ann = layout.node.find('./Properties/Annotation')
        if ann is None:
            continue
        txt = (ann.findtext('./AnnotationText') or ann.findtext('./DefaultAnnotationText') or '').strip()
        if not txt:
            continue

        tx = layout.x
        ty = layout.y
        owner = owner_section_for_tool(tx, ty, section_boxes)
        if owner is None:
            continue

        tr = text_rect(txt, tx - 6.0, ty + 40.0, DEFAULT_ANNOT_FONT)
        if not rect_inside(tr, owner['rect'], CONTAINMENT_MARGIN):
            out.append(make_violation(ctx.path, 'R-LAYOUT-001', 'M-LAYOUT-001', tid, 'major', f'Annotation escapes section boundary owner={owner["id"]}: ann_rect={tr} box_rect={owner["rect"]}'))

        for band in border_band_rects(owner['rect'], BORDER_BAND):
            if rect_intersects(tr, band):
                out.append(make_violation(ctx.path, 'R-ANN-001', 'M-LAYOUT-001', tid, 'major', f'Annotation intersects section border owner={owner["id"]}: ann_rect={tr} box_rect={owner["rect"]}'))
                break

    # Container overlap detection
    for idx, box_a in enumerate(container_boxes):
        for box_b in container_boxes[idx + 1:]:
            if is_ancestor(box_a['id'], box_b['id'], layout_by_id) or is_ancestor(box_b['id'], box_a['id'], layout_by_id):
                continue
            if not rect_intersects(box_a['rect'], box_b['rect']):
                continue
            rule = 'R-LAYOUT-009' if box_a.get('depth') == box_b.get('depth') else 'R-LAYOUT-011'
            out.append(
                make_violation(
                    ctx.path,
                    rule,
                    'M-LAYOUT-003',
                    f'{box_a["id"]}|{box_b["id"]}',
                    'major',
                    f'Containers overlap: {box_a["id"]} rect={box_a["rect"]} vs {box_b["id"]} rect={box_b["rect"]}',
                )
            )

    # Tools hidden by unrelated containers
    for layout in layout_nodes:
        if not is_actual_tool_plugin(layout.plugin):
            continue
        for container in container_boxes:
            if container['id'] == layout.parent_tool_id or is_ancestor(container['id'], layout.tool_id, layout_by_id):
                continue
            if rect_intersects(layout.rect, container['rect']):
                out.append(
                    make_violation(
                        ctx.path,
                        'R-LAYOUT-008',
                        'M-LAYOUT-004',
                        layout.tool_id,
                        'major',
                        f'Tool {layout.tool_id} is obscured by container {container["id"]}: tool_rect={layout.rect} container_rect={container["rect"]}',
                    )
                )
                break

    return out


def check_text_hygiene(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    for tid, xp, text in collect_visible_text_fields(ctx.root):
        if FORBIDDEN_VISIBLE_TOKEN_RE.search(text):
            out.append(make_violation(ctx.path, 'R-TEXT-002', 'M-TEXT-002', tid, 'major', f"Forbidden token 'obj' at {xp}"))
        if has_non_printable_chars(text):
            out.append(make_violation(ctx.path, 'R-TEXT-002', 'M-TEXT-002', tid, 'major', f'Non-printable/replacement char at {xp}'))
        if re.search(r'\n\s*\n', text):
            out.append(make_violation(ctx.path, 'R-TEXT-001', 'M-TEXT-001', tid, 'minor', f'Consecutive blank lines at {xp}'))

        lines = text.split('\n')
        for i, line in enumerate(lines):
            s = line.strip()
            if not s:
                continue
            words = re.findall(r"[^\W\d_']+(?:'[^\W\d_']+)?", s, flags=re.UNICODE)
            if words and words[-1].lower() in FORBIDDEN_LINE_END_WORDS:
                out.append(make_violation(ctx.path, 'R-TEXT-001', 'M-TEXT-001', tid, 'minor', f"Line ends with weak terminal word '{words[-1]}' at {xp} line={i+1}"))
                break
            if len(words) == 1 and i > 0 and i < (len(lines) - 1):
                out.append(make_violation(ctx.path, 'R-TEXT-001', 'M-TEXT-001', tid, 'minor', f"Orphan single-word line '{words[0]}' at {xp} line={i+1}"))
                break

    return out


def check_naming(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    name = ctx.path.name
    if ' ' in name or not re.match(r'^\d{2}_[^\s]+.*\.yxmd$', name):
        out.append(make_violation(ctx.path, 'R-NAME-001', 'M-NAME-001', 'workflow', 'major', f'Workflow filename violates naming standard: {name}'))

    if not is_managed_portfolio_workflow(ctx.path):
        return out

    for node in iter_workflow_nodes(ctx.root):
        tid = node.get('ToolID') or ''
        gs = node.find('./GuiSettings')
        plugin = gs.get('Plugin', '') if gs is not None else ''
        if 'DbFileOutput' not in plugin:
            continue
        f = node.find('./Properties/Configuration/File')
        if f is None or not (f.text or '').strip():
            continue
        bn = Path((f.text or '').replace('\\', '/')).name.lower()
        if not (bn.startswith('customgpt_') or re.match(r'^\d{2}_', bn)):
            out.append(make_violation(ctx.path, 'R-NAME-002', 'M-NAME-002', tid, 'minor', f'Output name is non-deterministic: {bn}'))

    return out


def check_configuration(ctx: WorkflowContext) -> List[Violation]:
    out: List[Violation] = []
    ver = ctx.root.get('yxmdVer', '')
    if ver not in {'2025.1', '2025.2'}:
        out.append(make_violation(ctx.path, 'R-CONFIG-001', 'M-CONFIG-001', 'document', 'major', f'yxmdVer expected 2025.1 by default or an explicitly waived supported version (2025.2); got {ver}'))
    for layout in collect_layout_nodes(ctx.root):
        if layout.plugin != TEXTBOX_PLUGIN:
            continue
        for color_tag in ('TextColor', 'FillColor'):
            color = layout.node.find(f'./Properties/Configuration/{color_tag}')
            if color is None:
                continue
            name = color.get('name') or ''
            if name.startswith('#'):
                out.append(make_violation(
                    ctx.path,
                    'R-CONFIG-003',
                    'M-CONFIG-003',
                    layout.tool_id,
                    'major',
                    f'TextBox {layout.tool_id} uses Designer-incompatible {color_tag} name={name}; use named colors or r/g/b attributes instead',
                ))
    return out


def check_structure(ctx: WorkflowContext, baselines: Dict[str, List[str]]) -> List[Violation]:
    out: List[Violation] = []

    nodes = iter_workflow_nodes(ctx.root)
    ids = [n.get('ToolID') or '' for n in nodes]
    if len(ids) != len(set(ids)):
        out.append(make_violation(ctx.path, 'R-CONFIG-002', 'M-STRUCT-001', 'graph', 'critical', 'Duplicate ToolID detected'))
    valid = set(ids)

    for c in ctx.root.findall('.//Connections/Connection'):
        o = c.find('./Origin'); d = c.find('./Destination')
        if o is None or d is None:
            continue
        ot = o.get('ToolID') or ''
        dt = d.get('ToolID') or ''
        if ot not in valid or dt not in valid:
            out.append(make_violation(ctx.path, 'R-CONFIG-002', 'M-STRUCT-001', 'graph', 'critical', f'Broken connection origin={ot} dest={dt}'))

    # Baseline-aware structure checks (strict only for 01 TOC family)
    m = re.match(r'^(\d{2})_', ctx.path.name)
    step = m.group(1) if m else ''
    this_plugins = load_plugins_in_order(ctx.root)

    if step == '01' and '01' in baselines and baselines['01']:
        if this_plugins != baselines['01']:
            out.append(make_violation(
                ctx.path,
                'R-CONFIG-002',
                'M-STRUCT-002',
                'graph',
                'major',
                f'TOC structure drift from golden workflow_01 (plugin sequence mismatch): expected={len(baselines["01"])} got={len(this_plugins)}'
            ))

    return out


def parse_rule_ids_from_rules_md(path: Path) -> List[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding='utf-8', errors='ignore')
    return sorted(set(re.findall(r'\bR-[A-Z]+-\d{3}\b', text)))


def governance_check(rules_path: Path) -> List[Violation]:
    missing: List[Violation] = []
    for rid in parse_rule_ids_from_rules_md(rules_path):
        if rid not in CHECK_IMPLEMENTATION:
            missing.append(Violation(file=str(rules_path), rule=rid, mistake_id='M-GOV-001', element_id='governance', severity='critical', description=f'Hard rule {rid} not mapped to verifier implementation'))
    return missing


def validate_one(path: Path, baselines: Dict[str, List[str]]) -> List[Violation]:
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return [make_violation(path, 'R-XML-000', 'M-XML-000', 'document', 'critical', f'XML parse failed: {e}')]

    ctx = WorkflowContext(path=path, root=root)
    out: List[Violation] = []
    out.extend(check_macro_integrity(ctx))
    out.extend(check_structure(ctx, baselines))
    out.extend(check_header_hierarchy(ctx))
    out.extend(check_contextual_containers(ctx))
    out.extend(check_layout_containment(ctx))
    out.extend(check_text_hygiene(ctx))
    out.extend(check_naming(ctx))
    out.extend(check_configuration(ctx))
    return out


def run_parallel(workflows: List[Path], workers: int, baselines: Dict[str, List[str]]) -> List[Violation]:
    violations: List[Violation] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        fut_map = {ex.submit(validate_one, wf, baselines): wf for wf in workflows}
        for fut in as_completed(fut_map):
            violations.extend(fut.result())
    violations.sort(key=lambda v: (v.file, v.rule, v.element_id, v.description))
    return violations


def build_grouped_report(violations: List[Violation]) -> Dict[str, dict]:
    grouped: Dict[str, dict] = {}
    for v in violations:
        kit = starter_kit_group(Path(v.file))
        grouped.setdefault(kit, {})
        grouped[kit].setdefault(v.file, {})
        grouped[kit][v.file].setdefault(v.rule, {})
        grouped[kit][v.file][v.rule].setdefault(v.mistake_id, [])
        grouped[kit][v.file][v.rule][v.mistake_id].append({
            'element_id': v.element_id,
            'severity': v.severity,
            'description': v.description,
        })
    return grouped


def run_agents(workflows: List[Path], workers: int, rules_path: Path, baselines: Dict[str, List[str]]) -> dict:
    agent_defs = [
        ('Agent 1 – Macro Integrity Agent', lambda c: check_macro_integrity(c)),
        ('Agent 2 – Tool Structure Agent', lambda c: check_structure(c, baselines)),
        ('Agent 3 – Header Hierarchy Agent', lambda c: check_header_hierarchy(c)),
        ('Agent 4 – Contextual Container Agent', lambda c: check_contextual_containers(c)),
        ('Agent 5 – Layout Containment Agent', lambda c: check_layout_containment(c)),
        ('Agent 6 – Text Hygiene Agent', lambda c: check_text_hygiene(c)),
        ('Agent 7 – Naming Convention Agent', lambda c: check_naming(c)),
        ('Agent 8 – Configuration Agent', lambda c: check_configuration(c)),
    ]

    ctx_map: Dict[Path, WorkflowContext] = {}
    parse_errors: List[Violation] = []
    for wf in workflows:
        try:
            ctx_map[wf] = WorkflowContext(path=wf, root=ET.parse(wf).getroot())
        except Exception as e:
            parse_errors.append(make_violation(wf, 'R-XML-000', 'M-XML-000', 'document', 'critical', f'XML parse failed: {e}'))

    reports = []
    for agent_name, fn in agent_defs:
        vios: List[Violation] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = [ex.submit(fn, ctx_map[wf]) for wf in sorted(ctx_map.keys())]
            for fut in as_completed(futs):
                vios.extend(fut.result())
        vios.sort(key=lambda x: (x.file, x.rule, x.element_id, x.description))
        reports.append({'agent': agent_name, 'violations': [asdict(v) for v in vios]})

    gov = governance_check(rules_path)
    reports.append({'agent': 'Agent 9 – Governance Agent', 'violations': [asdict(v) for v in gov]})

    if parse_errors:
        reports.append({'agent': 'Parse Errors', 'violations': [asdict(v) for v in parse_errors]})

    all_v = [Violation(**v) for r in reports for v in r['violations']]
    return {
        'total_workflows_inspected': len(workflows),
        'total_violations': len(all_v),
        'violations_by_agent': {r['agent']: len(r['violations']) for r in reports},
        'grouped': build_grouped_report(all_v),
        'status': 'PASS' if len(all_v) == 0 else 'FAIL',
        'agent_reports': reports,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Deterministic validator for Alteryx .yxmd workflows.')
    p.add_argument('workflows', nargs='*', help='Workflow files or directories.')
    p.add_argument('--dirs', nargs='*', default=[], help='Directory roots to recursively validate all .yxmd.')
    p.add_argument('--file-list', nargs='*', default=[], help='Text file(s) with one workflow path per line.')
    p.add_argument('--workers', type=int, default=max(1, min(24, os.cpu_count() or 4)), help='Parallel worker count for read-only checks.')
    p.add_argument('--report', default='', help='Write JSON report to path (optional).')
    p.add_argument('--agents', nargs='*', default=[], help='Run multi-agent inspection mode for path(s).')
    return p.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    rules_path = script_dir / 'WORKFLOW_RULES.md'
    baselines = load_structure_baselines(script_dir)

    if args.agents:
        workflows = discover_workflows([], args.agents, args.file_list)
    else:
        workflows = discover_workflows(args.workflows, args.dirs, args.file_list)

    if not workflows:
        print('ERROR: no workflows discovered. Use positional paths, --dirs, --file-list, or --agents.')
        return 2

    if args.agents:
        report = run_agents(workflows, args.workers, rules_path, baselines)
        payload = json.dumps(report, indent=2, ensure_ascii=False)
        print(payload)
        if args.report:
            out = Path(args.report)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload, encoding='utf-8')
        return 0 if report['status'] == 'PASS' else 1

    violations = run_parallel(workflows, args.workers, baselines)
    report_obj = {
        'summary': {
            'workflow_count': len(workflows),
            'total_violations': len(violations),
            'failed_workflows': len(set(v.file for v in violations)),
            'status': 'PASS' if not violations else 'FAIL',
        },
        'grouped': build_grouped_report(violations),
        'violations': [asdict(v) for v in violations],
    }

    payload = json.dumps(report_obj, indent=2, ensure_ascii=False)
    print(payload)

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding='utf-8')

    return 0 if not violations else 1


if __name__ == '__main__':
    raise SystemExit(main())
