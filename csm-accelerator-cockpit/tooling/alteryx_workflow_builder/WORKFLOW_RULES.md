# WORKFLOW_RULES.md

Hard rules enforced by `verify_workflows.py`.

## Mode Surface
- `starter_kit`: all rules below apply.
- `demo`: macro absolute-path protection, structural checks, text hygiene, version/config checks, and capability checks apply; strict layout/naming starter-kit constraints are relaxed.

## Macro Path Rules

### R-MACRO-001 Relative Paths Only
Macro references must be relative and end with `.yxmc`.

### R-MACRO-002 Forbidden Macro Tokens
In `starter_kit` mode, forbid excessive parent escapes and disallowed cross-kit tokens.

### R-MACRO-003 Approved Macro Roots
In `starter_kit` mode, if path matches `Starter Kits\\<root>\\Macros`, `<root>` must match current kit slug.

## Layout Containment Rules

### R-LAYOUT-001 Annotation Containment
`starter_kit` mode: annotation text must remain within owning section boundaries.

### R-LAYOUT-002 Text Containment
`starter_kit` mode: textbox/comment text must be fully contained in its box.

### R-LAYOUT-003 Border Intersection Prohibited
`starter_kit` mode: text/annotation cannot intersect section border bands.

## Annotation Rules

### R-ANN-001 Border Safety
`starter_kit` mode: annotation labels cannot cross section borders.

### R-ANN-002 Readability
`starter_kit` mode: annotation placement must remain readable and non-clipping.

## Text Hygiene Rules

### R-TEXT-001 Line-Break Hygiene
Visible text must not contain orphan one-word body lines, weak terminal words, or repeated blank lines.

### R-TEXT-002 Forbidden Text
Visible text must not contain `obj` token or non-printable/replacement characters.

## Naming Conventions

### R-NAME-001 Workflow Filename Standard
`starter_kit` mode: workflow filenames must match `^\d{2}_[^\s]+.*\.yxmd$` (except `main.yxmd`).

### R-NAME-002 Output Naming
`starter_kit` mode: output files must be deterministic (`customgpt_*` or `NN_*`).

## Configuration Invariants

### R-CONFIG-001 Workflow Version
`yxmdVer` must be `2025.1` or `2025.2`, or match explicit `--expected-version` when provided.

### R-CONFIG-002 Structural Integrity
- Tool IDs must be unique.
- Each node must have `GuiSettings` and non-empty `Plugin`.
- Connections must use canonical `<Connection><Origin/><Destination/></Connection>` and reference valid Tool IDs.
- `01_*` TOC structures are compared against golden baseline plugin sequence.

## Capability Coverage Rules

### R-CAP-001 Tier-2 Generic Fallback Prohibited
Tier-2 ops must not be emitted through generic fallback plugin structures.

### R-CAP-002 Tier-2 Semantic Minimums
Tier-2 tools must include minimum required config nodes/fields.

### R-CAP-003 Profile Availability
Tool/plugin usage must be compatible with resolved profile (`2025.1` or `2025.2`).


## Auto-Remediation Enforcement
When the skill is used for validation/analysis in `starter_kit` mode, failures under the following rules must trigger automatic remediation (not report-only behavior):
- R-LAYOUT-001, R-LAYOUT-002, R-LAYOUT-003
- R-ANN-001, R-ANN-002
- R-NAME-002
- R-CONFIG-002
- R-CAP-002 (where deterministic XML repair is possible)

Validation is only considered complete when these rule families return zero blocking violations for the selected scope.
