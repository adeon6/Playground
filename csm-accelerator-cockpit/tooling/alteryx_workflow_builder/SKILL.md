---
name: alteryx-workflow-builder
description: Build and harden Alteryx workflows from natural-language business requirements by producing deterministic workflow_spec JSON, compiling to .yxmd XML with native tool templates, validating assumptions/placeholders, enforcing static QA rules, rendering workflow previews, and optionally packaging outputs. Use for new Alteryx workflow generation, workflow_spec design, native Designer XML, starter-kit workflow QA, validation/remediation, workflow packaging, and generated workflow preview images. Pair with alteryx-beautification whenever visual polish, customer-facing canvas quality, lane discipline, connector clarity, or workflow beautification is required.
---

# Alteryx Workflow Builder

## Scope
Use this skill to:
- Build deterministic `workflow_spec.json` from requirements.
- Compile to `main.yxmd` using native templates for core and tier-2 tools.
- Produce `validation_report.json` with support-state and fallback diagnostics.
- Run required XML, connection, runtime, and visual/layout validation for workflow testing and validation tasks.
- Render workflow preview images for visual review when Designer screenshots are not available.

Do not use this skill for credential provisioning or OAuth setup. Runtime-only tuning remains out of scope unless required to verify generated workflow behavior.

## Ownership
- This skill is the sole owner of workflow rules, workflow validations, workflow errors, and workflow remediation.
- This skill owns workflow generation, schema design, native tool XML, validation commands, capability coverage, package safety, and deterministic build artifacts.
- `alteryx-beautification` owns canvas composition, visual storytelling, customer-facing polish, lane discipline, connector readability, and final render-review judgment.
- When a workflow is customer-facing, accelerator-ready, visually messy, or explicitly being beautified, use `alteryx-beautification` alongside this skill.
- For starter-kit work, any workflow-specific standards or failures mentioned by other skills defer to `alteryx-workflow-builder`.
- `alteryx-starter-kit-factory` may own kit structure, localization, TOC collateral, and packaging, but it does not own workflow QA or workflow repair.
- Visual reference workflows are not logic templates. Derive topology, schemas, formulas, tools, joins, outputs, and data contracts from the current approved requirements; use references only for presentation standards unless the current requirements independently require the same logic.

## Mandatory Build Artifacts
Always produce:
- `workflow_spec.json`
- `main.yxmd`
- `validation_report.json`

Optional when requested:
- `package.yxzp`

## Modes
- `demo`:
  - relaxed starter-kit enforcement
  - Browse permitted
- `starter_kit`:
  - strict naming, XML, connectivity, and runtime policy
  - Browse disallowed for non-TOC workflows
  - deterministic output naming required
  - auto-remediation loop required for validation and analysis tasks

## Version/Profile Rules
- Default: `2025.2`
- Compatibility: `2025.1`
- Resolution order:
  1. CLI override
  2. spec metadata (`designer_profile` / `designer_version`)
  3. capability registry default

## Supported Ops
Core:
- `csv_input`, `file_input`, `db_input`, `select`, `filter`, `formula`, `summarize`, `join`, `union`, `sort`, `unique`, `output_file`, `output_db`

Tier-2 native:
- `datetime`, `text_to_columns`, `multi_row_formula`, `cross_tab`, `transpose`, `sample`, `data_cleansing`, `record_id`, `browse`

Unsupported or beta classes remain out of scope until tier-2 gates pass.

## Compile and Fallback Policy
- Native-supported ops must compile through native templates.
- Generic fallback on native-supported ops is a hard compile blocker.
- Missing native template files are compile blockers.
- Templates must be Designer-native, not renderer-only approximations. Formula, Join, Filter, Summarize, and output tools must use native configuration shapes and native connection anchors that survive open/run/refresh in Designer.
- If compiling to a distribution folder, stage package-relative assets beside the emitted workflow so paths resolve from the workflow file location.

## Reference Overfitting Guardrail
- Before creating `workflow_spec.json`, derive the workflow topology from the active SOP, data contract, prompt, or existing workflow. Do not begin from a golden/reference workflow and swap labels.
- Never copy field names, sample data, scoring formulas, join keys, output schemas, tool counts, or branch topology from unrelated references unless the current project explicitly calls for them.
- If the requirements are too thin to justify concrete logic, either stop and log the gap, or build a clearly marked demo-safe interpretation with assumptions and gaps documented.
- Customer-facing hybrid references should influence canvas presentation only: title framing, contextual containers, lane discipline, documentation shelf, annotation density, and anti-spiderweb routing.

