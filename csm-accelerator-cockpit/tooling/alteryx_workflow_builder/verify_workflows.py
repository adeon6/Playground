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
from typing import Any, Dict, List, Sequence, Tuple

DEFAULT_TEXTBOX_FONT = 14.0
DEFAULT_ANNOT_FONT = 14.0
LINE_HEIGHT_MULT = 1.25
TEXT_PAD_X = 10.0
TEXT_PAD_Y = 10.0
CONTAINMENT_MARGIN = 4.0
BORDER_BAND = 3.0
ALLOWED_YXMD_VERSIONS = {"2025.1", "2025.2"}
DEFAULT_DESIGNER_PROFILE = "2025.2"
DEFAULT_MODE = "demo"
GENERIC_PLUGIN = "AlteryxBasePluginsGui.ToolContainer.ToolContainer"
TIER2_OPS = {
    "datetime",
    "text_to_columns",
    "multi_row_formula",
    "cross_tab",
    "transpose",
    "sample",
    "data_cleansing",
    "record_id",
    "browse",
}

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
    "R-LAYOUT-001": "check_layout_containment",
    "R-LAYOUT-002": "check_layout_containment",
    "R-LAYOUT-003": "check_layout_containment",
    "R-ANN-001": "check_layout_containment",
    "R-ANN-002": "check_layout_containment",
    "R-TEXT-001": "check_text_hygiene",
    "R-TEXT-002": "check_text_hygiene",
    "R-NAME-001": "check_naming",
    "R-NAME-002": "check_naming",
    "R-CONFIG-001": "check_configuration",
    "R-CONFIG-002": "check_structure",
    "R-CAP-001": "check_capability_coverage",
    "R-CAP-002": "check_capability_coverage",
    "R-CAP-003": "check_capability_coverage",
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


def mode_for_workflow(path: Path, mode_arg: str) -> str:
    if mode_arg in {"starter_kit", "demo"}:
        return mode_arg
    lowered = str(path).lower()
    if "office_of_finance_ai_starter_kits" in lowered or "starter kits" in lowered:
        return "starter_kit"
    return DEFAULT_MODE


def collect_visible_text_fields(root: ET.Element) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for node in root.findall('.//Nodes/Node'):
        tid = node.get('ToolID') or ''
        for xp in VISIBLE_TEXT_XPATHS:
            elem = node.find(xp)
            if elem is None or elem.text is None:
                continue
            out.append((tid, xp, elem.text))
    return out


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
    for n in root.findall('.//Nodes/Node'):
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


def load_capability_registry(skill_dir: Path) -> dict[str, Any]:
    path = skill_dir / 'references' / 'capability_registry.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def profile_from_yxmd(root: ET.Element) -> str:
    ver = (root.get('yxmdVer') or '').strip()
    if ver in ALLOWED_YXMD_VERSIONS:
        return ver
    return DEFAULT_DESIGNER_PROFILE


def plugin_to_op_for_profile(capability_registry: dict[str, Any], profile: str) -> dict[str, str]:
    out: dict[str, str] = {}
    ops = capability_registry.get('ops') or {}
    if not isinstance(ops, dict):
        return out

    for op, capability in ops.items():
        if not isinstance(capability, dict):
            continue
        availability = capability.get('availability') or []
        if availability and profile not in availability:
            continue
        plugin = str(capability.get('plugin', '')).strip()
        if plugin:
            out[plugin] = op
        for alias in capability.get('plugin_aliases') or []:
            alias_text = str(alias).strip()
            if alias_text:
                out[alias_text] = op
    return out


