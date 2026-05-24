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
            "content-strategy",
            "hv-analysis",
            "insight_pack",
            "dbs-xhs-title",
            "references/editor_prompt.md",
            "write-xiaohongshu",
            "humanizer-zh",
            "baoyu-image-cards",
            "imagegen",
            "Do not invent a hot topic",
        ]:
            self.assertIn(marker, text)

    def test_editor_prompt_enforces_natural_creator_voice(self) -> None:
        text = (ROOT / "references" / "editor_prompt.md").read_text(encoding="utf-8")
        for marker in [
            "真人博主",
            "不要把干货写成清单模板",
            "工具说明书",
            "如果读起来像 AI 在解释，请重写",
            "它做的事很直接",
            "这个数据仅是一个参考",
            "我会把它放在三个场景里用",
            "Accepted Voice Target",
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
            self.assertIn("xhs-warm-cute-open-source", config.read_text(encoding="utf-8"))

    def test_generate_assets_records_chain_and_cover_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["project_facts"] = {
                "name": "models.dev",
                "repo": "github.com/vercel/ai",
                "github_stars": "4.1k stars",
                "license": "MIT",
                "open_source": "true",
            }
            spec["source_urls"] = ["https://github.com/vercel/ai"]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            package = json.loads(
                (workspace / "asset-generation" / "outputs" / "current-publish-assets.json").read_text(encoding="utf-8")
            )
            source_text = json.dumps(package["skill_sources"], ensure_ascii=False)
            for marker in [
                "aihot",
                "agent-reach",
                "content-strategy",
                "hv-analysis-light",
            "dbs-xhs-title",
            "editor_prompt",
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
            self.assertIn("style: xhs-warm-cute-open-source", prompt)
            self.assertIn("Cover hook rules:", prompt)
            self.assertIn("Project name: models.dev", prompt)
            self.assertIn("GitHub stars: 4.1k stars", prompt)
            self.assertIn("central GitHub-style project card", prompt)

            copy = (
                workspace / "asset-generation" / "outputs" / "current-copy.md"
            ).read_text(encoding="utf-8")
            self.assertIn("洞察包摘要", copy)
            self.assertIn("内容类型：ai_product_release", copy)
            self.assertEqual(package["content_type"], "ai_product_release")
            self.assertIn("insight_pack", package)

    def test_generate_assets_rejects_missing_insight_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec.pop("insight_pack", None)
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("content_spec missing", generated.stderr + generated.stdout)

    def test_generate_assets_rejects_weak_source_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["insight_pack"]["source_facts"] = [
                {"claim": "只有一条来源事实。", "source_url": "https://example.com/source"}
            ]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("source_facts", generated.stderr + generated.stdout)

    def test_generate_assets_rejects_template_voice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["body_full"] = "它最适合三类人。这个工具值得关注。我会把它放在三个场景里用。总结一下，AI 工具要看长期价值。"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("body contains forbidden phrases", generated.stderr + generated.stdout)

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
