from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_log(path: Path, lines: list[str]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def file_non_empty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def transcript_ready(path: Path) -> bool:
    if not file_non_empty(path):
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return "Paste the consultant-client discovery transcript here." not in text


def contains_any(path: Path, patterns: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return any(p.lower() in text.lower() for p in patterns)


@dataclass
class Stage:
    id: str
    label: str
    required_inputs: list[str]
    outputs: list[str]
    pass_checks: list[str]


class Sequencer:
    def __init__(self, project_folder: Path, config_path: Path, dry_run: bool) -> None:
        self.project_folder = project_folder.resolve()
        self.config_path = config_path.resolve()
        self.pack_root = self.config_path.parent.parent
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.dry_run = dry_run
        self.status_file = self.project_folder / self.config["artifacts"]["status_file"]
        self.log_file = self.project_folder / self.config["artifacts"]["log_file"]
        self.prompt_file = self.project_folder / self.config["artifacts"]["prompt_file"]
        self.client = None if dry_run or not os.environ.get("OPENAI_API_KEY") else OpenAI()

    def ensure_structure(self) -> None:
        for rel in self.config["project_structure"]:
            ensure_dir(self.project_folder / rel)
        if not self.log_file.exists():
            self.log_file.write_text("# Pipeline Log\n", encoding="utf-8")

    def stages(self) -> list[Stage]:
        return [Stage(**item) for item in self.config["stages"]]

    def workflow_files(self) -> list[Path]:
        pattern = self.config["artifacts"]["workflow_glob"]
        folder = self.project_folder / Path(pattern).parent
        if not folder.exists():
            return []
        return sorted(folder.glob(Path(pattern).name))

    def stage_complete(self, stage: Stage) -> bool:
        artifacts = self.config["artifacts"]
        if stage.id == "01_discovery":
            return transcript_ready(self.project_folder / self.config["entry_rule"]["canonical_transcript_markdown"])
        if stage.id == "02_guided_capture":
            out = self.project_folder / artifacts["guided_capture"]
            return file_non_empty(out) and contains_any(out, ["confirmed", "assumed", "unknown"])
        if stage.id == "03_accelerator_sop":
            sop = self.project_folder / artifacts["accelerator_sop"]
            gap = self.project_folder / artifacts["gap_log"]
            return file_non_empty(sop) and file_non_empty(gap) and contains_any(sop, ["scope", "output", "validation"])
        if stage.id == "04_workflow_build":
            assessment = self.project_folder / artifacts["architecture_assessment"]
            return bool(self.workflow_files()) and file_non_empty(assessment)
        if stage.id == "05_review":
            return file_non_empty(self.status_file)
        return False

    def next_stage(self) -> Stage | None:
        for stage in self.stages():
            if not self.stage_complete(stage):
                return stage
        return None

    def last_completed_stage(self) -> str | None:
        completed = [stage.id for stage in self.stages() if self.stage_complete(stage)]
        return completed[-1] if completed else None

    def build_stage_prompt(self, stage_id: str) -> str:
        refs = self.config["reference_files"]
        runbook = self.pack_root / refs["runbook"]
        rule = self.pack_root / refs["operating_rule"]
        interview = self.pack_root / refs["interview_script"]
        capture_template = self.pack_root / refs["guided_capture_template"]
        capture_to_sop = self.pack_root / refs["guided_capture_to_sop_prompt"]
        sop_template = self.pack_root / refs["sop_template"]
        build_pack = self.pack_root / refs["workflow_build_prompt_pack"]

        doc01 = self.project_folder / self.config["entry_rule"]["canonical_transcript_markdown"]
        doc02 = self.project_folder / self.config["artifacts"]["guided_capture"]
        doc03 = self.project_folder / self.config["artifacts"]["accelerator_sop"]
        gap = self.project_folder / self.config["artifacts"]["gap_log"]
        assessment = self.project_folder / self.config["artifacts"]["architecture_assessment"]

        if stage_id == "02_guided_capture":
            return f"""Continue the accelerator operating-system sequence for project folder:
{self.project_folder}

Use these references as the source of truth:
- Runbook: {runbook}
- Operating rule: {rule}
- Discovery interview script: {interview}
- Guided capture template: {capture_template}
- Skill: consultant-client-sop-extractor skill

Your task:
- Read the discovery transcript at {doc01}
- Produce only the next stage artifact: {doc02}
- Preserve the distinction between Confirmed, Assumed, and Unknown / To Discover
- Keep the document compact and build-oriented
- Do not generate the SOP yet
"""
        if stage_id == "03_accelerator_sop":
            return f"""Continue the accelerator operating-system sequence for project folder:
{self.project_folder}

Use these references as the source of truth:
- Runbook: {runbook}
- Operating rule: {rule}
- Guided capture to SOP prompt: {capture_to_sop}
- SOP template: {sop_template}

Your task:
- Read the guided capture at {doc02}
- Produce only these next stage artifacts:
  - {doc03}
  - {gap}
- Make the SOP buildable for the first slice
- Surface gaps honestly instead of inventing certainty
- Do not build the workflow yet
"""
        if stage_id == "04_workflow_build":
            return f"""Continue the accelerator operating-system sequence for project folder:
{self.project_folder}

Use these references as the source of truth:
- Runbook: {runbook}
- Workflow build prompt pack: {build_pack}
- Skill first: alteryx-workflow-builder skill

Your task:
- Read the SOP at {doc03}
- Build the next implementation stage
- Produce a primary workflow under the project's workflows folder matching 00_*.yxmd
- Produce or update the architecture assessment at {assessment}
- Update the gap log if implementation required new assumptions
- Validate the workflow before considering the stage complete
"""
        if stage_id == "05_review":
            return f"""Continue the accelerator operating-system sequence for project folder:
{self.project_folder}

Use these references as the source of truth:
- Runbook: {runbook}

Your task:
- Review the generated workflow, outputs, assessment, and gap log
- Decide whether the project is demo-ready, blocked, or needs iteration
- Summarize the result in the pipeline status and project log
"""
        return f"""The project folder is ready at:
{self.project_folder}

Stage 01 is the discovery evidence intake stage. Place the consultant transcript at:
{doc01}

Then rerun the sequencer.
"""

    def update_status(self, stage: Stage | None, status: str, blocker: str | None) -> None:
        payload = {
            "project_name": self.project_folder.name,
            "current_stage": None if stage is None else stage.id,
            "status": status,
            "last_completed_stage": self.last_completed_stage(),
            "next_expected_artifact": None if stage is None else stage.outputs[0],
            "started_at": (read_json(self.status_file) or {}).get("started_at", now_iso()),
            "updated_at": now_iso(),
            "blocker": blocker,
            "prompt_file": str(self.prompt_file),
            "engine": {
                "mode": "openai_api",
                "dry_run": self.dry_run,
                "api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
            },
        }
        write_json(self.status_file, payload)

    def schema_for_stage(self, stage: Stage) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": ["completed", "blocked"]},
                "blocker": {"type": ["string", "null"]},
                "artifacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
                "notes": {"type": "string"},
            },
            "required": ["status", "blocker", "artifacts", "notes"],
        }

    def execute_stage_via_api(self, stage: Stage) -> dict[str, Any]:
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is missing or dry-run mode is enabled.")

        prompt = self.prompt_file.read_text(encoding="utf-8")
        response = self.client.responses.create(
            model="gpt-5",
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "stage_result",
                    "schema": self.schema_for_stage(stage),
                    "strict": True,
                }
            },
        )
        return json.loads(response.output_text)

    def write_artifacts(self, result: dict[str, Any]) -> None:
        for artifact in result["artifacts"]:
            target = self.project_folder / artifact["path"]
            ensure_dir(target.parent)
            target.write_text(artifact["content"], encoding="utf-8")

    def run(self) -> int:
        self.ensure_structure()
        stage = self.next_stage()
        if stage is None:
            self.update_status(None, "complete", None)
            append_log(self.log_file, ["", f"## {now_iso()}", "Pipeline already complete."])
            print("Pipeline already complete.")
            return 0

        prompt = self.build_stage_prompt(stage.id)
        self.prompt_file.write_text(prompt, encoding="utf-8")

        if stage.id == "01_discovery":
            self.update_status(stage, "waiting_for_input", "Discovery transcript has not been provided yet.")
            append_log(self.log_file, ["", f"## {now_iso()}", f"- Current stage: {stage.id}", "- Runtime status: waiting_for_input", f"- Prompt written: {self.prompt_file}"])
            print(f"Current stage: {stage.id}")
            print(f"Prompt written to: {self.prompt_file}")
            return 0

        if self.client is None:
            blocker = "OPENAI_API_KEY is not set. Set it to enable unattended API execution."
            self.update_status(stage, "blocked", blocker)
            append_log(self.log_file, ["", f"## {now_iso()}", f"- Current stage: {stage.id}", "- Runtime status: blocked", f"- Blocker: {blocker}", f"- Prompt written: {self.prompt_file}"])
            print(f"Current stage: {stage.id}")
            print(f"Prompt written to: {self.prompt_file}")
            print(blocker)
            return 0

        self.update_status(stage, "running", None)
        result = self.execute_stage_via_api(stage)
        self.write_artifacts(result)

        if result["status"] != "completed":
            self.update_status(stage, "blocked", result.get("blocker"))
            append_log(self.log_file, ["", f"## {now_iso()}", f"- Current stage: {stage.id}", "- Runtime status: blocked", f"- Blocker: {result.get('blocker')}"])
            print(f"Stage blocked: {result.get('blocker')}")
            return 1

        if not self.stage_complete(stage):
            blocker = f"Stage {stage.id} completed via API but local validation did not pass."
            self.update_status(stage, "blocked", blocker)
            append_log(self.log_file, ["", f"## {now_iso()}", f"- Current stage: {stage.id}", "- Runtime status: blocked", f"- Blocker: {blocker}"])
            print(blocker)
            return 1

        append_log(self.log_file, ["", f"## {now_iso()}", f"- Current stage: {stage.id}", "- Runtime status: completed"])
        return self.run()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the accelerator operating-system sequencer via the OpenAI API.")
    parser.add_argument("--project-folder", required=True, help="Path to the project folder.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("sequence_config.json")),
        help="Path to sequence_config.json.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate prompts and status only; do not call the API.")
    args = parser.parse_args()

    runner = Sequencer(Path(args.project_folder), Path(args.config), dry_run=args.dry_run)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
