# VALIDATION_PROTOCOL.md

## Deterministic Validation Strategy
Validation is static XML inspection only (no Designer runtime required).

## Standard Validation Pipeline
```bash
python3 scripts/validate_spec.py --spec <spec.json>
python3 scripts/compile.py --spec <spec.json> --out_dir <dist> --mode demo
python3 scripts/lint_yxmd.py <dist-or-yxmd> --recursive --mode demo
python3 verify_workflows.py --dirs <dist-or-folder> --mode demo
python3 scripts/golden_sanity.py
```

## Multi-Agent Inspection Mode
```bash
python3 verify_workflows.py --agents <path> --mode auto
```

Agents:
- Agent 1: macro integrity
- Agent 2: tool structure and connections
- Agent 3: layout containment (starter_kit only)
- Agent 4: text hygiene
- Agent 5: naming policy (starter_kit only)
- Agent 6: configuration/version
- Agent 7: capability coverage (tier-2/native/profile)
- Agent 8: governance mapping completeness

## Mode and Version Controls
- `--mode auto|starter_kit|demo`
- `--expected-version 2025.1|2025.2`
- `--designer-profile 2025.1|2025.2`

If `--expected-version` is omitted and `--designer-profile` is provided, expected version resolves to the profile value.

## Structured Violation Output
Each violation includes:
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


## Automatic Remediation Pipeline (Validation/Analysis)
When validating/analyzing existing workflows in `starter_kit` mode, the following loop is mandatory:
1. Baseline: lint + verify.
2. Geometry checks: layout quality + no-browse/AI-ready + strict layout policy (if validators are present).
3. Deterministic remediation pass for all failing classes.
4. Re-run full validation set.
5. Repeat until pass or no-improvement for two consecutive iterations.

### Required Remediation Classes
- Missing/invalid stage containers and section-title misalignment.
- Tools outside stage bounds, spacing collisions, annotation crossings/overlaps.
- AI-ready branch defects (missing output, non-horizontal pair, wrong stage/lane).
- Deterministic output naming/path normalization.
- Structural XML cleanup (empty plugin nodes, invalid connections, tier-2 config shape repairs such as transpose keys/data).

### Pass Criteria
- `verify_workflows.py`: PASS
- `scripts/lint_yxmd.py`: zero errors
- Geometry validators: PASS (when present)
