---
name: alteryx-workflow-builder
description: Build and harden Alteryx workflows from natural-language business requirements by producing deterministic workflow_spec JSON, compiling to .yxmd XML, validating assumptions/placeholders, enforcing static QA rules, and optionally packaging outputs. Use for new workflow generation, starter-kit workflow standardization, localization-safe build patterns, AI-ready output design for CustomGPT feeds, and static defect triage without running Designer.
---

# Alteryx Workflow Builder

## Mandatory Governance Integration
- This skill is governed by `workflow_builder.md`, `WORKFLOW_RULES.md`, `MISTAKES.md`, `VALIDATION_PROTOCOL.md`, and `CODEX_TASK.md`.
- Any `.yxmd` creation/edit must run `verify_workflows.py` and iterate fix->revalidate until exit code `0`.
- Work is incomplete if validation fails.

## Use This Skill For
- Build new Alteryx workflows from business problems.
- Convert requirements into deterministic `workflow_spec.json`.
- Compile specs into `main.yxmd` and static validation reports.
- Enforce starter-kit quality contracts before runtime testing.
- Detect common XML defects (bad paths, invalid references, unresolved placeholders) without opening Designer.

## Do Not Use This Skill For
- Reverse-engineering proprietary binary assets.
- Runtime-only performance tuning that requires live Designer execution.
- Credential provisioning or storing secrets in workflow assets.

## Output Contract
Always generate:
- `workflow_spec.json`
- `main.yxmd`
- `validation_report.json`

When packaging is requested, generate:
- `package.yxzp` including workflow, docs, optional sample data, and optional macros.

## Build Modes

### Mode A: Standard Workflow Build
1. Translate problem statement into deterministic `workflow_spec`.
2. Record unknowns in `assumptions`; never invent hidden data semantics.
3. Validate schema with `scripts/validate_spec.py`.
4. Compile with `scripts/compile.py`.
5. Lint output with `scripts/lint_yxmd.py`.
6. Package with `scripts/package_yxzp.py` only when requested.

### Mode B: Starter Kit Workflow Hardening
Use when workflow(s) are part of a starter kit portfolio.
1. Preserve use-case fidelity: workflow purpose must match kit name.
2. Keep relative/package-safe paths; avoid machine-specific absolute paths.
3. Keep AI-ready output branch and deterministic feed schema naming.
4. Keep governance notes and no embedded credentials.
5. Lint all workflows recursively before runtime execution.
6. Enforce layout geometry rules from `Office_of_Finance_AI_Starter_Kits/00_admin/WORKFLOW_LAYOUT_RULES.md` (stage-box spacing, no clipping, no overlap).
7. For non-TOC starter-kit workflows: no Browse tools; AI-ready transform/output must be horizontal, same-stage, lower-lane, and fully inside one section.
8. Enforce section-boundary safety: tools/icons/annotations cannot touch or cross divider lines.
9. Enforce minimum section inner padding (target: >= 40 px horizontal, >= 24 px vertical from borders for tool/icon footprints).
10. Enforce header contract:
   - dark title/description/feedback row aligned to section grid below
   - feedback box uses rounded rectangle style (`Shape=0`) and approved feedback link
   - feedback box height matches description height
11. Enforce instruction-row contract:
   - two aligned top light-blue instruction boxes + one full-width lower instruction box
   - instruction row aligned to title/description width envelope
12. Enforce annotation/readability contract:
   - annotation text cannot overlap connectors
   - annotation boxes must fit text without clipping
   - tool labels and annotations require non-overlapping vertical spacing
13. Enforce icon alignment contract:
   - decorative icons aligned with corresponding tools
   - decorative icons must not overlap tools/connectors/annotations.

14. Enforce header content integrity:
   - description panel text must not contain duplicated repeated lines
   - feedback panel text must never fall back to `Office of Finance AI Starter Kits | Accounting Automation`
   - approved feedback text is `Provide Feedback on this Starter Kit` plus the Asana URL on a new line
15. Enforce localized content integrity:
   - preserve localized text for title/description/instruction panels per language
   - only standardize geometry/style unless user explicitly requests text replacement
16. Macro-path integrity:
   - starter-kit macros must use relative paths only
   - macro root token must match the current kit slug
   - cross-kit macro references are forbidden
   - referenced `.yxmc` file must exist from the workflow relative path
17. TOC workflow-launch behavior:
   - TOC workflow links must remain relative
   - TOC `Open workflow` links must use launcher handler (`onclick="return launchWorkflow(this);"`)
   - clicking from Designer TOC must open `.yxmd` directly via Alteryx association, not browser download flow



## Workflow Visual Best-Practice Rules (Portfolio-Wide)
Apply these rules to all non-TOC starter-kit workflows unless explicitly overridden by the user.

1. Header row contract
- Use one unified dark header envelope containing title, description, and feedback panels.
- Keep top and bottom alignment consistent across all header panels.
- Feedback panel must use rounded rectangle style (`Shape=0`) and approved feedback link.
- Remove detached or duplicate feedback notes outside the header.

2. Instruction-row contract
- Use two aligned top light-blue instruction bars plus one full-width lower instruction bar.
- Keep instruction bars tightly spaced under the header (no large dead gap).
- Keep instruction row width aligned to the same envelope as section grid below.
- Use `https://www.alteryx.com/use-case-navigator` for the third instruction link when specified.

3. Section-grid contract
- Keep section boxes uniformly spaced (consistent horizontal gaps).
- Keep section title bars consistent in height and width alignment.
- Ensure section titles remain centered and not clipped.

4. Tool placement and spacing contract
- Keep tools fully inside their intended section.
- Do not allow tools/icons/annotations to touch or cross section divider lines.
- Maintain inner section padding and avoid tight border proximity.
- Maintain readable spacing between neighboring tools and between tool labels/annotations.