def plugin_to_op_all(capability_registry: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    ops = capability_registry.get('ops') or {}
    if not isinstance(ops, dict):
        return out

    for op, capability in ops.items():
        if not isinstance(capability, dict):
            continue
        plugin = str(capability.get('plugin', '')).strip()
        if plugin:
            out[plugin] = op
        for alias in capability.get('plugin_aliases') or []:
            alias_text = str(alias).strip()
            if alias_text:
                out[alias_text] = op
    return out


def check_macro_integrity(ctx: WorkflowContext, mode: str) -> List[Violation]:
    out: List[Violation] = []
    expected_slug = kit_slug_from_path(ctx.path).lower()

    for node in ctx.root.findall('.//Nodes/Node'):
        tid = node.get('ToolID') or ''
        eng = node.find('./EngineSettings')
        macro = '' if eng is None else (eng.get('Macro') or '').strip()
        if not macro:
            continue

        normalized = macro.replace('\\', '/')
        if not normalized.lower().endswith('.yxmc'):
            out.append(make_violation(ctx.path, 'R-MACRO-001', 'M-MACRO-002', tid, 'critical', f'Macro path must end with .yxmc: {macro}'))
            continue

        if re.match(r'^[A-Za-z]:\\', macro) or macro.startswith('\\') or macro.startswith('/'):
            out.append(make_violation(ctx.path, 'R-MACRO-001', 'M-MACRO-002', tid, 'critical', f'Absolute/UNC/rooted macro path: {macro}'))
            continue

        if mode != 'starter_kit':
            continue

        if '..\\..\\..\\..\\' in macro or '../../../../../' in normalized:
            out.append(make_violation(ctx.path, 'R-MACRO-002', 'M-MACRO-002', tid, 'major', f'Forbidden macro path escape depth: {macro}'))

        if expected_slug != 'unknown':
            m = re.search(r'Starter Kits\\([^\\]+)\\Macros', macro, flags=re.IGNORECASE)
            if m and m.group(1).lower() != expected_slug:
                out.append(make_violation(ctx.path, 'R-MACRO-003', 'M-MACRO-001', tid, 'critical', f'Macro root mismatch expected={expected_slug} got={m.group(1)} path={macro}'))

        if 'accounting_automation' in macro.lower() and expected_slug not in ('unknown', 'accounting_automation'):
            out.append(make_violation(ctx.path, 'R-MACRO-002', 'M-MACRO-001', tid, 'major', f'Forbidden macro token for this kit: {macro}'))

    return out


def collect_comment_boxes(root: ET.Element) -> List[dict]:
    boxes: List[dict] = []
    for node in root.findall('.//Nodes/Node'):
        gs = node.find('./GuiSettings')
        if gs is None or gs.get('Plugin') != 'AlteryxGuiToolkit.TextBox.TextBox':
            continue
        pos = gs.find('./Position')
        if pos is None:
            continue
        cfg = node.find('./Properties/Configuration')
        shape = ''
        if cfg is not None:
            sh = cfg.find('./Shape')
            shape = sh.get('shape') if sh is not None and sh.get('shape') else ''
        rect = (as_float(pos.get('x')), as_float(pos.get('y')), as_float(pos.get('width')), as_float(pos.get('height')))
        boxes.append({'id': node.get('ToolID') or '', 'shape': shape, 'rect': rect, 'node': node})
    return boxes


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


def check_layout_containment(ctx: WorkflowContext, mode: str) -> List[Violation]:
    if mode != 'starter_kit':
        return []

    out: List[Violation] = []
    boxes = collect_comment_boxes(ctx.root)
    section_boxes = [b for b in boxes if b['shape'] == '0' and b['rect'][2] >= 200 and b['rect'][3] >= 120]

    # Textbox/comment text containment
    for b in boxes:
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
    for node in ctx.root.findall('.//Nodes/Node'):
        tid = node.get('ToolID') or ''
        gs = node.find('./GuiSettings')
        if gs is None or gs.get('Plugin') == 'AlteryxGuiToolkit.TextBox.TextBox':
            continue
        pos = gs.find('./Position')
        ann = node.find('./Properties/Annotation')
        if pos is None or ann is None:
            continue
        txt = (ann.findtext('./AnnotationText') or ann.findtext('./DefaultAnnotationText') or '').strip()
        if not txt:
            continue

        tx = as_float(pos.get('x')); ty = as_float(pos.get('y'))
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


def check_naming(ctx: WorkflowContext, mode: str) -> List[Violation]:
    out: List[Violation] = []
    name = ctx.path.name
    if mode == 'starter_kit' and name != 'main.yxmd' and (' ' in name or not re.match(r'^\d{2}_[^\s]+.*\.yxmd$', name)):
        out.append(make_violation(ctx.path, 'R-NAME-001', 'M-NAME-001', 'workflow', 'major', f'Workflow filename violates naming standard: {name}'))

    if mode != 'starter_kit':
        return out

    for node in ctx.root.findall('.//Nodes/Node'):
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


def check_configuration(
    ctx: WorkflowContext,
    expected_version: str | None,
) -> List[Violation]:
    out: List[Violation] = []
    ver = ctx.root.get('yxmdVer', '')
    if expected_version and ver != expected_version:
        out.append(
            make_violation(
                ctx.path,
                'R-CONFIG-001',
                'M-CONFIG-001',
                'document',
                'major',
                f'yxmdVer expected {expected_version} got {ver}',
            )
        )
        return out

    if ver not in ALLOWED_YXMD_VERSIONS:
        out.append(
            make_violation(
                ctx.path,
                'R-CONFIG-001',
                'M-CONFIG-001',
                'document',
                'major',
                f'yxmdVer expected one of {sorted(ALLOWED_YXMD_VERSIONS)} got {ver}',
            )
        )
    return out


def check_structure(ctx: WorkflowContext, baselines: Dict[str, List[str]]) -> List[Violation]:
    out: List[Violation] = []

    nodes = ctx.root.findall('.//Nodes/Node')
    ids = [n.get('ToolID') or '' for n in nodes]
    if len(ids) != len(set(ids)):
        out.append(make_violation(ctx.path, 'R-CONFIG-002', 'M-STRUCT-001', 'graph', 'critical', 'Duplicate ToolID detected'))
    valid = set(ids)

    for node in nodes:
        tid = node.get('ToolID') or ''
        gs = node.find('./GuiSettings')
        if gs is None:
            out.append(make_violation(ctx.path, 'R-CONFIG-002', 'M-STRUCT-001', tid, 'critical', 'Node missing GuiSettings'))
            continue
        if not (gs.get('Plugin') or '').strip():
            out.append(make_violation(ctx.path, 'R-CONFIG-002', 'M-STRUCT-001', tid, 'critical', 'Node GuiSettings Plugin is empty'))

    for c in ctx.root.findall('.//Connections/Connection'):
        o = c.find('./Origin'); d = c.find('./Destination')
        if o is None or d is None:
            out.append(
                make_violation(
                    ctx.path,
                    'R-CONFIG-002',
                    'M-STRUCT-001',
                    'graph',
                    'critical',
                    'Connection is non-canonical (Origin/Destination child nodes required)',
                )
            )
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


def check_capability_coverage(
    ctx: WorkflowContext,
    capability_registry: dict[str, Any],
    designer_profile: str | None,
) -> List[Violation]:
    out: List[Violation] = []
    if not capability_registry:
        return out

    profile = designer_profile or profile_from_yxmd(ctx.root)
    profile_map = plugin_to_op_for_profile(capability_registry, profile)
    all_map = plugin_to_op_all(capability_registry)
    ops = capability_registry.get('ops') or {}

    for node in ctx.root.findall('.//Nodes/Node'):
        tid = node.get('ToolID') or ''
        gs = node.find('./GuiSettings')
        plugin = gs.get('Plugin', '') if gs is not None else ''
        cfg = node.find('./Properties/Configuration')

        if plugin == GENERIC_PLUGIN:
            op_name = (cfg.findtext('./Operation') if cfg is not None else '') or ''
            op_name = op_name.strip()
            if op_name in TIER2_OPS:
                out.append(
                    make_violation(
                        ctx.path,
                        'R-CAP-001',
                        'M-CAP-001',
                        tid,
                        'critical',
                        f"Tier-2 op '{op_name}' emitted via generic plugin fallback",
                    )
                )
            continue

        op_any = all_map.get(plugin, '')
        if not op_any:
            continue

        capability = ops.get(op_any, {}) if isinstance(ops, dict) else {}
        availability = capability.get('availability') or []
        if availability and profile not in availability:
            out.append(
                make_violation(
                    ctx.path,
                    'R-CAP-003',
                    'M-CAP-003',
                    tid,
                    'major',
                    f"Plugin '{plugin}' for op '{op_any}' unavailable for profile {profile}",
                )
            )

        op = profile_map.get(plugin, '')
        if op not in TIER2_OPS:
            continue

        if cfg is None:
            out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', f"Tier-2 op '{op}' missing Configuration"))
            continue

        if op == 'datetime':
            transforms = cfg.findall('./Transformations/Transformation')
            legacy_ok = bool((cfg.findtext('./InputFieldName') or '').strip()) and bool((cfg.findtext('./OutputFieldName') or '').strip())
            if not transforms and not legacy_ok:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'datetime requires Transformations/Transformation or InputFieldName/OutputFieldName'))
        if op == 'text_to_columns':
            if not (cfg.findtext('./Field') or '').strip():
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'text_to_columns missing Configuration/Field'))
            has_delimiter = cfg.find('./Delimiter') is not None or cfg.find('./Delimeters') is not None
            if not has_delimiter:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'text_to_columns missing Configuration/Delimiter'))
        if op == 'multi_row_formula':
            field_name = (cfg.findtext('./Field') or cfg.findtext('./UpdateField_Name') or '').strip()
            if not field_name:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'multi_row_formula missing Configuration/Field'))
            if not (cfg.findtext('./Expression') or '').strip():
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'multi_row_formula missing Configuration/Expression'))
        if op == 'cross_tab':
            has_groups = bool(cfg.findall('./GroupBy/Group')) or cfg.find('./GroupFields') is not None
            if not has_groups:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'cross_tab missing GroupBy/Group entries'))

            header = cfg.find('./HeaderField')
            data = cfg.find('./DataField')
            method = (cfg.findtext('./Method') or cfg.findtext('./Methods') or '').strip()
            if not method:
                method_el = cfg.find('./Methods/Method')
                if method_el is not None:
                    method = (method_el.attrib.get('method', '') or '').strip()
            header_ok = bool((header.text or '').strip()) if header is not None else False
            if header is not None and not header_ok:
                header_ok = bool((header.attrib.get('field', '') or '').strip())
            data_ok = bool((data.text or '').strip()) if data is not None else False
            if data is not None and not data_ok:
                data_ok = bool((data.attrib.get('field', '') or '').strip())

            if not header_ok:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'cross_tab missing Configuration/HeaderField'))
            if not data_ok:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'cross_tab missing Configuration/DataField'))
            if not method:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'cross_tab missing Configuration/Method'))
        if op == 'transpose':
            if not cfg.findall('./KeyFields/Key'):
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'transpose missing KeyFields/Key entries'))
            if not cfg.findall('./DataFields/Data'):
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'transpose missing DataFields/Data entries'))
        if op == 'sample':
            mode = (cfg.findtext('./Mode') or '').strip()
            if not mode:
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'sample missing Configuration/Mode'))
            if mode in {'first_n', 'random_n'} and not (cfg.findtext('./Value') or '').strip():
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', f"sample mode '{mode}' requires Configuration/Value"))
        if op == 'data_cleansing':
            if not cfg.findall('./Fields/Field'):
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'data_cleansing missing Fields/Field entries'))
            if not cfg.findall('./Options/Option'):
                out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'data_cleansing missing Options/Option entries'))
        if op == 'record_id' and not (cfg.findtext('./FieldName') or '').strip():
            out.append(make_violation(ctx.path, 'R-CAP-002', 'M-CAP-002', tid, 'major', 'record_id missing Configuration/FieldName'))

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


