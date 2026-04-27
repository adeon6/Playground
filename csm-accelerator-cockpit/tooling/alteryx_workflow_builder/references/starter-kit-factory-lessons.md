# Office of Finance AI Starter Kits - Knowledge Export

## Scope and outcome
This document captures the implementation standards, workflow rules, packaging contracts, testing approach, and failure/fix patterns learned while building and stabilizing the Office of Finance AI Starter Kits set.

Current target set: 25 starter kits.

## Canonical 25 starter kits
1. Unstructured Invoice Processing
2. Local LLM Automating Accounts Payable
3. Year End Balance True Up Reconciliation
4. Managing Entity Relationships
5. Invoice Processing
6. Accounting Automation
7. Advanced Trial Balance Mapping & Reporting
8. Automated Journal Entry
9. Consolidations
10. Extracting Data from Invoices Using AI Macros
11. Month-End Close Acceleration
12. Reconciliation
13. Regulatory Reporting
14. Expense Management
15. Rebates
16. Finance Report Analysis
17. Automated Financial Commentary
18. FPA Automation
19. Financial Forecasting & Client Segmentation
20. Price Check
21. Budget vs Actuals
22. Stock Price Analyzer (for Portfolio Manager)
23. Automating Internal Tax Compliance Controls
24. Tax Automation
25. Tax PDF Extraction

## Folder and packaging architecture
Root:
`/Users/joshua.burkhow/GitHub/alteryx_starter_kits/Office_of_Finance_AI_Starter_Kits`

Per-kit required structure:
- `<kit_slug>/Config.xml`
- `<kit_slug>/Icon.png`
- `<kit_slug>/Build/<kit_slug>.yxi`
- `<kit_slug>/Samples/<lang>/Starter Kits/<kit_slug>/...`
- `<kit_slug>/Samples/data/Starter Kits/<kit_slug>/...`

Required language set:
- `en`, `de`, `es`, `fr`, `it`, `ja`, `pt`, `zh`

Non-kit/admin assets should live in:
- `Office_of_Finance_AI_Starter_Kits/00_admin`

## Workflow contract per language
Minimum workflow set per language folder:
- `01 Table of Contents.yxmd`
- plus at least five non-TOC workflows (`02` to `06`)

Expected pattern:
- `02` foundation/intake
- `03` controls/validation
- `04` automation core
- `05` AI commentary/insights
- `06` reporting/handoff

Workflow design expectations:
- Non-TOC workflows: 30+ tools minimum
- Multiple branches and tool containers
- Container-level annotations
- Visual consistency (colors/layout/comments)
- Explicit QA/validation container(s)

## TOC and localized docs standards
TOC quality requirements:
- Clickable workflow cards/links
- Rich visual design (hero, logo, sections)
- Clear run order and prerequisites
- Governance and next-step blocks

Localized files required in each language `data` folder:
- `TableOfContents.html`
- `Setup_Guide.md`
- `CustomGPT_Build_Instructions.md`

TOC link rules:
- Links must point to local workflow names in same language folder
- Keep links synchronized whenever workflow filenames change

## AI Ready Data and CustomGPT contract
Each non-TOC workflow must produce AI-ready output suitable for CustomGPT ingestion.

Required feed behavior:
- `customgpt_master_feed.csv`
- use-case-specific feed(s)
- deterministic field naming
- data dictionary documenting schemas and intent

Macro contract:
- Use `AI Ready Macro.yxmc` in workflows feeding GPT outputs
- Macro paths must be relative and package-safe
- No missing macro references (avoid black-question-mark tools)

CustomGPT instructions in every kit should include:
- knowledge-only behavior
- no web lookup
- source citation expectations
- missing-data handling
- conversation starters

## Governance and security expectations
- No API keys in workflows/packages
- No machine-specific credentials/absolute local-only dependencies
- Document what data is sent to LLMs
- Include masking and audit guidance
- Include model/provider switching notes and cost/accuracy tradeoffs

## File naming and path length policy
Windows path length was a major runtime failure source.

Policy:
- Keep workflow names concise enough for Windows execution paths
- Prefer short canonical workflow filenames (`02 <short title>.yxmd`)
- Avoid long suffix patterns in production names
- Keep output filenames short and deterministic (e.g., `02_ai_ready_data.csv`)

## Key scripts and artifacts
Primary runner:
- `tools/alteryx/run_workflow_batch.ps1`

Primary outputs:
- `tools/alteryx/alteryx_test_results.txt`
- `tools/alteryx/alteryx_issues.txt`
- `tools/alteryx/failed_workflows_next_run.txt`

Static validation artifact:
- `tools/alteryx/post_fix_static_validation.txt`

Optional remediation utility:
- `tools/alteryx/fix_overlength_workflow_names.ps1`

