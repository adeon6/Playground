from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from csm_cockpit.app import app
from csm_cockpit import services


class CockpitServicesTest(unittest.TestCase):
    def test_question_bank_has_required_sections(self) -> None:
        sections = services.load_question_bank()
        labels = [section.label for section in sections]
        self.assertEqual(
            labels,
            [
                "Business Problem",
                "Current Process",
                "Desired Outcome",
                "Value Realisation",
                "Business Questions",
                "Scope",
                "Inputs, Sources, And Ownership",
                "Rules, Logic, And Definitions",
                "Exceptions And Safe Handling",
                "Validation And Trust",
                "Operational Readiness And Phasing",
            ],
        )
        self.assertNotIn("Opening", labels)
        self.assertNotIn("Operational Constraints", labels)
        self.assertNotIn("Close And Playback", labels)
        self.assertTrue(all(section.questions for section in sections))

    def test_transcript_analysis_marks_supported_and_missing_sections(self) -> None:
        sections = services.JON_SECTIONS
        text = """
        The customer has a manual process today where analysts use spreadsheets and extracts
        from source systems. The desired output is a dashboard and action list that supports
        prioritisation decisions. The team will validate the result by reconciling it to a
        trusted report and checking the output with the business owner.
        """
        capture = {section.id: {"status": "answered"} for section in sections}
        analysis = services.analyze_transcript_text(text, sections, capture)
        self.assertIn(analysis["current_process"]["status"], {"supported", "weak_evidence"})
        self.assertIn(analysis["desired_outcome"]["status"], {"supported", "weak_evidence"})
        self.assertEqual(analysis["rules_logic_definitions"]["status"], "missing")
        self.assertIn("summary", analysis["current_process"])

    def test_value_realization_detects_short_heading_style_transcript(self) -> None:
        sections = services.JON_SECTIONS
        text = """
        Customer:
        "Yes. If we can get that far quickly, that proves the approach."
        10. Value Realization
        Consultant:
        "How would you quantify success?"
        Customer:
        "It should halve the time taken to create the prioritised lists"
        """
        capture = {section.id: {"status": "answered"} for section in sections}
        analysis = services.analyze_transcript_text(text, sections, capture)
        self.assertEqual(analysis["value_realization"]["status"], "supported")
        self.assertGreaterEqual(analysis["value_realization"]["score"], 6)

    def test_markdown_transcript_is_canonicalized_into_project_docs(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp) / "runs"
            transcript = Path(tmp) / "demo.md"
            transcript.write_text("The business problem is manual work. The source system exports a file.", encoding="utf-8")
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                services.save_manifest(manifest)
                manifest = services.attach_transcript_from_path(manifest, transcript, sections)
                services.save_manifest(manifest)
                canonical = Path(manifest["transcript"]["canonical_path"])
                self.assertTrue(canonical.exists())
                self.assertTrue(str(canonical).startswith(str(services.RUNS_DIR)))
                self.assertEqual(canonical.name, "01_customer_discovery_conversation.md")
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_new_project_defaults_statuses_to_not_set(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                self.assertTrue(all(manifest["capture"][section.id]["status"] == "not_set" for section in sections))
                self.assertTrue(all(not manifest["capture"][section.id]["approved"] for section in sections))
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_follow_up_transcripts_are_additive(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp) / "runs"
            first = Path(tmp) / "first.md"
            second = Path(tmp) / "follow-up.md"
            first.write_text("The business problem is manual work and slow prioritisation.", encoding="utf-8")
            second.write_text("Value Realization: success means halving the time taken and measuring hours saved.", encoding="utf-8")
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                services.save_manifest(manifest)
                manifest = services.attach_transcript_from_path(manifest, first, sections)
                manifest = services.attach_transcript_from_path(manifest, second, sections)
                canonical = Path(manifest["transcript"]["canonical_path"]).read_text(encoding="utf-8")
                self.assertEqual(len(manifest["transcripts"]), 2)
                self.assertIn("Transcript Source 1", canonical)
                self.assertIn("Transcript Source 2", canonical)
                self.assertIn("follow-up.md", canonical)
                self.assertIn(manifest["analysis"]["value_realization"]["status"], {"supported", "weak_evidence"})
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_project_scaffold_uses_jon_operating_system_folders(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                services.save_manifest(manifest)
                project_dir = Path(tmp) / manifest["run_id"]
                expected = [
                    "00_start_here",
                    "01_discovery",
                    "02_sop_authoring",
                    "03_workflow_build",
                    "04_reference_examples",
                    "sequencer",
                    "tooling",
                ]
                for folder in expected:
                    self.assertTrue((project_dir / folder).exists(), folder)
                self.assertTrue((project_dir / "00_start_here" / "README_process_pack.md").exists())
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_generate_docs_writes_run_folder_only(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["notes"] = f"{section.label} notes"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "recommendation": "Evidence is strong enough for CSM review."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                for artifact in [*services.DOC_ARTIFACTS, *services.ACCELERATOR_ASSET_ARTIFACTS, services.PEER_REVIEW_STATUS_ARTIFACT]:
                    path = Path(manifest["artifacts"][artifact]["path"])
                    self.assertTrue(path.exists(), artifact)
                    self.assertTrue(str(path).startswith(tmp))
                prompt_path = Path(manifest["artifacts"][services.WORKFLOW_PROMPT_ARTIFACT]["path"])
                helper_path = Path(manifest["artifacts"][services.WORKFLOW_HELPER_ARTIFACT]["path"])
                build_manifest_path = Path(manifest["artifacts"][services.WORKFLOW_MANIFEST_ARTIFACT]["path"])
                self.assertTrue(prompt_path.exists())
                self.assertTrue(helper_path.exists())
                self.assertTrue(build_manifest_path.exists())
                prompt_text = prompt_path.read_text(encoding="utf-8")
                self.assertIn("Mandatory Local Tooling Gate", prompt_text)
                self.assertIn("tooling/tooling_manifest.json", prompt_text)
                self.assertIn("project-local tooling wins", prompt_text)
                self.assertTrue((Path(tmp) / manifest["run_id"] / "tooling" / "tooling_manifest.json").exists())
                self.assertTrue((Path(tmp) / manifest["run_id"] / "03_workflow_build" / "status" / "next_stage_prompt.md").exists())
                readiness = services.calculate_readiness(manifest, sections)
                self.assertEqual(readiness["workflow_gate"], "ready")
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_generate_docs_uses_one_final_readiness_snapshot(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["notes"] = f"{section.label} notes"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "summary": "Supported.", "recommendation": "Approved."}
                    for section in sections
                }

                manifest = services.generate_docs(manifest, sections)
                readiness = services.calculate_readiness(manifest, sections)
                sop_text = Path(manifest["artifacts"]["03_accelerator_sop.md"]["path"]).read_text(encoding="utf-8")
                assessment_text = Path(manifest["artifacts"]["sop_architecture_assessment.md"]["path"]).read_text(encoding="utf-8")
                pipeline_status = json.loads(Path(manifest["artifacts"][services.PIPELINE_STATUS_ARTIFACT]["path"]).read_text(encoding="utf-8"))

                self.assertEqual(readiness["workflow_gate"], "ready")
                self.assertEqual(readiness["overall_pct"], 100)
                self.assertEqual(readiness["artifact_pct"], 100)
                self.assertIn("Current gate status: **ready**", sop_text)
                self.assertIn("Overall readiness: **100%**", sop_text)
                self.assertNotIn("Current gate status: **blocked**", sop_text)
                self.assertNotIn("Generated document chain is incomplete.", sop_text)
                self.assertIn("Artifact readiness: 100%", assessment_text)
                self.assertEqual(pipeline_status["readiness"]["workflow_gate"], readiness["workflow_gate"])
                self.assertEqual(pipeline_status["readiness"]["overall_pct"], readiness["overall_pct"])
                self.assertEqual(pipeline_status["readiness"]["artifact_pct"], readiness["artifact_pct"])
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_transcript_evidence_is_advisory_not_workflow_blocking(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["notes"] = f"{section.label} notes"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "missing", "score": 0, "evidence": [], "summary": "No transcript support.", "recommendation": "CSM may keep as approved fact."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                readiness = services.calculate_readiness(manifest, sections)
                self.assertEqual(readiness["workflow_gate"], "ready")
                self.assertFalse(any("transcript answer" in blocker for blocker in readiness["blockers"]))
                gap_log = Path(manifest["artifacts"]["sop_gap_log.md"]["path"]).read_text(encoding="utf-8")
                self.assertIn("| None |", gap_log)
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_generate_docs_creates_james_accelerator_assets(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Inventory Accelerator", "Ada", sections)
                manifest["capture"]["business_problem"]["notes"] = "Teams manually reconcile inventory exceptions and lose time prioritising action."
                manifest["capture"]["value_realization"]["notes"] = "Reduce exception review time from 10 hours to 5 hours and measure hours saved weekly."
                manifest["capture"]["desired_outcome"]["notes"] = "Create a ranked action list for operations."
                manifest["capture"]["business_questions"]["notes"] = "Which cases should operations review first?"
                manifest["capture"]["scope"]["notes"] = "Phase 1 covers one region and active products."
                manifest["capture"]["inputs_sources_ownership"]["notes"] = "Inputs are CSV exports from the planning system at store-product-day grain."
                manifest["capture"]["rules_logic_definitions"]["notes"] = "Flag high-risk exceptions above threshold."
                manifest["capture"]["exceptions_safe_handling"]["notes"] = "Questionable records are flagged for review."
                manifest["capture"]["desired_outcome"]["notes"] = "Publish action list and leadership summary."
                manifest["capture"]["validation_trust"]["notes"] = "Validate against trusted operations report."
                manifest["capture"]["operational_readiness_phasing"]["notes"] = "Phase 1 can be manual; scheduling is later."
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "summary": "Supported.", "recommendation": "Approved."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                value_text = Path(manifest["artifacts"]["04_value_statement.md"]["path"]).read_text(encoding="utf-8")
                use_case_text = Path(manifest["artifacts"]["05_use_case_summary.md"]["path"]).read_text(encoding="utf-8")
                case_study_text = Path(manifest["artifacts"]["06_case_study_skeleton.md"]["path"]).read_text(encoding="utf-8")
                self.assertIn("Reduce exception review time", value_text)
                self.assertIn("manually reconcile inventory exceptions", value_text)
                self.assertIn("Which cases should operations review first?", use_case_text)
                self.assertIn("pre-delivery draft", case_study_text)
                for artifact in ["07_accelerator_101.md", "08_accelerator_102.md", "09_accelerator_201.md"]:
                    self.assertIn(artifact, manifest["artifacts"])
                    self.assertEqual(manifest["artifacts"][artifact]["group"], "customer_facing_assets")
                self.assertEqual(manifest["peer_review"]["state"], "ready_for_peer_review")
                peer_status = json.loads(Path(manifest["artifacts"][services.PEER_REVIEW_STATUS_ARTIFACT]["path"]).read_text(encoding="utf-8"))
                self.assertTrue(peer_status["ready_for_peer_review"])
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_workflow_handoff_prompt_is_hydrated_and_beautification_aware(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["notes"] = f"{section.label} notes"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "recommendation": "Evidence is strong enough for CSM review."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                prompt_path = Path(manifest["artifacts"][services.WORKFLOW_PROMPT_ARTIFACT]["path"])
                prompt_text = prompt_path.read_text(encoding="utf-8")
                self.assertNotIn("[INSERT PATH]", prompt_text)
                self.assertNotIn("[INSERT SOURCE STYLE]", prompt_text)
                self.assertNotIn("Project root: `.`", prompt_text)
                self.assertIn("Mandatory Identity And Path Gate", prompt_text)
                self.assertIn(str((Path(tmp) / manifest["run_id"]).resolve()), prompt_text)
                self.assertIn("Do not search parent folders", prompt_text)
                self.assertIn("02_sop_authoring/03_accelerator_sop.md", prompt_text)
                self.assertIn("04_reference_examples/accelerator_assets/04_value_statement.md", prompt_text)
                self.assertIn("04_reference_examples/accelerator_assets/07_accelerator_101.md", prompt_text)
                self.assertIn("supporting context", prompt_text)
                self.assertIn("Alteryx workflow-builder toolkit", prompt_text)
                self.assertIn("Beautification rules", prompt_text)
                self.assertIn("customer-facing hybrid reference", prompt_text.lower())
                self.assertIn("do not bypass the approved SOP/doc chain", prompt_text)
                self.assertIn("Do not copy these from the hybrid reference workflow", prompt_text)
                self.assertIn("visual grammar only", prompt_text)
                self.assertIn("spiderweb reduction", prompt_text.lower())
                self.assertIn("03_workflow_build/workflows", prompt_text)
                self.assertEqual(manifest["workflow_build"]["status"], "prompt_ready")
                build_manifest = json.loads(Path(manifest["artifacts"][services.WORKFLOW_MANIFEST_ARTIFACT]["path"]).read_text(encoding="utf-8"))
                self.assertEqual(build_manifest["run_id"], manifest["run_id"])
                self.assertEqual(build_manifest["canonical_project_root"], str((Path(tmp) / manifest["run_id"]).resolve()))
                self.assertEqual(build_manifest["project_identity_hash"], manifest["project_identity"]["identity_hash"])
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_codex_detection_checks_launch_command_not_open_session(self) -> None:
        with patch("csm_cockpit.services.shutil.which", side_effect=lambda command: r"C:\Tools\codex.exe" if command == "codex" else None):
            preflight = services.detect_workflow_environment()
        self.assertTrue(preflight["codex_detected"])
        self.assertEqual(preflight["codex_path"], r"C:\Tools\codex.exe")
        self.assertIn("Launch command", preflight["codex_detection_note"])

    def test_codex_detection_has_clear_missing_note(self) -> None:
        with patch("csm_cockpit.services.shutil.which", return_value=None), patch("csm_cockpit.services.Path.exists", return_value=False):
            preflight = services.detect_workflow_environment()
        self.assertFalse(preflight["codex_detected"])
        self.assertIn("already-open Codex chat cannot be detected", preflight["codex_detection_note"])

    def test_manifest_migration_maps_old_keys_to_v44_sections(self) -> None:
        manifest = {"capture": {}}
        manifest["capture"]["scope_priorities"] = {"status": "answered", "notes": "Old scope notes", "approved": True}
        manifest["capture"]["source_systems"] = {"status": "partial", "notes": "Old source notes", "approved": False}
        manifest["capture"]["data_shape_entities"] = {"status": "answered", "notes": "Old entity notes", "approved": True}
        manifest["capture"]["business_rules"] = {"status": "answered", "notes": "Old rule notes", "approved": True}
        manifest["capture"]["output_action"] = {"status": "answered", "notes": "Old output notes", "approved": True}
        manifest["capture"]["operational_constraints"] = {"status": "partial", "notes": "Old ops notes", "approved": False}
        manifest["capture"]["validation_trust"] = {"status": "", "notes": "Validation notes", "approved": False}

        migrated = services.migrate_manifest_sections(manifest, services.JON_SECTIONS)
        self.assertNotIn("scope_priorities", migrated["capture"])
        self.assertIn("Old scope notes", migrated["capture"]["scope"]["notes"])
        self.assertIn("Old source notes", migrated["capture"]["inputs_sources_ownership"]["notes"])
        self.assertIn("Old entity notes", migrated["capture"]["inputs_sources_ownership"]["notes"])
        self.assertIn("Old rule notes", migrated["capture"]["rules_logic_definitions"]["notes"])
        self.assertIn("Old output notes", migrated["capture"]["desired_outcome"]["notes"])
        self.assertIn("Old ops notes", migrated["capture"]["operational_readiness_phasing"]["notes"])
        self.assertEqual(migrated["capture"]["validation_trust"]["status"], "not_set")

    def test_readiness_metrics_do_not_expose_top_level_evidence_pct(self) -> None:
        sections = services.JON_SECTIONS
        manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
        readiness = services.calculate_readiness(manifest, sections)
        self.assertIn("capture_pct", readiness)
        self.assertIn("approval_pct", readiness)
        self.assertIn("artifact_pct", readiness)
        self.assertNotIn("evidence_pct", readiness)
        self.assertFalse(readiness["generation_ready"])
        self.assertIn("status not selected", readiness["blockers"][0])
        self.assertTrue(readiness["blocker_items"][0]["section_id"])

    def test_not_answered_is_selected_but_not_workflow_ready(self) -> None:
        sections = services.JON_SECTIONS
        manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
        for section in sections:
            manifest["capture"][section.id]["status"] = "answered"
            manifest["capture"][section.id]["approved"] = True
        manifest["capture"]["business_problem"]["status"] = "not_answered"
        readiness = services.calculate_readiness(manifest, sections)
        self.assertTrue(readiness["generation_ready"])
        self.assertIn("Business Problem: capture is No answer.", readiness["blockers"])

    def test_generated_docs_use_v44_section_names(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["notes"] = f"{section.label} notes"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "summary": "Supported.", "recommendation": "Approved."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                sop_text = Path(manifest["artifacts"]["03_accelerator_sop.md"]["path"]).read_text(encoding="utf-8")
                assessment_text = Path(manifest["artifacts"]["sop_architecture_assessment.md"]["path"]).read_text(encoding="utf-8")
                self.assertIn("Operational Readiness And Phasing", sop_text)
                self.assertIn("Value Realisation", sop_text)
                self.assertNotIn("Operational Constraints", sop_text)
                self.assertNotIn("Opening", sop_text)
                self.assertNotIn("Transcript evidence readiness", assessment_text)
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_autosave_endpoint_updates_section_and_readiness(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                transcript = Path(tmp) / "transcript.md"
                transcript.write_text("The business problem is manual work that causes delay and risk.", encoding="utf-8")
                services.save_manifest(manifest)
                manifest = services.attach_transcript_from_path(manifest, transcript, sections)
                services.save_manifest(manifest)
                client = TestClient(app)
                response = client.post(
                    f"/runs/{manifest['run_id']}/section/business_problem",
                    json={"status": "answered", "notes": "Manual work causes delay.", "approved": True},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertTrue(payload["approved"])
                self.assertEqual(payload["capture_status"], "answered")
                self.assertNotIn("evidence_pct", payload["readiness"])
                updated = services.load_manifest(manifest["run_id"])
                self.assertEqual(updated["capture"]["business_problem"]["notes"], "Manual work causes delay.")
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_ui_smoke_shows_v51_guided_flow(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                services.save_manifest(manifest)
                client = TestClient(app)
                response = client.get(f"/?run_id={manifest['run_id']}")
                self.assertEqual(response.status_code, 200)
                html = response.text
                self.assertIn("Accelerator Cockpit", html)
                self.assertIn("Internal Guided UI / V5.4", html)
                self.assertIn("Capture And Approval", html)
                self.assertIn("Discovery questions", html)
                self.assertIn("Review snippets (0)", html)
                self.assertIn("Next action", html)
                self.assertIn('data-role="next-action-message"', html)
                self.assertIn("Handoff files", html)
                self.assertIn("Generate / Refresh Handoff Files", html)
                self.assertIn("Approve for SOP handoff", html)
                self.assertIn("status-topline", html)
                self.assertIn('rows="1"', html)
                self.assertIn('type="radio"', html)
                self.assertIn("not_set", html)
                self.assertIn("disabled", html)
                self.assertIn("blocker-link", html)
                self.assertIn("data-jump-section", html)
                self.assertNotIn("CSM Accelerator", html)
                self.assertNotIn("Jon", html)
                self.assertNotIn("Download Helper", html)
                self.assertNotIn("Codex launch", html)
                self.assertNotIn("does not contain Codex", html)
                self.assertNotIn("Artifact Dashboard", html)
                self.assertNotIn("Human Approval", html)
                self.assertNotIn("Save Capture", html)
                self.assertNotIn("Save Approvals", html)
                self.assertNotIn("Generate / Refresh Workflow Handoff", html)
            finally:
                services.RUNS_DIR = original_runs_dir

    def test_autosave_collapse_only_for_approval_confirmation(self) -> None:
        sections = services.JON_SECTIONS
        with tempfile.TemporaryDirectory() as tmp:
            original_runs_dir = services.RUNS_DIR
            services.RUNS_DIR = Path(tmp)
            try:
                manifest = services.new_manifest("Test Customer", "Test Accelerator", "Ada", sections)
                services.save_manifest(manifest)
                client = TestClient(app)
                status_response = client.post(
                    f"/runs/{manifest['run_id']}/section/business_problem",
                    json={"status": "answered", "notes": "", "approved": False, "changed_field": "status"},
                )
                self.assertEqual(status_response.status_code, 200)
                self.assertFalse(status_response.json()["auto_collapse"])

                approval_response = client.post(
                    f"/runs/{manifest['run_id']}/section/business_problem",
                    json={"status": "answered", "notes": "", "approved": True, "changed_field": "approved"},
                )
                self.assertEqual(approval_response.status_code, 200)
                self.assertTrue(approval_response.json()["auto_collapse"])

                unapproval_response = client.post(
                    f"/runs/{manifest['run_id']}/section/business_problem",
                    json={"status": "answered", "notes": "", "approved": False, "changed_field": "approved"},
                )
                self.assertEqual(unapproval_response.status_code, 200)
                self.assertFalse(unapproval_response.json()["auto_collapse"])
            finally:
                services.RUNS_DIR = original_runs_dir


if __name__ == "__main__":
    unittest.main()
