from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any


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


def smoke_body() -> str:
    return (
        "Smoke body for DeepSeek-only image prompt tests. "
        "It is long enough to behave like a real article body but stays stable."
    )


def deepseek_copy_generation() -> dict[str, Any]:
    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "writer": "asset-generation/write_copy_deepseek.py",
        "prompt_path": "references/creator_prompt.md",
        "created_at": "2026-05-25T00:00:00+08:00",
    }


def deepseek_image_prompt_generation(body: str, title: str = "Smoke Title") -> dict[str, Any]:
    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "writer": "asset-generation/write_image_prompts_deepseek.py",
        "prompt_path": "references/image_prompt_creator_prompt.md",
        "source_title": title,
        "source_body_sha256": hashlib.sha256(body.strip().encode("utf-8")).hexdigest(),
        "created_at": "2026-05-25T00:00:00+08:00",
    }


def image_prompt_plan(index: int) -> dict[str, Any]:
    return {
        "card_role": "cover" if index == 1 else "inner",
        "visible_title": f"Smoke {index}",
        "visible_subtitle": "Fixture card",
        "visual_direction": f"Human editorial image direction for smoke card {index}.",
        "composition": "Large calm title, one central metaphor, enough blank space.",
        "text_style": "Natural Chinese editorial card wording, short and sparse.",
        "required_labels": ["fixture"],
        "avoid": ["generic AI infographic"],
    }


