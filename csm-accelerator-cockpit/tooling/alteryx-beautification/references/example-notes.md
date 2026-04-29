# Example Notes

Local preview assets are bundled with this skill:

- `assets/customer-facing-hybrid-reference.png`
- `assets/customer-guide-example.png`
- `assets/balanced-hybrid-example.png`

Use them as visual references, not as rigid templates.

## Customer-Facing Hybrid Reference

This is the primary reference for new customer-presentable workflows.

Look for:

- a dark title banner that explains the workflow before the tool body starts
- semantically colored containers around every real tool group
- clean left-to-right lanes with no avoidable connector crossings
- concise tool annotations instead of long comments in the logic body
- a bottom documentation shelf that explains the reading order, assumptions, outputs, and validation
- an optional side tip panel that gives one focused reuse or review note

This reference is the merged standard: keep our colored-container workflow body and add the cleaner top-and-bottom documentation framing.

## Customer Guide Example

Look for:

- a top title plus scope cards
- named sections
- a bottom reading guide instead of excessive comments inside the workflow body
- customer-facing explanation that supports the canvas without overwhelming it

## Balanced Hybrid Example

Look for:

- a staged merge instead of one visually noisy mega-hub
- separated core-feed and policy lanes
- right-side output anchoring
- a design choice where a few extra joins were accepted because the workflow became easier to read

## Main Lesson

The correct beautification move is not always "use fewer tools." Often the better move is "use the fewest tools that still produce a clean visual story."

## Customer-Facing Sample Workflow Reference

Use `customer-facing-canvas-framing.yxmd` as the upstream Alteryx sample reference for the top banner and documentation shelf pattern. Use `customer-facing-hybrid-reference.yxmd` as the preferred reference for our full generated-workflow standard.

Look for:

- a dark top title banner that explains purpose before the reader reaches the tools
- a workflow body with clean left-to-right logic and no connector web
- a bottom documentation shelf that teaches the workflow without cluttering the logic lane
- a small optional tip panel for focused guidance
- documentation boxes whose fill colors harmonize with their parent containers

Do not copy this reference mechanically. Preserve the user's logical-container style when requested, then apply the reference's top-and-bottom framing around that logic.
