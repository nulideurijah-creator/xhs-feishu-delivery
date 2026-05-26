#!/usr/bin/env python3
"""Generate the current Xiaohongshu manual publish asset package from a spec.

Reads asset-generation/content_spec.json and writes structured outputs used by
model image generation, local publishing-package generation, and Feishu delivery.
"""

from __future__ import annotations

import json
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "content-history"))
from history_utils import assert_not_duplicate  # noqa: E402

SPEC_PATH = ROOT / "asset-generation" / "content_spec.json"
OUT = ROOT / "asset-generation" / "outputs"
PACKAGE_PATH = OUT / "current-publish-assets.json"
COPY_PATH = OUT / "current-copy.md"
PROMPT_PACKAGE_PATH = OUT / "current-image-card-prompts.md"

IMAGE_PRESET = "sketch-summary"
IMAGE_STYLE = "xhs-warm-cute-open-source"
IMAGE_LAYOUT = "balanced"
IMAGE_PALETTE = "macaron"
COPY_WRITER = "asset-generation/write_copy_deepseek.py"
IMAGE_PROMPT_WRITER = "asset-generation/write_image_prompts_deepseek.py"

def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return
    path.write_text(normalized, encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_spec(spec: dict[str, Any]) -> None:
    """Validate business rules before any image or Feishu work begins."""
    required = [
        "review_id",
        "content_id",
        "title",
        "topic",
        "writing_brief",
        "body_full",
        "tags",
        "image_slug",
        "pages",
    ]
    missing = [key for key in required if not spec.get(key)]
    if missing:
        raise ValueError(f"content_spec missing: {missing}")
    validate_writing_brief(spec["writing_brief"])
    validate_copy_generation(spec.get("copy_generation"))
    validate_image_prompt_generation(spec.get("image_prompt_generation"), spec)
    if len(str(spec["title"])) > 20:
        raise ValueError(f"title too long: {len(str(spec['title']))}/20")
    body = str(spec["body_full"])
    if len(body) > 1000:
        raise ValueError(f"body too long: {len(body)}/1000")
    tags = spec.get("tags", [])
    if not isinstance(tags, list) or not 1 <= len(tags) <= 10:
        raise ValueError(f"invalid tags count: {len(tags) if isinstance(tags, list) else 'invalid'}")
    pages = spec.get("pages", [])
    if not isinstance(pages, list) or len(pages) != 6:
        raise ValueError("content_spec must contain exactly 6 pages")
    validate_pages(pages)


def validate_writing_brief(brief: Any) -> None:
    """Make sure the model-written body is grounded in source-backed facts."""
    if not isinstance(brief, dict):
        raise ValueError("writing_brief must be an object")
    facts = brief.get("facts")
    if not isinstance(facts, list) or len(facts) < 2:
        raise ValueError("writing_brief.facts must contain at least two source-backed facts")
    for index, item in enumerate(facts, start=1):
        if not isinstance(item, dict) or not str(item.get("claim", "")).strip() or not str(item.get("source_url", "")).strip():
            raise ValueError(f"writing_brief.facts[{index}] must include claim and source_url")


def validate_copy_generation(copy_generation: Any) -> None:
    """Reject title/body/tags that were not produced by the mandatory DeepSeek writer."""
    if not isinstance(copy_generation, dict):
        raise ValueError("copy_generation must record DeepSeek writing")
    provider = str(copy_generation.get("provider", "")).strip().lower()
    writer = str(copy_generation.get("writer", "")).strip()
    model = str(copy_generation.get("model", "")).strip().lower()
    if provider != "deepseek" or COPY_WRITER not in writer or "deepseek" not in model:
        raise ValueError("copy_generation must record DeepSeek writing")


def body_hash(spec: dict[str, Any]) -> str:
    return hashlib.sha256(str(spec.get("body_full", "")).strip().encode("utf-8")).hexdigest()


def validate_image_prompt_generation(image_prompt_generation: Any, spec: dict[str, Any]) -> None:
    """Reject image prompts that were not planned by the mandatory DeepSeek writer."""
    if not isinstance(image_prompt_generation, dict):
        raise ValueError("image_prompt_generation must record DeepSeek image prompt writing")
    provider = str(image_prompt_generation.get("provider", "")).strip().lower()
    writer = str(image_prompt_generation.get("writer", "")).strip()
    model = str(image_prompt_generation.get("model", "")).strip().lower()
    source_title = str(image_prompt_generation.get("source_title", "")).strip()
    source_body_sha256 = str(image_prompt_generation.get("source_body_sha256", "")).strip()
    if provider != "deepseek" or IMAGE_PROMPT_WRITER not in writer or "deepseek" not in model:
        raise ValueError("image_prompt_generation must record DeepSeek image prompt writing")
    if source_title != str(spec.get("title", "")).strip():
        raise ValueError("image_prompt_generation is stale: source_title does not match current title")
    if source_body_sha256 != body_hash(spec):
        raise ValueError("image_prompt_generation is stale: source_body_sha256 does not match current body")


def validate_pages(pages: list[Any]) -> None:
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"content_spec.pages[{index}] must be an object")
        if not str(page.get("page_id", "")).strip():
            raise ValueError(f"content_spec.pages[{index}] missing page_id")
        plan = page.get("image_prompt_plan")
        if not isinstance(plan, dict):
            raise ValueError(f"content_spec.pages[{index}] missing DeepSeek image_prompt_plan")
        for field in [
            "card_role",
            "visible_title",
            "visible_subtitle",
            "visual_direction",
            "composition",
            "text_style",
        ]:
            if not str(plan.get(field, "")).strip():
                raise ValueError(f"content_spec.pages[{index}].image_prompt_plan missing {field}")
        for field in ["required_labels", "avoid"]:
            value = plan.get(field, [])
            if value is not None and not isinstance(value, list):
                raise ValueError(f"content_spec.pages[{index}].image_prompt_plan.{field} must be a list")


