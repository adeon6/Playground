# Shelf Inventory Accelerator Proof

This package is a single-folder proof of the accelerator concept using the shelf inventory use case.

It is intended to demonstrate the full chain:
- consultant-to-customer discovery conversation
- guided live capture into SOP structure
- accelerator SOP suitable for build
- fully documented Alteryx workflow package
- validated outputs that satisfy the original business asks

## What Is In This Folder

- Source discovery conversation:
  - `docs/01_customer_discovery_conversation.md`
- Guided live SOP capture:
  - `docs/02_guided_sop_capture.md`
- Derived accelerator SOP:
  - `docs/03_accelerator_sop.md`
- Traceability proof:
  - `docs/04_traceability_matrix.md`
- Proof summary:
  - `docs/05_proof_summary.md`
- Data contract and architecture notes:
  - `docs/data_contract.md`
  - `docs/sop_architecture_assessment.md`
  - `docs/sop_gap_log.md`
- Runnable Alteryx assets:
  - `workflows/00_ShelfInventory_Demo_EndToEnd.yxmd`
- Generated outputs and validation evidence:
  - `data/generated/*`

## Core Scope

- Simulated SAP IS-Retail-style source tables
- External operational datasets aligned to the use case
- Deterministic data generation
- Single end-to-end workflow
- Replenishment, dashboard, and governance outputs
- Validation against deterministic reference baselines

## Primary Runnable Asset

- `workflows/00_ShelfInventory_Demo_EndToEnd.yxmd`

## Validation Status

- Demo data generation: PASS
- Single workflow engine run: PASS
- Single workflow output vs reference baseline: PASS
- Replenishment output validation: PASS
- Dashboard output validation: PASS
- Monitoring/governance output validation: PASS

## Run End To End

- `powershell -ExecutionPolicy Bypass -File .\alteryx\shelf_inventory_accelerator_proof\run_demo_pipeline.ps1`
