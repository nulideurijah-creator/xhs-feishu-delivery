from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publish-mainline" / "outputs"
ASSET_PACKAGE = ROOT / "asset-generation" / "outputs" / "current-publish-assets.json"
PACKAGE_JSON = OUT / "manual-publish-package.json"
PACKAGE_MD = OUT / "manual-publish-package.md"


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def normalize_tag(value: Any) -> str:
    return str(value).strip().lstrip("#")


def validate_assets(package: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    title = str(package.get("title", "")).strip()
    body = str(package.get("body_full", "")).strip()
    tags = [normalize_tag(tag) for tag in package.get("tags", []) if normalize_tag(tag)]
    images = package.get("images", [])

    if not title:
        errors.append("title_missing")
    if len(title) > 20:
        errors.append("title_too_long")
    if not body:
        errors.append("body_missing")
    if len(body) > 1000:
        errors.append("body_too_long")
    if not tags:
        errors.append("tags_missing")
    if not isinstance(images, list) or len(images) != 6:
        errors.append("expected_6_images")

    normalized_images: list[dict[str, Any]] = []
    if isinstance(images, list):
        for index, item in enumerate(images, start=1):
            if not isinstance(item, dict):
                errors.append(f"image_{index}_invalid")
                continue
            image_path = ROOT / str(item.get("image_path", ""))
            if not image_path.exists():
                errors.append(f"image_{index}_missing")
            elif image_path.stat().st_size <= 0:
                errors.append(f"image_{index}_empty")
            normalized_images.append(
                {
                    "index": index,
                    "page_id": item.get("page_id", f"image-{index:02d}"),
                    "title": item.get("title", ""),
                    "image_path": str(image_path.relative_to(ROOT)).replace("\\", "/"),
                    "image_abs_path": str(image_path.resolve()),
                    "review_status": item.get("review_status", ""),
                }
            )
    return errors, normalized_images


def render_markdown(result: dict[str, Any]) -> str:
    image_lines = "\n".join(
        f"{item['index']}. `{item['image_abs_path']}`" for item in result["images"]
    )
    tag_lines = "\n".join(f"- {tag}" for tag in result["tags"])
    return (
        "# 小红书发布内容包\n\n"
        f"- 内容 ID：`{result['content_id']}`\n"
        f"- 小红书发布：手动\n"
        f"- 飞书交付：直接发送完整内容\n"
        f"- 自动发布：已关闭\n"
        f"- 生成时间：`{result['created_at']}`\n\n"
        "## 标题\n\n"
        f"{result['title']}\n\n"
        "## 正文\n\n"
        f"{result['body_full']}\n\n"
        "## 标签\n\n"
        f"{tag_lines}\n\n"
        "## 图片\n\n"
        f"{image_lines}\n\n"
        "## 手动操作提示\n\n"
        "- 发布前自己通读一遍正文，确认表达符合账号口吻。\n"
        "- 在小红书发布页手动上传图片，按上方顺序排列。\n"
        "- 标签在小红书发布页手动选择为话题。\n"
        "- 原创声明按实际情况开启。\n"
        "- 不使用自动化发布。\n"
    )


def build_package() -> dict[str, Any]:
    package = load_json(ASSET_PACKAGE)
    if not package:
        raise FileNotFoundError(ASSET_PACKAGE)

    errors, images = validate_assets(package)
    tags = [normalize_tag(tag) for tag in package.get("tags", []) if normalize_tag(tag)]
    status = "manual_package_ready" if not errors else "blocked"
    result = {
        "status": status,
        "blocked_reasons": errors,
        "review_id": package.get("review_id", ""),
        "content_id": package.get("content_id", ""),
        "platform": "xiaohongshu",
        "publish_mode": "manual_only",
        "auto_publish_enabled": False,
        "delivery_mode": "feishu_package_card",
        "title": str(package.get("title", "")).strip(),
        "body_full": str(package.get("body_full", "")).strip(),
        "body_char_count": len(str(package.get("body_full", "")).strip()),
        "tags": tags,
        "images": images,
        "source_urls": package.get("source_urls", []),
        "source_verification": package.get("source_verification", {}),
        "created_at": now(),
    }
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result = build_package()
    PACKAGE_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    PACKAGE_MD.write_text(render_markdown(result), encoding="utf-8")
    print(f"status: {result['status']}")
    print(f"package: {PACKAGE_MD}")
    return 0 if result["status"] == "manual_package_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