## Validation Commands
```bash
python scripts/validate_spec.py --spec ./examples/support_sla/workflow_spec.json
python scripts/compile.py --spec ./examples/support_sla/workflow_spec.json --out_dir ./dist --mode demo
python scripts/lint_yxmd.py ./dist --recursive --mode demo --report ./dist/lint_report.json
python verify_workflows.py --dirs ./dist --mode demo
python scripts/golden_sanity.py
python scripts/smoke_test.py
python scripts/render_workflow_image.py ./dist/main.yxmd --out ./dist/main.preview.png
& "C:\Program Files\Alteryx\bin\AlteryxEngineCmd.exe" ./dist/main.yxmd
```

## Deterministic Validation Loop (Required)
For every create or edit cycle:
1. Compile workflow.
2. Run `lint_yxmd.py`.
3. Run `verify_workflows.py`.
4. Run repo-native structural checks that exist for the target repo.
5. Run `AlteryxEngineCmd.exe` when available.
6. Fix violations, runtime errors, runtime warnings caused by bad generated XML, and package-path defects.
7. Re-run until all required gates pass.

## Automatic Validation + Remediation Contract (Required)
When this skill is used to validate, test, inspect, or analyze existing workflows, remediation is mandatory by default.

### Trigger
- Any request containing validate, validation, test, testing, check, analyze, inspect, QA, XML, connection, runtime, AI-ready, question-mark tool, layout, straight lines, sections, or starter-kit compliance.

### Required Automatic Loop
For each target scope, run this loop:
1. Run baseline checks:
   - `python3 scripts/lint_yxmd.py <scope> --recursive --mode starter_kit --expected-version 2025.1`
   - `python3 verify_workflows.py --dirs <scope> --mode starter_kit --expected-version 2025.1`
2. Run required structural checks that exist for the repo. In this repo, include:
   - `python3 /Users/joshua.burkhow/.codex/tmp/accounting_rules_capture/check_workflow_native_contract.py <single-workflow-path>`
3. Run required visual/layout checks for workflow testing and validation tasks. In this repo, include:
   - `python3 /Users/joshua.burkhow/.codex/tmp/accounting_rules_capture/check_accounting_standard.py <single-workflow-path>` when the Accounting checker applies to the workflow family
   - `python3 tools/alteryx/validate_workflow_layout_policy.py --workflow-list <list> --require-straight-same-stage` when the repo validator is available
   - `python3 tools/alteryx/validate_layout_quality.py --root <scope_root>` as informational only when it conflicts with approved Accounting split-stage rules
   - `python3 tools/alteryx/validate_no_browse_and_ai_ready_layout.py --root <scope_root> --expected-workflow-count <N>` as informational only when it conflicts with approved Accounting split-stage rules
4. For VM-backed starter-kit workflows, run `AlteryxEngineCmd.exe` after each edit cycle against the VM source-of-truth file.
5. If any failure exists, repair it automatically. Required remediation areas include:
   - missing macro or custom-plugin detection and repair
   - broken tool XML repair for 2025.1 native tools
   - connection repair so all real tools are connected
   - AI-ready branch repair using the approved split-section pattern
   - deterministic output filename and path normalization
   - duplicate `EngineSettings` removal
   - explicit `LayoutType=Horizontal` repair for workflows and referenced macros
   - broken transpose key or data tags
   - invalid summarize action names and invalid native-tool configuration shapes
   - consecutive `Formula` consolidation on the same branch when there is no real boundary
   - removal of invalid multiple standard outputs from the same source tool
   - layout and section repair so the workflow follows the approved visual reference for that workflow family
   - straight-line cleanup where possible and line-crossing reduction where the layout policy requires it
   - header, section title, and section box repair when the visual checker flags them
6. Re-run the full required validation set.
7. Continue until all required gates pass or two consecutive iterations show no improvement.
8. If no-improvement stop is reached, return a concrete blocker list with file paths and do not claim completion.

