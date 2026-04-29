# alteryx-workflow-builder

Repository-local Codex skill for deterministic Alteryx workflow generation and static validation.

## What It Does
- Builds `workflow_spec.json` from a prompt or uses an existing spec.
- Compiles to Designer-style `main.yxmd` (canonical `GuiSettings/Position` and `Connection/Origin/Destination`).
- Emits `validation_report.json` with capability support-state (`robust|beta|unsupported`) and fallback diagnostics.
- Enforces tier-2 native coverage (`datetime`, `text_to_columns`, `multi_row_formula`, `cross_tab`, `transpose`, `sample`, `data_cleansing`, `record_id`, `browse`).

## Modes
- `demo`: relaxed naming/layout policy, Browse allowed.
- `starter_kit`: strict starter-kit policy (no Browse in non-TOC, deterministic output naming, stricter layout/naming checks).

## Version/Profile Policy
- Default profile/version: `2025.2`.
- Compatibility profile: `2025.1`.
- Resolution order: explicit CLI override -> spec metadata -> registry default.

## Core Commands
```bash
python3 scripts/alteryx_build.py --problem "Build SLA summary from tickets.csv" --out_dir ./dist --mode demo
python3 scripts/alteryx_build.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist --mode starter_kit --designer_profile 2025.2
python3 scripts/compile.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist --mode demo
python3 scripts/lint_yxmd.py ./dist --recursive --mode demo --report ./dist/lint_report.json
python3 verify_workflows.py --dirs ./golden --mode demo
python3 scripts/golden_sanity.py
python3 scripts/smoke_test.py
```

## Tier-2 Regression and Corpus Tools
```bash
python3 scripts/regress_tier2_signatures.py
python3 scripts/index_challenge_corpus.py --root /path/to/weekly_challenges
python3 scripts/extract_tool_signatures.py /path/to/workflow.yxmd --out ./dist/signatures.json
```

## Distribution Hygiene
```bash
python3 scripts/clean_skill_tree.py .
python3 scripts/sync_installed_skill.py --target /Users/joshua.burkhow/.codex/skills/alteryx-workflow-builder
```