def validate_one(
    path: Path,
    baselines: Dict[str, List[str]],
    capability_registry: dict[str, Any],
    mode_arg: str,
    expected_version: str | None,
    designer_profile: str | None,
) -> List[Violation]:
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return [make_violation(path, 'R-XML-000', 'M-XML-000', 'document', 'critical', f'XML parse failed: {e}')]

    ctx = WorkflowContext(path=path, root=root)
    mode = mode_for_workflow(path, mode_arg)
    out: List[Violation] = []
    out.extend(check_macro_integrity(ctx, mode))
    out.extend(check_structure(ctx, baselines))
    out.extend(check_layout_containment(ctx, mode))
    out.extend(check_text_hygiene(ctx))
    out.extend(check_naming(ctx, mode))
    out.extend(check_configuration(ctx, expected_version))
    out.extend(check_capability_coverage(ctx, capability_registry, designer_profile))
    return out


def run_parallel(
    workflows: List[Path],
    workers: int,
    baselines: Dict[str, List[str]],
    capability_registry: dict[str, Any],
    mode_arg: str,
    expected_version: str | None,
    designer_profile: str | None,
) -> List[Violation]:
    violations: List[Violation] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        fut_map = {
            ex.submit(
                validate_one,
                wf,
                baselines,
                capability_registry,
                mode_arg,
                expected_version,
                designer_profile,
            ): wf
            for wf in workflows
        }
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


