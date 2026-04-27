# alteryx-workflow-builder

Developer notes for the repo-local Codex skill that converts business problems into Alteryx workflow artifacts and enforces static QA checks.

## Python
- Python 3.10+
- Dependency: `jsonschema`

Install dependency:
```bash
python -m pip install jsonschema
```

## Main CLI
```bash
python scripts/alteryx_build.py --problem "Build a weekly SLA dashboard workflow from tickets.csv" --out_dir ./dist
python scripts/alteryx_build.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist --designer_version 2025.1 --package
```

## Static Lint
```bash
python scripts/lint_yxmd.py ./dist --recursive --expected-version 2025.1 --report ./dist/lint_report.json
```

## Workflow Image Preview
Generate a canvas-style PNG preview from workflow XML:
```bash
python scripts/render_workflow_image.py ./dist/01_support_sla_weekly.yxmd --out ./dist/01_support_sla_weekly.png
```

Notes:
- This is a recreated preview, not a true Alteryx Designer screenshot.
- `scripts/render_workflow_image.py` is the canonical renderer.
- `scripts/render_workflow_image_v2.py` is kept only as a compatibility alias to the same implementation.
- Dependency: `pillow`
- Install with:
```bash
python -m pip install pillow
```

## Real Designer Screenshot
Capture a true screenshot from an Alteryx Designer window by automating `File > Open` and then grabbing the window:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\capture_designer_screenshot.ps1 `
  -WorkflowPath ".\dist\01_support_sla_weekly.yxmd" `
  -OutputPath ".\dist\01_support_sla_weekly.designer.png"
```

Notes:
- This is intended for local interactive Windows sessions.
- It is especially useful for `.yxwz` analytic apps, where shell-opening the file may not open the editable Designer view directly.

## Low-level Commands
```bash
python scripts/validate_spec.py --spec ./examples/support_sla/workflow_spec.json
python scripts/compile.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist
python scripts/package_yxzp.py --source_dir ./dist --out ./dist/package.yxzp
python scripts/smoke_test.py
```

## Notes
- Compiler outputs stable tool IDs from SHA-1 hashes of step IDs.
- Layout is deterministic: fixed X spacing and branch-aware Y offsets.
- Default generated `yxmdVer` is `2025.1` unless overridden by `metadata.designer_version`.
- Linter catches non-runtime issues (invalid XML, unresolved placeholders, broken connections, duplicate ToolIDs, risky absolute paths).
- Runtime verification is a separate step from static linting. Use `C:\Program Files\Alteryx\bin\AlteryxEngineCmd.exe <workflow.yxmd>` to execute a workflow outside Designer when live validation is needed.
- To inspect runtime results from CLI-driven execution, wire a temporary Browse or Output Data tool, run the workflow with `AlteryxEngineCmd.exe`, then inspect the produced temp/output artifact before finalizing fixes.
