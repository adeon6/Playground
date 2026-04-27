# templates/README.md

## `base.yxmd`

`base.yxmd` is the deterministic baseline for new workflow generation.

Use it when:
- creating a new workflow variant
- repairing drift back to approved structure

Allowed variations:
- localized text
- deterministic output names
- relative input/output path parameters
- minimal layout coordinates required to satisfy containment rules

Forbidden variations:
- macro root drift
- absolute paths
- tool graph drift that violates structure rules
- text/layout violations from `WORKFLOW_RULES.md`

Always validate after editing:
```bash
python verify_workflows.py --dirs starter_kits/
```
