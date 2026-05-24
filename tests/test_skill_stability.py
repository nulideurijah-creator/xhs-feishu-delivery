from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


class SkillStabilityTests(unittest.TestCase):
    def test_skill_md_declares_mature_skill_chain(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in [
            "Required Mature Skill Chain",
            "aihot",
            "agent-reach",
            "dbs-xhs-title",
            "write-xiaohongshu",
            "humanizer-zh",
            "baoyu-image-cards",
            "imagegen",
            "Do not invent a hot topic",
        ]:
            self.assertIn(marker, text)

    def test_init_workspace_copies_diagnostics_and_baoyu_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            completed = run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "init_workspace.py"),
                    "--workspace",
                    str(workspace),
                ]
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((workspace / "diagnostics" / "doctor.py").exists())
            config = workspace / ".baoyu-skills" / "baoyu-image-cards" / "EXTEND.md"
            self.assertTrue(config.exists())
            self.assertIn("xhs-ai-hook-sketch", config.read_text(encoding="utf-8"))

    def test_generate_assets_records_chain_and_cover_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            package = json.loads(
                (workspace / "asset-generation" / "outputs" / "current-publish-assets.json").read_text(encoding="utf-8")
            )
            source_text = json.dumps(package["skill_sources"], ensure_ascii=False)
            for marker in [
                "aihot",
                "dbs-xhs-title",
                "write-xiaohongshu",
                "humanizer-zh",
                "baoyu-image-cards",
                "imagegen",
            ]:
                self.assertIn(marker, source_text)

            prompt = (
                workspace
                / "image-generation"
                / "prompts"
                / "starter-ai-tool-evaluation"
                / "01-cover.md"
            ).read_text(encoding="utf-8")
            self.assertIn("style: xhs-ai-hook-sketch", prompt)
            self.assertIn("Cover hook rules:", prompt)

    def test_doctor_reports_missing_images_without_failing_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            doctor = run([sys.executable, str(workspace / "diagnostics" / "doctor.py")], cwd=workspace)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(
                (workspace / "diagnostics" / "outputs" / "doctor-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "blocked")
            self.assertIn("images_missing:6", report["blocked_reasons"])

    def test_safety_scan_blocks_legacy_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
            (skill_dir / "render_current_cards.py").write_text("print('legacy')\n", encoding="utf-8")
            completed = run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_skill_safety.py"),
                    "--skill-dir",
                    str(skill_dir),
                ]
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forbidden file name", completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
