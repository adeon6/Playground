# CSM Accelerator Cockpit

This is a local, double-clickable prototype for helping a CSM run Jon's accelerator discovery process.

GitHub Pages hosts the landing page and downloadable ZIP. The real app runs locally because transcript handling, project files, and generated SOP artifacts should stay on the user's machine.

## Quick Start

1. Download or clone this folder.
2. Extract the ZIP into a fresh folder. The current ZIP opens as `csm-accelerator-cockpit-v4`.
3. Double-click `Start CSM Cockpit.bat`.
4. Wait for the browser to open.
5. Create a new accelerator project, attach a transcript, save guided capture, approve sections, and generate docs.
6. Double-click `Stop CSM Cockpit.bat` when finished.

The launcher creates a private `.venv`, installs dependencies from `requirements.txt`, starts the local FastAPI app, and opens `http://127.0.0.1:8765`.

## What Is The Brain?

V4 uses an explainable local rules engine for transcript coverage, not a hidden hosted AI model.

- It accepts `.docx`, `.md`, and `.txt` transcripts.
- It maps transcript evidence to Jon's section-level discovery model.
- It starts with transcript review before section-level capture.
- It summarizes why a section appears supported, weak, missing, or conflicting.
- It includes Value Realization and removes ambiguous Known Unknowns / Close Playback sections from the CSM workflow.
- It requires human approval before the SOP is treated as workflow-build ready.
- It generates a project-specific Codex workflow-build prompt and helper script after the SOP gate.
- It detects whether this machine exposes a launchable Codex command and whether Alteryx Designer/Engine is installed, but it does not contain or replace Codex and cannot detect an already-open Codex chat session.

Optional OpenAI-assisted evidence extraction can be added later, but it is deliberately not required for this shareable prototype.

## Workflow Build Handoff

Codex is still the workflow-building brain. The cockpit prepares the handoff package:

- `status/codex_workflow_build_prompt.md`
- `status/START_CODEX_WORKFLOW_BUILD.ps1`
- `status/workflow_build_manifest.json`
- project folders for `workflows/`, `validation/`, and generated sample data

The ZIP also bundles the local Alteryx workflow-builder toolkit and beautification guidance under `tooling/`. When the SOP gate is ready, the UI can copy the hydrated prompt, open the workflow folder, and optionally launch local Codex if a launchable Codex command is detected on the machine.

## Jon Process Pack

The app bundles Jon's latest accelerator operating-system files under `process_pack/`, including:

- `01_discovery/accelerator_interview_script.md`
- `02_sop_authoring/guided_sop_capture_template.md`
- `03_workflow_build/sop_to_alteryx_super_prompt_pack.md`
- `sequencer/sequence_config.json`

The app uses those files as the methodology reference and prepares a Large-only workflow handoff prompt when the SOP gate is ready.

## Generated Project Files

Each project is stored locally under:

```text
csm_cockpit/runs/<project-id>/
```

Each project contains Jon's expected folders:

```text
docs/
data/raw/
data/generated/
status/
workflows/
validation/
```

Generated docs are written into the project folder first. The advanced `SYNC` action is intentionally hidden behind an expandable control and only copies generated docs into `starter_docs/` when explicitly requested.

## Developer Commands

Run directly:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn csm_cockpit.app:app --reload --port 8765
```

Run tests:

```powershell
python -m unittest discover csm_cockpit/tests
```
