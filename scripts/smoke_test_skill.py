#!/usr/bin/env python3
"""Smoke-test an installed or local xhs-feishu-delivery skill directory.

The smoke test creates a temporary workspace, initializes it from the skill,
runs asset generation, and verifies the stable handoff contract. It does not
call image generation, Feishu, Xiaohongshu, or the network.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_MARKERS = [
    "aihot",
    "agent-reach",
    "creator_prompt.md",
    "baoyu-image-cards",
    "imagegen",
]

EXPECTED_IMAGE_STYLE = "xhs-warm-cute-open-source"


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


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_smoke_spec(workspace: Path) -> None:
    """Create a temporary spec for the smoke test without shipping starter copy."""
    spec = {
        "review_id": "publish-smoke-test",
        "content_id": "smoke-ai-tool-evaluation",
        "title": "Smoke Test",
        "topic": "Smoke test topic",
        "summary": "Smoke test fixture for packaging.",
        "hot_source": "smoke-test",
        "source_urls": ["https://example.com/ai-tool", "https://example.com/ai-tool-docs"],
        "source_verification": {"source": "smoke test fixture", "checked_at": "2026-05-25T00:00:00+08:00"},
        "writing_brief": {
            "facts": [
                {"claim": "Smoke fact one.", "source_url": "https://example.com/ai-tool"},
                {"claim": "Smoke fact two.", "source_url": "https://example.com/ai-tool-docs"},
            ],
            "why_now": "Smoke reason for writing now.",
            "creator_angle": "Write like a Xiaohongshu AI tools creator sharing one useful discovery.",
            "audience": "AI tool users and indie builders.",
            "do_not_say": ["Do not use formula-title language."],
        },
        "project_facts": {},
        "body_full": "SMOKE TEST BODY. Fixture only. Do not use as Xiaohongshu copywriting guidance.",
        "tags": ["smoke", "test", "fixture"],
        "image_slug": "smoke-test",
        "pages": [
            {"page_id": "01-cover", "title": "Smoke Test", "subtitle": "先看能不能进流程", "visual": "A creator comparing a shiny demo screen with a real work desk."},
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


def assert_ok(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def smoke_test(skill_dir: Path, keep_workspace: bool) -> tuple[dict[str, Any], int]:
    failures: list[str] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="xhs-skill-smoke-"))
    workspace = temp_dir / "workspace"

    try:
        init_script = skill_dir / "scripts" / "init_workspace.py"
        asset_script = workspace / "asset-generation" / "generate_current_assets.py"
        config_path = workspace / ".baoyu-skills" / "baoyu-image-cards" / "EXTEND.md"
        package_path = workspace / "asset-generation" / "outputs" / "current-publish-assets.json"
        cover_prompt = workspace / "image-generation" / "prompts" / "smoke-test" / "01-cover.md"

        assert_ok(init_script.exists(), failures, "init_workspace_missing")
        if init_script.exists():
            completed = run([sys.executable, str(init_script), "--workspace", str(workspace)])
            assert_ok(completed.returncode == 0, failures, f"init_workspace_failed:{completed.stderr.strip()}")
        write_smoke_spec(workspace)

        assert_ok(config_path.exists(), failures, "baoyu_extend_missing")
        if config_path.exists():
            config_text = config_path.read_text(encoding="utf-8")
            assert_ok(EXPECTED_IMAGE_STYLE in config_text, failures, "baoyu_style_missing")
            assert_ok("preferred_image_backend: codex-imagegen" in config_text, failures, "image_backend_missing")

        assert_ok(asset_script.exists(), failures, "asset_generator_missing")
        if asset_script.exists():
            completed = run([sys.executable, str(asset_script)], cwd=workspace)
            assert_ok(completed.returncode == 0, failures, f"asset_generator_failed:{completed.stderr.strip()}")

        assert_ok(package_path.exists(), failures, "asset_package_missing")
        package: dict[str, Any] = {}
        if package_path.exists():
            package = load_json(package_path)
            assert_ok(package.get("status") == "assets_pending_images", failures, "unexpected_asset_status")
            images = package.get("images", [])
            assert_ok(isinstance(images, list) and len(images) == 6, failures, "images_not_6")
            source_text = json.dumps(package.get("skill_sources", {}), ensure_ascii=False)
            for marker in EXPECTED_MARKERS:
                assert_ok(marker in source_text, failures, f"skill_marker_missing:{marker}")
            package_text = json.dumps(package, ensure_ascii=False)
            for term in legacy_terms():
                assert_ok(term not in package_text, failures, f"legacy_term_found:{term}")

        assert_ok(cover_prompt.exists(), failures, "cover_prompt_missing")
        if cover_prompt.exists():
            prompt_text = cover_prompt.read_text(encoding="utf-8")
            assert_ok(f"style: {EXPECTED_IMAGE_STYLE}" in prompt_text, failures, "cover_style_missing")
            assert_ok("Cover hook rules:" in prompt_text, failures, "cover_hook_rules_missing")
            assert_ok("central GitHub-style project card" in prompt_text, failures, "cover_project_visibility_missing")
            assert_ok("title: Smoke Test" in prompt_text, failures, "cover_title_missing")

        result = {
            "status": "ok" if not failures else "failed",
            "failures": failures,
            "skill_dir": str(skill_dir),
            "workspace": str(workspace),
            "kept_workspace": keep_workspace,
        }
        return result, 0 if not failures else 1
    finally:
        if not keep_workspace:
            shutil.rmtree(temp_dir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test xhs-feishu-delivery")
    parser.add_argument("--skill-dir", default=str(Path(__file__).resolve().parents[1]), help="Path to the skill directory")
    parser.add_argument("--keep-workspace", action="store_true", help="Keep the temporary workspace for inspection")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    result, code = smoke_test(skill_dir, args.keep_workspace)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if code == 0:
        print("smoke_test_ok")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
