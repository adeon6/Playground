from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COCKPIT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = COCKPIT_ROOT / "runs"
STARTER_DOCS_DIR = PROJECT_ROOT / "starter_docs"
QUESTION_TEMPLATE_DOCX = PROJECT_ROOT / "assets" / "guided_discovery_conversation_template.docx"
DEFAULT_TRANSCRIPT_PATH = PROJECT_ROOT / "sample_data" / "sanitized_geo_spatial_discovery.docx"

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

REQUIRED_FOR_SOP_GATE = {
    "business_problem",
    "current_process",
    "desired_outcome",
    "business_questions",
    "scope",
    "inputs",
    "rules",
    "validation",
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
]


@dataclass(frozen=True)
class Section:
    id: str
    label: str
    prompt: str
    capture_fields: list[str]
    keywords: list[str]
    required: bool = True


FALLBACK_SECTIONS = [
    Section(
        "opening",
        "Opening",
        "Frame the discovery, confirm the customer, owner, intended outcome, and whether this is a proof of concept or production path.",
        ["Customer / engagement", "Primary business owner", "Supporting SMEs", "Intended outcome", "Discovery goal"],
        ["agenda", "goal", "objective", "today", "proof of concept", "poc", "business owner", "stakeholder"],
        required=False,
    ),
    Section(
        "business_problem",
        "Business Problem",
        "Understand the pain, business consequence, affected teams, and why solving this matters.",
        ["Core business problem", "Current pain", "Consequences / business impact", "Affected teams", "Desired improvement theme"],
        ["problem", "pain", "challenge", "manual", "slow", "risk", "trust", "inconsistent", "business impact"],
    ),
    Section(
        "current_process",
        "Current Process",
        "Capture how the work is done today, including steps, systems, handoffs, spreadsheets, and trust issues.",
        ["Current-state process", "Systems and teams involved", "Manual steps", "Bottlenecks", "Trust / quality issues"],
        ["current process", "today", "as is", "manual steps", "spreadsheet", "handoff", "workflow", "process"],
    ),
    Section(
        "desired_outcome",
        "Desired Outcome",
        "Clarify the first useful output, who consumes it, and what decision or action it should support.",
        ["Desired outputs", "Intended users", "Supported decisions / actions", "First-slice success criteria", "Deferred items"],
        ["output", "deliverable", "dashboard", "report", "app", "action", "decision", "success", "first version"],
    ),
    Section(
        "business_questions",
        "Business Questions",
        "List the questions the accelerator must answer and how cases should be prioritised or reviewed.",
        ["Core business questions", "Decision points", "Prioritisation needs", "Review / exception needs", "Business significance"],
        ["question", "decide", "prioritize", "prioritise", "exception", "review", "what should", "which cases"],
    ),
    Section(
        "scope",
        "Scope",
        "Separate first-slice scope from explicit exclusions, pilot boundaries, and later phases.",
        ["In-scope entities / domains", "Out-of-scope areas", "Pilot boundary", "Phase 1 intent", "Explicit exclusions"],
        ["scope", "in scope", "out of scope", "pilot", "phase", "region", "business unit", "product", "customer", "channel"],
    ),
    Section(
        "inputs",
        "Inputs",
        "Capture source systems, files, ownership, refresh cadence, fields, grain, and joins.",
        ["Source systems", "Input files / tables", "Owners", "Key fields", "Refresh cadence", "Known data quality constraints"],
        ["data", "source", "input", "file", "table", "field", "column", "extract", "system", "owner"],
    ),
    Section(
        "rules",
        "Rules",
        "Document business logic, definitions, calculations, thresholds, joins, filters, and exception handling.",
        ["Definitions", "Rules / logic", "Calculations", "Thresholds", "Join keys", "Filters"],
        ["rule", "logic", "definition", "threshold", "join", "filter", "criteria", "calculation", "formula"],
    ),
    Section(
        "exceptions",
        "Exceptions",
        "Identify bad, missing, invalid, or unsafe cases and how the first slice should handle them.",
        ["Known exceptions", "Missing / invalid data handling", "Safe defaults", "Fallback behaviour", "Governance review cases"],
        ["exception", "missing", "null", "bad data", "invalid", "edge case", "error", "safe", "fallback"],
        required=False,
    ),
    Section(
        "validation",
        "Validation",
        "Define how the customer will trust the output, who validates it, and what reconciliation is needed.",
        ["Validation method", "Review owner", "Reconciliation source", "Acceptance checks", "Sign-off expectations"],
        ["validate", "validation", "reconcile", "check", "test", "trust", "review", "sign-off", "compare"],
    ),
    Section(
        "operational_readiness",
        "Operational Readiness",
        "Capture run cadence, handover needs, operating owner, deployment path, and support expectations.",
        ["Run cadence", "Operating owner", "Handover needs", "Deployment path", "Support expectations"],
        ["operational", "schedule", "refresh", "run", "owner", "handover", "deploy", "production", "support"],
        required=False,
    ),
    Section(
        "playback",
        "Playback",
        "Play back confirmed facts, assumptions, open questions, and immediate next steps.",
        ["Confirmed facts", "Assumptions", "Open questions", "Next actions", "Approval state"],
        ["playback", "recap", "summary", "confirmed", "assumption", "open question", "next step"],
        required=False,
    ),
]


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return cleaned or "accelerator-run"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def template_root() -> Path:
    return COCKPIT_ROOT / "templates"


