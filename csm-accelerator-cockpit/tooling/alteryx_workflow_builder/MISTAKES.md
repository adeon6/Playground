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

### Mistake ID: M-CAP-001
Description:
Tier-2 tool emitted through generic fallback plugin container.

Correct Behavior:
Tier-2 tools must compile to dedicated native plugin templates.

Detection Method:
Fail when generic plugin node advertises a tier-2 operation in configuration.

### Mistake ID: M-CAP-002
Description:
Tier-2 tool configuration emitted without minimum required semantic payload.

Correct Behavior:
Each tier-2 tool includes required config nodes/fields for deterministic static validation.

Detection Method:
Per-tool semantic checks for required configuration node presence.

### Mistake ID: M-CAP-003
Description:
Tool/plugin emitted for a profile where it is unavailable.

Correct Behavior:
Tool usage remains compatible with profile implied by workflow version (2025.1/2025.2).

Detection Method:
Registry availability checks by plugin->op mapping and `yxmdVer` profile.
