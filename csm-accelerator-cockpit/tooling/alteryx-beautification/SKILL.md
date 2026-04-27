---
name: alteryx-beautification
description: Use when creating, beautifying, or refactoring Alteryx workflows (.yxmd, .yxmc, .yxwz) where the canvas must read clearly in Designer. Apply lane discipline, contextual containers, native-feeling on-canvas documentation, render-review iteration, and aggressive spiderweb reduction without changing business logic.
metadata:
  short-description: Beautify Alteryx workflows with lane discipline and render review
---

# Alteryx Beautification

## Overview

Use this skill when a workflow needs to look intentional and readable on the canvas, not merely valid in XML. The goal is a customer-safe or colleague-safe Alteryx workflow with a clear narrative, semantically titled containers, readable annotations, and connector routing that does not force the reader to untangle a web.

## Use This Skill For

- Beautifying an existing `.yxmd`, `.yxmc`, or `.yxwz`
- Refactoring a workflow that works but looks messy
- Reducing connector crossings, fan-in knots, or branch ambiguity
- Adding on-canvas documentation for customers or internal handoff
- Rebuilding layout after logic changes so the workflow still reads cleanly

## Do Not Use This Skill For

- Pure business-logic changes where canvas readability is not part of the request
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
3. Re-layout the workflow so the primary story reads left to right and each branch owns visible space.
4. Apply the anti-spiderweb rules from [spiderweb-reduction.md](references/spiderweb-reduction.md).
5. Add documentation sparingly:
   - prefer native tool annotations for key logic
   - use only a few strong comment boxes
   - if the workflow is customer-facing, a bottom reading guide is often better than cluttering the tool lanes
6. Validate and iterate:
   - run the workflow verifier if available
   - run lint checks if available
   - render the workflow preview
   - inspect the picture, not just the XML
   - if the workflow still feels tangled, keep going
7. If output values matter, run the workflow engine and confirm the beautification preserved behavior.

## Non-Negotiables

- Do not change business logic unless the user explicitly asks.
- Keep paths relative and package-safe unless the user explicitly needs otherwise.
- Every real Alteryx tool should belong to a clearly titled contextual container in beautified workflows.
- If a connector crossing can be removed by geometry without harming the story, remove it.
- A workflow is not visually complete if the reader has to decode a spiderweb to understand it.

## Read These References

- Read [layout-playbook.md](references/layout-playbook.md) for the core composition rules.
- Read [spiderweb-reduction.md](references/spiderweb-reduction.md) when crossings, crowded hubs, or branch tangles are the problem.
- Read [validation-loop.md](references/validation-loop.md) for the practical validate-render-run loop.
- Read [example-notes.md](references/example-notes.md) if you want concrete example patterns and review cues.
