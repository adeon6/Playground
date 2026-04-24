# Accelerator Process And Decision Map

This file defines how the accelerator process should actually work end to end.

Use it as the operating view above the individual templates and prompts.

## Core Principle

The process is not:
- conversation
- then documentation
- then build

The process is:
- discover enough truth to define a credible first slice
- convert that truth into an honest buildable spec
- prove the spec by building and validating a runnable implementation
- use the build outcome to assess whether the SOP and process were strong enough

The operating sequence remains:
- `01` = raw evidence
- `02` = organized meaning
- `03` = buildable spec
- `04` = runnable implementation and validation
- `05` = traceability and proof packaging
- `06` = review, decision, and next action

## Build Stack Rule

Workflow build must start with the canonical `Large` prompt in:

- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)

Only after that should the operator apply:

1. the project `03_accelerator_sop`
2. the project planning files
3. the project gap log
4. the local project data context

Do not begin build from the project SOP alone.
Do not begin build from project planning docs alone.
Do not replace this stack with memory, prior thread context, or ad hoc judgment.

## End-To-End Flow

### Phase 0. Setup The Project

Purpose:
- create a clean working area before discovery begins

Inputs:
- customer or use-case name
- working location
- known delivery objective

Outputs:
- project folder
- `docs`, `data`, and `workflows` locations
- agreed first working artifact locations

Decision gate:
- do we know where `01`, `02`, `03`, and the build outputs will live?

If no:
- stop and set the project structure first

### Phase 1. Run Discovery

Purpose:
- capture what the customer actually means, not what we assume they mean

Primary assets:
- [guided_discovery_conversation_template.docx](process_pack/01_discovery/guided_discovery_conversation_template.docx)
- [accelerator_interview_script.md](process_pack/01_discovery/accelerator_interview_script.md)

What must be captured:
- business problem
- current process
- desired outcome
- value realisation
- business questions
- scope clues
- source clues
- business rules
- validation and trust signals
- phasing constraints

Output:
- `01_customer_discovery_conversation`

Decision gate:
- do we have enough raw business signal to describe the problem, the first useful outcome, and the trust standard?

If no:
- run more discovery before moving on

If yes:
- move to guided capture

### Phase 2. Convert Discovery Into Guided Capture

Purpose:
- turn raw conversation into structured meaning without pretending ambiguity is resolved

Primary assets:
- [guided_sop_capture_template.md](process_pack/02_sop_authoring/guided_sop_capture_template.md)

What must happen here:
- organize the discovery into the SOP shape
- preserve important client language
- separate `Confirmed`, `Assumed`, and `Unknown / To Discover`
- identify what will block build if left unresolved
- carry forward value signals, both quantitative and qualitative

Output:
- `02_guided_sop_capture`

Decision gate:
- is there enough structured signal to define a first implementation slice honestly?

Minimum yes criteria:
- clear business problem
- visible first-slice objective
- clear value story
- initial scope boundary
- business questions to answer
- visible trust and validation expectations
- explicit unknowns

If no:
- go back to discovery

If yes:
- move to SOP authoring

### Phase 3. Convert Guided Capture Into Accelerator SOP

Purpose:
- create the clean buildable specification for the first implementation slice

Primary assets:
- [guided_capture_to_accelerator_sop_prompt.md](process_pack/02_sop_authoring/guided_capture_to_accelerator_sop_prompt.md)
- [accelerator_sop_template.md](process_pack/02_sop_authoring/accelerator_sop_template.md)

What the SOP must define:
- business problem
- desired outcome
- accelerator objective
- value statement
- scope boundary
- business questions
- source expectations
- likely analytical grain
- core rules and logic
- outputs
- validation expectations
- discovery actions and gaps

Output:
- `03_accelerator_sop`
- `sop_gap_log`

Decision gate:
- is the SOP specific enough to build from without pretending unresolved items are settled?

Minimum yes criteria:
- first slice is explicit
- outputs are explicit
- validation standard is explicit
- key assumptions are visible
- unresolved source or rule ambiguity is logged

If no:
- return to guided capture or discovery, depending on what is weak

If yes:
- move to workflow build

### Phase 4. Build The Runnable Workflow Slice

Purpose:
- pressure-test the SOP by turning it into a runnable Alteryx implementation

Primary assets:
- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)

Build expectations:
- the first build instruction layer is always `Large` from the prompt pack
- `alteryx-workflow-builder` is used first for the workflow build step
- `alteryx-beautification` is run before build signoff
- synthetic or local deterministic inputs unless live connectivity is explicitly required
- one primary end-to-end `.yxmd` workflow unless there is a strong reason not to
- stable outputs
- explicit validation evidence
- honest treatment of assumptions and workarounds

