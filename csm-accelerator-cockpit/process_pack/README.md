# Accelerator Operating System

This folder is the curated home for the accelerator process files from this thread.

Use this folder when you want one clear place to start without hunting across the wider repository.

The original source files have been left in their existing locations so older references do not break.

## Start Here

Open these first:

- [accelerator_sequence_runbook.md](process_pack/00_start_here/accelerator_sequence_runbook.md)
- [00_01-02-03_operating_rule.md](process_pack/00_start_here/00_01-02-03_operating_rule.md)
- [accelerator_process_and_decision_map.md](process_pack/00_start_here/accelerator_process_and_decision_map.md)

If you only want one file to orient yourself, start with the runbook.

## Folder Structure

### `00_start_here`
- the sequence-level guidance
- the operating rule
- the runbook
- the end-to-end process and decision map

### `01_discovery`
- the guided conversation assets
- the Word template for customer discovery
- the interview script

### `01_discovery/tools`
- the script used to generate the Word discovery template

### `02_sop_authoring`
- the files used to move from guided capture to accelerator SOP
- the guided capture template
- the SOP-generation prompt
- the SOP template

### `03_workflow_build`
- the prompt pack used to turn the SOP into a runnable workflow package

### `04_reference_examples`
- example proof material to show the sequence in practice

## Recommended Working Order

1. Use [guided_discovery_conversation_template.docx](process_pack/01_discovery/guided_discovery_conversation_template.docx)
2. Follow [accelerator_interview_script.md](process_pack/01_discovery/accelerator_interview_script.md)
3. Create the guided capture using [guided_sop_capture_template.md](process_pack/02_sop_authoring/guided_sop_capture_template.md)
4. Generate the SOP using [guided_capture_to_accelerator_sop_prompt.md](process_pack/02_sop_authoring/guided_capture_to_accelerator_sop_prompt.md)
5. Start workflow build with the `Large` section in [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
6. Package the proof into `04_traceability_matrix.md` and `05_proof_summary.md`

## Non-Negotiable Build Order

For any workflow build, use this stack in order:

1. `Large` in [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
2. project `03_accelerator_sop.md`
3. project planning files such as `workflow_plan.md`, `source_inventory.md`, `join_map.md`, `synthetic_data_plan.md`, `output_contract.md`
4. project `sop_gap_log.md`
5. local project data context
6. build with `alteryx-workflow-builder`
7. beautify with `alteryx-beautification`
8. rerun validation after beautification

Do not skip the `Large` prompt.
Do not start from the SOP alone.
Do not sign off a workflow before the beautification pass.

## What Is In This Pack

- [accelerator_sequence_runbook.md](process_pack/00_start_here/accelerator_sequence_runbook.md)
- [guided_discovery_conversation_template.docx](process_pack/01_discovery/guided_discovery_conversation_template.docx)
- [accelerator_interview_script.md](process_pack/01_discovery/accelerator_interview_script.md)
- [generate_guided_conversation_doc.py](process_pack/01_discovery/tools/generate_guided_conversation_doc.py)
- [guided_sop_capture_template.md](process_pack/02_sop_authoring/guided_sop_capture_template.md)
- [guided_capture_to_accelerator_sop_prompt.md](process_pack/02_sop_authoring/guided_capture_to_accelerator_sop_prompt.md)
- [accelerator_sop_template.md](process_pack/02_sop_authoring/accelerator_sop_template.md)
- [sop_to_alteryx_super_prompt_pack.md](process_pack/03_workflow_build/sop_to_alteryx_super_prompt_pack.md)
- [shelf_inventory_accelerator_proof_README.md](process_pack/04_reference_examples/shelf_inventory_accelerator_proof_README.md)

## Suggested Next Improvement

If you want this even cleaner, the next step would be to create a matching starter project skeleton under this folder so every new accelerator begins from the same ready-made `docs`, `data`, and `workflows` layout.
