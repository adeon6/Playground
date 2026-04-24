# Guided SOP Capture Template

This document is designed to be used live in a customer conversation.

It combines:
- the consultant interview flow
- the accelerator SOP structure
- live capture fields

The aim is to avoid a two-step process where notes are taken first and the SOP is written later.

Use this document as the working artifact during discovery.

## How To Use

For each section:
- ask the consultant prompts
- capture the answers directly in this document
- distinguish between:
  - `Confirmed`
  - `Assumed`
  - `Unknown / To Discover`

By the end of the meeting, this should already be a usable first SOP draft.

---

## 0. Document Control

Customer: `[Customer name]`
Engagement: `[Project / accelerator name]`
Document ID: `[SOP-ACC-XXX]`
Version: `0.1`
Date: `[YYYY-MM-DD]`
Consultant: `[Name]`
Primary Stakeholders: `[Roles / names]`
Target Product: `Alteryx`
Status: `Discovery`

---

## 1. Executive Summary

### Consultant Prompts
- What problem are you trying to solve?
- What is slow, manual, inaccurate, or risky today?
- What would â€œworkingâ€ look like?
- What should the first accelerator slice prove?

### Capture Notes

Business problem:
- `[Capture here]`

Desired outcome:
- `[Capture here]`

Accelerator objective:
- `[Capture here]`

### SOP Output

#### 1.1 Business Problem
- `[Write concise statement here]`

#### 1.2 Desired Outcome
- `[Write concise statement here]`

#### 1.3 Accelerator Objective
- `[Write concise statement here]`

#### 1.4 Value Statement
- `[Write 2-4 evidence-backed sentences here]`

---

## 2. Discovery Summary

### Consultant Prompts
- How is this done today?
- Where do manual steps, spreadsheets, emails, or handoffs happen?
- Which part hurts the most?
- What business questions do you want answered?
- What would make this accelerator feel successful?

### Capture Notes

Pain points:
- `[Capture here]`

Current process:
- `[Capture here]`

Business questions:
- `[Capture here]`

Measures of success:
- `[Capture here]`

### SOP Output

#### 2.1 Pain Points
- `[Refine from notes]`

#### 2.2 Current Process
- `[Refine from notes]`

#### 2.3 Business Questions To Answer
- `[Refine from notes]`

#### 2.4 Measures of Success
- `[Refine from notes]`

---

## 2A. Value Capture

Use this section to capture value early, even when the customer cannot give a hard ROI number yet.

### Consultant Prompts
- What is the business impact of the current process being manual, slow, inconsistent, or hard to trust?
- If this workflow worked well, what would change operationally for the team?
- How would you measure success numerically, if possible?
- If you cannot quantify it yet, what qualitative improvement would still matter?
- What would make the business trust the output enough to use it?
- What volume, frequency, turnaround time, backlog, effort, or error rate matters here?

### Capture Notes

Current pain or risk:
- `[Capture here]`

Operational change enabled by workflow:
- `[Capture here]`

Quantitative value signals:
- `[Capture counts, hours, cycle time, SLA, volumes, error rates, rework, backlog, frequency]`

Qualitative value signals:
- `[Capture trust, consistency, visibility, decision speed, user confidence, stakeholder alignment]`

Success evidence or trust signals:
- `[Capture what would make users believe and adopt the output]`

Value unknowns to validate later:
- `[Capture here]`

### SOP Output

#### 2A.1 Current Pain Or Risk
- `[Refine from notes]`

#### 2A.2 Workflow-Enabled Operational Change
- `[Refine from notes]`

#### 2A.3 Quantitative Value Signals
- `[Refine from notes]`

#### 2A.4 Qualitative Value Signals
- `[Refine from notes]`

#### 2A.5 Trust And Adoption Signals
- `[Refine from notes]`

#### 2A.6 Draft Value Statement Formula
- `Today [current pain/risk] happens because [current process constraint].`
- `This workflow would [operational change].`
- `That creates value by [time saved / risk reduced / consistency improved / decision speed increased / trust improved].`

---

## 3. Scope

### Consultant Prompts
- What is definitely in scope for the accelerator?
- What is out of scope for the first slice?
- Is there a preferred pilot area?
- Are we proving feasibility, business value, or both?

### Capture Notes

In scope:
- `[Capture here]`

Out of scope:
- `[Capture here]`

Pilot boundary:
- `[Capture here]`

### SOP Output

#### 3.1 In Scope
- `[Refine from notes]`

#### 3.2 Out Of Scope
- `[Refine from notes]`

---

## 4. Solution Hypothesis

### Consultant Prompts
- What should the workflow do end to end?
- If we gave you one useful output quickly, what would it be?
- What is the likely row-level grain of the main dataset?
- What outputs are most useful first?

### Capture Notes

Proposed workflow objective:
- `[Capture here]`

Likely analytical grain:
- `[Capture here]`

Likely outputs:
- `[Capture here]`

### SOP Output

#### 4.1 Proposed Workflow Objective
- `[Refine from notes]`

#### 4.2 Proposed Analytical Grain
- `[Refine from notes]`

#### 4.3 Proposed Outputs
- `[Refine from notes]`

---

## 5. Source System Discovery Plan

### Consultant Prompts
- Where does the data probably live?
- Which systems, files, owners, or teams are involved?
- What do we know about the source shape?
- What do we not know yet?
- What must be discovered before build can continue?

### Capture Notes

Expected source systems:
- `[Capture here]`

Known facts:
- `[Capture here]`

Assumptions:
- `[Capture here]`

Unknowns:
- `[Capture here]`

