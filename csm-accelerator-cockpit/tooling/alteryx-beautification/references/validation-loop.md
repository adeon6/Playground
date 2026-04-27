# Validation Loop

## Required Mindset

XML validity is necessary but not sufficient. A beautified workflow is only done when the validator is happy, the render looks clean, and the runtime behavior still holds.

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