def static_root() -> Path:
    return COCKPIT_ROOT / "static"


def _normalise_section_label(raw: str) -> str:
    label = re.sub(r"^\s*\d+\.\s*", "", raw).strip()
    lower = label.lower()
    mappings = {
        "opening and framing": "Opening",
        "inputs, sources, and ownership": "Inputs",
        "rules, logic, and definitions": "Rules",
        "exceptions and safe handling": "Exceptions",
        "validation and trust": "Validation",
        "operational readiness and phasing": "Operational Readiness",
        "close and playback": "Playback",
    }
    return mappings.get(lower, label)


def _section_id(label: str) -> str:
    return slugify(label).replace("-", "_")


def _fallback_by_label() -> dict[str, Section]:
    return {section.label.lower(): section for section in FALLBACK_SECTIONS}


def _extract_capture_fields(text: str, fallback: list[str]) -> list[str]:
    after_marker = re.sub(r"(?is)^.*?specific capture for this section:\s*", "", text).strip()
    lines = [line.strip(" -:\t") for line in re.split(r"[\r\n]+", after_marker) if line.strip()]
    if len(lines) >= 2:
        return lines

    # Some Word table exports collapse the capture list into one line. Use known fallback
    # fields instead of guessing boundaries from title case.
    return fallback


def load_question_bank(template_path: Path = QUESTION_TEMPLATE_DOCX) -> list[Section]:
    fallback_lookup = _fallback_by_label()
    if not template_path.exists():
        return FALLBACK_SECTIONS

    try:
        document = Document(str(template_path))
    except Exception:
        return FALLBACK_SECTIONS

    sections: list[Section] = []
    for table in document.tables:
        rows = table.rows
        index = 1
        while index < len(rows):
            raw_title = rows[index].cells[0].text.strip()
            label = _normalise_section_label(raw_title)
            if not label:
                index += 1
                continue

            fallback = fallback_lookup.get(label.lower())
            if fallback is None:
                index += 1
                continue

            prompt = fallback.prompt
            fields = fallback.capture_fields
            if index + 1 < len(rows):
                prompt_text = rows[index + 1].cells[0].text.strip()
                capture_text = rows[index + 1].cells[1].text.strip()
                prompt = prompt_text or prompt
                fields = _extract_capture_fields(capture_text, fields)

            sections.append(
                Section(
                    id=fallback.id or _section_id(label),
                    label=label,
                    prompt=prompt,
                    capture_fields=fields,
                    keywords=fallback.keywords,
                    required=fallback.required,
                )
            )
            index += 2

    return sections if len(sections) >= 8 else FALLBACK_SECTIONS


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