## Static validation checks (no runtime)
Use XML and filesystem checks to catch defects before VM runs:
1. Structure check: required folders/files for all kits/languages
2. XML parse check for all `.yxmd` and `.yxmc`
3. Macro reference check: macro file exists and path resolves
4. Connection integrity check: required join/inputs wired
5. Duplicate artifact check: remove `._*`, ` (1)` copies, `* 2.*` leftovers
6. Path checks: no absolute machine paths; no overlong output path refs
7. Version check: workflows on `yxmdVer="2025.1"`
8. Localization presence: translated TOC/docs exist for each language

## Runtime smoke test flow
1. Install YXI
2. Open localized TOC
3. Run demo/foundation workflows
4. Verify output samples and AI-ready files
5. Run production/handoff workflow
6. Capture pass/fail in test reports

## Known failure patterns and proven fixes

### 1) XML parse errors from unescaped ampersands
Symptom:
- ParseError with "expected entity name"

Fix:
- Replace `&` with `&amp;` in XML text content
- Re-validate parse for all affected workflows

### 2) "Can't read the file" runtime errors
Common causes:
- Duplicate/temporary files referenced (e.g., ` (1).yxmd`)
- Missing files in run list
- Overlong workflow path names on Windows

Fix:
- Remove duplicate artifacts
- Normalize canonical filenames
- Regenerate run list
- Enforce duplicate exclusion in auto-discovery

### 3) Output write failures (`system cannot find path specified`)
Cause:
- Overlong output file path names

Fix:
- Shorten output filenames (`NN_ai_ready_data.csv`)

### 4) Join/macro input wiring errors
Symptom:
- missing incoming connection / both sides required

Fix:
- Validate connections in XML
- Rewire to proper upstream tabular outputs

### 5) Duplicate artifacts reappearing
Sources:
- Finder/Drive/VM sync side effects
- "(1)" copy files
- `._` metadata files

Fix:
- Periodic duplicate cleanup
- Discovery filters for `._*` and ` (n).yxmd`

## Duplicate cleanup policy
Delete from starter-kit trees:
- `._*.yxmd`
- `* (n).yxmd`
- zero-byte duplicate copies
- empty duplicate folders (e.g., suffix ` 2`)

After cleanup, always re-run:
- workflow count check (target: 1200 for 25 kits x 8 languages x 6 workflows)
- parse check
- run-list regeneration

## Count invariants
Current expected invariant for this portfolio:
- 25 kits
- 8 languages
- 6 workflows per language
- total: 1200 workflows

Formula:
`25 * 8 * 6 = 1200`

## Build and release checklist
1. Confirm kit folders and naming
2. Confirm 6 workflows per language (`01` to `06`)
3. Confirm TOC links and localized docs
4. Confirm AI-ready outputs and feed schema docs
5. Run static validation checks
6. Run batch runtime tests
7. Generate failed-only rerun list
8. Fix failures and rerun until clean
9. Record final report and delivery notes

## Operational commands (PowerShell)
Run all discovered workflows:
```powershell
powershell -ExecutionPolicy Bypass -File .\tools\alteryx\run_workflow_batch.ps1
```

Run only failed workflows from last report:
```powershell
$wf = (Resolve-Path .\tools\alteryx\failed_workflows_next_run.txt).Path
powershell -ExecutionPolicy Bypass -File .\tools\alteryx\run_workflow_batch.ps1 `
  -DiscoverAllStarterKitWorkflows $false `
  -WorkflowListPath "$wf"
```

## Notes on evidence freshness
`alteryx_test_results.txt` and `alteryx_issues.txt` are point-in-time snapshots. If file cleanup/recovery happens after a run, reports are stale until rerun.



## Workflow visual/layout standards
Use `Office_of_Finance_AI_Starter_Kits/00_admin/WORKFLOW_LAYOUT_RULES.md` as the source of truth for spacing, stage-box geometry, text clipping prevention, AI-ready branch placement, and no-Browse policy in non-TOC workflows.


## Portfolio-Wide Workflow Visual Best Practices (Approved)

These are global standards and must be treated as default workflow hardening policy.

1. Unified dark header with title, description, and feedback panels aligned top/bottom.
2. Feedback panel uses rounded rectangle shape (`Shape=0`) and approved link behavior.
3. Instruction bars are compact, aligned, and width-consistent with section grid.
4. Section boxes use uniform spacing and consistent title-bar geometry.
5. Tools, icons, and annotations never cross divider lines or section borders.
6. Prefer straight same-section connectors unless readability rules force bends.
7. Annotation text must not overlap connectors/tools and must not clip.
8. Decorative icons are aligned with tool rows and never overlap tool footprints.
9. AI-ready transform/output remain in a lower same-section lane and fully contained.
10. Keep `yxmdVer=2025.1`, relative paths, and deterministic output labeling.

