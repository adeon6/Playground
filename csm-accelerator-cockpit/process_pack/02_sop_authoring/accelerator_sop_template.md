# Customer Accelerator SOP Template

This template is designed for the accelerator use case:
- a consultant discovers pain points with a customer
- the conversation is converted into a buildable SOP
- the build process discovers source structure where needed
- Codex uses the SOP to drive schema discovery, workflow design, build, validation, and gap logging

It is derived from the structure of the existing `201` shelf optimisation SOP, but adapted so it works earlier in the lifecycle when source details may still be unknown.

## 0. Document Control

Field | Detail
--- | ---
Customer | `[Customer name]`
Engagement | `[Project / accelerator name]`
Document ID | `[SOP-ACC-XXX]`
Version | `0.1 / 0.2 / 1.0`
Date | `[YYYY-MM-DD]`
Consultant | `[Name]`
Primary Stakeholders | `[Roles / names]`
Target Product | `Alteryx`
Status | `Discovery / Draft Build / Validated Demo / Production Design`

## 1. Executive Summary

### 1.1 Business Problem
- What pain point is the customer trying to solve?
- What is slow, manual, inaccurate, risky, or invisible today?
- What decision or action do they want to improve?

### 1.2 Desired Outcome
- What would â€œworkingâ€ look like for the customer?
- What output, report, queue, model, alert, or operational decision should exist at the end?

### 1.3 Accelerator Objective
- What can be delivered quickly in the accelerator phase?
- What should the first runnable slice prove?

### 1.4 Value Statement
- Summarize the value of the workflow in 2-4 sentences.
- Base it on the source content already evidenced in the conversation, guided capture, or SOP.
- State:
  - what pain, delay, inconsistency, or risk exists today
  - what the workflow changes operationally
  - what business value is created
- Do not invent ROI figures or generic claims that are not supported by the source material.
- Prefer both of these where possible:
  - quantitative value signals such as effort saved, cycle time reduced, backlog reduced, volume handled, or error rate improved
  - qualitative value signals such as trust, consistency, visibility, auditability, user confidence, or faster decision-making
- If the value is not yet quantifiable, state the qualitative value clearly and mark the quantitative proof points as `Unknown / To Discover`.
- Suggested formula:
  - `Today [current pain/risk] happens because [current process constraint].`
  - `This workflow would [operational change].`
  - `That creates value by [quantitative and/or qualitative benefit].`

## 2. Discovery Summary

This section should be written from the consultant conversation, not from the source system.

### 2.1 Pain Points
- `[Pain point 1]`
- `[Pain point 2]`
- `[Pain point 3]`

### 2.2 Current Process
- How is the work done today?
- What tools, spreadsheets, teams, or manual steps are involved?
- Where are the known delays or failure points?

### 2.3 Business Questions To Answer
- What does the customer need to know?
- What operational questions must the workflow answer?

### 2.4 Measures of Success
- What KPI or improvement matters?
- Faster turnaround?
- Fewer manual steps?
- Better visibility?
- Better prediction?

### 2.5 Value Evidence
- What value can already be evidenced from the conversation or guided capture?
- Separate:
  - quantitative value signals
  - qualitative value signals
  - trust and adoption signals
  - unknown value assumptions to validate later

## 3. Scope

### 3.1 In Scope
- business process stages included in the accelerator
- outputs to build now
- source systems or source candidates to inspect now

### 3.2 Out Of Scope
- production hardening items to defer
- integrations not required for the first slice
- model governance or automation features that depend on later maturity

## 4. Solution Hypothesis

This section bridges the consulting conversation and the build.

### 4.1 Proposed Workflow Objective
- What should the Alteryx workflow do end to end?

### 4.2 Proposed Analytical Grain
- What is the likely row-level grain of the main analytical table?
- Examples:
  - one row per order
  - one row per project and WBS
  - one row per SKU and store

### 4.3 Proposed Outputs
- analytical base table
- dashboard feed
- exception queue
- review pack
- alert output

## 5. Source System Discovery Plan

This is the most important addition versus a traditional SOP.

### 5.1 Expected Source Systems
- `[System or file source 1]`
- `[System or file source 2]`
- `[API / warehouse / ERP / spreadsheet source 3]`

