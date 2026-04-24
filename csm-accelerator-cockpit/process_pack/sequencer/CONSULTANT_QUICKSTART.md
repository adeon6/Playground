# Consultant Quickstart

This is the simplest way a consultant should use the accelerator sequencer.

## What You Do

1. Create or choose a project folder.
2. Put the client conversation transcript in:
   - `docs/01_customer_discovery_conversation.md`
3. Run:

```powershell
.\sequencer\run_accelerator_sequence.ps1 -ProjectFolder "<project-folder>"
```

Or, for the fully unattended API-based path:

```powershell
python .\sequencer\run_accelerator_sequence.py --project-folder "<project-folder>"
```

## What Happens Next

The sequencer will:

1. confirm the project folders exist
2. detect the next missing stage
3. write the next-stage execution prompt to:
   - `status/next_stage_prompt.md`
4. update:
   - `status/pipeline_status.json`
   - `status/pipeline_log.md`

## What â€œDoneâ€ Looks Like

The target sequence is:

- `docs/01_customer_discovery_conversation.md`
- `docs/02_guided_sop_capture.md`
- `docs/03_accelerator_sop.md`
- `docs/sop_gap_log.md`
- `docs/sop_architecture_assessment.md`
- `workflows/00_<project_name>.yxmd`

## Runtime Notes

- The PowerShell sequencer is a local orchestration scaffold and status/prompt generator.
- The Python sequencer is the fully unattended path and uses the OpenAI API.
- To enable unattended API execution, set `OPENAI_API_KEY` before running the Python sequencer.

## Consultant Experience In Plain English

For a consultant, this should feel like:

1. drop the transcript in the project folder
2. run one command
3. open the status file if something blocks
4. otherwise keep following the next-stage output

The consultant should not need to remember the `01 -> 02 -> 03 -> 04 -> 05` method by memory. The sequencer carries that discipline for them.