Outputs:
- workflow
- generated data
- business outputs
- validation evidence
- updated gap log
- architecture assessment

Required signoff condition:
- validation must be rerun after beautification, not just after initial build

Decision gate:
- did the workflow actually run and produce outputs that satisfy the intended first-slice objective?

If no:
- stay in build iteration until either:
  - the slice works, or
  - a concrete blocker proves the SOP or discovery is insufficient

If the blocker is implementation-only:
- continue iterating in build

If the blocker is source ambiguity, scope ambiguity, or logic ambiguity:
- loop back to SOP or discovery as appropriate

If yes:
- move to proof packaging

### Phase 5. Package Traceability And Proof

Purpose:
- convert a runnable slice into a consultant-facing proof pack that shows what was asked for, what was built, what was validated, and what remains unresolved

Inputs:
- accelerator SOP
- workflow outputs
- validation evidence
- architecture assessment
- gap log

Outputs:
- `04_traceability_matrix`
- `05_proof_summary`

Decision gate:
- can another operator or stakeholder see a clean line from business question to workflow output and understand what the proof does and does not establish?

If no:
- improve traceability and proof packaging before review

If yes:
- move to review

### Phase 6. Review And Decide The Next Move

Purpose:
- decide whether the package is ready to demo, needs refinement, or needs deeper rework

Inputs:
- workflow outputs
- validation evidence
- architecture assessment
- traceability matrix
- proof summary
- gap log

Decision questions:
- does the implementation answer the business questions that mattered most?
- is the output useful, not just technically correct?
- is the value story still credible after the build?
- are the remaining assumptions acceptable for a demo?
- what would have to be clarified before production design?

Possible outcomes:
- demo-ready
- refine implementation
- refine SOP
- run more discovery
- stop the slice and reframe the problem

## Decision Logic

### When To Loop Back To Discovery

Go back to discovery when:
- the problem statement is still vague
- value is unclear or unconvincing
- stakeholders disagree on what success means
- key scope boundaries are still unstable
- source ownership or operating context is missing

### When To Loop Back To Guided Capture

Go back to guided capture when:
- the conversation exists but the meaning is still messy
- confirmed vs assumed vs unknown is weak
- the first slice is not yet cleanly bounded
- the value signals are scattered rather than structured

### When To Loop Back To SOP

Go back to the SOP when:
- the build exposes missing business logic
- outputs are underspecified
- validation criteria are too weak
- source expectations are too vague to implement cleanly

### When To Stay In Build Iteration

Stay in build when:
- the objective is clear
- the rules are mostly clear
- the workflow issue is technical rather than conceptual
- a pragmatic implementation fix is available without redefining scope

## Real Exit Criteria By Phase

### Discovery Exit

Exit discovery only when:
- the business pain is clear
- the first useful outcome is clear
- the value realisation story is visible
- the trust standard is visible

### Guided Capture Exit

Exit guided capture only when:
- the first slice can be described coherently
- unknowns are explicit
- assumptions are visible enough to challenge

### SOP Exit

Exit SOP authoring only when:
- another operator could build from it
- another operator would know what not to fake
- another operator could see what still needs discovery

### Build Exit

Exit build only when:
- the workflow runs, or
- the blocker is explicitly diagnosed and recorded as a process/specification issue

## Role Split

### Consultant

Best suited for:
- leading discovery
- shaping the business problem
- testing whether the first slice matters

### Analyst Or Codex Operator

Best suited for:
- converting discovery into guided capture
- drafting the accelerator SOP
- keeping assumptions and gaps visible

### Implementation Engineer Or Codex Operator

Best suited for:
- workflow build
- data shaping
- validation
- architecture assessment grounded in runnable truth

## What Good Looks Like

A strong run through this process should produce:
- a credible first-slice problem statement
- a grounded value statement
- a clear and honest accelerator SOP
- a runnable Alteryx implementation
- evidence of what worked
- evidence of what had to be assumed
- a traceability view from requirement to implementation
- a proof summary suitable for consultant and stakeholder review
- a clear decision on what happens next

## Short Version

- discovery tells us what the client means
- guided capture tells us what that means for the work
- the SOP tells us what we can build now
- the build tells us whether the SOP was truly good enough
- the proof pack tells us what was actually demonstrated
- the review tells us whether to demo, refine, or loop back