### Per-Workflow Checker Discipline (Required)
- If a checker only accepts a single workflow path, you must iterate it one workflow at a time across the full target file list.
- Never treat one JSON `PASS` from a single-workflow checker as proof that the full starter-kit scope passed.
- For this repo, treat these as single-workflow checkers unless their interface explicitly changes:
  - `check_accounting_standard.py`
  - `check_workflow_native_contract.py`
- Required command pattern:
```bash
while IFS= read -r wf; do
  python3 /Users/joshua.burkhow/.codex/tmp/accounting_rules_capture/check_accounting_standard.py "$wf" || exit 1
  python3 /Users/joshua.burkhow/.codex/tmp/accounting_rules_capture/check_workflow_native_contract.py "$wf" || exit 1
  python3 tools/alteryx/validate_workflow_layout_policy.py --workflow "$wf" --require-straight-same-stage || exit 1
done < workflow_list.txt
```

### Required Per-Workflow Audit Report
- For starter-kit validation, generate and review a per-workflow audit report before signoff.
- The report must explicitly identify failures for:
  - header alignment
  - section title-to-box alignment
  - section gap consistency
  - `Transformations` right-side dead space
  - straight-line and line-crossing issues
- If any workflow fails, list each failed workflow and the exact reasons before any completion message.

### Required Completion Gate
Do not report success until all required gates below pass:
- `verify_workflows.py` summary status = `PASS`
- `lint_yxmd.py` total_errors = `0`
- `check_workflow_native_contract.py` result = `PASS` when the checker exists for the repo
- `check_accounting_standard.py` result = `PASS` when the Accounting checker applies to the workflow family
- `validate_workflow_layout_policy.py` result = `PASS` when used
- VM `AlteryxEngineCmd.exe` run = `PASS` for VM-backed starter-kit workflows
- per-workflow audit report failed workflows = `0`

### Required Visual Review Loop
For workflow testing and validation tasks, visual/layout review is required.

When workflow files were changed or validated:
- apply the approved named visual reference for that workflow family
- for general customer-facing generated workflows, use `golden/customer_facing_hybrid_reference/10_REFERENCE_customer_facing_hybrid.yxmd` as the primary reference
- for documentation-frame examples, use `golden/customer_facing_canvas_framing/REFERENCE_customer_facing_canvas_framing.yxmd`
- use `scripts/render_workflow_image.py` to generate a preview image when Designer is unavailable
- use `scripts/capture_designer_screenshot.ps1` for a true Designer screenshot in an interactive Windows session when needed
- consult `alteryx-beautification` for visual repair decisions and anti-spiderweb layout work
- inspect changed workflows in batches of up to 5
- if a batch has issues, fix that batch before moving to the next batch
- reopen the same batch after each fix to confirm the issue is resolved
- stop after 5 clean batches, or sooner if fewer than 25 workflows were changed and all changed workflows were covered

### Required Visual Completion Gate
For workflow testing and validation tasks:
- visual batch review completed for the changed workflows
- any remaining generic layout validator failures are called out as approved false positives with a concrete reason

### Scope Discipline
- Only modify files in the user-specified scope.
- Do not treat runtime testing as a substitute for required XML and structural validation.
- Do not skip visual/layout remediation when the task is workflow testing or validation.

## 2025.1 Repair Notes
- When a user points to a VM-hosted `C:\...` workflow copy, treat that VM file as the source of truth and run `AlteryxEngineCmd.exe` after every workflow edit before claiming success.
- For the Parallels validation bridge in this environment, use `prlctl exec "2025.1 Server" cmd /c ...`.
- Stage host-side workflow snapshots through `~/.codex/tmp`, then copy them into the VM with `\\Mac\Home\.codex\tmp\...` so the VM-local `C:\Users\SEuser\Github\...` file is the one Designer and `AlteryxEngineCmd.exe` execute.
- If VM execution details are in doubt, check the established helper scripts and memories before inventing a new bridge:
  - `~/.codex/memories/codex_vm_tools/codex_vm_patch_workflow.ps1`
  - `~/.codex/memories/codex_vm_tools/codex_vm_run_workflow.ps1`
- Do not assume a clean engine run is sufficient proof of correctness.
- Treat missing macro or missing custom-plugin nodes as a hard failure for starter-kit workflows, even when static validators and engine runs pass.
- Audit workflow XML for non-native macro or plugin references:
  - `EngineSettings Macro=...`
  - `GuiSettings Plugin=...` values that point to macro wrappers or unresolved custom tools
  - relative `.yxmc` dependencies that must resolve from the full starter-kit folder shape
