from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document


APP_VERSION = "0.3.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COCKPIT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = COCKPIT_ROOT / "runs"
STARTER_DOCS_DIR = PROJECT_ROOT / "starter_docs"
PROCESS_PACK_DIR = PROJECT_ROOT / "process_pack"
SEQUENCE_CONFIG_PATH = PROCESS_PACK_DIR / "sequencer" / "sequence_config.json"
LARGE_PROMPT_PATH = PROCESS_PACK_DIR / "03_workflow_build" / "sop_to_alteryx_super_prompt_pack.md"
QUESTION_TEMPLATE_DOCX = PROCESS_PACK_DIR / "01_discovery" / "guided_discovery_conversation_template.docx"
DEFAULT_TRANSCRIPT_PATH = PROJECT_ROOT / "sample_data" / "sanitized_geo_spatial_discovery.md"

CAPTURE_STATUSES = {
    "answered": "Answered",
    "partial": "Partial",
    "not_answered": "Not answered",
    "needs_follow_up": "Needs follow-up",
}

EVIDENCE_STATUSES = {
    "supported": "Supported",
    "weak_evidence": "Weak evidence",
    "missing": "Missing",
    "conflicting": "Conflicting",
    "not_run": "Not run",
}

DOC_ARTIFACTS = [
    "01_customer_discovery_conversation.md",
    "02_guided_sop_capture.md",
    "03_accelerator_sop.md",
    "sop_gap_log.md",
    "sop_architecture_assessment.md",
]

ARTIFACT_LABELS = {
    "01_customer_discovery_conversation.md": "Discovery conversation",
    "02_guided_sop_capture.md": "Guided SOP capture",
    "03_accelerator_sop.md": "Accelerator SOP",
    "sop_gap_log.md": "Gap log",
    "sop_architecture_assessment.md": "Architecture assessment",
    "status/next_stage_prompt.md": "Workflow handoff prompt",
    "status/pipeline_status.json": "Pipeline status",
    "status/pipeline_log.md": "Pipeline log",
}

PROJECT_FOLDERS = [
    "docs",
    "data/raw",
    "data/generated",
    "status",
    "workflows",
]

REQUIRED_FOR_SOP_GATE = {
    "business_problem",
    "current_process",
    "desired_outcome",
    "business_questions",
    "scope_priorities",
    "source_systems",
    "data_shape_entities",
    "business_rules",
    "output_action",
    "validation_trust",
}

UNCERTAINTY_TERMS = [
    "not sure",
    "don't know",
    "do not know",
    "unknown",
    "tbc",
    "to be confirmed",
    "haven't decided",
    "have not decided",
    "need to check",
    "need follow",
    "we need to ask",
]


@dataclass(frozen=True)
class Section:
    id: str
    label: str
    prompt: str
    capture_fields: list[str]
    keywords: list[str]
    required: bool = True
    gate_reason: str = "Required for SOP and workflow-build handoff."


