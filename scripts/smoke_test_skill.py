#!/usr/bin/env python3
"""Smoke-test an installed or local xhs-feishu-delivery skill directory.

The smoke test creates a temporary workspace, initializes it from the skill,
runs asset generation, and verifies the stable handoff contract. It does not
call image generation, Feishu, Xiaohongshu, or the network.
"""

from __future__ import annotations

import argparse
import hashlib
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
    "DeepSeek",
    "creator_prompt.md",
    "write_image_prompts_deepseek.py",
    "baoyu-image-cards",
    "imagegen",
]

EXPECTED_IMAGE_STYLE = "xhs-warm-cute-open-source"


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


def write_smoke_spec(workspace: Path) -> None:
    """Create a temporary spec without shipping starter copy."""
    title = "Smoke Title"
    body = (
        "This is a stable smoke-test body. It represents the final DeepSeek copy "
        "without requiring any network call during validation."
    )
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
        "source_verification": {"source": "smoke test fixture", "checked_at": "2026-05-25T00:00:00+08:00"},
        "writing_brief": {
            "facts": [
                {"claim": "Smoke fact one.", "source_url": "https://example.com/ai-tool"},
                {"claim": "Smoke fact two.", "source_url": "https://example.com/ai-tool-docs"},
            ],
            "do_not_say": ["Do not add unsupported claims."],
        },
        "project_facts": {},
        "body_full": body,
        "tags": ["AI tools", "automation", "Xiaohongshu", "workflow", "Feishu"],
        "copy_generation": {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "writer": "asset-generation/write_copy_deepseek.py",
            "prompt_path": "references/creator_prompt.md",
            "created_at": "2026-05-25T00:00:00+08:00",
        },
        "image_prompt_generation": {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "writer": "asset-generation/write_image_prompts_deepseek.py",
            "prompt_path": "references/image_prompt_creator_prompt.md",
            "source_title": title,
            "source_body_sha256": hashlib.sha256(body.strip().encode("utf-8")).hexdigest(),
            "created_at": "2026-05-25T00:00:00+08:00",
        },
        "image_slug": "smoke-test",
        "pages": pages,
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
        if package_path.exists():
            package = load_json(package_path)
            assert_ok(package.get("status") == "assets_pending_images", failures, "unexpected_asset_status")
            images = package.get("images", [])
            assert_ok(isinstance(images, list) and len(images) == 6, failures, "images_not_6")
            source_text = json.dumps(package.get("skill_sources", {}), ensure_ascii=False)
            for marker in EXPECTED_MARKERS:
                assert_ok(marker in source_text, failures, f"skill_marker_missing:{marker}")

        assert_ok(cover_prompt.exists(), failures, "cover_prompt_missing")
        if cover_prompt.exists():
            prompt_text = cover_prompt.read_text(encoding="utf-8")
            assert_ok(f"style: {EXPECTED_IMAGE_STYLE}" in prompt_text, failures, "cover_style_missing")
            assert_ok("DeepSeek-generated image prompt plan" in prompt_text, failures, "deepseek_image_prompt_plan_missing")
            assert_ok("Cover hook rules:" not in prompt_text, failures, "removed_cover_hook_rules_present")
            assert_ok("Main title, verbatim" not in prompt_text, failures, "removed_main_title_template_present")
            assert_ok("title: Smoke 1" in prompt_text, failures, "cover_title_missing")

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
