---
name: alteryx-beautification
description: Use when creating, beautifying, or refactoring Alteryx workflows (.yxmd, .yxmc, .yxwz) where the canvas must read clearly in Designer. Apply lane discipline, contextual containers, native-feeling on-canvas documentation, customer-facing canvas framing, render-review iteration, and aggressive spiderweb reduction without changing business logic. Pair with alteryx-workflow-builder for workflow generation, workflow_spec design, native tool XML, validation, linting, and packaging.
---

# Alteryx Beautification

## Overview

Use this skill when a workflow needs to look intentional and readable on the canvas, not merely valid in XML. The goal is a customer-safe or colleague-safe Alteryx workflow with a clear narrative, semantically titled containers, readable annotations, and connector routing that does not force the reader to untangle a web.

## Ownership Boundary

- This skill owns visual design: canvas composition, section/container naming, documentation framing, annotations, connector readability, render review, and customer-facing polish.
- `alteryx-workflow-builder` owns workflow generation, workflow_spec design, native tool XML, tool configuration rules, validation/lint commands, package safety, and remediation of structural workflow defects.
- When creating a workflow from scratch, changing tool logic, validating XML, compiling from a spec, or packaging outputs, use `alteryx-workflow-builder` first and then apply this skill for the visual pass.
- When beautifying an existing workflow, preserve business logic and use builder validation tools when available to prove the XML remains structurally sound.
- Beautification references define visual grammar, not workflow logic. Do not copy schemas, field names, formulas, tool sequences, join patterns, output structures, or business entities from a reference workflow unless the current requirement independently calls for them.

## Use This Skill For

- Beautifying an existing `.yxmd`, `.yxmc`, or `.yxwz`
- Refactoring a workflow that works but looks messy
- Reducing connector crossings, fan-in knots, or branch ambiguity
- Adding on-canvas documentation for customers or internal handoff
- Rebuilding layout after logic changes so the workflow still reads cleanly

## Do Not Use This Skill For

- Pure business-logic changes where canvas readability is not part of the request
- Generating workflow XML, building a workflow_spec, or choosing native Alteryx tool configuration without `alteryx-workflow-builder`
- Blindly minimizing tool count when that would worsen scanability
- Claiming a workflow is complete before a render review has passed

## Workflow

1. Inspect the current workflow and render a preview before editing when possible.
2. Identify the visual story:
   - title and scope
   - major acts or sections
   - main trunk
   - branch hubs
   - output endpoints
   - where the current workflow genuinely needs different topology, tools, inputs, outputs, or branches from the reference
3. Re-layout the workflow so the primary story reads left to right and each branch owns visible space.
4. Apply the anti-spiderweb rules from [spiderweb-reduction.md](references/spiderweb-reduction.md).
5. Add documentation sparingly:
   - prefer native tool annotations for key logic
   - use only a few strong comment boxes
   - if the workflow is customer-facing, a bottom reading guide is often better than cluttering the tool lanes
   - for customer-facing workflows, frame the canvas with a concise top banner and a bottom documentation shelf
   - keep long explanation outside the tool lane unless it clarifies the exact nearby logic
   - for customer-facing accelerator work, use [customer-facing-hybrid-profile.md](references/customer-facing-hybrid-profile.md) and its reference workflow as the primary visual standard
6. Validate and iterate:
   - run `alteryx-workflow-builder` verifier/lint checks when the builder skill is installed
   - render the workflow preview
   - inspect the picture, not just the XML
   - when Designer or `AlteryxEngineCmd.exe` is available, run the workflow and confirm the canvas still looks correct after run/refresh
   - if the workflow still feels tangled, keep going
7. If output values matter, run the workflow engine and confirm the beautification preserved behavior.

## Reference Workflow Guardrail

- Use reference workflows as taste anchors for presentation quality: title/banner, lane discipline, tool containment, documentation shelf, annotation density, connector cleanliness, and visual hierarchy.
- Do not use reference workflows as hidden business templates. The current SOP, data contract, user request, or existing workflow must determine the actual tools, schemas, formulas, joins, branch count, output types, and data shape.
- Similar visual structure is acceptable when the current work independently follows common workflow stages such as input, preparation, enrichment, analysis, and output.
- Similar logic or schema is not acceptable unless the requirement explicitly calls for that same logic or schema.
- If a requirement needs geospatial, reporting, macros, batch processing, parsing, predictive tools, many inputs, few inputs, no joins, or a non-linear topology, adapt the visual language around that real design instead of forcing it into the customer-facing hybrid example.
- When the source requirements are thin, label any invented workflow pattern as a demo-safe interpretation and record the missing specifics in the gap log rather than silently reusing a familiar reference shape.

## Non-Negotiables

- Do not change business logic unless the user explicitly asks.
- Do not let a beautification reference change or imply business logic; visual polish must follow the workflow, not the other way around.
- Keep paths relative and package-safe unless the user explicitly needs otherwise.
- Every real Alteryx tool should belong to a clearly titled contextual container in beautified workflows.
- Tool containment must be real Designer containment: place section tools inside the owning ToolContainer's `<ChildNodes>`, not as root-level siblings over a decorative container backplate.
- If a connector crossing can be removed by geometry without harming the story, remove it.
- A workflow is not visually complete if the reader has to decode a spiderweb to understand it.
- A workflow is not visually complete if containers collapse to header-only or appear empty after Designer open/run/refresh.
- TextBox/comment styling must use Designer-native color XML. Do not use CSS-style hex values as `name` attributes for `TextColor` or `FillColor`; use named colors or `r`/`g`/`b` attributes so Designer displays the text and fill.

## Read These References

- Read [layout-playbook.md](references/layout-playbook.md) for the core composition rules.
- Read [customer-facing-hybrid-profile.md](references/customer-facing-hybrid-profile.md) when the workflow must be customer-presentable on first open.
- Read [spiderweb-reduction.md](references/spiderweb-reduction.md) when crossings, crowded hubs, or branch tangles are the problem.
- Read [validation-loop.md](references/validation-loop.md) for the practical validate-render-run loop.
- Read [example-notes.md](references/example-notes.md) if you want concrete example patterns and review cues.