### 5.2 Known Versus Unknown

For each source, record:
- what is confirmed
- what is assumed
- what is unknown
- what must be discovered before build can continue

Example fields:
- system name
- access method
- likely entities/tables/files
- likely key fields
- likely date fields
- likely measures
- expected refresh pattern
- owner

### 5.3 Discovery Actions
- inspect schemas
- sample source rows
- infer keys and joins
- profile nulls and duplicates
- validate date and numeric fields
- confirm whether source shape matches discovery assumptions

### 5.4 Discovery Completion Gate

The build may proceed only when the team has:
- a usable source inventory
- at least one viable join path
- a working grain hypothesis
- enough fields to answer the business questions

## 6. Data Contract

This section should be completed after schema discovery.

For each dataset define:
- dataset name
- source system
- purpose
- grain
- primary key or likely key
- required fields
- nullable fields
- business meaning
- quality rules
- join role
- classification: raw / staged / analytical / output

The `201` SOP already did this well for SAP tables; this template makes that same idea explicit for unknown customer data after discovery.

## 7. Business Rules And Logic

### 7.1 Core Rules
- filters
- inclusions and exclusions
- status logic
- date windows
- calculations
- KPI definitions

### 7.2 Assumptions
- record any rule that had to be inferred from conversation rather than confirmed from source data

### 7.3 Edge Cases
- rejected rows
- missing keys
- late-arriving records
- conflicting source values
- null timestamps

## 8. Workflow Build Blueprint

This section replaces a premature detailed tool-by-tool design during discovery.

### 8.1 Stage 1: Ingest
- inputs
- connection method
- initial filters
- schema enforcement

### 8.2 Stage 2: Standardize
- typing
- field renaming
- key normalization
- date normalization
- reject handling

### 8.3 Stage 3: Blend
- join sequence
- summarization to correct grain
- enrichment logic

### 8.4 Stage 4: Compute
- derived fields
- KPI calculations
- flags
- scoring logic

### 8.5 Stage 5: Output
- business outputs
- analytical output
- exception outputs
- review outputs

### 8.6 Stage 6: Validation
- row-count checks
- join-completeness checks
- sample reconciliation
- business-rule validation

## 9. Automation And Operationalisation

This section should be marked clearly as:
- required now
- deferred
- assumed future state

Capture:
- run frequency
- parameterization
- scheduling target
- alerting requirements
- write-back requirements
- downstream consumers

## 10. Testing And Validation Plan

### 10.1 Minimum Validation
- source data loaded successfully
- required columns found
- joins behave as expected
- outputs exist
- output schema matches expectation
- KPI calculations reconcile to a reference baseline

### 10.2 Demo Validation
- deterministic local run
- repeatable outputs
- evidence file produced

### 10.3 Production Validation
- thresholds
- operational acceptance criteria
- runtime monitoring

## 11. Gaps, Risks, And Open Questions

This section must be explicit.

Examples:
- source schema not yet confirmed
- key field not trusted
- source ownership unclear
- KPI definition still ambiguous
- access method not approved
- production schedule unknown

For each item capture:
- gap
- impact
- workaround
- owner
- next action

## 12. Handoff Artifacts

The accelerator should aim to produce:
- SOP
- schema discovery notes
- data contract
- runnable workflow
- sample or synthetic data where needed
- validation report
- architecture assessment
- gap log

## Consultant Prompting Notes

When using this SOP in the accelerator, the consultant should try to capture the following during customer conversation:
- What decision are you trying to improve?
- What is the current manual process?
- What output would make this useful in week 1?
- What systems probably hold the data?
- What entities are likely involved?
- What are the key statuses, dates, and measures?
- What are the known bad-data problems?
- What would count as a credible first success?

## Why This Differs From The 201 SOP

The `201` SOP was a later-stage, implementation-heavy SOP with known systems, known tables, and a mostly known physical architecture.

This accelerator template is intentionally earlier-stage:
- it preserves the strong structure of the `201` SOP
- it adds a formal source discovery stage
- it distinguishes confirmed facts from assumptions
- it is designed to move from consulting conversation to buildable implementation
- it supports partial knowledge without pretending the source shape is already known
