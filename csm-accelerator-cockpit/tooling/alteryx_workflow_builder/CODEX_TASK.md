# CODEX_TASK.md

## Mandatory Execution Procedure

1. Generate or modify workflow.
2. Run `verify_workflows.py`.
3. If validation fails, apply minimal corrections.
4. Re-run `verify_workflows.py`.
5. Repeat until validation is clean.
6. Complete only when validator returns exit code `0`.

## Hard Rule

No workflow generation is considered complete unless `verify_workflows.py` returns zero.
If verification fails, the task is incomplete.
Rendered review is also part of completion: if the canvas still has avoidable spiderweb routing or tangled branch geometry, the task is not visually complete even if the validator passes.

## Commands

Validate explicit files:
```bash
python verify_workflows.py /path/to/workflow_a.yxmd /path/to/workflow_b.yxmd
```

Validate directory recursively:
```bash
python verify_workflows.py --dirs starter_kits/
```

Run multi-agent inspection:
```bash
python verify_workflows.py --agents starter_kit_path
```
