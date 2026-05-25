from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def legacy_terms() -> list[str]:
    return [
        "dbs-" + "xhs-title",
        "insight" + "_pack",
        "actionable" + "_framework",
        "title" + "_candidates",
        "editor" + "_prompt",
    ]


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


def write_smoke_spec(workspace: Path) -> dict:
    spec = {
        "review_id": "publish-smoke-test",
        "content_id": "smoke-ai-tool-evaluation",
        "title": "这个工具有点顺",
        "topic": "Smoke test topic",
        "summary": "Smoke test fixture for packaging.",
        "hot_source": "smoke-test",
        "source_urls": ["https://example.com/ai-tool", "https://example.com/ai-tool-docs"],
        "source_verification": {
            "source": "smoke test fixture",
            "checked_at": "2026-05-25T00:00:00+08:00",
        },
        "writing_brief": {
            "facts": [
                {"claim": "Smoke fact one.", "source_url": "https://example.com/ai-tool"},
                {"claim": "Smoke fact two.", "source_url": "https://example.com/ai-tool-docs"},
            ],
            "do_not_say": ["Do not use formula-title language."],
        },
        "project_facts": {},
        "body_full": (
            "我最近在做一个 agent demo, 最烦的是流程跑起来以后才发现前面理解歪了。"
            "这个小工具让我停了一下, 因为它没有急着堆功能, 而是先把任务拆分和状态看清楚。"
            "这点不算炫, 但对每天调工具的人挺实际。"
        ),
        "tags": ["AI工具", "开发工具", "Agent", "效率工具", "开源项目"],
        "image_slug": "smoke-test",
        "pages": [
            {
                "page_id": "01-cover",
                "title": "这个工具有点顺",
                "subtitle": "先看能不能进流程",
                "visual": "A creator comparing a shiny demo screen with a real work desk.",
            },
            {"page_id": "02-gap", "title": "Smoke Page 2", "subtitle": "Fixture only", "visual": "A simple smoke test placeholder card."},
            {"page_id": "03-task", "title": "Smoke Page 3", "subtitle": "Fixture only", "visual": "A simple smoke test placeholder card."},
            {"page_id": "04-output", "title": "Smoke Page 4", "subtitle": "Fixture only", "visual": "A simple smoke test placeholder card."},
            {"page_id": "05-rework", "title": "Smoke Page 5", "subtitle": "Fixture only", "visual": "A simple smoke test placeholder card."},
            {"page_id": "06-save", "title": "Smoke Page 6", "subtitle": "Fixture only", "visual": "A simple smoke test placeholder card."},
        ],
    }
    path = workspace / "asset-generation" / "content_spec.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return spec


