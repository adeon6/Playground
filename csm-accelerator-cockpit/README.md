# CSM Accelerator Cockpit

This is a local, double-clickable prototype for helping a CSM run an accelerator discovery process.

It is intentionally not hosted on GitHub Pages because the real app needs Python to read DOCX transcripts, score evidence, store run manifests, and generate markdown handoff documents. GitHub hosts the source and update history; the app runs locally on the user's machine.

## Quick Start

1. Download or clone this folder.
2. Double-click `Start CSM Cockpit.bat`.
3. Wait for the browser to open.
4. Create a run, save the guided capture, and analyze the sanitized sample transcript.
5. Double-click `Stop CSM Cockpit.bat` when finished.

The launcher creates a private `.venv` folder, installs dependencies from `requirements.txt`, starts the local FastAPI app, and opens `http://127.0.0.1:8765`.

## What Is The Brain?

V1 uses an explainable local rules engine, not a hidden AI model.

- The app reads the DOCX transcript with `python-docx`.
- It loads the discovery checklist from the template if available, otherwise from the built-in question bank.
- Each section has keywords and expected capture fields.
- Transcript snippets are scored against those keywords.
- Each section is marked as `supported`, `weak evidence`, `missing`, or `conflicting`.
- The CSM still has the final approval gate before docs are generated.

An optional OpenAI extraction layer can be added later, but it is deliberately not required for this shareable V1.

## Generated Files

Each run is stored under:

```text
csm_cockpit/runs/<run-id>/
```

Generated handoff docs are written to the run folder first. The app only copies them into `starter_docs/` if the user explicitly types `SYNC` in the UI.

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

