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

## Required Commands

Validate all workflows under a root:
```bash
python3 verify_workflows.py --dirs starter_kits/
```

Run multi-agent inspection mode:
```bash
python3 verify_workflows.py --agents starter_kit_path
```
