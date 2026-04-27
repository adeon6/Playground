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
