# Customer-Facing Hybrid Profile

Use this profile when a workflow must be presentable on first open in Designer, especially for customer playback, accelerator review, CSM handoff, or reusable starter-kit work.

Primary reference asset:

- `assets/customer-facing-hybrid-reference.yxmd`
- `assets/customer-facing-hybrid-reference.png`

This reference is the taste anchor for the whole canvas, not only the documentation frame. It demonstrates the combined standard:

- colored contextual containers around all real Alteryx tools
- a calm customer-facing title banner above the workflow body
- readable lanes with minimal spiderweb effect
- concise native tool annotations
- a bottom documentation shelf
- an optional side tip panel
- package-safe relative inputs and outputs

## Canvas Structure

- Top: customer-facing title banner.
- Middle: executable workflow body.
- Bottom: documentation shelf.
- Side, optional: one focused tip or caveat panel.

The reader should understand the use case before reaching the tools, follow the logic left to right, and then have enough documentation below the workflow to explain how to reuse or validate it.

## Top Banner Rules

- Use a dark, calm banner color.
- Place the broad workflow category and specific use case in the left title panel.
- Place concise purpose and outcome text in the right explanation panel.
- Keep the banner above every tool container.
- Leave visible whitespace between the banner and the tool body.
- The banner should orient the reader, not become a full SOP.

## Workflow Body Rules

- Every real Alteryx tool belongs inside a titled contextual container.
- Container color should be semantic, light, and desaturated.
- Inputs should usually use green/teal family colors.
- Prep/formula sections should usually use blue family colors.
- Join/blend sections should usually use purple family colors.
- Scoring/summary/action sections may use warm orange family colors.
- Output sections should use a restrained output/review tint.
- Keep the main story left to right: inputs, prep, blend, analysis, outputs.
- Use vertical lanes for peer inputs or peer outputs.
- Keep hubs centered relative to their inputs and outputs.
- Avoid connector crossings whenever geometry can solve them.

## Annotation Rules

- Prefer native tool annotations for local logic.
- Keep tool annotations short and concrete.
- Use the annotation to say what the tool does, not to explain the whole business case.
- Do not scatter long comment boxes through the workflow body.
- Long explanations belong in the bottom documentation shelf.

## Documentation Shelf Rules

- Add a bottom tool container titled like `Expand this tool container for workflow descriptions`.
- Use a pale, calm fill.
- Divide the shelf into columns when there is more than one paragraph of explanation.
- Use short section headings such as `Data input and prep`, `Blend and prioritize`, or `Outputs and validation`.
- Match the fill of text boxes inside the shelf to the shelf body so they feel embedded.
- Include assumptions, reading order, output purpose, and validation checks.

## Side Tip Rules

- Use at most one side tip panel unless the user explicitly asks for more.
- Put the side tip near the documentation shelf or the relevant output zone.
- Use it for reuse guidance, caveats, validation reminders, or reviewer shortcuts.
- Keep it short.

## Validation Expectations

- Run `verify_workflows.py` until it passes.
- Run `lint_yxmd.py` until there are no errors or warnings.
- Render the workflow preview and inspect the image.
- If runtime behavior matters, run `AlteryxEngineCmd.exe` and capture the smoke-test output.
- Do not call a workflow customer-ready until XML validation, linting, and rendered visual review all pass.
