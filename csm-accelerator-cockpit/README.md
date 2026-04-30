# Accelerator Cockpit

This is a local, double-clickable prototype for guided accelerator discovery, evidence review, SOP approval, and workflow handoff preparation.

GitHub Pages hosts the landing page and downloadable ZIP. The real app runs locally because transcript handling, project files, and generated SOP artifacts should stay on the user's machine.

## Quick Start

1. Download or clone this folder.
2. Extract the ZIP into a fresh folder. The standard ZIP opens as `csm-accelerator-cockpit-v5.4`.
3. Double-click `Start Accelerator Cockpit.bat`.
4. Wait for the browser to open.
5. Create a new accelerator project, attach transcript evidence, work the guided sections, approve sections inline, and generate docs.
6. Double-click `Stop Accelerator Cockpit.bat` when finished.

The launcher creates a private `.venv`, installs dependencies from `requirements.txt`, starts the local FastAPI app, and opens `http://127.0.0.1:8765`.

## What Is The Brain?

V5.4 uses an explainable local rules engine for transcript coverage, not a hidden hosted AI model.

- It accepts `.docx`, `.md`, and `.txt` transcripts.
- It supports additive follow-up transcripts, building one combined evidence corpus.
- It maps transcript evidence to the guided discovery template.
- It starts with transcript review before section-level capture.
- It summarizes transcript support as advisory evidence; only status and approval block or unblock generation.
- It keeps capture, evidence playback, and SOP approval in one autosaving Guided Call section.
- It uses the required sections, including Value Realisation and Operational Readiness And Phasing.
- It requires human approval before the SOP is treated as workflow-build ready.
- It generates James-style accelerator assets: value statement, use-case summary, case-study skeleton, and 101/102/201 drafts.
- It generates a project-specific workflow-build prompt and manifest after the SOP gate.
- It checks whether Alteryx Designer/Engine and bundled builder tooling are available.

Optional OpenAI-assisted evidence extraction can be added later, but it is deliberately not required for this shareable prototype.

## Download Options

- `csm-accelerator-cockpit-v5.4-local.zip` is the standard self-contained package. It bundles project-local workflow-builder and beautification tooling, writes a tooling manifest, and forces generated workflow prompts to use that local tooling.
- `csm-accelerator-cockpit-v5.4-with-global-skills.zip` includes the same cockpit plus `Install Or Update Codex Alteryx Skills.bat`. Run that installer only if you also want future Codex sessions outside cockpit projects to use the same global Alteryx workflow-builder and beautification skills.

## Workflow Build Handoff

The cockpit prepares a controlled workflow-build handoff package:

- `03_workflow_build/status/codex_workflow_build_prompt.md`
- `03_workflow_build/status/START_CODEX_WORKFLOW_BUILD.ps1`
- `03_workflow_build/status/workflow_build_manifest.json`
- project folders for `03_workflow_build/workflows/`, `03_workflow_build/validation/`, and generated sample data

The ZIP also bundles the local Alteryx workflow-builder toolkit, the refreshed customer-facing hybrid reference workflow, and beautification guidance under `tooling/`. When the SOP gate is ready, the UI can copy the hydrated prompt and open the workflow folder.

Bundled workflow-builder and beautification tooling must be refreshed and checked against the global `.codex` skills during every Cockpit release. The generated project-local `tooling/` folder is the source of truth for downstream workflow builds, so colleagues do not need matching global skills installed.

V4.2 also writes an absolute canonical project root and identity hash into the generated prompt and manifest. The handoff is instructed to fail closed if the path, project ID, SOP gate, or identity hash does not match, and not to fallback-search nearby projects.

V4.3 added customer-facing accelerator asset drafts and `status/peer_review_status.json` so CSMs can distinguish internal build docs from reusable customer-facing content.

V4.4 simplifies the UI around the discovery template: no separate Human Approval step, no standalone Artifact Dashboard, no evidence percentage card, and no manual Save Capture/Save Approvals buttons.

The guided UI uses status radio buttons with a true untouched state, clickable blockers, a single handoff generation button, and calmer section collapse behavior.

V5 aligns generated project outputs to the operating-system folder structure, treats transcript evidence as advisory rather than blocking, bundles the latest workflow-builder/beautification skills, and instructs the workflow build to start from the approved folder chain rather than skipping straight from transcript to `.yxmd`.

V5 also makes the reference-workflow boundary explicit: the hybrid workflow reference is visual grammar only. The build must not copy its schemas, formulas, tool sequence, output shape, or business entities unless the current approved SOP independently requires them.

V5.1 fixes stale readiness in generated SOP/assessment markdown, tightens the guided section layout, and refreshes the UI toward a cleaner Alteryx-inspired internal style.

V5.2 moves section collapse to the explicit SOP approval checkbox, adds a compact next-action strip, improves review-snippet affordances, and tightens responsive section layout.

V5.3 makes workflow-build handoffs reproducible across machines by refreshing the bundled Alteryx builder/beautification tooling at package time, writing a project-local tooling manifest, and forcing generated Codex prompts to read and use the project-local tooling before workflow design.

V5.4 adds a second optional download package that can install or update the two global Codex Alteryx skills from the bundled package, while keeping the standard package fully self-contained and unchanged in behavior.

## Process Pack

The app bundles the accelerator operating-system files under `process_pack/`, including:

- `01_discovery/accelerator_interview_script.md`
- `02_sop_authoring/guided_sop_capture_template.md`
- `03_workflow_build/sop_to_alteryx_super_prompt_pack.md`
- `sequencer/sequence_config.json`

The app uses those files as the methodology reference and prepares a Large-only workflow handoff prompt when the SOP gate is ready.

## Generated Project Files

Each project is stored locally under:

```text
%USERPROFILE%\Documents\CODEX\alteryx\accelerator_projects\<project-id>\
```

Each project contains the expected folders:

```text
00_start_here/
01_discovery/
02_sop_authoring/
03_workflow_build/
04_reference_examples/
sequencer/
data/raw/transcripts/
data/generated/
tooling/
```

Generated docs are written into the project folders first. The UI shows the handoff-file state inside Workflow Handoff and links directly to the generated project folder.

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

Before packaging a new Cockpit release, refresh bundled tooling from:

```text
C:\Users\Adeon\.codex\skills\alteryx-workflow-builder
C:\Users\Adeon\.codex\skills\alteryx-beautification
```

Then regenerate the local ZIP and run the package smoke tests so the distributed app receives the same builder and beautification rules used locally.
