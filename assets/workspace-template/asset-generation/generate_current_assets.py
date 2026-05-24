#!/usr/bin/env python3
"""Generate the current Xiaohongshu manual publish asset package from a spec.

Reads asset-generation/content_spec.json and writes structured outputs used by
image rendering, local publishing-package generation, and Feishu delivery.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "asset-generation" / "content_spec.json"
OUT = ROOT / "asset-generation" / "outputs"
PACKAGE_PATH = OUT / "current-publish-assets.json"
COPY_PATH = OUT / "current-copy.md"
TITLE_PATH = OUT / "current-title-candidates.md"
PROMPT_PACKAGE_PATH = OUT / "current-image-card-prompts.md"

FORBIDDEN_PHRASES = [
    # Phrases the original workflow owner rejected during real content review.
    # Keep this list short and concrete; it prevents known AI-sounding wording.
    "它做的事很直接",
    "这个数据先当热度参考",
    "但别只看 GitHub star",
    "这类项目真正值得看的是方向",
    "不仅",
    "而且",
    "此外",
    "综上",
]


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_spec(spec: dict[str, Any]) -> None:
    """Validate business rules before any image or Feishu work begins."""
    required = ["review_id", "content_id", "title", "body_full", "tags", "pages"]
    missing = [key for key in required if not spec.get(key)]
    if missing:
        raise ValueError(f"content_spec missing: {missing}")
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
    hits = [phrase for phrase in FORBIDDEN_PHRASES if phrase in body]
    if hits:
        raise ValueError(f"body contains forbidden phrases: {hits}")


def render_copy(spec: dict[str, Any]) -> str:
    tag_text = " ".join(f"#{str(tag).strip().lstrip('#')}" for tag in spec["tags"])
    return f"""标题：{spec['title']}
正文：
{spec['body_full']}
标签：{tag_text}
"""


def render_titles(spec: dict[str, Any]) -> str:
    lines = [
        "# 标题候选",
        "",
        "来源：`dbs-xhs-title` 公式匹配规则 + 当前选题人工筛选",
        "",
        "| 序号 | 标题 | 类型 | 理由 |",
        "|---|---|---|---|",
    ]
    for index, item in enumerate(spec.get("title_candidates", []), start=1):
        lines.append(
            f"| {index} | {item.get('title', '')} | {item.get('type', '')} | {item.get('reason', '')} |"
        )
    return "\n".join(lines)


def card_prompt(page: dict[str, Any], spec: dict[str, Any]) -> str:
    return f"""---
source: asset-generation/content_spec.json
content_id: {spec["content_id"]}
page_id: {page["page_id"]}
title: {page["title"]}
ratio: "3:4"
preset: knowledge-card
style: notion
layout: dense
palette: macaron
review_status: pending
---

Use case: infographic-diagram
Asset type: Xiaohongshu vertical image card
Primary request:
Create one polished 3:4 Chinese Xiaohongshu knowledge card about {spec["topic"]}.

Text must be clear, large, and sparse:
- Main title, verbatim: "{page["title"]}"
- Small subtitle, verbatim: "{page["subtitle"]}"

Scene/backdrop:
- Warm cream background, soft macaron zones in blue, mint, peach, and lavender.
- Clean Notion-style hand-drawn infographic, thin black outline, light paper texture.

Subject and visual:
- {page["visual"]}

Composition:
- One large title area at the top.
- One central visual metaphor in the middle.
- One small subtitle band at the bottom.
- Keep enough margin for mobile cropping.

Constraints:
- No fake brand logo.
- No watermark.
- No dense paragraphs.
- No English sentence blocks; only short labels are allowed when necessary.
- Avoid lifestyle, beauty, food, travel, or generic social media visuals.
- Do not imply the workflow can be shipped without human review.
"""


def build_package(spec: dict[str, Any]) -> dict[str, Any]:
    """Create the machine-readable asset package consumed by later steps."""
    prompt_dir = ROOT / "image-generation" / "prompts" / spec["image_slug"]
    image_dir = ROOT / "image-generation" / "outputs" / "images" / spec["image_slug"]
    images: list[dict[str, Any]] = []
    for index, page in enumerate(spec["pages"], start=1):
        prompt_path = prompt_dir / f"{page['page_id']}.md"
        image_path = image_dir / f"{page['page_id']}.png"
        write_text(prompt_path, card_prompt(page, spec))
        images.append(
            {
                "index": index,
                "page_id": page["page_id"],
                "title": page["title"],
                "subtitle": page["subtitle"],
                "image_path": image_path.relative_to(ROOT).as_posix(),
                "image_abs_path": str(image_path.resolve()),
                "prompt_path": prompt_path.relative_to(ROOT).as_posix(),
                "review_status": "approved" if image_path.exists() and image_path.stat().st_size > 0 else "pending",
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
        "body_full": spec["body_full"],
        "body_char_count": len(spec["body_full"]),
        "tags": [str(tag).strip().lstrip("#") for tag in spec["tags"]],
        "title_candidates": spec.get("title_candidates", []),
        "images": images,
        "publish_mode": "manual_only",
        "auto_publish_enabled": False,
        "publish_checks": [
            "内容保持 AI 圈热点垂类，不混入泛生活选题。",
            "正文已避开用户指出的 AI 感表达。",
            "账号收到小红书 AI 使用违规警报，当前禁止 MCP 或浏览器脚本真实发布。",
            "飞书只交付完整内容，不自动发布到小红书。",
            "标签由发布人手动在小红书 App 或网页发布页选择。",
            "不包含音乐字段或选曲说明。",
        ],
        "source_files": {
            "content_spec": str(SPEC_PATH.relative_to(ROOT)),
            "copy": str(COPY_PATH.relative_to(ROOT)),
            "title_candidates": str(TITLE_PATH.relative_to(ROOT)),
            "image_prompt_package": str(PROMPT_PACKAGE_PATH.relative_to(ROOT)),
        },
        "skill_sources": {
            "topic": "aihot",
            "title": "dbs-xhs-title style rules",
            "copy": "write-xiaohongshu + humanizer-zh editing rules",
            "image_prompts": "baoyu-image-cards",
        },
        "created_at": now(),
    }


def render_prompt_package(package: dict[str, Any]) -> str:
    lines = [
        "# 图卡 prompt 包",
        "",
        "来源：`baoyu-image-cards` 规则，preset=`knowledge-card`，style=`notion`，layout=`dense`，palette=`macaron`。",
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
    package = build_package(spec)
    write_json(PACKAGE_PATH, package)
    write_text(COPY_PATH, render_copy(spec))
    write_text(TITLE_PATH, render_titles(spec))
    write_text(PROMPT_PACKAGE_PATH, render_prompt_package(package))
    print(f"status: {package['status']}")
    print(f"title: {package['title']}")
    print(f"images_ready: {sum(1 for item in package['images'] if item['review_status'] == 'approved')}/6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
