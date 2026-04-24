from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csm_cockpit import services


class CockpitServicesTest(unittest.TestCase):
    def test_question_bank_has_required_sections(self) -> None:
        sections = services.load_question_bank()
        labels = {section.label for section in sections}
        self.assertIn("Business Problem", labels)
        self.assertIn("Inputs", labels)
        self.assertIn("Validation", labels)
        self.assertGreaterEqual(len(sections), 10)

    def test_transcript_analysis_marks_supported_and_missing_sections(self) -> None:
        sections = services.FALLBACK_SECTIONS
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
        self.assertEqual(analysis["exceptions"]["status"], "missing")

    def test_generate_docs_writes_run_folder_only(self) -> None:
        sections = services.FALLBACK_SECTIONS
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
                for artifact in services.DOC_ARTIFACTS:
                    path = Path(manifest["artifacts"][artifact]["path"])
                    self.assertTrue(path.exists(), artifact)
                    self.assertTrue(str(path).startswith(tmp))
                readiness = services.calculate_readiness(manifest, sections)
                self.assertEqual(readiness["workflow_gate"], "ready")
            finally:
                services.RUNS_DIR = original_runs_dir


if __name__ == "__main__":
    unittest.main()

