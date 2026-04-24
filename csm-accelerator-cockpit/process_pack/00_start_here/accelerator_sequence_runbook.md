# Accelerator Sequence Runbook

This runbook is the operator-facing sequence for moving from customer discovery to a runnable Alteryx accelerator package.

It is designed so a new operator can pick up the work and run each step in order without reconstructing the method from memory.

## Purpose

Use this runbook to execute the full chain:

1. customer discovery conversation
2. guided capture
3. accelerator SOP
4. SOP-to-workflow build
5. traceability and proof packaging
6. validation and review

This runbook assumes the target product is `Alteryx`.

## Non-Negotiable Build Rule

For every workflow build, the first build input must be the `Large` section in:

- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)

This is mandatory.

Do not start a workflow build from the project SOP alone.
Do not start a workflow build from planning files alone.
Do not improvise a build from memory or from prior thread context.

The required build stack is:

1. `Large` in `sop_to_alteryx_super_prompt_pack.md`
2. `docs/03_accelerator_sop.md`
3. project planning files such as `workflow_plan.md`, `source_inventory.md`, `join_map.md`, `synthetic_data_plan.md`, `output_contract.md`
4. `docs/sop_gap_log.md`
5. local project `data/raw` and `data/generated`

If this order is not followed, the build is out of process.

## Operating Rule

Always follow the sequence in order:

- `01` = raw evidence
- `02` = organized meaning
- `03` = buildable spec
- `04` = traceability from spec to implementation
- `05` = proof summary and review packaging
- `06+` = implementation review and next decision

Do not skip the guided capture step.
Do not jump from conversation notes straight to workflow build.

Reference:
- [00_01-02-03_operating_rule.md](process_pack/00_start_here/00_01-02-03_operating_rule.md)
- [accelerator_process_and_decision_map.md](process_pack/00_start_here/accelerator_process_and_decision_map.md)

## Standard File Convention

Use this default sequence unless the project already has an established structure:

- `docs/01_customer_discovery_conversation.md`
- `docs/02_guided_sop_capture.md`
- `docs/03_accelerator_sop.md`
- `docs/04_traceability_matrix.md`
- `docs/05_proof_summary.md`
- `docs/sop_gap_log.md`
- `docs/sop_architecture_assessment.md`
- `workflows/00_<project_name>.yxmd`

If a project starts from a Word discovery artifact, keep the Word file as the primary meeting record and create the matching markdown file for the sequence.

## Step 0. Create The Working Folder

Owner:
- operator

Goal:
- create or confirm the project folder and output locations before starting the sequence

Inputs:
- project name
- customer or use-case name
- chosen working directory

Actions:
- create a project folder under the working area
- create `docs`, `data`, and `workflows` folders if they do not already exist
- decide whether the discovery artifact will start in Word, Markdown, or both

Required outputs:
- project folder ready for sequence files

Done when:
- the folder exists
- the `docs` location is ready
- the operator knows where `01`, `02`, and `03` will be written

## Step 1. Run The Guided Conversation

Owner:
- consultant or discovery operator

Goal:
- capture the customer discovery conversation in a structured way without prematurely turning it into requirements

Primary input:
- live customer conversation or simulated customer discovery notes

Primary tools and references:
- [guided_discovery_conversation_template.docx](process_pack/01_discovery/guided_discovery_conversation_template.docx)
- [accelerator_interview_script.md](process_pack/01_discovery/accelerator_interview_script.md)

Primary output:
- `docs/01_customer_discovery_conversation.md`

Optional retained artifact:
- the completed Word capture document

What to capture:
- consultant-client dialogue
- business problem
- current process
- desired outcome
- business questions
- scope clues
- source clues
- trust criteria
- constraints

What not to do:
- do not clean it into polished SOP language
- do not fill gaps by guessing
- do not jump into detailed workflow design

Done when:
- the discovery record reflects what the customer actually said
- important ambiguity is preserved rather than smoothed out
- the next operator can see the raw business signal clearly

## Step 2. Convert `01` Into Guided Capture

Owner:
- analyst or Codex operator

Goal:
- turn the raw conversation into structured discovery notes that are ready to become an SOP

