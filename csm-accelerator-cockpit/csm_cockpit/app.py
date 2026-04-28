from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .services import (
    APP_VERSION,
    ACCELERATOR_ASSET_ARTIFACTS,
    CAPTURE_STATUSES,
    DEFAULT_TRANSCRIPT_PATH,
    DOC_ARTIFACTS,
    EVIDENCE_STATUSES,
    PEER_REVIEW_STATUS_ARTIFACT,
    PROJECT_ROOT,
    attach_transcript_from_path,
    attach_uploaded_transcript,
    artifact_cards,
    artifact_file_path,
    calculate_readiness,
    delete_run,
    generate_docs,
    generate_workflow_build_handoff,
    list_manifests,
    load_manifest,
    load_question_bank,
    launch_codex_for_run,
    new_manifest,
    open_project_subfolder,
    process_stages,
    reanalyze_transcript_corpus,
    run_dir,
    save_manifest,
    static_root,
    sync_generated_docs,
    template_root,
    update_approvals_from_form,
    update_capture_from_form,
)


app = FastAPI(title="CSM Accelerator Cockpit V4.4.1")
app.mount("/static", StaticFiles(directory=static_root()), name="static")
templates = Jinja2Templates(directory=template_root())


def _sections():
    return load_question_bank()


def _manifest_or_404(run_id: str) -> dict[str, Any]:
    try:
        return load_manifest(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc


def _redirect(run_id: str | None = None, anchor: str = "") -> RedirectResponse:
    suffix = f"?run_id={run_id}" if run_id else ""
    fragment = f"#{anchor}" if anchor else ""
    return RedirectResponse(url=f"/{suffix}{fragment}", status_code=303)


def _helper_files_created(manifest: dict[str, Any] | None) -> bool:
    if not manifest:
        return False
    artifacts = manifest.get("artifacts", {})
    helper_artifacts = [*DOC_ARTIFACTS, *ACCELERATOR_ASSET_ARTIFACTS, PEER_REVIEW_STATUS_ARTIFACT]
    return all(artifacts.get(name, {}).get("exists") for name in helper_artifacts)


@app.get("/")
async def home(request: Request, run_id: str | None = None):
    sections = _sections()
    runs = list_manifests()
    manifest = None
    readiness = None
    if run_id:
        manifest = _manifest_or_404(run_id)
    elif runs:
        manifest = runs[0]

    if manifest:
        readiness = calculate_readiness(manifest, sections)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "sections": sections,
            "runs": runs,
            "manifest": manifest,
            "readiness": readiness,
            "capture_statuses": CAPTURE_STATUSES,
            "evidence_statuses": EVIDENCE_STATUSES,
            "doc_artifacts": DOC_ARTIFACTS,
            "artifact_cards": artifact_cards(manifest) if manifest else [],
            "helper_files_created": _helper_files_created(manifest),
            "process_stages": process_stages(),
            "default_transcript_path": str(DEFAULT_TRANSCRIPT_PATH),
            "default_transcript_exists": DEFAULT_TRANSCRIPT_PATH.exists(),
            "app_version": APP_VERSION,
        },
    )


@app.post("/runs")
async def create_run(
    customer_name: str = Form(""),
    project_name: str = Form(""),
    csm_name: str = Form(""),
):
    sections = _sections()
    manifest = new_manifest(customer_name, project_name, csm_name, sections)
    save_manifest(manifest)
    return _redirect(manifest["run_id"], "transcript-review")


@app.post("/runs/{run_id}/capture")
async def save_capture(run_id: str, request: Request):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    form = dict(await request.form())
    update_capture_from_form(manifest, form, sections)
    reanalyze_transcript_corpus(manifest, sections)
    save_manifest(manifest)
    return _redirect(run_id, "guided-call")