JON_SECTIONS = [
    Section(
        "opening",
        "Opening",
        "Frame the call, confirm the intended use case, and set the expectation that gaps are allowed.",
        ["Customer / engagement", "Business owner", "CSM / consultant", "Discovery purpose"],
        ["agenda", "today", "purpose", "objective", "goal", "business owner", "stakeholder"],
        required=False,
        gate_reason="Context only.",
    ),
    Section(
        "business_problem",
        "Business Problem",
        "Capture the pain, business consequence, affected users, and why solving it matters now.",
        ["Core problem", "Business impact", "Affected teams", "Why now", "Cost of current state"],
        ["problem", "pain", "challenge", "manual", "slow", "risk", "impact", "cost", "inconsistent", "trust"],
    ),
    Section(
        "current_process",
        "Current Process",
        "Describe the current-state process, handoffs, systems, spreadsheets, and known friction.",
        ["Current process", "Systems involved", "Manual steps", "Handoffs", "Bottlenecks"],
        ["current process", "today", "as is", "manual steps", "spreadsheet", "handoff", "workflow", "process"],
    ),
    Section(
        "desired_outcome",
        "Desired Outcome",
        "Clarify what first useful output should exist and what business decision or action it enables.",
        ["Target output", "Consumer", "Decision / action", "First-slice success", "Deferred items"],
        ["output", "deliverable", "dashboard", "report", "app", "action", "decision", "success", "first version"],
    ),
    Section(
        "business_questions",
        "Business Questions",
        "List the questions the accelerator must answer and how users decide what to do next.",
        ["Core questions", "Decision points", "Prioritisation", "Review cases", "Business significance"],
        ["question", "decide", "prioritize", "prioritise", "rank", "exception", "review", "what should", "which cases"],
    ),
    Section(
        "scope_priorities",
        "Scope / Priorities",
        "Separate the first slice from explicit exclusions, pilot boundaries, and later phases.",
        ["In-scope", "Out-of-scope", "Pilot boundary", "Phase 1 priority", "Later phases"],
        ["scope", "in scope", "out of scope", "pilot", "phase", "priority", "region", "business unit", "product"],
    ),
    Section(
        "source_systems",
        "Source Systems",
        "Identify source systems, extract owners, refresh cadence, access constraints, and package-safe inputs.",
        ["Systems", "Input files / tables", "Owners", "Refresh cadence", "Access constraints"],
        ["source", "system", "input", "file", "table", "extract", "owner", "refresh", "cadence", "access"],
    ),
    Section(
        "data_shape_entities",
        "Data Shape / Entities",
        "Capture grain, entities, fields, joins, sample rows, and data-quality constraints.",
        ["Grain", "Entities", "Key fields", "Join keys", "Quality constraints", "Sample row expectations"],
        ["data", "field", "column", "entity", "grain", "row", "join", "key", "quality", "sample"],
    ),
    Section(
        "known_unknowns",
        "Known Unknowns",
        "Record what the customer does not know yet so it becomes a gap-log item, not silent risk.",
        ["Unknowns", "Open questions", "Assumptions", "Follow-ups", "Owner for answers"],
        ["unknown", "not sure", "don't know", "to be confirmed", "assumption", "open question", "follow up"],
        required=False,
        gate_reason="Important for the gap log, but not required as positive evidence.",
    ),
    Section(
        "business_rules",
        "Business Rules",
        "Document definitions, calculations, thresholds, filters, joins, and exception-handling rules.",
        ["Definitions", "Rules / logic", "Calculations", "Thresholds", "Filters", "Exception rules"],
        ["rule", "logic", "definition", "threshold", "join", "filter", "criteria", "calculation", "formula"],
    ),
    Section(
        "output_action",
        "Output / Action",
        "Define the generated outputs, action lists, review queues, and how users will consume them.",
        ["Outputs", "Action list", "Dashboard / workbook", "Review queue", "Delivery format"],
        ["output", "action list", "dashboard", "workbook", "report", "review queue", "publish", "export"],
    ),
    Section(
        "validation_trust",
        "Validation / Trust",
        "Define how outputs are reconciled, who validates them, and what acceptance checks prove trust.",
        ["Validation method", "Review owner", "Reconciliation source", "Acceptance checks", "Sign-off"],
        ["validate", "validation", "reconcile", "check", "test", "trust", "review", "sign-off", "compare"],
    ),
    Section(
        "operational_constraints",
        "Operational Constraints",
        "Capture cadence, ownership, deployment path, security, handover, and support expectations.",
        ["Run cadence", "Operating owner", "Deployment path", "Security / access", "Support expectations"],
        ["operational", "schedule", "refresh", "run", "owner", "handover", "deploy", "production", "support"],
        required=False,
        gate_reason="Supports implementation planning after the SOP is usable.",
    ),
    Section(
        "close_playback",
        "Close / Playback",
        "Play back confirmed facts, assumptions, gaps, and next actions before the SOP is generated.",
        ["Confirmed facts", "Assumptions", "Open gaps", "Next actions", "Approval state"],
        ["playback", "recap", "summary", "confirmed", "assumption", "open question", "next step"],
        required=False,
        gate_reason="Human governance step.",
    ),
]


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return cleaned or "accelerator-project"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def template_root() -> Path:
    return COCKPIT_ROOT / "templates"


def static_root() -> Path:
    return COCKPIT_ROOT / "static"


def load_sequence_config() -> dict[str, Any]:
    if SEQUENCE_CONFIG_PATH.exists():
        try:
            return json.loads(SEQUENCE_CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "project_structure": PROJECT_FOLDERS,
        "stages": [
            {"id": "01_discovery", "name": "Discovery"},
            {"id": "02_guided_capture", "name": "Guided SOP capture"},
            {"id": "03_accelerator_sop", "name": "Accelerator SOP"},
            {"id": "04_workflow_build", "name": "Workflow build handoff"},
            {"id": "05_review", "name": "Review"},
        ],
    }