class SkillStabilityTests(unittest.TestCase):
    def test_skill_md_declares_clean_model_writing_chain(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in [
            "Mature Research + Model Writing Chain",
            "aihot",
            "agent-reach",
            "writing_brief",
            "references/creator_prompt.md",
            "baoyu-image-cards",
            "imagegen",
            "Do not invent a hot topic",
            "sent history",
            "--check-history",
            "content-history/sent-posts.jsonl",
            "Do not ask the user to choose image watermark",
            "--yes",
        ]:
            self.assertIn(marker, text)
        for term in legacy_terms():
            self.assertNotIn(term, text)

    def test_creator_prompt_is_the_only_copy_prompt(self) -> None:
        prompt_path = ROOT / "references" / "creator_prompt.md"
        self.assertTrue(prompt_path.exists())
        self.assertFalse((ROOT / "references" / ("editor" + "_prompt.md")).exists())
        text = prompt_path.read_text(encoding="utf-8")
        for marker in [
            "小红书垂直领域爆款博主",
            "GitHub 开源生态",
            "`writing_brief`",
            "只用这份提示词生成最终",
            "AI 圈内热点资讯",
            "GitHub 高星开源项目",
            "轻松唠嗑风",
            "用词禁令",
            "Final output must be publishable title, body, and tags only.",
        ]:
            self.assertIn(marker, text)
        for term in legacy_terms():
            self.assertNotIn(term, text)

    def test_image_generation_contract_uses_noninteractive_baoyu_defaults(self) -> None:
        text = (ROOT / "references" / "image_generation.md").read_text(encoding="utf-8")
        for marker in [
            "watermark: none",
            "xhs-warm-cute-open-source",
            "layout: `balanced`",
            "palette: `macaron`",
            "backend: `imagegen`",
            "confirmation: skipped",
            "Do not ask the user to pick",
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
            self.assertTrue((workspace / "automation-lock" / "automation_lock.py").exists())
            self.assertFalse((workspace / "asset-generation" / "content_spec.json").exists())
            config = workspace / ".baoyu-skills" / "baoyu-image-cards" / "EXTEND.md"
            self.assertTrue(config.exists())
            self.assertIn("xhs-warm-cute-open-source", config.read_text(encoding="utf-8"))

    def test_automation_lock_blocks_second_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            lock_script = workspace / "automation-lock" / "automation_lock.py"
            first = run([sys.executable, str(lock_script), "--acquire", "--owner", "first"], cwd=workspace)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = run([sys.executable, str(lock_script), "--acquire", "--owner", "second"], cwd=workspace)
            self.assertEqual(second.returncode, 2)
            self.assertIn('"status": "busy"', second.stdout)
            release = run([sys.executable, str(lock_script), "--release", "--owner", "first"], cwd=workspace)
            self.assertEqual(release.returncode, 0, release.stderr)

    def test_generate_assets_records_model_writing_chain_and_cover_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = write_smoke_spec(workspace)
            spec["project_facts"] = {
                "name": "models.dev",
                "repo": "github.com/vercel/ai",
                "github_stars": "4.1k stars",
                "license": "MIT",
                "open_source": "true",
            }
            spec["source_urls"] = ["https://github.com/vercel/ai"]
            spec["writing_brief"]["facts"] = [
                {"claim": "models.dev lists AI model API metadata.", "source_url": "https://github.com/vercel/ai"},
                {"claim": "The project is open source.", "source_url": "https://github.com/vercel/ai"},
            ]
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
                "creator_prompt.md",
                "baoyu-image-cards",
                "imagegen",
                "image_defaults",
                "--yes",
            ]:
                self.assertIn(marker, source_text)
            for term in legacy_terms():
                self.assertNotIn(term, json.dumps(package, ensure_ascii=False))

            prompt = (
                workspace
                / "image-generation"
                / "prompts"
                / "smoke-test"
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
            self.assertIn("事实素材摘要", copy)
            self.assertNotIn("洞察包摘要", copy)
            self.assertIn("writing_brief", package)

    def test_generate_assets_rejects_missing_writing_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = write_smoke_spec(workspace)
            spec.pop("writing_brief", None)
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
            spec = write_smoke_spec(workspace)
            spec["writing_brief"]["facts"] = [
                {"claim": "Only one source-backed fact.", "source_url": "https://example.com/source"}
            ]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("writing_brief.facts", generated.stderr + generated.stdout)

    def test_generate_assets_rejects_stale_cover_title_after_copy_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = write_smoke_spec(workspace)
            spec["pages"][0]["title"] = "旧封面标题"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("cover page title must match current title", generated.stderr + generated.stdout)

    def test_deepseek_copy_syncs_cover_title(self) -> None:
        module_path = ROOT / "assets" / "workspace-template" / "asset-generation" / "write_copy_deepseek.py"
        spec = importlib.util.spec_from_file_location("write_copy_deepseek", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = {"title": "新标题", "pages": [{"page_id": "01-cover", "title": "旧标题"}]}
        self.assertTrue(module.sync_cover_page(payload))
        self.assertEqual(payload["pages"][0]["title"], "新标题")

    def test_deepseek_copy_rejects_prompt_forbidden_fragments(self) -> None:
        module_path = ROOT / "assets" / "workspace-template" / "asset-generation" / "write_copy_deepseek.py"
        spec = importlib.util.spec_from_file_location("write_copy_deepseek_forbidden", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaisesRegex(ValueError, "forbidden fragments"):
            module.normalize_copy(
                {
                    "title": "这个工具挺顺",
                    "body_full": "首先，本项目颇具优势。总体来说，它很适合开发者。",
                    "tags": ["AI工具", "开发工具", "Agent", "开源项目", "效率工具"],
                }
            )

    def test_generate_assets_rejects_duplicate_github_repo_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            history_dir = workspace / "content-history"
            history_dir.mkdir(parents=True, exist_ok=True)
            (history_dir / "sent-posts.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "record_type": "xhs_sent_post",
                        "delivery_id": "publish-tradingagents-old",
                        "content_id": "tradingagents-old",
                        "title": "旧标题",
                        "topic": "TradingAgents",
                        "topic_key": "github.com/tauricresearch/tradingagents",
                        "source_keys": ["github.com/tauricresearch/tradingagents"],
                        "sent_at": "2026-05-24T12:00:00+08:00",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            spec_path = workspace / "asset-generation" / "content_spec.json"
            spec = write_smoke_spec(workspace)
            spec["topic"] = "TradingAgents 开源项目"
            spec["project_facts"] = {
                "name": "TradingAgents",
                "repo": "TauricResearch/TradingAgents",
                "github_stars": "79,140 stars",
                "license": "Apache-2.0",
                "open_source": "true",
            }
            spec["source_urls"] = ["https://github.com/TauricResearch/TradingAgents"]
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("duplicate content history", generated.stderr + generated.stdout)
            self.assertIn("github.com/tauricresearch/tradingagents", generated.stderr + generated.stdout)

    def test_history_reads_source_keys_from_writing_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            module_path = workspace / "content-history" / "history_utils.py"
            spec = importlib.util.spec_from_file_location("workspace_history_utils", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.assertEqual(
                module.normalize_source_url("https://github.com/TauricResearch/TradingAgents"),
                "github.com/tauricresearch/tradingagents",
            )
            self.assertEqual(
                module.normalize_source_url("https://fortune.com/2026/05/ai-agent-costs"),
                "fortune.com/2026/05/ai-agent-costs",
            )
            self.assertEqual(
                module.normalize_github_repo("GitHub CLI/API"),
                "",
            )
            source_keys = module.source_keys_from_spec(
                {
                    "topic": "TradingAgents",
                    "source_urls": ["https://github.com/TauricResearch/TradingAgents"],
                    "source_verification": {"source": "GitHub CLI/API, repository README"},
                    "writing_brief": {
                        "facts": [
                            {
                                "claim": "TradingAgents is a GitHub project.",
                                "source_url": "https://github.com/TauricResearch/TradingAgents",
                            }
                        ]
                    },
                }
            )
            self.assertFalse(any("github cli" in key for key in source_keys))
            self.assertIn("github.com/tauricresearch/tradingagents", source_keys)

    def test_preflight_uses_cross_platform_script_path(self) -> None:
        text = (ROOT / "assets" / "workspace-template" / "publish-mainline" / "preflight.py").read_text(encoding="utf-8")
        self.assertIn("sys.executable", text)
        self.assertNotIn(".\\publish-mainline\\build_manual_publish_package.py", text)

    def test_send_records_successful_delivery_in_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            package_path = workspace / "asset-generation" / "outputs" / "current-publish-assets.json"
            package = json.loads(package_path.read_text(encoding="utf-8"))
            for image in package["images"]:
                image_path = workspace / image["image_path"]
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"png")
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertEqual(
                run([sys.executable, str(workspace / "publish-mainline" / "build_manual_publish_package.py")], cwd=workspace).returncode,
                0,
            )
            self.assertEqual(run([sys.executable, str(workspace / "publish-mainline" / "preflight.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "feishu-delivery" / "build_delivery_card.py")], cwd=workspace).returncode, 0)

            module_path = workspace / "feishu-delivery" / "send_delivery_card.py"
            spec = importlib.util.spec_from_file_location("workspace_send_delivery_card", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            old_env = os.environ.copy()
            try:
                os.environ.update(
                    {
                        "FEISHU_APP_ID": "app",
                        "FEISHU_APP_SECRET": "secret",
                        "FEISHU_RECEIVE_ID_TYPE": "open_id",
                        "FEISHU_RECEIVE_ID": "ou_test",
                    }
                )
                module.get_tenant_access_token = lambda env: "token"
                module.upload_image = lambda token, image_path: f"img_{image_path.stem}"
                module.send_message = lambda env, token, card: {"code": 0, "data": {"message_id": "om_test"}}

                self.assertEqual(module.main(["--send"]), 0)
            finally:
                os.environ.clear()
                os.environ.update(old_env)

            history_path = workspace / "content-history" / "sent-posts.jsonl"
            self.assertTrue(history_path.exists())
            records = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["message_id"], "om_test")
            self.assertEqual(records[0]["delivery_id"], package["review_id"])
            self.assertIn(records[0]["topic_key"], records[0]["source_keys"])

    def test_doctor_reports_missing_images_without_failing_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            doctor = run([sys.executable, str(workspace / "diagnostics" / "doctor.py")], cwd=workspace)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(
                (workspace / "diagnostics" / "outputs" / "doctor-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "blocked")
            self.assertIn("images_missing:6", report["blocked_reasons"])

    def test_doctor_blocks_playwright_mcp_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
            self.assertEqual(init.returncode, 0, init.stderr)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            artifact = workspace / ".playwright-mcp" / "page.yml"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("legacy browser automation artifact\n", encoding="utf-8")

            doctor = run([sys.executable, str(workspace / "diagnostics" / "doctor.py")], cwd=workspace)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads(
                (workspace / "diagnostics" / "outputs" / "doctor-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["status"], "blocked")
            self.assertTrue(any(item.startswith("risky_artifacts_found:") for item in report["blocked_reasons"]))

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

    def test_safety_scan_blocks_playwright_mcp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "skill"
            artifact = skill_dir / ".playwright-mcp" / "page.yml"
            artifact.parent.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
            artifact.write_text("legacy browser state\n", encoding="utf-8")
            completed = run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_skill_safety.py"),
                    "--skill-dir",
                    str(skill_dir),
                ]
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forbidden path", completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
