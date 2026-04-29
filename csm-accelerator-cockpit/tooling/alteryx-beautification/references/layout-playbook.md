# Layout Playbook

## Canvas Story First

- Start with the narrative, not the coordinates.
- A good workflow usually reads as `inputs -> prep -> enrichment/analysis -> outputs`.
- Put the title at the top. Put scope or assumption cards below it.
- Outputs should feel predictably anchored on the right.

## Container Rules

- Every actual Alteryx tool should live inside a clearly titled container.
- Container colors should feel semantically related to the dominant tool family inside them.
- Prefer light fills with stronger borders and readable text contrast.
- Containers should clarify structure, not just box everything for decoration.

## Annotation Rules

- Prefer native tool annotations for central logic steps.
- Use separate comment boxes only when they truly improve orientation.
- Keep comments close to the tools they explain.
- Avoid turning the canvas into a poster.
- TextBox/comment colors must be Designer-native. Use named colors or RGB attributes; do not emit CSS-style hex color names such as `name="#0d3153"`, because Designer can drop the textbox text/fill even when the preview renderer looks correct.

## Customer-Facing Canvas Framing

Use this profile when the workflow should be presentable to a customer, CSM, or executive reviewer on the first open.

- Use `assets/customer-facing-hybrid-reference.yxmd` as the primary reference when building a complete customer-facing workflow. It shows the intended combination of colored logic containers, title banner, documentation shelf, side tip, clean annotations, and output anchoring.
- Keep the logic-body style rules intact, including contextual containers and clean connectors.
- Add a calm top title banner above the workflow body.
- Use the banner to orient the reader: broad workflow category on the first line, specific use case on the second line.
- Put a short purpose/outcome explanation beside or within the banner; it should say what the workflow does, why it exists, and what it produces.
- Keep the top banner concise. It is an orientation panel, not the full documentation.
- Leave deliberate whitespace between the banner and the workflow body so the canvas reads as title, then logic.
- Add a bottom documentation shelf when the workflow is customer-facing or reusable.
- The bottom shelf should contain the step-by-step reading guide, assumptions, outputs, and validation notes.
- Organize long shelf content into columns with short bold-like headings rather than scattering notes around the workflow.
- Use an optional side tip panel only for genuinely helpful caveats, shortcuts, or review guidance.
- Match TextBox/comment fills to their parent documentation container fill so notes feel embedded, not pasted on.
- The overall canvas should read as: title and purpose above, workflow logic in the middle, explanation below.

## Geometry Rules

- Straight-through chains should be straight whenever possible.
- Repeated patterns should use repeated geometry.
- Fan-out branches should have visible separation.
- Merge hubs should sit where the eye expects them, not where they happened to land.
- When a refactor moves a container, also reflow the tools inside it.

## Readability Tradeoffs

- Fewer tools is not automatically cleaner.
- Symmetry helps when it reinforces the logic, not when it fights it.
- Empty space should be purposeful, not accidental.
- If one version is simpler to scan, prefer it even if it uses a few more tools.