Discovery actions:
- `[Capture here]`

### SOP Output

#### 5.1 Expected Source Systems
- `[Refine from notes]`

#### 5.2 Known Versus Unknown

Confirmed:
- `[Refine from notes]`

Assumed:
- `[Refine from notes]`

Unknown / To Discover:
- `[Refine from notes]`

#### 5.3 Discovery Actions
- `[Refine from notes]`

#### 5.4 Discovery Completion Gate
- usable source inventory
- at least one viable join path
- working grain hypothesis
- enough fields to answer the business questions

---

## 6. Data Contract

Complete this section after source inspection, but seed it during the conversation where possible.

### Consultant Prompts
- What are the likely core entities?
- What are the likely keys?
- What dates matter?
- What measures matter?
- What dimensions matter?
- Are there known joins or reference tables?

### Capture Notes

Likely entities:
- `[Capture here]`

Likely keys:
- `[Capture here]`

Likely measures:
- `[Capture here]`

Likely dates:
- `[Capture here]`

Likely joins:
- `[Capture here]`

### SOP Output

For each dataset:
- Dataset name: `[Fill in]`
- Source system: `[Fill in]`
- Purpose: `[Fill in]`
- Grain: `[Fill in]`
- Key: `[Fill in]`
- Required fields: `[Fill in]`
- Nullable fields: `[Fill in]`
- Business meaning: `[Fill in]`
- Quality rules: `[Fill in]`
- Join role: `[Fill in]`
- Classification: `raw / staged / analytical / output`

---

## 7. Business Rules And Logic

### Consultant Prompts
- What records should be included?
- What records should be excluded?
- What statuses matter?
- What formulas or thresholds are used today?
- What exceptions or overrides exist?
- What edge cases do we need to handle?

### Capture Notes

Inclusion rules:
- `[Capture here]`

Exclusion rules:
- `[Capture here]`

Status logic:
- `[Capture here]`

Formulas and KPI logic:
- `[Capture here]`

Edge cases:
- `[Capture here]`

### SOP Output

#### 7.1 Core Rules
- `[Refine from notes]`

#### 7.2 Assumptions
- `[List inferred rules here]`

#### 7.3 Edge Cases
- `[Refine from notes]`

---

## 8. Workflow Build Blueprint

### Consultant Prompts
- What should happen at ingest?
- What needs standardizing?
- What needs joining or summarizing?
- What should be computed?
- What should be output?
- What must be validated before signoff?

### Capture Notes

Ingest ideas:
- `[Capture here]`

Standardization ideas:
- `[Capture here]`

Blend ideas:
- `[Capture here]`

Compute ideas:
- `[Capture here]`

Outputs:
- `[Capture here]`

Validation expectations:
- `[Capture here]`

### SOP Output

#### 8.1 Stage 1: Ingest
- `[Refine from notes]`

#### 8.2 Stage 2: Standardize
- `[Refine from notes]`

#### 8.3 Stage 3: Blend
- `[Refine from notes]`

#### 8.4 Stage 4: Compute
- `[Refine from notes]`

#### 8.5 Stage 5: Output
- `[Refine from notes]`

#### 8.6 Stage 6: Validation
- `[Refine from notes]`

---

## 9. Automation And Operationalisation

### Consultant Prompts
- Does this need scheduling now or later?
- Are alerts, write-backs, or downstream integrations required?
- What is needed now versus deferred?
- Who will consume the outputs?

### Capture Notes

Needed now:
- `[Capture here]`

Deferred:
- `[Capture here]`

Future-state assumptions:
- `[Capture here]`

### SOP Output

#### 9. Automation And Operationalisation

Required now:
- `[Refine from notes]`

Deferred:
- `[Refine from notes]`

Future state:
- `[Refine from notes]`

---

## 10. Testing And Validation Plan

### Consultant Prompts
- How will the customer know the first slice is credible?
- What can we reconcile to?
- What reports, totals, or spot checks exist today?
- What would count as a failed result?

### Capture Notes

Validation expectations:
- `[Capture here]`

Reconciliation targets:
- `[Capture here]`

Failure conditions:
- `[Capture here]`

### SOP Output

#### 10.1 Minimum Validation
- `[Refine from notes]`

#### 10.2 Demo Validation
- deterministic local run
- repeatable outputs
- evidence file produced

#### 10.3 Production Validation
- `[Refine from notes]`

---

## 11. Gaps, Risks, And Open Questions

### Consultant Prompts
- What donâ€™t we know yet?
- What could block the accelerator?
- What source questions still need answering?
- What business-rule ambiguity remains?
- What access, governance, or ownership risk exists?

### Capture Notes

Gaps:
- `[Capture here]`

Risks:
- `[Capture here]`

Open questions:
- `[Capture here]`

### SOP Output

For each item:
- Gap / risk / open question: `[Fill in]`
- Impact: `[Fill in]`
- Workaround: `[Fill in]`
- Owner: `[Fill in]`
- Next action: `[Fill in]`

---

## 12. Handoff Artifacts

### SOP Output

The accelerator should aim to produce:
- SOP
- schema discovery notes
- data contract
- runnable workflow
- sample or synthetic data where needed
- validation report
- architecture assessment
- gap log

---

## Consultant Reminders

- Do not ask the customer to design the workflow.
- Ask about decisions, actions, pain, and trust first.
- Distinguish confirmed facts from assumptions.
- If source structure is unknown, mark it for discovery rather than forcing certainty.
- Keep the first slice narrow enough to build quickly.
- Aim to leave the meeting with a draft SOP, not just raw notes.