def load_question_bank(template_path: Path = QUESTION_TEMPLATE_DOCX) -> list[Section]:
    # Jon's interview script is the source of truth for V2. The Word template is bundled
    # for reference, but the app keeps section-level prompts stable for CSM usability.
    return JON_SECTIONS


def read_docx_text(path: Path) -> str:
    document = Document(str(path))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                parts.append(row_text)
    return "\n".join(parts)


def read_transcript_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError("Transcript must be a .docx, .md, or .txt file.")


def split_evidence_units(text: str) -> list[str]:
    rough_units = re.split(r"[\r\n]{2,}|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    units = []
    for unit in rough_units:
        cleaned = re.sub(r"\s+", " ", unit).strip()
        if len(cleaned) >= 35:
            units.append(cleaned)
    return units


def _keyword_hits(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    total = 0
    found: list[str] = []
    lower_text = text.lower()
    for keyword in keywords:
        count = len(re.findall(re.escape(keyword.lower()), lower_text))
        if count:
            total += count
            found.append(keyword)
    return total, found


def _top_evidence(units: list[str], section: Section, limit: int = 3) -> list[dict[str, Any]]:
    scored: list[tuple[int, list[str], str]] = []
    for unit in units:
        score, keywords = _keyword_hits(unit, section.keywords)
        if score:
            scored.append((score, keywords, unit))
    scored.sort(key=lambda item: (item[0], len(item[2])), reverse=True)
    return [
        {
            "score": score,
            "keywords": keywords[:6],
            "snippet": snippet[:420],
        }
        for score, keywords, snippet in scored[:limit]
    ]


def _evidence_summary(section: Section, evidence: list[dict[str, Any]], status: str) -> str:
    if status == "missing":
        return "No useful transcript signal was found for this section."
    found_keywords = sorted({keyword for item in evidence for keyword in item.get("keywords", [])})
    keyword_text = ", ".join(found_keywords[:5]) if found_keywords else "section terms"
    if status == "supported":
        return f"Transcript evidence repeatedly touches this section through {keyword_text}."
    if status == "weak_evidence":
        return f"Transcript evidence hints at this section through {keyword_text}, but needs CSM confirmation."
    return "Transcript includes uncertainty or ambiguity that should be resolved before approval."


def analyze_transcript_text(
    text: str,
    sections: list[Section],
    capture: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    capture = capture or {}
    units = split_evidence_units(text)
    analysis: dict[str, dict[str, Any]] = {}
    for section in sections:
        evidence = _top_evidence(units, section)
        score = sum(item["score"] for item in evidence)
        status = "missing"
        if score >= 6 or len(evidence) >= 3:
            status = "supported"
        elif score >= 2:
            status = "weak_evidence"

        capture_status = capture.get(section.id, {}).get("status", "not_answered")
        combined_snippets = " ".join(item["snippet"].lower() for item in evidence)
        has_uncertainty = any(term in combined_snippets for term in UNCERTAINTY_TERMS)
        if has_uncertainty and capture_status in {"answered", "partial"} and status != "missing":
            status = "conflicting"

        recommendation = "Capture this as a follow-up, assumption, or confirmed gap before SOP approval."
        if status == "supported" and capture_status == "not_answered":
            recommendation = "Transcript appears to answer this; CSM should summarize and approve it."
        elif status == "supported":
            recommendation = "Evidence is strong enough for CSM playback and approval."
        elif status == "weak_evidence":
            recommendation = "Partial evidence found. CSM should confirm or add a follow-up."
        elif status == "conflicting":
            recommendation = "Transcript includes uncertainty that conflicts with the captured status."

        analysis[section.id] = {
            "status": status,
            "score": score,
            "summary": _evidence_summary(section, evidence, status),
            "evidence": evidence,
            "recommendation": recommendation,
            "updated_at": utc_now(),
        }

    return analysis


def ensure_runs_dir() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def manifest_path(run_id: str) -> Path:
    return run_dir(run_id) / "manifest.json"


def ensure_project_structure(project_dir: Path) -> None:
    for folder in PROJECT_FOLDERS:
        (project_dir / folder).mkdir(parents=True, exist_ok=True)


def _artifact_path(project_dir: Path, artifact: str) -> Path:
    if artifact.startswith("status/"):
        return project_dir / artifact
    return project_dir / "docs" / artifact


def _artifact_record(project_dir: Path, artifact: str) -> dict[str, Any]:
    path = _artifact_path(project_dir, artifact)
    return {
        "name": artifact,
        "label": ARTIFACT_LABELS.get(artifact, artifact),
        "path": str(path),
        "relative_path": str(path.relative_to(project_dir)).replace("\\", "/"),
        "exists": path.exists(),
        "status": "generated" if path.exists() else "not_generated",
    }


def new_manifest(customer_name: str, project_name: str, csm_name: str, sections: list[Section]) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = slugify(customer_name or project_name or "customer")
    run_id = f"{timestamp}-{base}"
    project_dir = run_dir(run_id)
    manifest = {
        "schema_version": 2,
        "run_id": run_id,
        "customer_name": customer_name.strip() or "Unnamed customer",
        "project_name": project_name.strip() or "Accelerator discovery",
        "csm_name": csm_name.strip(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "project_structure": PROJECT_FOLDERS,
        "process_pack": {
            "source": "Jon accelerator operating system",
            "large_prompt": str(LARGE_PROMPT_PATH),
            "sequence_config": str(SEQUENCE_CONFIG_PATH),
        },
        "transcript": {
            "source_path": "",
            "stored_path": "",
            "canonical_path": str(project_dir / "docs" / "01_customer_discovery_conversation.md"),
            "characters": 0,
            "analyzed_at": "",
        },
        "capture": {
            section.id: {
                "status": "not_answered",
                "notes": "",
                "approved": False,
            }
            for section in sections
        },
        "analysis": {},
        "artifacts": {
            artifact: _artifact_record(project_dir, artifact)
            for artifact in [*DOC_ARTIFACTS, "status/next_stage_prompt.md", "status/pipeline_status.json", "status/pipeline_log.md"]
        },
        "sync": {
            "synced_at": "",
            "target_docs_dir": str(STARTER_DOCS_DIR),
        },
    }
    return manifest


def _refresh_artifact_records(manifest: dict[str, Any]) -> dict[str, Any]:
    project_dir = run_dir(manifest["run_id"])
    records = manifest.setdefault("artifacts", {})
    for artifact in [*DOC_ARTIFACTS, "status/next_stage_prompt.md", "status/pipeline_status.json", "status/pipeline_log.md"]:
        existing = records.get(artifact, {})
        generated_at = existing.get("generated_at", "")
        records[artifact] = _artifact_record(project_dir, artifact)
        if generated_at and records[artifact]["exists"]:
            records[artifact]["generated_at"] = generated_at
    return manifest


def save_manifest(manifest: dict[str, Any]) -> None:
    ensure_runs_dir()
    project_dir = run_dir(manifest["run_id"])
    ensure_project_structure(project_dir)
    manifest["updated_at"] = utc_now()
    _refresh_artifact_records(manifest)
    path = manifest_path(manifest["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_manifest(run_id: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path(run_id).read_text(encoding="utf-8"))
    return _refresh_artifact_records(manifest)


def list_manifests() -> list[dict[str, Any]]:
    ensure_runs_dir()
    manifests = []
    for path in sorted(RUNS_DIR.glob("*/manifest.json"), reverse=True):
        try:
            manifests.append(_refresh_artifact_records(json.loads(path.read_text(encoding="utf-8"))))
        except json.JSONDecodeError:
            continue
    return manifests


def update_capture_from_form(manifest: dict[str, Any], form: dict[str, Any], sections: list[Section]) -> dict[str, Any]:
    capture = manifest.setdefault("capture", {})
    for section in sections:
        item = capture.setdefault(section.id, {})
        status = str(form.get(f"status_{section.id}", item.get("status", "not_answered")))
        item["status"] = status if status in CAPTURE_STATUSES else "not_answered"
        item["notes"] = str(form.get(f"notes_{section.id}", item.get("notes", ""))).strip()
    return manifest


def update_approvals_from_form(manifest: dict[str, Any], form: dict[str, Any], sections: list[Section]) -> dict[str, Any]:
    capture = manifest.setdefault("capture", {})
    for section in sections:
        item = capture.setdefault(section.id, {})
        item["approved"] = form.get(f"approved_{section.id}") == "on"
    return manifest


def _canonical_transcript_md(manifest: dict[str, Any], source_path: Path, text: str) -> str:
    project_dir = run_dir(manifest["run_id"])
    canonical = project_dir / "docs" / "01_customer_discovery_conversation.md"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    content = [
        f"# {manifest['customer_name']} - Discovery Conversation\n\n",
        f"- Project: {manifest['project_name']}\n",
        f"- CSM: {manifest.get('csm_name') or 'Not captured'}\n",
        f"- Source file: {source_path.name}\n",
        f"- Captured in cockpit: {utc_now()}\n\n",
        "## Transcript Text\n\n",
        text.strip(),
        "\n",
    ]
    canonical.write_text("".join(content), encoding="utf-8")
    return str(canonical)


def attach_transcript_from_path(manifest: dict[str, Any], source_path: Path, sections: list[Section]) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(f"Transcript not found: {source_path}")

    text = read_transcript_text(source_path)
    target_dir = run_dir(manifest["run_id"]) / "data" / "raw" / "transcripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(source_path.stem) + source_path.suffix.lower()
    target = target_dir / safe_name
    if source_path.resolve() != target.resolve():
        shutil.copy2(source_path, target)

    canonical = _canonical_transcript_md(manifest, target, text)
    manifest["transcript"] = {
        "source_path": str(source_path),
        "stored_path": str(target),
        "canonical_path": canonical,
        "characters": len(text),
        "analyzed_at": utc_now(),
    }
    manifest["analysis"] = analyze_transcript_text(text, sections, manifest.get("capture", {}))
    return manifest


def attach_uploaded_transcript(
    manifest: dict[str, Any],
    original_name: str,
    bytes_payload: bytes,
    sections: list[Section],
) -> dict[str, Any]:
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".docx", ".md", ".txt"}:
        raise ValueError("Transcript upload must be .docx, .md, or .txt.")
    target_dir = run_dir(manifest["run_id"]) / "data" / "raw" / "transcripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slugify(Path(original_name).stem)}{suffix}"
    target.write_bytes(bytes_payload)
    return attach_transcript_from_path(manifest, target, sections)


def calculate_readiness(manifest: dict[str, Any], sections: list[Section]) -> dict[str, Any]:
    capture = manifest.get("capture", {})
    analysis = manifest.get("analysis", {})
    required_sections = [section for section in sections if section.id in REQUIRED_FOR_SOP_GATE]

    capture_weights = {
        "answered": 1.0,
        "partial": 0.65,
        "needs_follow_up": 0.35,
        "not_answered": 0.0,
    }
    evidence_weights = {
        "supported": 1.0,
        "weak_evidence": 0.55,
        "missing": 0.0,
        "conflicting": 0.0,
        "not_run": 0.0,
    }

    def avg(values: list[float]) -> int:
        return round((sum(values) / len(values)) * 100) if values else 0

    capture_pct = avg([capture_weights.get(capture.get(section.id, {}).get("status", "not_answered"), 0) for section in required_sections])
    evidence_pct = avg([evidence_weights.get(analysis.get(section.id, {}).get("status", "not_run"), 0) for section in required_sections])
    approval_pct = avg([1.0 if capture.get(section.id, {}).get("approved") else 0.0 for section in required_sections])
    doc_pct = avg([1.0 if manifest.get("artifacts", {}).get(name, {}).get("exists") else 0.0 for name in DOC_ARTIFACTS])
    overall_pct = round(capture_pct * 0.35 + evidence_pct * 0.25 + approval_pct * 0.25 + doc_pct * 0.15)

    blockers: list[str] = []
    for section in required_sections:
        item = capture.get(section.id, {})
        evidence_status = analysis.get(section.id, {}).get("status", "not_run")
        if item.get("status") in {"not_answered", "needs_follow_up"}:
            blockers.append(f"{section.label}: capture is {CAPTURE_STATUSES.get(item.get('status'), 'not answered')}.")
        if evidence_status in {"missing", "conflicting", "not_run"}:
            blockers.append(f"{section.label}: transcript evidence is {EVIDENCE_STATUSES.get(evidence_status, 'not run')}.")
        if not item.get("approved"):
            blockers.append(f"{section.label}: CSM approval is pending.")

    missing_docs = [ARTIFACT_LABELS[name] for name in DOC_ARTIFACTS if not manifest.get("artifacts", {}).get(name, {}).get("exists")]
    if missing_docs:
        blockers.append("Generated document chain is incomplete.")

    sop_exists = manifest.get("artifacts", {}).get("03_accelerator_sop.md", {}).get("exists", False)
    return {
        "capture_pct": capture_pct,
        "evidence_pct": evidence_pct,
        "approval_pct": approval_pct,
        "artifact_pct": doc_pct,
        "overall_pct": overall_pct,
        "workflow_gate": "ready" if not blockers and sop_exists else "blocked",
        "blockers": blockers[:14],
        "required_section_count": len(required_sections),
    }


def _section_capture_md(section: Section, manifest: dict[str, Any]) -> str:
    item = manifest.get("capture", {}).get(section.id, {})
    analysis = manifest.get("analysis", {}).get(section.id, {})
    evidence = analysis.get("evidence", [])
    lines = [
        f"### {section.label}",
        "",
        f"- CSM status: {CAPTURE_STATUSES.get(item.get('status', 'not_answered'), 'Not answered')}",
        f"- CSM approval: {'approved' if item.get('approved') else 'pending'}",
        f"- Transcript evidence: {EVIDENCE_STATUSES.get(analysis.get('status', 'not_run'), 'Not run')}",
        f"- Evidence summary: {analysis.get('summary', 'Transcript analysis has not run yet.')}",
        f"- Notes: {item.get('notes') or 'Not captured yet.'}",
    ]
    if evidence and analysis.get("status") != "supported":
        lines.append("- Review snippets:")
        for evidence_item in evidence:
            snippet = evidence_item["snippet"].replace("\n", " ")
            lines.append(f"  - {snippet}")
    lines.append("")
    return "\n".join(lines)


def _confirmed_sections(manifest: dict[str, Any], sections: list[Section]) -> list[Section]:
    return [
        section
        for section in sections
        if manifest.get("capture", {}).get(section.id, {}).get("approved")
        and manifest.get("analysis", {}).get(section.id, {}).get("status") in {"supported", "weak_evidence"}
    ]


def _gap_rows(manifest: dict[str, Any], sections: list[Section]) -> list[dict[str, str]]:
    rows = []
    for section in sections:
        capture_item = manifest.get("capture", {}).get(section.id, {})
        analysis_item = manifest.get("analysis", {}).get(section.id, {})
        capture_status = capture_item.get("status", "not_answered")
        evidence_status = analysis_item.get("status", "not_run")
        is_required = section.id in REQUIRED_FOR_SOP_GATE
        if (
            capture_status in {"not_answered", "needs_follow_up"}
            or evidence_status in {"missing", "conflicting", "not_run"}
            or (is_required and not capture_item.get("approved"))
        ):
            rows.append(
                {
                    "section": section.label,
                    "required": "yes" if is_required else "supporting",
                    "capture": CAPTURE_STATUSES.get(capture_status, "Not answered"),
                    "evidence": EVIDENCE_STATUSES.get(evidence_status, "Not run"),
                    "approval": "approved" if capture_item.get("approved") else "pending",
                    "next_step": analysis_item.get("recommendation", "CSM follow-up required."),
                }
            )
    return rows


def _pipeline_status(manifest: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    sequence = load_sequence_config()
    return {
        "run_id": manifest["run_id"],
        "customer_name": manifest["customer_name"],
        "project_name": manifest["project_name"],
        "updated_at": utc_now(),
        "readiness": readiness,
        "workflow_build": {
            "state": readiness["workflow_gate"],
            "large_prompt_only": True,
            "automatic_generation": False,
        },
        "stages": sequence.get("stages", []),
    }


def _workflow_handoff_prompt(manifest: dict[str, Any], readiness: dict[str, Any]) -> str:
    large_prompt = LARGE_PROMPT_PATH.read_text(encoding="utf-8") if LARGE_PROMPT_PATH.exists() else "Large prompt pack is missing from the process pack."
    sop_path = run_dir(manifest["run_id"]) / "docs" / "03_accelerator_sop.md"
    gap_path = run_dir(manifest["run_id"]) / "docs" / "sop_gap_log.md"
    assessment_path = run_dir(manifest["run_id"]) / "docs" / "sop_architecture_assessment.md"
    state = "READY" if readiness["workflow_gate"] == "ready" else "BLOCKED"
    blockers = "\n".join(f"- {blocker}" for blocker in readiness["blockers"]) or "- None"
    return f"""# Next Stage Prompt: Workflow Build Handoff

State: {state}

This project follows Jon's Large-only workflow build process. Do not start workflow generation from the SOP alone.

## Required Local Inputs
- Accelerator SOP: `{sop_path.name}`
- Gap log: `{gap_path.name}`
- Architecture assessment: `{assessment_path.name}`
- Project folders: `docs`, `data/raw`, `data/generated`, `status`, `workflows`

## Current Blockers
{blockers}

## Build Instruction
Use the Large prompt below only after the SOP gate is ready. If blocked, resolve the gap log first.

---

{large_prompt}
"""


def generate_docs(manifest: dict[str, Any], sections: list[Section]) -> dict[str, Any]:
    project_dir = run_dir(manifest["run_id"])
    ensure_project_structure(project_dir)
    docs_dir = project_dir / "docs"
    status_dir = project_dir / "status"
    readiness = calculate_readiness(_refresh_artifact_records(manifest), sections)
    confirmed = _confirmed_sections(manifest, sections)
    gap_rows = _gap_rows(manifest, sections)

    common_header = (
        f"# {manifest['customer_name']} - {manifest['project_name']}\n\n"
        f"- CSM: {manifest.get('csm_name') or 'Not captured'}\n"
        f"- Project ID: `{manifest['run_id']}`\n"
        f"- Generated: {utc_now()}\n"
        f"- Process: Jon accelerator operating system, Large-only workflow handoff\n\n"
    )

    discovery = [
        common_header,
        "## Discovery Capture\n\n",
        "This file is the CSM-safe discovery handoff. It summarizes capture status, transcript support, assumptions, and gaps without requiring the next person to read a raw transcript first.\n\n",
    ]
    discovery.extend(_section_capture_md(section, manifest) for section in sections)

    guided = [common_header, "## Confirmed Facts\n\n"]
    if confirmed:
        for section in confirmed:
            notes = manifest["capture"][section.id].get("notes") or manifest.get("analysis", {}).get(section.id, {}).get("summary", "Confirmed by transcript evidence.")
            guided.append(f"- **{section.label}:** {notes}\n")
    else:
        guided.append("- No sections have been approved yet.\n")
    guided.append("\n## Assumptions And Open Questions\n\n")
    if gap_rows:
        for row in gap_rows:
            guided.append(f"- **{row['section']} ({row['required']}):** {row['next_step']}\n")
    else:
        guided.append("- No open gaps detected.\n")
    guided.append("\n## Candidate Workflow Modules\n\n")
    guided.append("- Input standardisation and source contract validation.\n")
    guided.append("- Data-shape normalization into neutral accelerator entities.\n")
    guided.append("- Business rule application and exception routing.\n")
    guided.append("- Prioritisation, scoring, and output publishing.\n")
    guided.append("- Governance review output for weak or unsafe cases.\n")

    sop = [
        common_header,
        "## Build Objective\n\n",
        "Create a first-slice accelerator workflow only after the SOP gate is satisfied. The workflow should reflect approved customer facts, explicit assumptions, and known open gaps.\n\n",
        "## Scope And Business Outcome\n\n",
        manifest.get("capture", {}).get("scope_priorities", {}).get("notes") or "- Scope still requires CSM approval.\n",
        "\n\n## Input Contract\n\n",
        manifest.get("capture", {}).get("source_systems", {}).get("notes") or "- Source systems, ownership, cadence, and access constraints still require approval.\n",
        "\n",
        manifest.get("capture", {}).get("data_shape_entities", {}).get("notes") or "- Grain, entities, fields, and joins still require approval.\n",
        "\n\n## Business Logic\n\n",
        manifest.get("capture", {}).get("business_rules", {}).get("notes") or "- Business definitions, thresholds, filters, and exception rules still require approval.\n",
        "\n\n## Outputs And Actions\n\n",
        manifest.get("capture", {}).get("output_action", {}).get("notes") or "- Output/action design still requires approval.\n",
        "\n\n## Validation Expectations\n\n",
        manifest.get("capture", {}).get("validation_trust", {}).get("notes") or "- Validation method and sign-off owner still require approval.\n",
        "\n\n## Workflow Logic Modules\n\n",
    ]
    for module in ["Ingest and profile inputs", "Normalize to neutral schema", "Apply rules and assumptions", "Score and prioritise outputs", "Publish action and governance views"]:
        sop.append(f"- {module}\n")
    sop.append("\n## SOP Gate\n\n")
    sop.append(f"- Current gate status: **{readiness['workflow_gate']}**\n")
    sop.append(f"- Overall readiness: **{readiness['overall_pct']}%**\n")
    if readiness["blockers"]:
        sop.append("- Blockers:\n")
        for blocker in readiness["blockers"]:
            sop.append(f"  - {blocker}\n")
    else:
        sop.append("- No blockers detected. Workflow generation can be handed to the Large-only workflow builder path.\n")

    gap_log = [
        common_header,
        "## Gap Log\n\n",
        "| Section | Required | Capture | Transcript Evidence | Approval | Next Step |\n",
        "|---|---|---|---|---|---|\n",
    ]
    if gap_rows:
        for row in gap_rows:
            gap_log.append(f"| {row['section']} | {row['required']} | {row['capture']} | {row['evidence']} | {row['approval']} | {row['next_step']} |\n")
    else:
        gap_log.append("| None | yes | Complete | Supported | Approved | Ready for workflow handoff. |\n")

    assessment = [
        common_header,
        "## Architecture Assessment\n\n",
        "The cockpit treats `03_accelerator_sop.md` as the mandatory handoff gate before workflow generation.\n\n",
        "## Readiness Scores\n\n",
        f"- Capture readiness: {readiness['capture_pct']}%\n",
        f"- Transcript evidence readiness: {readiness['evidence_pct']}%\n",
        f"- Human approval readiness: {readiness['approval_pct']}%\n",
        f"- Artifact readiness: {readiness['artifact_pct']}%\n",
        f"- Overall readiness: {readiness['overall_pct']}%\n\n",
        "## Workflow Build Position\n\n",
    ]
    if readiness["workflow_gate"] == "ready":
        assessment.append("The project can move into Jon's Large-only workflow build handoff after final human review.\n")
    else:
        assessment.append("The project is not ready for workflow generation. Resolve the SOP gate blockers and regenerate the handoff prompt.\n")

    content_by_name = {
        "01_customer_discovery_conversation.md": "".join(discovery),
        "02_guided_sop_capture.md": "".join(guided),
        "03_accelerator_sop.md": "".join(sop),
        "sop_gap_log.md": "".join(gap_log),
        "sop_architecture_assessment.md": "".join(assessment),
    }

    for name, content in content_by_name.items():
        path = docs_dir / name
        path.write_text(content, encoding="utf-8")
        manifest.setdefault("artifacts", {}).setdefault(name, {})
        manifest["artifacts"][name].update(
            {
                "path": str(path),
                "relative_path": str(path.relative_to(project_dir)).replace("\\", "/"),
                "exists": True,
                "status": "generated",
                "generated_at": utc_now(),
            }
        )

    refreshed_readiness = calculate_readiness(_refresh_artifact_records(manifest), sections)
    status = _pipeline_status(manifest, refreshed_readiness)
    (status_dir / "pipeline_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (status_dir / "pipeline_log.md").write_text(
        f"# Pipeline Log\n\n- {utc_now()}: Generated cockpit document chain. Workflow gate: {refreshed_readiness['workflow_gate']}.\n",
        encoding="utf-8",
    )
    (status_dir / "next_stage_prompt.md").write_text(_workflow_handoff_prompt(manifest, refreshed_readiness), encoding="utf-8")

    return _refresh_artifact_records(manifest)


def sync_generated_docs(manifest: dict[str, Any]) -> dict[str, Any]:
    docs_dir = run_dir(manifest["run_id"]) / "docs"
    STARTER_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for name in DOC_ARTIFACTS:
        source = docs_dir / name
        if source.exists():
            shutil.copy2(source, STARTER_DOCS_DIR / name)
    manifest["sync"]["synced_at"] = utc_now()
    return manifest


def artifact_cards(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = _refresh_artifact_records(manifest).get("artifacts", {})
    return [records[name] for name in [*DOC_ARTIFACTS, "status/next_stage_prompt.md"] if name in records]


def process_stages() -> list[dict[str, Any]]:
    return load_sequence_config().get("stages", [])


def sections_as_dicts(sections: list[Section]) -> list[dict[str, Any]]:
    return [asdict(section) for section in sections]