def render_fact_summary(spec: dict[str, Any]) -> str:
    brief = spec["writing_brief"]
    fact_lines = []
    for item in brief.get("facts", [])[:4]:
        if isinstance(item, dict):
            fact_lines.append(f"- {item.get('claim', '')} ({item.get('source_url', '')})")
    return "\n".join(["事实来源：", *fact_lines])


def render_copy(spec: dict[str, Any]) -> str:
    tag_text = " ".join(f"#{str(tag).strip().lstrip('#')}" for tag in spec["tags"])
    return f"""标题：{spec['title']}
事实素材摘要：
{render_fact_summary(spec)}

正文：
{spec['body_full']}

标签：{tag_text}
"""


def page_layout(page: dict[str, Any]) -> str:
    """Allow a page to override the default baoyu layout in content_spec.json."""
    layout = str(page.get("layout") or IMAGE_LAYOUT).strip()
    return layout or IMAGE_LAYOUT


def project_fact_block(spec: dict[str, Any]) -> str:
    """Render verified GitHub/open-source facts for the image prompt."""
    facts = spec.get("project_facts", {})
    lines: list[str] = []
    if isinstance(facts, dict):
        labels = {
            "name": "Project name",
            "repo": "GitHub repo",
            "github_stars": "GitHub stars",
            "stars": "GitHub stars",
            "license": "License",
            "open_source": "Open-source status",
            "url": "Project URL",
            "description": "Project note",
        }
        for key, label in labels.items():
            value = facts.get(key)
            if value:
                lines.append(f"- {label}: {value}")

    source_urls = [str(url) for url in spec.get("source_urls", []) if url]
    github_urls = [url for url in source_urls if "github.com" in url.lower()]
    if github_urls and not any(line.startswith("- GitHub repo:") for line in lines):
        lines.append(f"- GitHub source URL: {github_urls[0]}")

    if not lines:
        return (
            "Verified project/source facts:\n"
            "- No GitHub star, repo, license, or open-source facts were provided. "
            "Do not invent repo names, star counts, licenses, or logos."
        )
    return (
        "Verified project/source facts:\n"
        + "\n".join(lines)
        + "\nShow these facts only when they fit the card topic, and never invent unverified counts."
    )


