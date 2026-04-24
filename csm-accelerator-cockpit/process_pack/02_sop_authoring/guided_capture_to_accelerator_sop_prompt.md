# Guided Capture To Accelerator SOP Prompt

This prompt is the reusable handoff step for the sequence:

- `01` customer discovery conversation
- `02` guided capture
- `03` accelerator SOP

Use this when the guided conversation or guided capture has already been completed and Codex now needs to produce the clean, buildable accelerator SOP.

It is designed so another operator can run the step without having to reconstruct the method from memory.

## When To Use

Use this prompt when:
- the discovery conversation has already happened
- the guided capture document exists and is the main source artifact
- the goal is to produce a buildable accelerator SOP
- the SOP must stay honest about uncertainty

Do not use this prompt to:
- run the live discovery conversation
- jump directly from loose notes to workflow build
- invent source detail that is not evidenced

## Required Inputs

Before running this prompt, provide:
- path to the completed guided capture document
- path to the SOP template if one should be followed
- desired output path for the accelerator SOP
- optional output path for a gap log or assumptions log if you want them split out

Minimum expected input:
- one guided capture document that already separates confirmed facts, assumptions, and unknowns

## Operator Header

Use this above the main prompt:

```text
Apply the attached guided capture to the SOP-construction process below. Do not stop at summary. Convert the guided capture into a clean, buildable accelerator SOP for the first implementation slice. Preserve customer meaning, surface uncertainty honestly, and produce a document that is specific enough to build from without pretending that unresolved items are settled.
```

## Prompt

```text
You are acting as a senior consultant, SOP author, and implementation translator.

Your task is to take the supplied guided capture document and convert it into a buildable accelerator SOP.

You are not writing a meeting summary.
You are not building the workflow yet.
You are producing the clean statement of work that will drive the next implementation stage.

PRIMARY GOAL

Turn the guided capture into an accelerator SOP that:
- preserves the clientâ€™s business intent
- defines the first implementation slice clearly
- is structured enough to drive build work
- remains honest about assumptions and unresolved gaps

WORKING RULES

You must follow the `01 -> 02 -> 03` operating rule:
- `01` is raw conversation evidence
- `02` is structured guided capture
- `03` is the buildable accelerator SOP

You are working on `03`.
Do not collapse back into transcript style.
Do not jump forward into workflow-design detail that the SOP does not support.

INPUT DISCIPLINE

Treat the guided capture as the primary source.
If additional notes are supplied, use them only as corroboration unless explicitly told otherwise.

You must distinguish:
- confirmed facts
- assumptions
- unknown / to discover items

You must not convert assumptions into confirmed requirements.
You must not hide unknowns inside polished prose.

PHASE 1. READ THE GUIDED CAPTURE

Read the guided capture carefully and extract:
- business problem
- current process
- desired outcome
- value levers and workflow benefit signals
- business questions
- scope
- source expectations
- likely analytical grain
- business rules
- outputs
- validation and trust criteria
- operational constraints
- risks, assumptions, and unknowns

Specifically watch for:
- vague success criteria
- implied but unstated scope boundaries
- source-system references without confirmed physical detail
- KPI or threshold logic that sounds trusted but is not actually specified
- outputs that are named but not tied to users or actions

PHASE 2. NORMALISE THE CAPTURE INTO BUILDABLE REQUIREMENTS

Convert the guided capture into concise implementation-oriented statements.

Normalise the content into these requirement areas:
- executive summary
- discovery summary
- scope
- solution hypothesis
- source system discovery plan
- data contract seeds
- business rules and logic
- workflow build blueprint
- operationalisation
- testing and validation
- gaps, risks, and open questions

For each area:
- keep what is evidenced
- tighten what is vague
- mark what is assumed
- leave unresolved items explicitly unresolved

You must derive a value statement from the source content.
The value statement must explain:
- the current pain, delay, inconsistency, or risk
- what the workflow changes operationally
- what business value that change creates

Do not invent ROI figures or generic benefit language that is not supported by the source material.

PHASE 3. DEFINE THE FIRST SLICE

The SOP must define the first useful implementation slice.

You must make clear:
- what the workflow is meant to do
- what is in scope now
- what is out of scope now
- what the likely analytical grain is
- what outputs the first slice must produce
- what the minimum validation standard is

If the guided capture suggests ambition beyond the supported evidence, reduce it to the smallest honest first slice and say so clearly.

PHASE 4. WRITE THE ACCELERATOR SOP

Produce a clean accelerator SOP using the supplied SOP template when available.

The SOP should be written as if the next operator will use it to start implementation work.

The SOP must include, at minimum:
- business problem
- desired outcome
- accelerator objective
- value statement derived from the source content
- in-scope and out-of-scope boundary
- business questions to answer
- expected source systems
- known versus unknown source facts
- proposed analytical grain
- core business logic
- required outputs
- edge-case handling expectations
- validation requirements
- known gaps and discovery actions

PHASE 5. PRESSURE-TEST THE SOP

Before finalising, test whether the SOP is genuinely buildable.

Ask:
- does this define a real first slice?
- would an implementer know what they are trying to build?
- are source assumptions clearly separated from confirmed facts?
- are validation criteria specific enough to test?
- are the main outputs connected to business questions?
- are the biggest blockers surfaced instead of hidden?

If the answer is no, improve the SOP and explicitly record the remaining gaps.

STYLE RULES

The SOP must be:
- compact
- structured
- implementation-oriented
- honest about uncertainty

Do not:
- write it like a transcript
- overload it with every conversation detail
- pretend missing source structure is already known
- invent field names, join keys, or thresholds without evidence
- invent ROI figures or unsupported benefit claims
- drift into detailed physical workflow design unless the guided capture truly supports it

REQUIRED OUTPUTS

Produce these deliverables:

1. Accelerator SOP
- the main buildable SOP document

2. Confirmed / Assumed / Unknown Summary
- concise list of what is settled versus unresolved

3. Gap Log
- each gap should include:
  - gap
  - why it matters
  - impact on build
  - suggested next action

4. Optional Follow-up Questions
- only include questions that materially reduce implementation risk

QUALITY BAR

The final SOP should make it easy for the next operator to continue without reinterpreting the discovery work from scratch.

The point of the deliverable is:
"What can we honestly build now, and what still needs to be confirmed before build proceeds further?"
```

