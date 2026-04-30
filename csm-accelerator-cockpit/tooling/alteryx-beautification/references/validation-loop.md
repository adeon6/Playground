# Validation Loop

## Required Mindset

XML validity is necessary but not sufficient. A beautified workflow is only done when the validator is happy, the render looks clean, runtime behavior still holds, and Designer preserves the intended container layout after open/run/refresh.

## Recommended Loop

1. Edit the workflow.
2. Run the verifier.
3. Fix the smallest viable issue.
4. Re-run the verifier.
5. Render a preview image.
6. Inspect the preview for:
   - crossings
   - branch ambiguity
   - crowded hubs
   - clipped annotations
   - container crowding
   - dead space
7. If output values matter, run the Alteryx engine and confirm outputs still match expectations.
8. After engine execution or Designer run, inspect the workflow again for post-run visual drift:
   - containers must remain expanded with their tools inside
   - no section should collapse to an empty header unless intentionally folded
   - documentation containers must still contain their text boxes

## Commands

If the local workflow-builder tooling exists, prefer these:

```bash
python C:\Users\Adeon\OneDrive\Documents\Playground\alteryx_workflow_builder\verify_workflows.py <workflow-or-root>
python C:\Users\Adeon\OneDrive\Documents\Playground\alteryx_workflow_builder\scripts\lint_yxmd.py <workflow> --expected-version 2025.1 --report <report-path>
python C:\Users\Adeon\OneDrive\Documents\Playground\alteryx_workflow_builder\scripts\render_workflow_image.py <workflow> --out <png-path>
& "C:\Program Files\Alteryx\bin\AlteryxEngineCmd.exe" <workflow>
```

If those exact paths do not exist in the current environment, use the equivalent local verifier, renderer, and engine commands that do.

## Interpreting Lint Warnings

- Text boxes and containers may show up as disconnected in static lint; that is usually acceptable.
- Real connector or containment failures are not acceptable.
- A render that still looks tangled is a failure even if the verifier passes.
- A preview with section boxes behind tools is not enough proof of containment. Confirm the XML uses ToolContainer `<ChildNodes>` or verify in Designer after run.