Primary input:
- `docs/01_customer_discovery_conversation.md`

Primary tools and references:
- [guided_sop_capture_template.md](process_pack/02_sop_authoring/guided_sop_capture_template.md)
- [consultant-client-sop-extractor skill](consultant-client-sop-extractor skill)

Primary output:
- `docs/02_guided_sop_capture.md`

Required structure:
- executive summary
- discovery summary
- scope
- solution hypothesis
- source system discovery plan
- data contract seeds
- business rules and logic
- testing and validation
- risks and gaps

Required discipline:
- every major point must be treated as `Confirmed`, `Assumed`, or `Unknown / To Discover`
- keep client wording where it matters
- identify what would block build if left unresolved

Done when:
- the capture is structured and compact
- assumptions are explicit
- unknowns are visible
- the document can act as the primary input to SOP generation

## Step 3. Convert `02` Into The Accelerator SOP

Owner:
- analyst or Codex operator

Goal:
- convert the guided capture into a clean, buildable SOP for the first implementation slice

Primary input:
- `docs/02_guided_sop_capture.md`

Primary tools and references:
- [guided_capture_to_accelerator_sop_prompt.md](process_pack/02_sop_authoring/guided_capture_to_accelerator_sop_prompt.md)
- [accelerator_sop_template.md](process_pack/02_sop_authoring/accelerator_sop_template.md)

Primary outputs:
- `docs/03_accelerator_sop.md`
- `docs/sop_gap_log.md`

Optional outputs:
- confirmed / assumed / unknown summary
- follow-up questions list

What the SOP must define:
- business problem
- desired outcome
- accelerator objective
- scope boundary
- business questions
- expected source systems
- likely analytical grain
- core business logic
- required outputs
- validation requirements
- known gaps and discovery actions

What not to do:
- do not let the SOP become a transcript
- do not pretend unresolved source details are settled
- do not invent physical schema detail without evidence

Done when:
- the SOP is specific enough to build from
- the first slice is clearly defined
- the main gaps are surfaced
- another operator can pick up the SOP and move to implementation

## Step 4. Build The Workflow From The SOP

Owner:
- Codex operator or implementation engineer

Goal:
- turn the SOP into a runnable, validated Alteryx implementation slice

Primary input:
- `docs/03_accelerator_sop.md`

Primary tools and references:
- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
- [alteryx-workflow-builder skill](alteryx-workflow-builder skill)
- [alteryx-beautification skill](alteryx-beautification skill)

Recommended prompt mode:
- `Large` only

Required build input order:

1. `Large` in `sop_to_alteryx_super_prompt_pack.md`
2. `docs/03_accelerator_sop.md`
3. project planning files
4. `docs/sop_gap_log.md`
5. local project data

Primary outputs:
- one primary `.yxmd` workflow
- synthetic or local demo data
- business outputs
- validation evidence
- architecture assessment
- updated gap log if needed

Mandatory build sub-steps:

1. build or modify the workflow with `alteryx-workflow-builder`
2. beautify the workflow with `alteryx-beautification`
3. re-run static validation after beautification
4. re-run Alteryx Engine runtime after beautification when the engine is available

The build is not complete if beautification was skipped.
The build is not complete if validation was only run before beautification.

Expected deliverables:
- `workflows/00_<project_name>.yxmd`
- `docs/sop_architecture_assessment.md`
- `docs/validation_evidence.md`
- `docs/sop_gap_log.md`
- supporting generated outputs under `data/generated/`

Done when:
- the workflow runs
- the workflow has been beautified for readable handoff
- outputs are generated
- validation has been performed
- the implementation package records what had to be assumed or worked around
- runtime execution has passed in Alteryx Engine or Designer without workflow errors
- the next operator does not need to manually repair the workflow before first use

## Step 5. Create Traceability And Proof Packaging

Owner:
- Codex operator, analyst, or consultant

Goal:
- turn the runnable slice into a consultant-facing proof pack that clearly shows what was asked for, what was built, what was proved, and what remains open

Primary inputs:
- `docs/03_accelerator_sop.md`
- generated workflow outputs
- validation evidence
- architecture assessment
- gap log

