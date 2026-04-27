# workflow_builder.md

## Mandatory Deterministic Build Loop

Whenever Codex creates or edits any `.yxmd` workflow:

1. Generate or modify workflow XML.
2. Run `verify_workflows.py` automatically.
3. If validation fails, apply the smallest possible correction.
4. Re-run validation.
5. Repeat until all failures are resolved.
6. Finalize only when exit code is `0`.

## Hard Completion Rule

No workflow build is considered complete unless `verify_workflows.py` returns exit code `0`.

## Runtime Verification Rule

Static validation does not prove runtime behavior. When a task depends on actual output values, Codex must run the workflow with `C:\Program Files\Alteryx\bin\AlteryxEngineCmd.exe`, inspect a Browse/output artifact, and only then claim the output was verified.

## Beautification Color Guidance

When using named containers as part of beautification:

1. Container color must feel related to the dominant tool family inside it, not merely different from neighboring containers.
2. Prefer light, desaturated fills with stronger borders and darker title text over muddy or heavily saturated blocks.
3. Input-heavy sections should generally echo input-tool greens/teals.
4. Transformation or formula-heavy sections should generally echo the cooler blues used by those tools.
5. Output or review sections should generally echo the output/browse family colors with a lighter tint.
6. When a section mixes tool families, choose the color from the dominant logic step, not from a random accent.
7. Across one workflow, palettes should feel intentionally related, as if they belong to the same visual system.
8. Every actual Alteryx tool must live inside at least one clearly titled Tool Container that gives the surrounding group contextual meaning.
9. Text boxes, comment boxes, and Tool Container nodes themselves are not considered "tools" for this containment rule.
10. If the workflow uses a header area, make the title the top-most header element and place the secondary scope or assumption cards beneath it.
11. Header explanation cards should look intentionally designed, with visible fills and readable contrast, rather than plain canvas comments.
12. Connector topology is part of beautification, not a late cleanup step. Actively reduce spiderweb effect by separating lanes, reordering peer inputs when helpful, centering hubs, and moving sections so a reader can trace each branch without mental untangling.
13. If a connector crossing can be removed through geometry changes without hurting the story of the workflow, it should be removed. Do not accept "technically fine" routing when a cleaner lane layout is available.
14. During rendered review, explicitly inspect for avoidable connector tangles, stacked fan-in/fan-out knots, and branch ambiguity. A workflow is not visually complete if the reader has to visually decode a web of crossing lines to understand it.

## Required Commands

Validate all workflows under a root:
```bash
python verify_workflows.py --dirs starter_kits/
```

Run multi-agent inspection mode:
```bash
python verify_workflows.py --agents starter_kit_path
```
