# MISTAKES.md

## Policy
If Codex repeats a correction more than once,
the correction must:
1. Become a Hard Rule in `WORKFLOW_RULES.md`
2. Be enforced in `verify_workflows.py`
3. Be referenced by ID in future failures

## Mistake Ledger

### Mistake ID: M-MACRO-001
Description:
Macro paths rewritten from approved root token to the wrong starter-kit root.

Correct Behavior:
Never rewrite approved macro roots; root token must match current kit.

Detection Method:
Fail if macro path `Starter Kits\\<root>\\Macros` has `<root>` different from inferred kit slug.

### Mistake ID: M-MACRO-002
Description:
Absolute or UNC macro path introduced.

Correct Behavior:
Macro paths remain relative and package-safe.

Detection Method:
Fail on drive-letter paths, UNC paths, rooted paths, or forbidden deep-parent escapes.

### Mistake ID: M-LAYOUT-001
Description:
Annotation label crosses comment/section border.

Correct Behavior:
Annotation rectangle fully contained within owning box with required margin.

Detection Method:
Containment + border-band intersection checks.

### Mistake ID: M-LAYOUT-002
Description:
Comment/section text renders outside border.

Correct Behavior:
Text rectangle fully contained inside box rectangle.

Detection Method:
Strict rectangle containment with conservative text estimation.

### Mistake ID: M-COMP-001
Description:
One or more actual tools are left free-roaming without belonging to a clearly titled Tool Container.

Correct Behavior:
Every actual tool belongs to at least one contextual Tool Container with a non-empty caption or annotation that explains the group.

Detection Method:
Traverse the container ancestry for each non-textbox, non-container node and fail when no titled Tool Container ancestor exists.

### Mistake ID: M-COMP-002
Description:
The workflow title is not the highest header element, or explanatory header notes are arranged beside the title instead of beneath it.

Correct Behavior:
The title sits at the top of the header stack, and secondary header notes are placed below it.

Detection Method:
Inspect top-level header text boxes, identify the primary title by font prominence, and fail when other header notes are not positioned below it.

### Mistake ID: M-CONN-001
Description:
The workflow is technically valid but visually tangled, with avoidable connector crossings or fan-in/fan-out knots that make the reader untangle a spiderweb to follow the logic.

Correct Behavior:
Actively rearrange source order, lane placement, branch hubs, and section spacing to minimize connector tangles. A beautified workflow should let a reader follow each branch with little to no visual decoding effort.

Detection Method:
Use rendered workflow review and connector-topology checks where available. Until deterministic crossing detection is implemented, treat this as a mandatory visual review failure when avoidable tangles remain.

### Mistake ID: M-COMP-003
Description:
One or more header explanation boxes are styled so lightly that they read like plain uncolored comments.

Correct Behavior:
Header explanation boxes use visible fills and readable contrast so they register as intentional workflow guidance panels.

Detection Method:
Inspect top-level explanatory text boxes and fail when fill styling is missing or effectively white.

### Mistake ID: M-TEXT-001
Description:
Unnecessary line breaks produce broken phrases or orphan lines.

Correct Behavior:
No weak terminal line endings, no orphan body lines, no double blank lines.

Detection Method:
Line-level text hygiene checks across all visible text fields.

### Mistake ID: M-TEXT-002
Description:
Stray token `obj` or non-printable/replacement characters in visible text.

Correct Behavior:
Visible text is clean and printable.

Detection Method:
Forbidden token and control-character scan.

### Mistake ID: M-STRUCT-001
Description:
Duplicate tool IDs or connections targeting missing nodes.

Correct Behavior:
Unique Tool IDs and valid connection endpoints.

Detection Method:
Graph integrity checks.

### Mistake ID: M-STRUCT-002
Description:
TOC workflow structure drifts from approved golden structure.

Correct Behavior:
TOC-family workflows retain golden plugin sequence.

Detection Method:
Compare `01_*` workflow plugin sequence against `golden/workflow_01.yxmd`.

### Mistake ID: M-GOV-001
Description:
Hard rule in `WORKFLOW_RULES.md` lacks deterministic enforcement.

Correct Behavior:
Every hard rule maps to a check in `verify_workflows.py`.

Detection Method:
Governance agent parses rules and fails missing rule->check mapping.