def split_evidence_units(text: str) -> list[str]:
    rough_units = re.split(r"[\r\n]{2,}|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    units = []
    for unit in rough_units:
        cleaned = re.sub(r"\s+", " ", unit).strip()
        if len(cleaned) >= 40:
            units.append(cleaned)
    return units


def _keyword_hits(text: str, keywords: list[str]) -> int:
    total = 0
    lower_text = text.lower()
    for keyword in keywords:
        pattern = re.escape(keyword.lower())
        total += len(re.findall(pattern, lower_text))
    return total


def _top_evidence(units: list[str], section: Section, limit: int = 3) -> list[dict[str, Any]]:
    scored: list[tuple[int, str]] = []
    for unit in units:
        score = _keyword_hits(unit, section.keywords)
        if score:
            scored.append((score, unit))
    scored.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return [{"score": score, "snippet": snippet[:420]} for score, snippet in scored[:limit]]


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
        if score >= 8 or len(evidence) >= 3:
            status = "supported"
        elif score >= 2:
            status = "weak_evidence"

        capture_status = capture.get(section.id, {}).get("status", "not_answered")
        combined_snippets = " ".join(item["snippet"].lower() for item in evidence)
        has_uncertainty = any(term in combined_snippets for term in UNCERTAINTY_TERMS)
        if has_uncertainty and capture_status in {"answered", "partial"} and status != "missing":
            status = "conflicting"

        recommendation = "Ask follow-up or mark as an assumption before SOP approval."
        if status == "supported" and capture_status == "not_answered":
            recommendation = "Transcript appears to answer this even though CSM capture is not answered."
        elif status == "supported":
            recommendation = "Evidence is strong enough for CSM review."
        elif status == "weak_evidence":
            recommendation = "Partial evidence found. CSM should confirm before approval."
        elif status == "conflicting":
            recommendation = "Transcript includes uncertainty that conflicts with the capture state."

        analysis[section.id] = {
            "status": status,
            "score": score,
            "evidence": evidence,
            "recommendation": recommendation,
            "updated_at": utc_now(),
        }

    return analysis


def ensure_runs_dir() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def new_manifest(customer_name: str, project_name: str, csm_name: str, sections: list[Section]) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = slugify(customer_name or project_name or "customer")
    run_id = f"{timestamp}-{base}"
    run_dir = RUNS_DIR / run_id
    manifest = {
        "run_id": run_id,
        "customer_name": customer_name.strip() or "Unnamed customer",
        "project_name": project_name.strip() or "Accelerator discovery",
        "csm_name": csm_name.strip(),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "transcript": {
            "source_path": "",
            "stored_path": "",
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
            artifact: {
                "path": str(run_dir / "docs" / artifact),
                "exists": False,
                "status": "not_generated",
            }
            for artifact in DOC_ARTIFACTS
        },
        "sync": {
            "synced_at": "",
            "target_docs_dir": str(STARTER_DOCS_DIR),
        },
    }
    return manifest


def run_dir(run_id: str) -> Path:
    return RUNS_DIR / run_id


def manifest_path(run_id: str) -> Path:
    return run_dir(run_id) / "manifest.json"


def save_manifest(manifest: dict[str, Any]) -> None:
    ensure_runs_dir()
    manifest["updated_at"] = utc_now()
    path = manifest_path(manifest["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_manifest(run_id: str) -> dict[str, Any]:
    return json.loads(manifest_path(run_id).read_text(encoding="utf-8"))


def list_manifests() -> list[dict[str, Any]]:
    ensure_runs_dir()
    manifests = []
    for path in sorted(RUNS_DIR.glob("*/manifest.json"), reverse=True):
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
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


def attach_transcript_from_path(manifest: dict[str, Any], source_path: Path, sections: list[Section]) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(f"Transcript not found: {source_path}")
    target_dir = run_dir(manifest["run_id"]) / "transcripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_path.name
    if source_path.resolve() != target.resolve():
        shutil.copy2(source_path, target)

    text = read_docx_text(target)
    manifest["transcript"] = {
        "source_path": str(source_path),
        "stored_path": str(target),
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
    target_dir = run_dir(manifest["run_id"]) / "transcripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(Path(original_name).stem) + ".docx"
    target = target_dir / safe_name
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

    def avg(values: list[float]) -> float:
        return round((sum(values) / len(values)) * 100) if values else 0

    capture_pct = avg([capture_weights.get(capture.get(section.id, {}).get("status", "not_answered"), 0) for section in required_sections])
    evidence_pct = avg([evidence_weights.get(analysis.get(section.id, {}).get("status", "not_run"), 0) for section in required_sections])
    approval_pct = avg([1.0 if capture.get(section.id, {}).get("approved") else 0.0 for section in required_sections])
    artifact_pct = avg([1.0 if manifest.get("artifacts", {}).get(name, {}).get("exists") else 0.0 for name in DOC_ARTIFACTS])
    overall_pct = round(capture_pct * 0.35 + evidence_pct * 0.25 + approval_pct * 0.25 + artifact_pct * 0.15)

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

    missing_docs = [name for name in DOC_ARTIFACTS if not manifest.get("artifacts", {}).get(name, {}).get("exists")]
    if missing_docs:
        blockers.append("Generated docs are incomplete.")

    return {
        "capture_pct": capture_pct,
        "evidence_pct": evidence_pct,
        "approval_pct": approval_pct,
        "artifact_pct": artifact_pct,
        "overall_pct": overall_pct,
        "workflow_gate": "ready" if not blockers else "blocked",
        "blockers": blockers[:12],
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
        f"- Notes: {item.get('notes') or 'Not captured yet.'}",
    ]
    if evidence:
        lines.append("- Evidence snippets:")
        for evidence_item in evidence:
            snippet = evidence_item["snippet"].replace("\n", " ")
            lines.append(f"  - {snippet}")
    else:
        lines.append("- Evidence snippets: none found.")
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
        if (
            capture_status in {"not_answered", "needs_follow_up"}
            or evidence_status in {"missing", "conflicting", "not_run"}
            or not capture_item.get("approved")
        ):
            rows.append(
                {
                    "section": section.label,
                    "capture": CAPTURE_STATUSES.get(capture_status, "Not answered"),
                    "evidence": EVIDENCE_STATUSES.get(evidence_status, "Not run"),
                    "approval": "approved" if capture_item.get("approved") else "pending",
                    "next_step": analysis_item.get("recommendation", "CSM follow-up required."),
                }
            )
    return rows


def generate_docs(manifest: dict[str, Any], sections: list[Section]) -> dict[str, Any]:
    docs_dir = run_dir(manifest["run_id"]) / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    readiness = calculate_readiness(manifest, sections)
    confirmed = _confirmed_sections(manifest, sections)
    gap_rows = _gap_rows(manifest, sections)

    common_header = (
        f"# {manifest['customer_name']} - {manifest['project_name']}\n\n"
        f"- CSM: {manifest.get('csm_name') or 'Not captured'}\n"
        f"- Run ID: `{manifest['run_id']}`\n"
        f"- Generated: {utc_now()}\n"
        f"- Transcript: `{manifest.get('transcript', {}).get('stored_path') or 'not attached'}`\n\n"
    )

    discovery = [
        common_header,
        "## Discovery Capture\n\n",
        "This file is generated from CSM capture plus transcript evidence. It is the safe replacement for a raw transcript handoff.\n\n",
    ]
    discovery.extend(_section_capture_md(section, manifest) for section in sections)

    guided = [
        common_header,
        "## Confirmed Facts\n\n",
    ]
    if confirmed:
        for section in confirmed:
            notes = manifest["capture"][section.id].get("notes") or "Confirmed by transcript evidence."
            guided.append(f"- **{section.label}:** {notes}\n")
    else:
        guided.append("- No sections have been approved yet.\n")
    guided.append("\n## Assumptions And Open Questions\n\n")
    if gap_rows:
        for row in gap_rows:
            guided.append(f"- **{row['section']}:** {row['next_step']}\n")
    else:
        guided.append("- No open gaps detected.\n")
    guided.append("\n## Candidate Workflow Modules\n\n")
    guided.append("- Input standardisation and source contract validation.\n")
    guided.append("- Business rule application and exception routing.\n")
    guided.append("- Prioritisation, scoring, and output publishing.\n")
    guided.append("- Governance review output for weak or unsafe cases.\n")

    sop = [
        common_header,
        "## Build Objective\n\n",
        "Create a first-slice accelerator workflow only after the SOP gate is satisfied. The workflow should reflect approved customer facts, explicit assumptions, and known open gaps.\n\n",
        "## Input Contract\n\n",
    ]
    inputs_notes = manifest.get("capture", {}).get("inputs", {}).get("notes")
    sop.append(inputs_notes + "\n\n" if inputs_notes else "- Source files, ownership, grain, and joins still require approval.\n\n")
    sop.append("## Workflow Logic Modules\n\n")
    for module in ["Ingest and profile inputs", "Normalize to neutral schema", "Apply rules and assumptions", "Score and prioritise outputs", "Publish action and governance views"]:
        sop.append(f"- {module}\n")
    sop.append("\n## Validation Expectations\n\n")
    validation_notes = manifest.get("capture", {}).get("validation", {}).get("notes")
    sop.append(validation_notes + "\n\n" if validation_notes else "- Validation method is not fully approved yet.\n\n")
    sop.append("## SOP Gate\n\n")
    sop.append(f"- Current gate status: **{readiness['workflow_gate']}**\n")
    sop.append(f"- Overall readiness: **{readiness['overall_pct']}%**\n")
    if readiness["blockers"]:
        sop.append("- Blockers:\n")
        for blocker in readiness["blockers"]:
            sop.append(f"  - {blocker}\n")
    else:
        sop.append("- No blockers detected. Workflow generation can be handed to the workflow builder.\n")

    gap_log = [
        common_header,
        "## Gap Log\n\n",
        "| Section | Capture | Transcript Evidence | Approval | Next Step |\n",
        "|---|---|---|---|---|\n",
    ]
    if gap_rows:
        for row in gap_rows:
            gap_log.append(f"| {row['section']} | {row['capture']} | {row['evidence']} | {row['approval']} | {row['next_step']} |\n")
    else:
        gap_log.append("| None | Complete | Supported | Approved | Ready for workflow handoff. |\n")

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
        assessment.append("The run is ready to move into the Alteryx workflow builder path.\n")
    else:
        assessment.append("The run is not ready for workflow generation. Resolve the SOP gate blockers first.\n")

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
                "exists": True,
                "status": "generated",
                "generated_at": utc_now(),
            }
        )

    return manifest


def sync_generated_docs(manifest: dict[str, Any]) -> dict[str, Any]:
    docs_dir = run_dir(manifest["run_id"]) / "docs"
    STARTER_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for name in DOC_ARTIFACTS:
        source = docs_dir / name
        if source.exists():
            shutil.copy2(source, STARTER_DOCS_DIR / name)
    manifest["sync"]["synced_at"] = utc_now()
    return manifest


def sections_as_dicts(sections: list[Section]) -> list[dict[str, Any]]:
    return [asdict(section) for section in sections]