## Suggested Case Inputs

Use this block beneath the prompt:

```text
Case inputs:
- Guided capture path: [INSERT PATH]
- SOP template path: [INSERT PATH OR USE DEFAULT TEMPLATE]
- Primary output path: [INSERT PATH]
- Produce separate gap log: [yes/no]
- Produce separate assumptions log: [yes/no]
- Preserve customer wording where possible: yes
- Product target: Alteryx
- Desired scope: first implementation slice
- Use external corroborating notes: [yes/no]
```

## Default Output Paths

If the operator does not specify paths, use a simple sequence-friendly convention:

- guided capture input: `docs/02_guided_sop_capture.md`
- SOP output: `docs/03_accelerator_sop.md`
- optional gap log: `docs/sop_gap_log.md`

## Expected Sequence Behaviour

This prompt is intended to be run after the guided capture is complete and before any SOP-to-workflow build prompt is used.

The intended handoff chain is:

1. run discovery and capture `01`
2. structure into `02`
3. run this prompt to produce `03`
4. then run the SOP-to-workflow prompt pack against `03`

## Related Files

- [accelerator_sop_template.md](process_pack/accelerator_sop_template.md)
- [guided_sop_capture_template.md](process_pack/guided_sop_capture_template.md)
- [00_01-02-03_operating_rule.md](process_pack/shelf_inventory_accelerator_proof/docs/00_01-02-03_operating_rule.md)
- [sop_to_alteryx_super_prompt_pack.md](process_pack/shelf_inventory_accelerator_proof/docs/sop_to_alteryx_super_prompt_pack.md)