def run_agents(
    workflows: List[Path],
    workers: int,
    rules_path: Path,
    baselines: Dict[str, List[str]],
    capability_registry: dict[str, Any],
    mode_arg: str,
    expected_version: str | None,
    designer_profile: str | None,
) -> dict:
    agent_defs = [
        ('Agent 2 – Tool Structure Agent', lambda c, _m: check_structure(c, baselines)),
        ('Agent 4 – Text Hygiene Agent', lambda c, _m: check_text_hygiene(c)),
        ('Agent 8 – Governance Agent', None),
    ]

    ctx_map: Dict[Path, tuple[WorkflowContext, str]] = {}
    parse_errors: List[Violation] = []
    for wf in workflows:
        try:
            ctx_map[wf] = (WorkflowContext(path=wf, root=ET.parse(wf).getroot()), mode_for_workflow(wf, mode_arg))
        except Exception as e:
            parse_errors.append(make_violation(wf, 'R-XML-000', 'M-XML-000', 'document', 'critical', f'XML parse failed: {e}'))

    reports = []
    # Agents that require mode/profile/version are run explicitly for clarity.
    mode_agents = [
        ('Agent 1 – Macro Integrity Agent', lambda c, m: check_macro_integrity(c, m)),
        ('Agent 3 – Layout Containment Agent', lambda c, m: check_layout_containment(c, m)),
        ('Agent 5 – Naming Convention Agent', lambda c, m: check_naming(c, m)),
        ('Agent 6 – Configuration Agent', lambda c, _m: check_configuration(c, expected_version)),
        ('Agent 7 – Capability Coverage Agent', lambda c, _m: check_capability_coverage(c, capability_registry, designer_profile)),
    ]

    for agent_name, fn in mode_agents + [row for row in agent_defs if row[1] is not None]:
        vios: List[Violation] = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = [ex.submit(fn, ctx_map[wf][0], ctx_map[wf][1]) for wf in sorted(ctx_map.keys())]
            for fut in as_completed(futs):
                vios.extend(fut.result())
        vios.sort(key=lambda x: (x.file, x.rule, x.element_id, x.description))
        reports.append({'agent': agent_name, 'violations': [asdict(v) for v in vios]})

    gov = governance_check(rules_path)
    reports.append({'agent': 'Agent 8 – Governance Agent', 'violations': [asdict(v) for v in gov]})

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
    p.add_argument('--capability-registry', default='', help='Optional capability registry JSON path.')
    p.add_argument('--mode', default='auto', choices=['auto', 'starter_kit', 'demo'], help='Governance mode (or auto by path).')
    p.add_argument('--expected-version', default=None, choices=sorted(ALLOWED_YXMD_VERSIONS), help='Optional required yxmdVer for all workflows.')
    p.add_argument('--designer-profile', default=None, choices=sorted(ALLOWED_YXMD_VERSIONS), help='Optional capability profile override.')
    return p.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    rules_path = script_dir / 'WORKFLOW_RULES.md'
    baselines = load_structure_baselines(script_dir)
    capability_registry = load_capability_registry(script_dir)
    if args.capability_registry:
        capability_registry_path = Path(args.capability_registry)
        try:
            capability_registry = json.loads(capability_registry_path.read_text(encoding='utf-8'))
        except Exception:
            capability_registry = {}

    if args.agents:
        workflows = discover_workflows([], args.agents, args.file_list)
    else:
        workflows = discover_workflows(args.workflows, args.dirs, args.file_list)

    if not workflows:
        print('ERROR: no workflows discovered. Use positional paths, --dirs, --file-list, or --agents.')
        return 2

    resolved_expected_version = args.expected_version or args.designer_profile

    if args.agents:
        report = run_agents(
            workflows,
            args.workers,
            rules_path,
            baselines,
            capability_registry,
            args.mode,
            resolved_expected_version,
            args.designer_profile,
        )
        report['mode'] = args.mode
        report['expected_version'] = resolved_expected_version
        report['designer_profile'] = args.designer_profile
        payload = json.dumps(report, indent=2, ensure_ascii=False)
        print(payload)
        if args.report:
            out = Path(args.report)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(payload, encoding='utf-8')
        return 0 if report['status'] == 'PASS' else 1

    violations = run_parallel(
        workflows,
        args.workers,
        baselines,
        capability_registry,
        args.mode,
        resolved_expected_version,
        args.designer_profile,
    )
    report_obj = {
        'summary': {
            'workflow_count': len(workflows),
            'total_violations': len(violations),
            'failed_workflows': len(set(v.file for v in violations)),
            'status': 'PASS' if not violations else 'FAIL',
        },
        'mode': args.mode,
        'expected_version': resolved_expected_version,
        'designer_profile': args.designer_profile,
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