def render_string_list(title: str, values: list[Any]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if not items:
        return f"{title}: none"
    return title + ":\n" + "\n".join(f"- {item}" for item in items)


def card_prompt(page: dict[str, Any], spec: dict[str, Any]) -> str:
    plan = page["image_prompt_plan"]
    return f"""---
source: asset-generation/content_spec.json
content_id: {spec["content_id"]}
page_id: {page["page_id"]}
title: {plan["visible_title"]}
ratio: "3:4"
preset: {IMAGE_PRESET}
style: {IMAGE_STYLE}
layout: {page_layout(page)}
palette: {IMAGE_PALETTE}
review_status: pending
---

Use case: infographic-diagram
Asset type: Xiaohongshu vertical image card
Baoyu preset wrapper, keep unchanged:
- preset: {IMAGE_PRESET}
- style: {IMAGE_STYLE}
- layout: {page_layout(page)}
- palette: {IMAGE_PALETTE}
- ratio: 3:4
- backend: image2 or the runtime-equivalent real raster image model

{project_fact_block(spec)}

DeepSeek-generated image prompt plan, use as the content source:
- Card role: {plan["card_role"]}
- Visible title: {plan["visible_title"]}
- Visible subtitle: {plan["visible_subtitle"]}
- Visual direction: {plan["visual_direction"]}
- Composition: {plan["composition"]}
- Text style: {plan["text_style"]}
{render_string_list("Required short labels", plan.get("required_labels", []))}
{render_string_list("Avoid", plan.get("avoid", []))}

Constraints:
- No fake brand logo.
- No watermark.
- No dense paragraphs.
- No English sentence blocks; only short labels are allowed when necessary.
- Avoid lifestyle, beauty, food, travel, or generic social media visuals.
- Do not use harsh black brush lettering.
- Do not imply the workflow can be shipped without human review.
"""


def image_is_ready(image_path: Path, prompt_path: Path) -> bool:
    if not image_path.exists() or image_path.stat().st_size <= 0:
        return False
    if not prompt_path.exists():
        return False
    return image_path.stat().st_mtime >= prompt_path.stat().st_mtime


def build_package(spec: dict[str, Any], history_check: dict[str, Any]) -> dict[str, Any]:
    """Create the machine-readable asset package consumed by later steps."""
    prompt_dir = ROOT / "image-generation" / "prompts" / spec["image_slug"]
    image_dir = ROOT / "image-generation" / "outputs" / "images" / spec["image_slug"]
    images: list[dict[str, Any]] = []
    for index, page in enumerate(spec["pages"], start=1):
        prompt_path = prompt_dir / f"{page['page_id']}.md"
        image_path = image_dir / f"{page['page_id']}.png"
        plan = page["image_prompt_plan"]
        write_text(prompt_path, card_prompt(page, spec))
        images.append(
            {
                "index": index,
                "page_id": page["page_id"],
                "title": plan["visible_title"],
                "subtitle": plan["visible_subtitle"],
                "image_path": image_path.relative_to(ROOT).as_posix(),
                "image_abs_path": str(image_path.resolve()),
                "prompt_path": prompt_path.relative_to(ROOT).as_posix(),
                "review_status": "approved" if image_is_ready(image_path, prompt_path) else "pending",
            }
        )

    all_images_ready = all(item["review_status"] == "approved" for item in images)
    return {
        "review_id": spec["review_id"],
        "review_type": "publish",
        "content_id": spec["content_id"],
        "platform": "xiaohongshu",
        "status": "assets_ready" if all_images_ready else "assets_pending_images",
        "title": spec["title"],
        "summary": spec.get("summary", ""),
        "topic": spec["topic"],
        "hot_source": spec.get("hot_source", ""),
        "source_urls": spec.get("source_urls", []),
        "source_verification": spec.get("source_verification", {}),
        "history_check": history_check,
        "writing_brief": spec["writing_brief"],
        "copy_generation": spec.get("copy_generation", {}),
        "image_prompt_generation": spec.get("image_prompt_generation", {}),
        "project_facts": spec.get("project_facts", {}),
        "body_full": spec["body_full"],
        "body_char_count": len(spec["body_full"]),
        "tags": [str(tag).strip().lstrip("#") for tag in spec["tags"]],
        "image_slug": spec["image_slug"],
        "images": images,
        "publish_mode": "manual_only",
        "auto_publish_enabled": False,
        "publish_checks": [
            "内容保持 AI 圈热点垂类，不混入泛生活选题。",
            "标题和正文由当前模型直接写成最终稿。",
            "图片由模型生成，脚本不使用本地模板渲染器冒充成品图。",
            "飞书只交付完整内容，不自动发布到小红书。",
            "标签由发布人在小红书 App 或网页发布页手动选择为话题。",
            "不包含音乐字段或选曲说明。",
        ],
        "source_files": {
            "content_spec": str(SPEC_PATH.relative_to(ROOT)),
            "copy": str(COPY_PATH.relative_to(ROOT)),
            "image_prompt_package": str(PROMPT_PACKAGE_PATH.relative_to(ROOT)),
        },
        "skill_sources": {
            "topic": "aihot",
            "verification": "agent-reach for official sources, GitHub facts, X posts, papers, and source URLs",
            "writing": "DeepSeek v4 Flash only via asset-generation/write_copy_deepseek.py using references/creator_prompt.md, verified facts, and writing_brief",
            "image_prompts": "DeepSeek-only via asset-generation/write_image_prompts_deepseek.py, then baoyu-image-cards + image2/imagegen raster backend",
            "image_style": IMAGE_STYLE,
            "image_defaults": "use workspace .baoyu-skills EXTEND.md non-interactively: no watermark, balanced layout, macaron palette, imagegen backend, --yes/direct defaults",
        },
        "created_at": now(),
    }


def render_prompt_package(package: dict[str, Any]) -> str:
    lines = [
        "# 图卡 prompt 包",
        "",
        f"来源：`baoyu-image-cards` 规则，preset=`{IMAGE_PRESET}`，style=`{IMAGE_STYLE}`，layout=`{IMAGE_LAYOUT}`，palette=`{IMAGE_PALETTE}`。",
        "",
    ]
    for image in package["images"]:
        lines.extend(
            [
                f"## {image['page_id']}",
                "",
                f"- 标题：{image['title']}",
                f"- 副标题：{image['subtitle']}",
                f"- prompt：`{image['prompt_path']}`",
                f"- 目标图片：`{image['image_path']}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    spec = load_json(SPEC_PATH)
    validate_spec(spec)
    history_check = assert_not_duplicate(spec)
    package = build_package(spec, history_check)
    write_json(PACKAGE_PATH, package)
    write_text(COPY_PATH, render_copy(spec))
    write_text(PROMPT_PACKAGE_PATH, render_prompt_package(package))
    print(f"status: {package['status']}")
    print(f"title: {package['title']}")
    print(f"images_ready: {sum(1 for item in package['images'] if item['review_status'] == 'approved')}/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
