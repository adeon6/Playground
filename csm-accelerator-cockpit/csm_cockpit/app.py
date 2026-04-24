from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .services import (
    CAPTURE_STATUSES,
    DEFAULT_TRANSCRIPT_PATH,
    DOC_ARTIFACTS,
    EVIDENCE_STATUSES,
    RUNS_DIR,
    STARTER_DOCS_DIR,
    attach_transcript_from_path,
    attach_uploaded_transcript,
    calculate_readiness,
    generate_docs,
    list_manifests,
    load_manifest,
    load_question_bank,
    new_manifest,
    run_dir,
    save_manifest,
    static_root,
    sync_generated_docs,
    template_root,
    update_approvals_from_form,
    update_capture_from_form,
)


app = FastAPI(title="CSM Accelerator Cockpit V1")
app.mount("/static", StaticFiles(directory=static_root()), name="static")
templates = Jinja2Templates(directory=template_root())


def _sections():
    return load_question_bank()


def _manifest_or_404(run_id: str) -> dict[str, Any]:
    try:
        return load_manifest(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc


def _redirect(run_id: str | None = None) -> RedirectResponse:
    suffix = f"?run_id={run_id}" if run_id else ""
    return RedirectResponse(url=f"/{suffix}", status_code=303)


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
        "index.html",
        {
            "request": request,
            "sections": sections,
            "runs": runs,
            "manifest": manifest,
            "readiness": readiness,
            "capture_statuses": CAPTURE_STATUSES,
            "evidence_statuses": EVIDENCE_STATUSES,
            "doc_artifacts": DOC_ARTIFACTS,
            "default_transcript_path": str(DEFAULT_TRANSCRIPT_PATH),
            "default_transcript_exists": DEFAULT_TRANSCRIPT_PATH.exists(),
            "runs_dir": str(RUNS_DIR),
            "starter_docs_dir": str(STARTER_DOCS_DIR),
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
    return _redirect(manifest["run_id"])


@app.post("/runs/{run_id}/capture")
async def save_capture(run_id: str, request: Request):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    form = dict(await request.form())
    update_capture_from_form(manifest, form, sections)
    if manifest.get("transcript", {}).get("stored_path"):
        attach_transcript_from_path(manifest, Path(manifest["transcript"]["stored_path"]), sections)
    save_manifest(manifest)
    return _redirect(run_id)


@app.post("/runs/{run_id}/transcript")
async def analyze_transcript(
    run_id: str,
    transcript_file: UploadFile | None = File(None),
    transcript_path: str = Form(""),
):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    try:
        if transcript_file and transcript_file.filename:
            payload = await transcript_file.read()
            manifest = attach_uploaded_transcript(manifest, transcript_file.filename, payload, sections)
        elif transcript_path.strip():
            manifest = attach_transcript_from_path(manifest, Path(transcript_path.strip()), sections)
        else:
            raise HTTPException(status_code=400, detail="Attach a DOCX file or provide a transcript path.")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_manifest(manifest)
    return _redirect(run_id)


@app.post("/runs/{run_id}/approve")
async def save_approvals(run_id: str, request: Request):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    form = dict(await request.form())
    update_approvals_from_form(manifest, form, sections)
    save_manifest(manifest)
    return _redirect(run_id)


@app.post("/runs/{run_id}/generate-docs")
async def generate_run_docs(run_id: str):
    sections = _sections()
    manifest = _manifest_or_404(run_id)
    manifest = generate_docs(manifest, sections)
    save_manifest(manifest)
    return _redirect(run_id)


@app.post("/runs/{run_id}/sync-docs")
async def sync_docs(run_id: str, confirmation: str = Form("")):
    manifest = _manifest_or_404(run_id)
    if confirmation.strip().upper() != "SYNC":
        raise HTTPException(status_code=400, detail="Type SYNC to copy generated docs into the starter docs folder.")
    manifest = sync_generated_docs(manifest)
    save_manifest(manifest)
    return _redirect(run_id)


@app.get("/health")
async def health():
    return {"status": "ok", "runs_dir": str(RUNS_DIR)}

