from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from csm_cockpit import services


class CockpitServicesTest(unittest.TestCase):
    def test_question_bank_has_required_sections(self) -> None:
        sections = services.load_question_bank()
        labels = {section.label for section in sections}
        self.assertIn("Business Problem", labels)
        self.assertIn("Value Realization", labels)
        self.assertIn("Source Systems", labels)
        self.assertIn("Validation / Trust", labels)
        self.assertNotIn("Known Unknowns", labels)
        self.assertNotIn("Close / Playback", labels)
        self.assertGreaterEqual(len(sections), 11)

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
        self.assertEqual(analysis["business_rules"]["status"], "missing")
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
                prompt_path = Path(tmp) / manifest["run_id"] / "status" / "codex_workflow_build_prompt.md"
                helper_path = Path(tmp) / manifest["run_id"] / "status" / "START_CODEX_WORKFLOW_BUILD.ps1"
                build_manifest_path = Path(tmp) / manifest["run_id"] / "status" / "workflow_build_manifest.json"
                self.assertTrue(prompt_path.exists())
                self.assertTrue(helper_path.exists())
                self.assertTrue(build_manifest_path.exists())
                self.assertTrue((Path(tmp) / manifest["run_id"] / "status" / "next_stage_prompt.md").exists())
                readiness = services.calculate_readiness(manifest, sections)
                self.assertEqual(readiness["workflow_gate"], "ready")
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
                manifest["capture"]["scope_priorities"]["notes"] = "Phase 1 covers one region and active products."
                manifest["capture"]["source_systems"]["notes"] = "Inputs are CSV exports from the planning system."
                manifest["capture"]["data_shape_entities"]["notes"] = "Grain is store-product-day with product and store keys."
                manifest["capture"]["business_rules"]["notes"] = "Flag high-risk exceptions above threshold."
                manifest["capture"]["output_action"]["notes"] = "Publish action list and leadership summary."
                manifest["capture"]["validation_trust"]["notes"] = "Validate against trusted operations report."
                for section in sections:
                    manifest["capture"][section.id]["status"] = "answered"
                    manifest["capture"][section.id]["approved"] = True
                manifest["analysis"] = {
                    section.id: {"status": "supported", "score": 9, "evidence": [], "summary": "Supported.", "recommendation": "Approved."}
                    for section in sections
                }
                manifest = services.generate_docs(manifest, sections)
                value_text = (Path(tmp) / manifest["run_id"] / "docs" / "04_value_statement.md").read_text(encoding="utf-8")
                use_case_text = (Path(tmp) / manifest["run_id"] / "docs" / "05_use_case_summary.md").read_text(encoding="utf-8")
                case_study_text = (Path(tmp) / manifest["run_id"] / "docs" / "06_case_study_skeleton.md").read_text(encoding="utf-8")
                self.assertIn("Reduce exception review time", value_text)
                self.assertIn("manually reconcile inventory exceptions", value_text)
                self.assertIn("Which cases should operations review first?", use_case_text)
                self.assertIn("pre-delivery draft", case_study_text)
                for artifact in ["07_accelerator_101.md", "08_accelerator_102.md", "09_accelerator_201.md"]:
                    self.assertIn(artifact, manifest["artifacts"])
                    self.assertEqual(manifest["artifacts"][artifact]["group"], "customer_facing_assets")
                self.assertEqual(manifest["peer_review"]["state"], "ready_for_peer_review")
                peer_status = json.loads((Path(tmp) / manifest["run_id"] / services.PEER_REVIEW_STATUS_ARTIFACT).read_text(encoding="utf-8"))
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
                self.assertIn("docs/03_accelerator_sop.md", prompt_text)
                self.assertIn("docs/04_value_statement.md", prompt_text)
                self.assertIn("docs/07_accelerator_101.md", prompt_text)
                self.assertIn("supporting context", prompt_text)
                self.assertIn("Alteryx workflow-builder toolkit", prompt_text)
                self.assertIn("Beautification rules", prompt_text)
                self.assertIn("spiderweb reduction", prompt_text.lower())
                self.assertIn("workflows", prompt_text)
                self.assertEqual(manifest["workflow_build"]["status"], "prompt_ready")
                build_manifest = json.loads((Path(tmp) / manifest["run_id"] / "status" / "workflow_build_manifest.json").read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