def write_smoke_spec(workspace: Path) -> dict[str, Any]:
    title = "Smoke Title"
    body = smoke_body()
    pages = []
    for index, page_id in enumerate(
        ["01-cover", "02-gap", "03-task", "04-output", "05-rework", "06-save"],
        start=1,
    ):
        pages.append(
            {
                "page_id": page_id,
                "layout": "balanced",
                "image_prompt_plan": image_prompt_plan(index),
            }
        )
    spec = {
        "review_id": "publish-smoke-test",
        "content_id": "smoke-ai-tool-evaluation",
        "title": title,
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
            "do_not_say": ["Do not add unsupported claims."],
        },
        "project_facts": {
            "name": "models.dev",
            "repo": "github.com/vercel/ai",
            "github_stars": "4.1k stars",
            "license": "MIT",
            "open_source": "true",
        },
        "body_full": body,
        "tags": ["AI tools", "automation", "Xiaohongshu", "workflow", "Feishu"],
        "copy_generation": deepseek_copy_generation(),
        "image_prompt_generation": deepseek_image_prompt_generation(body, title),
        "image_slug": "smoke-test",
        "pages": pages,
    }
    path = workspace / "asset-generation" / "content_spec.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return spec


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillStabilityTests(unittest.TestCase):
    def init_workspace(self, workspace: Path) -> None:
        init = run([sys.executable, str(ROOT / "scripts" / "init_workspace.py"), "--workspace", str(workspace)])
        self.assertEqual(init.returncode, 0, init.stderr)

    def test_skill_md_declares_deepseek_copy_and_image_prompt_chain(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in [
            "Mature Research + DeepSeek Writing Chain",
            "write_copy_deepseek.py",
            "write_image_prompts_deepseek.py",
            "image_prompt_generation.provider=deepseek",
            "baoyu-image-cards",
            "imagegen",
            "--check-history",
            "--yes",
        ]:
            self.assertIn(marker, text)

    def test_prompt_references_exist(self) -> None:
        self.assertTrue((ROOT / "references" / "creator_prompt.md").exists())
        image_prompt = ROOT / "references" / "image_prompt_creator_prompt.md"
        self.assertTrue(image_prompt.exists())
        text = image_prompt.read_text(encoding="utf-8")
        self.assertIn("DeepSeek Image Prompt Creator", text)
        self.assertIn("image_prompt_plan", text)
        self.assertIn("backend: `image2`", text)

    def test_init_workspace_copies_deepseek_image_prompt_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            self.assertTrue((workspace / "asset-generation" / "write_copy_deepseek.py").exists())
            self.assertTrue((workspace / "asset-generation" / "write_image_prompts_deepseek.py").exists())
            self.assertTrue((workspace / "asset-generation" / "generate_current_assets.py").exists())
            self.assertTrue((workspace / "feishu-delivery" / "send_pending_delivery.py").exists())
            self.assertTrue((workspace / "feishu-delivery" / "install_pending_sender.py").exists())

    def test_generate_assets_uses_deepseek_plan_and_removes_old_prompt_brain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            write_smoke_spec(workspace)

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            package = json.loads(
                (workspace / "asset-generation" / "outputs" / "current-publish-assets.json").read_text(encoding="utf-8")
            )
            self.assertEqual(package["status"], "assets_pending_images")
            self.assertEqual(package["image_prompt_generation"]["provider"], "deepseek")
            self.assertEqual(len(package["images"]), 6)
            source_text = json.dumps(package["skill_sources"], ensure_ascii=False)
            self.assertIn("write_image_prompts_deepseek.py", source_text)
            self.assertIn("baoyu-image-cards", source_text)

            prompt = (
                workspace / "image-generation" / "prompts" / "smoke-test" / "01-cover.md"
            ).read_text(encoding="utf-8")
            self.assertIn("style: xhs-warm-cute-open-source", prompt)
            self.assertIn("Baoyu preset wrapper, keep unchanged", prompt)
            self.assertIn("DeepSeek-generated image prompt plan", prompt)
            self.assertIn("Visible title: Smoke 1", prompt)
            self.assertIn("Project name: models.dev", prompt)
            self.assertIn("GitHub stars: 4.1k stars", prompt)
            self.assertNotIn("Cover hook rules:", prompt)
            self.assertNotIn("friendly but still high-click cover hook", prompt)
            self.assertNotIn("Main title, verbatim", prompt)
            self.assertNotIn("Small subtitle, verbatim", prompt)
            self.assertNotIn("Subject and visual:", prompt)

    def test_generate_assets_requires_deepseek_copy_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            spec = write_smoke_spec(workspace)
            spec.pop("copy_generation", None)
            (workspace / "asset-generation" / "content_spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("copy_generation must record DeepSeek writing", generated.stderr + generated.stdout)

    def test_generate_assets_requires_deepseek_image_prompt_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            spec = write_smoke_spec(workspace)
            spec.pop("image_prompt_generation", None)
            (workspace / "asset-generation" / "content_spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("image_prompt_generation must record DeepSeek image prompt writing", generated.stderr + generated.stdout)

    def test_generate_assets_rejects_stale_image_prompt_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            spec = write_smoke_spec(workspace)
            spec["body_full"] += " changed"
            (workspace / "asset-generation" / "content_spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("image_prompt_generation is stale", generated.stderr + generated.stdout)

    def test_deepseek_image_prompt_writer_marks_source_and_rejects_old_fragments(self) -> None:
        module = load_module(
            ROOT / "assets" / "workspace-template" / "asset-generation" / "write_image_prompts_deepseek.py",
            "write_image_prompts_deepseek_test",
        )
        payload = {"title": "Smoke Title", "body_full": smoke_body()}
        module.mark_image_prompt_generation(payload, Path("references/image_prompt_creator_prompt.md"))
        self.assertEqual(payload["image_prompt_generation"]["provider"], "deepseek")
        self.assertEqual(payload["image_prompt_generation"]["writer"], "asset-generation/write_image_prompts_deepseek.py")
        self.assertEqual(payload["image_prompt_generation"]["source_title"], "Smoke Title")

        plan = image_prompt_plan(1)
        plan["composition"] = "Cover hook rules: central GitHub-style project card"
        with self.assertRaises(ValueError):
            module.normalize_plan(plan)

    def test_history_duplicate_check_blocks_reused_github_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            history_dir = workspace / "content-history"
            history_dir.mkdir(parents=True, exist_ok=True)
            (history_dir / "sent-posts.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "record_type": "xhs_sent_post",
                        "delivery_id": "publish-old",
                        "content_id": "old",
                        "title": "Old",
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
            spec = write_smoke_spec(workspace)
            spec["topic"] = "TradingAgents open-source project"
            spec["project_facts"] = {
                "name": "TradingAgents",
                "repo": "https://github.com/TauricResearch/TradingAgents",
                "github_stars": "79k stars",
                "license": "Apache-2.0",
            }
            spec["source_urls"] = ["https://github.com/TauricResearch/TradingAgents"]
            (workspace / "asset-generation" / "content_spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertNotEqual(generated.returncode, 0)
            self.assertIn("duplicate content history", generated.stderr + generated.stdout)
            self.assertIn("github.com/tauricresearch/tradingagents", generated.stderr + generated.stdout)

    def test_preflight_uses_cross_platform_script_path(self) -> None:
        text = (ROOT / "assets" / "workspace-template" / "publish-mainline" / "preflight.py").read_text(encoding="utf-8")
        self.assertIn("sys.executable", text)
        self.assertIn('ROOT / "publish-mainline" / "build_manual_publish_package.py"', text)
        self.assertNotIn(".\\publish-mainline\\build_manual_publish_package.py", text)

    def test_feishu_scripts_bypass_proxy_by_default(self) -> None:
        for relative_path in [
            "feishu-delivery/check_feishu_ready.py",
            "feishu-delivery/send_delivery_card.py",
        ]:
            text = (ROOT / "assets" / "workspace-template" / relative_path).read_text(encoding="utf-8")
            self.assertIn("DEFAULT_BYPASS_PROXY = True", text)
            self.assertIn("request.ProxyHandler({})", text)
            self.assertIn("URL_OPENER.open", text)

    def test_pending_sender_is_on_demand_only(self) -> None:
        text = (
            ROOT
            / "assets"
            / "workspace-template"
            / "feishu-delivery"
            / "install_pending_sender.py"
        ).read_text(encoding="utf-8")
        self.assertIn("Register-ScheduledTask", text)
        self.assertIn('"trigger_mode": "on_demand"', text)
        self.assertNotIn('"/SC"', text)
        self.assertNotIn('"MINUTE"', text)

    def test_doctor_reports_missing_images_without_failing_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)

            doctor = run([sys.executable, str(workspace / "diagnostics" / "doctor.py")], cwd=workspace)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads((workspace / "diagnostics" / "outputs" / "doctor-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertIn("images_missing:6", report["blocked_reasons"])

    def test_doctor_blocks_risky_browser_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            artifact = workspace / ".playwright-mcp" / "page.yml"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("legacy browser state\n", encoding="utf-8")

            doctor = run([sys.executable, str(workspace / "diagnostics" / "doctor.py")], cwd=workspace)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            report = json.loads((workspace / "diagnostics" / "outputs" / "doctor-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "blocked")
            self.assertTrue(any(item.startswith("risky_artifacts_found:") for item in report["blocked_reasons"]))

    def test_send_records_successful_delivery_in_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            package_path = workspace / "asset-generation" / "outputs" / "current-publish-assets.json"
            package = json.loads(package_path.read_text(encoding="utf-8"))
            time.sleep(1.1)
            for image in package["images"]:
                image_path = workspace / image["image_path"]
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"png")
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            self.assertEqual(run([sys.executable, str(workspace / "publish-mainline" / "build_manual_publish_package.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "publish-mainline" / "preflight.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "feishu-delivery" / "build_delivery_card.py")], cwd=workspace).returncode, 0)
            (workspace / "feishu-delivery" / ".env").write_text(
                "\n".join(
                    [
                        "FEISHU_APP_ID=app",
                        "FEISHU_APP_SECRET=secret",
                        "FEISHU_RECEIVE_ID_TYPE=open_id",
                        "FEISHU_RECEIVE_ID=ou_test",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            module = load_module(workspace / "feishu-delivery" / "send_delivery_card.py", "workspace_send_delivery_card")
            module.get_tenant_access_token = lambda env: "token"
            module.upload_image = lambda token, image_path: f"img_{image_path.stem}"
            module.send_message = lambda env, token, card: {"code": 0, "data": {"message_id": "om_test"}}
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(["--send"]), 0)

            history_path = workspace / "content-history" / "sent-posts.jsonl"
            self.assertTrue(history_path.exists())
            records = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["message_id"], "om_test")
            self.assertEqual(records[0]["delivery_id"], package["review_id"])
            self.assertIn(records[0]["topic_key"], records[0]["source_keys"])

    def test_pending_sender_queues_valid_package_and_defers_during_automation_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.init_workspace(workspace)
            write_smoke_spec(workspace)
            generated = run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            package_path = workspace / "asset-generation" / "outputs" / "current-publish-assets.json"
            package = json.loads(package_path.read_text(encoding="utf-8"))
            time.sleep(1.1)
            for image in package["images"]:
                image_path = workspace / image["image_path"]
                image_path.parent.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(b"png")
            self.assertEqual(run([sys.executable, str(workspace / "asset-generation" / "generate_current_assets.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "publish-mainline" / "build_manual_publish_package.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "publish-mainline" / "preflight.py")], cwd=workspace).returncode, 0)
            self.assertEqual(run([sys.executable, str(workspace / "feishu-delivery" / "build_delivery_card.py")], cwd=workspace).returncode, 0)

            queued = run([sys.executable, str(workspace / "feishu-delivery" / "send_pending_delivery.py"), "--queue"], cwd=workspace)
            self.assertEqual(queued.returncode, 0, queued.stderr + queued.stdout)
            pending_path = workspace / "feishu-delivery" / "outputs" / "pending-send.json"
            self.assertTrue(pending_path.exists())
            pending = json.loads(pending_path.read_text(encoding="utf-8"))
            self.assertEqual(pending["status"], "pending")
            self.assertEqual(pending["delivery_id"], package["review_id"])

            (workspace / ".xhs_automation.lock").write_text("{}", encoding="utf-8")
            deferred = run([sys.executable, str(workspace / "feishu-delivery" / "send_pending_delivery.py"), "--send-pending"], cwd=workspace)
            self.assertEqual(deferred.returncode, 0, deferred.stderr + deferred.stdout)
            result = json.loads((workspace / "feishu-delivery" / "outputs" / "pending-send-result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "deferred_lock_active")
            self.assertTrue(pending_path.exists())

    def test_safety_scan_blocks_legacy_renderer_and_browser_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
            (skill_dir / "render_current_cards.py").write_text("print('legacy')\n", encoding="utf-8")
            completed = run([sys.executable, str(ROOT / "scripts" / "validate_skill_safety.py"), "--skill-dir", str(skill_dir)])
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forbidden file name", completed.stderr + completed.stdout)

        with tempfile.TemporaryDirectory() as temp:
            skill_dir = Path(temp) / "skill"
            artifact = skill_dir / ".playwright-mcp" / "page.yml"
            artifact.parent.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
            artifact.write_text("legacy browser state\n", encoding="utf-8")
            completed = run([sys.executable, str(ROOT / "scripts" / "validate_skill_safety.py"), "--skill-dir", str(skill_dir)])
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("forbidden path", completed.stderr + completed.stdout)

    def test_smoke_test_script_passes_without_network(self) -> None:
        completed = run(
            [
                sys.executable,
                str(ROOT / "scripts" / "smoke_test_skill.py"),
                "--skill-dir",
                str(ROOT),
            ]
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("smoke_test_ok", completed.stdout)


if __name__ == "__main__":
    unittest.main()