5. Connector readability contract
- Prefer straight lines for same-section linear chains when possible.
- Use bends only when required to avoid boundary violations, overlaps, or branch ambiguity.
- Avoid routing connectors through annotation text footprints.

6. Annotation and narrative text contract
- Keep annotation text above/below tool lanes, not on top of connector lines.
- Avoid annotation overlap with tool icons or other annotations.
- Keep text boxes sized to prevent clipping.
- Use concise, section-specific narrative text (avoid duplicate generic text across sections).

7. Decorative icon contract
- Align decorative icons with corresponding tool rows.
- Decorative icons must not overlap tools, connectors, annotations, or section borders.

8. AI-ready branch contract
- Keep `AI READY DATA TRANSFORM` and `AI READY DATA OUTPUT` in same section and lower lane.
- Keep AI-ready branch horizontal and fully contained inside section boundaries.
- Keep AI-ready macro configured per policy and outputs deterministic.

9. Output annotation clarity
- Keep output labels explicit and user-readable.
- Use filename-style annotations only when explicitly requested; otherwise use clean semantic labels.

10. Determinism and packaging safety
- Keep `yxmdVer="2025.1"` unless user explicitly requests otherwise.
- Keep macro/output paths relative and package-safe.
- Keep non-TOC workflows Browse-free when portfolio policy requires Output Data tools.

11. Header content integrity
- Description panel text must not contain duplicated repeated lines.
- Feedback panel text must never revert to `Office of Finance AI Starter Kits | Accounting Automation`.
- Feedback panel must use approved content: `Provide Feedback on this Starter Kit` + Asana URL on the next line.

12. Localization protection during geometry updates
- When propagating layout fixes across languages, preserve localized text content.
- Do not overwrite localized description/instruction text with English unless explicitly requested.

## Versioning Rules
- Default generated workflow version is `yxmdVer="2025.1"`.
- Override only when user explicitly requests a different version.
- Keep version consistent across related workflow sets.

## Planner Rules
- Allowed `op` values:
  - `csv_input`, `file_input`, `db_input`, `select`, `cleanse`, `formula`, `filter`, `join`, `union`, `summarize`, `sort`, `unique`, `output_file`, `output_db`, `macro_call`, `python_script`
- Keep step IDs stable and descriptive.
- Prefer explicit field-level args over implicit assumptions.
- Keep branching dependencies explicit with `depends_on`.

## Static QA Rules
Run lint checks before runtime tests.

Use:
```bash
python scripts/lint_yxmd.py <workflow-or-folder> --recursive --expected-version 2025.1 --report ./lint_report.json
```

Key checks:
- XML parse validity.
- Version mismatch (`yxmdVer`).
- Unresolved `{{PLACEHOLDER}}` tokens.
- Broken connection references (`FromToolID`/`ToToolID`).
- Duplicate `ToolID` values.
- Absolute-path/path-length risk signals.
- Disconnected tool detection.
- Browse tool detection for non-TOC starter-kit workflows.
- AI-ready pair geometry checks (horizontal + same-stage + lower-lane + in-section).
- Section-boundary crossing detection (tools/icons/annotations crossing divider lines).
- Section-padding threshold checks.
- Header and instruction-row width alignment checks.
- Feedback box style/placement checks.
- Textbox clipping, annotation overlap, and stage-box containment checks.
- Designer-native TextBox color checks. Use named colors or `r`/`g`/`b` attributes; never emit CSS hex strings in `TextColor` or `FillColor` `name` attributes.

## Security and Governance
- Never embed API keys, passwords, or credentials.
- Keep DB connection details as placeholders if unknown.
- Flag inline credential patterns as warnings.
- Keep AI/LLM payload outputs explicit and auditable.


## Deterministic Validation and Correction System (Mandatory)

Use `workflow_builder.md`, `WORKFLOW_RULES.md`, `MISTAKES.md`, `VALIDATION_PROTOCOL.md`, and `CODEX_TASK.md` as first-class governance inputs.

For every workflow create/edit operation, enforce this loop:
1. Generate or modify workflow.
2. Run `verify_workflows.py`.
3. If validation fails, apply minimal corrections.
4. Re-run validator.
5. Repeat until validation passes.
6. Finalize only when validator exit code is `0`.

Global validation command:
```bash
python verify_workflows.py --dirs starter_kits/
```

Multi-agent validation command:
```bash
python verify_workflows.py --agents starter_kit_path
```

No workflow build is complete unless `verify_workflows.py` returns exit code `0`.

## CLI Commands
Build from problem text:
```bash
python scripts/alteryx_build.py --problem "Build a weekly SLA dashboard workflow from tickets.csv" --out_dir ./dist
```

Build from existing spec and pin version:
```bash
python scripts/alteryx_build.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist --designer_version 2025.1
```

Compile only:
```bash
python scripts/compile.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist
```

Lint workflows statically:
```bash
python scripts/lint_yxmd.py ./dist --recursive --expected-version 2025.1 --report ./dist/lint_report.json
```

Package artifacts:
```bash
python scripts/package_yxzp.py --source_dir ./dist --out ./dist/package.yxzp
```

Smoke test:
```bash
python scripts/smoke_test.py
```

Macro safety check (repo verifier):
```bash
python verify_workflows.py --macro-only <workflow-or-folder>
```

## References
Read as needed:
- `references/starter-kit-factory-lessons.md`

Use this reference when requests involve:
- multi-language starter-kit consistency
- TOC/documentation patterns
- duplicate cleanup policy
- static/runtime test triage patterns from Office of Finance kits
- workflow visual/layout quality and spacing policy
