#!/usr/bin/env python3
"""Build a buttonless Feishu delivery card for the current Xiaohongshu package."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"

ASSET_PACKAGE = ROOT / "asset-generation" / "outputs" / "current-publish-assets.json"
MANUAL_PACKAGE = ROOT / "publish-mainline" / "outputs" / "manual-publish-package.md"
REQUEST_PATH = OUT / "delivery-request.json"
CARD_PATH = OUT / "delivery-card.json"

CARD_FORBIDDEN_TERMS = [
    "发布方式",
    "人工发布包",
    "发布前检查",
    "**状态**",
]


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def normalize_tag(value: Any) -> str:
    return str(value).strip().lstrip("#")


def validate_images(package: dict[str, Any]) -> list[dict[str, Any]]:
    images = package.get("images")
    if not isinstance(images, list) or len(images) != 6:
        raise ValueError("current-publish-assets.json must contain exactly 6 images")

    result: list[dict[str, Any]] = []
    for index, item in enumerate(images, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"image item #{index} must be an object")
        image_path = ROOT / str(item.get("image_path", ""))
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        if image_path.stat().st_size <= 0:
            raise ValueError(f"image is empty: {image_path}")
        if item.get("review_status") != "approved":
            raise ValueError(f"image is not approved: {image_path}")
        result.append(
            {
                "index": index,
                "page_id": str(item.get("page_id") or f"image-{index:02d}"),
                "title": str(item.get("title") or f"图片 {index}").strip(),
                "image_path": rel(image_path),
                "image_abs_path": str(image_path.resolve()),
            }
        )
    return result


def build_request() -> dict[str, Any]:
    package = load_json(ASSET_PACKAGE)
    title = str(package.get("title", "")).strip()
    body = str(package.get("body_full", "")).strip()
    tags = [normalize_tag(tag) for tag in package.get("tags", []) if normalize_tag(tag)]
    images = validate_images(package)

    if not title:
        raise ValueError("title is required")
    if len(title) > 20:
        raise ValueError(f"title too long: {len(title)}/20")
    if not body:
        raise ValueError("body_full is required")
    if len(body) > 1000:
        raise ValueError(f"body too long: {len(body)}/1000")
    if not tags:
        raise ValueError("tags are required")

    return {
        "delivery_id": package.get("review_id", "xhs-delivery-current"),
        "content_id": package.get("content_id", ""),
        "platform": "xiaohongshu",
        "topic": package.get("topic", ""),
        "title": title,
        "body_full": body,
        "tags": tags,
        "images": images,
        "manual_package_path": rel(MANUAL_PACKAGE) if MANUAL_PACKAGE.exists() else "",
        "source_files": package.get("source_files", {}),
        "created_at": now(),
    }


def has_action_or_button(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("tag") in {"action", "button"}:
            return True
        return any(has_action_or_button(item) for item in value.values())
    if isinstance(value, list):
        return any(has_action_or_button(item) for item in value)
    return False


def validate_card(card: dict[str, Any]) -> None:
    metadata = card.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("delivery card must contain metadata")
    expected = {
        "button_mode": "none",
        "approval_required": False,
        "auto_publish_enabled": False,
        "requires_callback_url": False,
        "requires_websocket_receiver": False,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"invalid metadata {key}: {metadata.get(key)!r}")
    if has_action_or_button(card):
        raise ValueError("delivery card must not contain action/button elements")
    rendered = json.dumps(card, ensure_ascii=False)
    hits = [term for term in CARD_FORBIDDEN_TERMS if term in rendered]
    if hits:
        raise ValueError(f"delivery card contains forbidden terms: {hits}")


def build_card(delivery: dict[str, Any]) -> dict[str, Any]:
    image_lines = "\n".join(
        f"{item['index']}. {item['title']}" for item in delivery["images"]
    )
    tag_text = " ".join(f"#{tag}" for tag in delivery["tags"])

    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**选题**\n{delivery['topic']}"},
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**标题（复制到小红书标题栏）**\n{delivery['title']}",
            },
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**正文（复制到小红书正文）**\n{delivery['body_full']}",
            },
        },
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**图片清单**\n{image_lines}"},
        },
    ]

    for item in delivery["images"]:
        elements.append(
            {
                "tag": "img",
                "img_key": f"__IMAGE_KEY_{item['page_id']}__",
                "alt": {"tag": "plain_text", "content": item["title"]},
            }
        )

    elements.append(
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**标签（复制后在小红书逐个选择话题）**\n{tag_text}",
            },
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": f"小红书内容：{delivery['title']}",
            },
        },
        "elements": elements,
        "metadata": {
            "delivery_id": delivery["delivery_id"],
            "content_id": delivery["content_id"],
            "button_mode": "none",
            "approval_required": False,
            "auto_publish_enabled": False,
            "requires_callback_url": False,
            "requires_websocket_receiver": False,
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    delivery = build_request()
    card = build_card(delivery)
    validate_card(card)
    REQUEST_PATH.write_text(
        json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CARD_PATH.write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"delivery_request: {REQUEST_PATH}")
    print(f"delivery_card: {CARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
