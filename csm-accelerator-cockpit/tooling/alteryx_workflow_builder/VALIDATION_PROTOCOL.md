# VALIDATION_PROTOCOL.md

## Deterministic Validation Strategy

Validation runs directly on `.yxmd` XML and is split into independent rule domains.
Read-only validations run in parallel. Any corrective edits run serially.

Connector topology deserves special handling: avoidable spiderweb routing is a real beautification failure even when XML and containment checks pass. Until deterministic crossing detection is implemented in the verifier, rendered workflow inspection remains a mandatory validation step for connector clarity, branch traceability, and anti-spaghetti layout review.

## Multi-Agent Inspection System

Run:
```bash
python verify_workflows.py --agents starter_kit_path
```

Agents (parallel):

### Agent 1 – Macro Integrity Agent
Checks macro paths, forbidden tokens, and approved macro roots.

### Agent 2 – Tool Structure Agent
Checks tool uniqueness, connection integrity, and golden/template structural invariants.

### Agent 3 – Layout Containment Agent
Checks text/annotation containment, border intersections, and minimum internal margins.

### Agent 4 – Text Hygiene Agent
Checks forbidden tokens (`obj`), non-printables, broken line endings, orphan lines, and double blanks.

### Agent 5 – Naming Convention Agent
Checks workflow file naming and deterministic output naming conventions.

### Agent 6 – Configuration Agent
Checks invariant workflow configuration (including version and protected structural settings).

### Agent 7 – Governance Agent
Checks that each hard rule in `WORKFLOW_RULES.md` is mapped to deterministic enforcement in `verify_workflows.py`.

## Structured Failure Output

Each violation emits:

```json
{
  "file": "...",
  "rule": "R-...",
  "mistake_id": "M-...",
  "element_id": "...",
  "severity": "critical|major|minor",
  "description": "..."
}
```

## Reporting

Use:
```bash
python verify_workflows.py --dirs starter_kits/ --report validation_report.json
```

Report contains:
- summary counts
- grouped failures by starter kit, workflow, rule, mistake ID
- detailed violation list