@app.post("/runs/{run_id}/section/{section_id}")
async def autosave_section(run_id: str, section_id: str, request: Request):
    sections = _sections()
    section_by_id = {section.id: section for section in sections}
    section = section_by_id.get(section_id)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section not found: {section_id}")

    manifest = _manifest_or_404(run_id)
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Expected JSON payload.") from exc

    capture = manifest.setdefault("capture", {})
    item = capture.setdefault(section_id, {"status": "not_set", "notes": "", "approved": False})
    status = str(payload.get("status", item.get("status", "not_set")))
    changed_field = str(payload.get("changed_field", ""))
    item["status"] = status if status in CAPTURE_STATUSES else "not_set"
    item["notes"] = str(payload.get("notes", item.get("notes", ""))).strip()
    item["approved"] = bool(payload.get("approved", item.get("approved", False)))

    reanalyze_transcript_corpus(manifest, sections)
    save_manifest(manifest)
    refreshed = load_manifest(run_id)
    readiness = calculate_readiness(refreshed, sections)
    analysis = refreshed.get("analysis", {}).get(section_id, {})
    evidence_status = analysis.get("status", "not_run")
    should_open = item["status"] in {"not_set", "partial", "not_answered", "needs_follow_up"}
    auto_collapse = changed_field == "status" and item["status"] == "answered"
    return {
        "ok": True,
        "section_id": section_id,
        "section_label": section.label,
        "capture_status": item["status"],
        "capture_label": CAPTURE_STATUSES.get(item["status"], "Not answered"),
        "approved": item["approved"],
        "approval_label": "approved" if item["approved"] else "pending",
        "evidence_status": evidence_status,
        "evidence_label": EVIDENCE_STATUSES.get(evidence_status, "Not run"),
        "readiness": readiness,
        "should_open": should_open,
        "auto_collapse": auto_collapse,
    }


@app.post("/runs/{run_id}/transcript")
async def analyze_transcript(
    run_id: str,
    transcript_file: UploadFile | None = File(None),
    transcript_path: str = Form(""),
    transcript_source: str = Form("upload"),
):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    try:
        if transcript_source == "sample":
            source = Path(transcript_path.strip()) if transcript_path.strip() else DEFAULT_TRANSCRIPT_PATH
            manifest = attach_transcript_from_path(manifest, source, sections, source_type="bundled_demo")
        elif transcript_file and transcript_file.filename:
            payload = await transcript_file.read()
            manifest = attach_uploaded_transcript(manifest, transcript_file.filename, payload, sections)
        else:
            raise HTTPException(status_code=400, detail="Choose upload and attach a transcript, or choose the bundled demo transcript.")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_manifest(manifest)
    return _redirect(run_id, "transcript-review")


@app.post("/runs/{run_id}/approve")
async def save_approvals(run_id: str, request: Request):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    form = dict(await request.form())
    update_approvals_from_form(manifest, form, sections)
    save_manifest(manifest)
    return _redirect(run_id, "guided-call")


@app.post("/runs/{run_id}/generate-docs")
async def generate_run_docs(run_id: str):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    manifest = generate_docs(manifest, sections)
    save_manifest(manifest)
    return _redirect(run_id, "workflow-handoff")


@app.post("/runs/{run_id}/workflow-build")
async def generate_workflow_build(run_id: str):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    manifest = generate_workflow_build_handoff(manifest, sections)
    save_manifest(manifest)
    return _redirect(run_id, "workflow-handoff")


@app.post("/runs/{run_id}/launch-codex")
async def launch_codex(run_id: str):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    try:
        manifest = launch_codex_for_run(manifest, sections)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_manifest(manifest)
    return _redirect(run_id, "workflow-handoff")


@app.post("/runs/{run_id}/open-folder")
async def open_folder(run_id: str, target: str = Form("project")):
    manifest = _manifest_or_404(run_id)
    try:
        open_project_subfolder(manifest, target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _redirect(run_id, "workflow-handoff")


@app.post("/runs/{run_id}/sync-docs")
async def sync_docs(run_id: str, confirmation: str = Form("")):
    manifest = _manifest_or_404(run_id)
    if confirmation.strip().upper() != "SYNC":
        raise HTTPException(status_code=400, detail="Type SYNC to copy generated docs into the starter docs folder.")
    manifest = sync_generated_docs(manifest)
    save_manifest(manifest)
    return _redirect(run_id, "workflow-handoff")


@app.post("/runs/{run_id}/delete")
async def delete_project(run_id: str, confirmation: str = Form("")):
    _manifest_or_404(run_id)
    if confirmation.strip().upper() != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to remove this generated project.")
    try:
        delete_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _redirect()


@app.get("/runs/{run_id}/artifacts/{artifact_key:path}")
async def get_artifact(run_id: str, artifact_key: str):
    try:
        path = artifact_file_path(run_id, artifact_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(path)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "csm-accelerator-cockpit",
        "version": APP_VERSION,
        "app_root": str(PROJECT_ROOT),
        "process": "Jon accelerator operating system aligned",
    }