Primary outputs:
- `docs/04_traceability_matrix.md`
- `docs/05_proof_summary.md`

What `04_traceability_matrix.md` must do:
- map discovery questions or business needs to SOP requirements
- map SOP requirements to workflow logic and output files
- show what was validated
- show where traceability breaks because of unresolved gaps

What `05_proof_summary.md` must do:
- summarize what the first slice proved
- summarize what it did not prove
- point to the core evidence files
- state the most important next action

Done when:
- the proof pack makes it easy for a consultant or stakeholder to understand what is real, what is approximated, and what happens next

## Step 6. Review And Decide The Next Move

Owner:
- delivery lead, consultant, or operator

Goal:
- decide whether the package is good enough to demo, refine, or extend

Primary inputs:
- generated outputs
- validation summary
- architecture assessment
- traceability matrix
- proof summary
- updated gap log

Review questions:
- does the workflow answer the business questions from the discovery?
- are the outputs actionable or only technically correct?
- are the main assumptions acceptable for a demo slice?
- what would need to be confirmed before moving toward production design?
- is another discovery pass required?

Possible outcomes:
- demo-ready
- needs SOP refinement
- needs source clarification
- needs implementation iteration

Done when:
- the next step is explicitly chosen
- the project status is visible to the next operator

## Recommended Prompt Stack By Step

Use this simplified mapping:

1. Discovery conversation
- use the Word template and interview script

2. Guided capture
- use the structured capture template
- use the extraction skill if needed

3. SOP generation
- run [guided_capture_to_accelerator_sop_prompt.md](process_pack/guided_capture_to_accelerator_sop_prompt.md)

4. Workflow build
- start with `Large` in [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
- then apply the project SOP and planning files beneath it

5. Traceability and proof packaging
- create `04_traceability_matrix.md`
- create `05_proof_summary.md`

## Minimum Handoff Pack

If work is being passed to another person, hand over at least:

- current project folder path
- latest `01`, `02`, and `03` documents
- current `04_traceability_matrix.md`
- current `05_proof_summary.md`
- current gap log
- current architecture assessment if implementation has started
- the next step number from this runbook
- any decisions already made about scope, source style, and deliverable format

## Decision Gates

Do not move from one step to the next unless these checks pass:

From Step 1 to Step 2:
- the conversation record reflects real customer language
- ambiguity has not been flattened away

From Step 2 to Step 3:
- confirmed vs assumed vs unknown is explicit
- there is enough signal to define a first slice

From Step 3 to Step 4:
- the SOP has a clear objective
- the scope boundary is usable
- outputs and validation expectations are visible

From Step 4 to Step 5:
- the workflow runs successfully and produces the expected outputs, or the package is treated as incomplete
- the gap log reflects what actually happened during build

From Step 5 to Step 6:
- traceability from requirement to output is visible
- the proof summary distinguishes what was proved from what remains unresolved

## Failure Handling

If the sequence stalls:

- if discovery is too vague, return to Step 1 or Step 2
- if the guided capture is weak, rewrite `02` before writing `03`
- if the SOP is too ambiguous to build, improve `03` before forcing implementation
- if the workflow build exposes major requirement gaps, update `03` and the gap log before continuing
- if static validation passes but runtime execution fails, do not hand off the package as complete; fix the workflow or stop the sequence as incomplete

## Practical Default

If the operator is unsure what to do next, use this default:

1. create or confirm `01`
2. create `02`
3. run the SOP prompt to create `03`
4. run the SOP-to-workflow prompt pack
5. create `04_traceability_matrix.md` and `05_proof_summary.md`
6. review outputs, proof, and gaps

## Related Files

- [guided_discovery_conversation_template.docx](process_pack/01_discovery/guided_discovery_conversation_template.docx)
- [accelerator_interview_script.md](process_pack/01_discovery/accelerator_interview_script.md)
- [guided_sop_capture_template.md](process_pack/02_sop_authoring/guided_sop_capture_template.md)
- [guided_capture_to_accelerator_sop_prompt.md](process_pack/02_sop_authoring/guided_capture_to_accelerator_sop_prompt.md)
- [accelerator_sop_template.md](process_pack/02_sop_authoring/accelerator_sop_template.md)
- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