- Any node that renders in Designer as a black question-mark tool is unresolved and must be fixed before completion.
- If the macro file exists, restore the expected relative path and preserve the full starter-kit folder shape so Designer resolves it correctly.
- If the macro file is missing or unsupported for the target profile, replace it with a native-tool equivalent and revalidate.
- Preserve Designer-authored connection semantics when repairing native XML:
  - `Join` downstream origins should use `Connection="Join"` for the matched stream.
  - `Union` incoming destinations should use `Connection="Input"` on the destination side.
  - `Filter` branch outputs should use `Connection="True"` and `Connection="False"`.
- For `MultiRowFormula` create-field repairs, include both the top-level `Field` element and the explicit create-field metadata.
- For 2025.1 `Summarize` repairs, use Designer-native action names such as `Avg`, not prose variants like `Average`.
- For 2025.1 `Join` repairs, use the native Designer shape with `<Configuration joinByRecordPos="False">`, paired `<JoinInfo connection="Left|Right">` blocks, and a `<SelectConfiguration>` for the join output.
- For starter-kit workflows, do not leave multiple `Formula` tools in a row. Collapse consecutive formula-only steps into one `Formula` tool with multiple expressions, preserving expression order.
- Every starter-kit workflow and every referenced macro must explicitly use `LayoutType=Horizontal`.
- Remove duplicate `EngineSettings` nodes when repairing tool XML.
- All real processing tools must be connected. Do not leave disconnected tools in a completed workflow unless the user explicitly requested a draft stub.
- Do not allow more than one standard output file branch from the same source tool.
- Use the approved split-section AI-ready pattern for starter-kit workflows:
  - a `Union` immediately before the AI Ready macro
  - every final structured output branch also feeds that pre-AI `Union`
  - the AI-ready output is separate from the standard output path
- When staging a local validation snapshot of a VM workflow, preserve the full starter-kit folder shape so relative macro, data, and output paths resolve the same way they do in the VM copy.
- Do not add `HtmlBox` side panels to non-TOC starter-kit workflows. They are acceptable for TOC pages, but they are not part of the non-TOC workflow design system.

## Visual Rules
Apply this section for workflow testing and validation tasks, and for any explicit visual formatting or layout cleanup request.

- For customer-facing or accelerator-ready generated workflows, combine native tool generation with `alteryx-beautification` and the customer-facing hybrid reference.
- Use a concise top banner, contextual containers around the workflow body, and a bottom documentation shelf when first-open presentation quality matters.
- Treat connector readability as part of correctness for visual workflow work; avoidable crossings and tangled hubs must be fixed through geometry.
- For Accounting-derived finance starter kits, use `accounting_close_exception_resolution` as the visual reference.
- Use the approved five-section visual model:
  - `Data Input`
  - `Data Preparation`
  - `Transformations`
  - `AI Ready`
  - `Data Output`
- Keep section boxes behind tools.
- Keep section widths tool-driven and remove extra dead space.
- Keep section gaps consistent.
- `Data Input` should be left aligned to the page system and its tool stack should be visually centered inside the section.
- `Data Output` tools should be vertically stacked and visually centered inside the section.
- The dark hero header box is background only. The workflow title should appear once, in the inset title box only.
- Use the approved feedback band pattern only when that workflow family already uses it or the user explicitly asks for it.
- Use `check_accounting_standard.py` for these visual checks when it applies to the repo and workflow family.

## Governance Sources
Use these files as the contract surface:
- `workflow_builder.md`
- `WORKFLOW_RULES.md`
- `MISTAKES.md`
- `VALIDATION_PROTOCOL.md`
- `CODEX_TASK.md`
- `golden/customer_facing_hybrid_reference/10_REFERENCE_customer_facing_hybrid.yxmd` for generated customer-facing workflow style
- `scripts/render_workflow_image.py` for rendered visual review

## Distribution Hygiene
```bash
python scripts/clean_skill_tree.py .
python C:/Users/Adeon/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/Adeon/.codex/skills/alteryx-workflow-builder
```

- decorative embedded base64 image boxes in workflows must be audited against the branded/golden reference; they must stay small, out of AI Ready/Data Output, and never be stretched to fill a section
