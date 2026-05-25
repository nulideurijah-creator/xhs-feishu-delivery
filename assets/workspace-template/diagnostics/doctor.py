#!/usr/bin/env python3
"""Diagnose whether a workspace is ready for manual XHS Feishu delivery.

The doctor is intentionally read-only. It checks local files, config, generated
asset metadata, image availability, and Feishu environment fields. It does not
call Feishu, generate images, or publish anything.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "diagnostics" / "outputs"
REPORT_JSON = OUT / "doctor-report.json"
REPORT_MD = OUT / "doctor-report.md"

REQUIRED_DIRS = [
    "asset-generation",
    "image-generation",
    "publish-mainline",
    "feishu-delivery",
]

REQUIRED_FILES = [
    "asset-generation/content_spec.json",
    "asset-generation/generate_current_assets.py",
    "publish-mainline/build_manual_publish_package.py",
    "publish-mainline/preflight.py",
    "feishu-delivery/build_delivery_card.py",
    "feishu-delivery/send_delivery_card.py",
    "feishu-delivery/check_feishu_ready.py",
    ".baoyu-skills/baoyu-image-cards/EXTEND.md",
]

CONTENT_REQUIRED = [
    "review_id",
    "content_id",
    "title",
    "topic",
    "content_type",
    "insight_pack",
    "body_full",
    "tags",
    "image_slug",
    "pages",
]

ALLOWED_CONTENT_TYPES = {
    "github_project_recommendation",
    "ai_product_release",
    "ai_industry_shift",
    "ai_technical_breakthrough",
}

FEISHU_REQUIRED = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_RECEIVE_ID_TYPE",
    "FEISHU_RECEIVE_ID",
]

EXPECTED_SKILL_MARKERS = [
    "aihot",
    "agent-reach",
    "dbs-xhs-title",
    "editor_prompt",
    "baoyu-image-cards",
    "imagegen",
]

EXPECTED_IMAGE_STYLE = "xhs-warm-cute-open-source"
EXPECTED_IMAGE_BACKEND = "preferred_image_backend: codex-imagegen"

DANGEROUS_FILE_NAMES = {
    "cookies.json",
    "render_current_cards.py",
    "xhs-login-qrcode.png",
}

DANGEROUS_PATH_FRAGMENTS = [
    ".playwright-mcp",
    "playwright-mcp",
    "xiaohongshu" + "-mcp",
    "ws" + "_review_server",
    "callback" + "_server",
    "local" + "tunnel",
    "ng" + "rok",
]


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def add(condition: bool, items: list[str], message: str) -> None:
    if condition:
        items.append(message)


def check_structure(blockers: list[str]) -> None:
    for relative in REQUIRED_DIRS:
        add(not (ROOT / relative).is_dir(), blockers, f"missing_dir:{relative}")
    for relative in REQUIRED_FILES:
        add(not (ROOT / relative).is_file(), blockers, f"missing_file:{relative}")


def check_baoyu_config(blockers: list[str]) -> dict[str, Any]:
    path = ROOT / ".baoyu-skills" / "baoyu-image-cards" / "EXTEND.md"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    checks = {
        "exists": path.exists(),
        "style": EXPECTED_IMAGE_STYLE in text,
        "backend": EXPECTED_IMAGE_BACKEND in text,
        "watermark_disabled": "enabled: false" in text,
    }
    for key, ok in checks.items():
        add(not ok, blockers, f"baoyu_config_{key}_missing")
    return checks


def check_content_spec(blockers: list[str]) -> dict[str, Any]:
    path = ROOT / "asset-generation" / "content_spec.json"
    spec = load_json(path)
    if not spec:
        blockers.append("content_spec_missing_or_empty")
        return {"exists": path.exists()}
    for key in CONTENT_REQUIRED:
        add(not spec.get(key), blockers, f"content_spec_missing:{key}")
    title = str(spec.get("title", ""))
    body = str(spec.get("body_full", ""))
    tags = spec.get("tags", [])
    pages = spec.get("pages", [])
    content_type = str(spec.get("content_type", ""))
    insight_pack = spec.get("insight_pack", {})
    add(len(title) > 20, blockers, f"title_too_long:{len(title)}/20")
    add(len(body) > 1000, blockers, f"body_too_long:{len(body)}/1000")
    add(content_type not in ALLOWED_CONTENT_TYPES, blockers, f"invalid_content_type:{content_type}")
    add(not isinstance(tags, list) or not tags, blockers, "tags_missing")
    add(not isinstance(pages, list) or len(pages) != 6, blockers, "pages_not_6")
    check_insight_pack(insight_pack, blockers)
    return {
        "exists": True,
        "title": title,
        "title_length": len(title),
        "content_type": content_type,
        "body_length": len(body),
        "tag_count": len(tags) if isinstance(tags, list) else 0,
        "page_count": len(pages) if isinstance(pages, list) else 0,
        "image_slug": spec.get("image_slug", ""),
    }


def check_insight_pack(pack: Any, blockers: list[str]) -> None:
    if not isinstance(pack, dict):
        blockers.append("insight_pack_invalid")
        return
    for key in [
        "core_hook",
        "one_sentence_event",
        "why_it_matters",
        "key_takeaways",
        "use_cases",
        "actionable_framework",
        "source_facts",
        "boundaries",
        "reader_payoff",
    ]:
        add(not pack.get(key), blockers, f"insight_pack_missing:{key}")

    framework = pack.get("actionable_framework", {})
    if not isinstance(framework, dict):
        blockers.append("insight_pack_actionable_framework_invalid")
    else:
        add(not str(framework.get("name", "")).strip(), blockers, "insight_pack_framework_name_missing")
        items = framework.get("items", [])
        add(not isinstance(items, list) or not items, blockers, "insight_pack_framework_items_missing")

    source_facts = pack.get("source_facts", [])
    add(not isinstance(source_facts, list) or len(source_facts) < 2, blockers, "insight_pack_source_facts_lt_2")
    if isinstance(source_facts, list):
        for index, item in enumerate(source_facts, start=1):
            invalid = (
                not isinstance(item, dict)
                or not str(item.get("claim", "")).strip()
                or not str(item.get("source_url", "")).strip()
            )
            add(invalid, blockers, f"insight_pack_source_fact_invalid:{index}")


def check_asset_package(blockers: list[str]) -> dict[str, Any]:
    path = ROOT / "asset-generation" / "outputs" / "current-publish-assets.json"
    package = load_json(path)
    if not package:
        blockers.append("asset_package_missing:run_asset_generator")
        return {"exists": path.exists(), "images_ready": 0, "images_total": 0}

    images = package.get("images", [])
    missing_images: list[str] = []
    if not isinstance(images, list) or len(images) != 6:
        blockers.append("asset_package_images_not_6")
        images = []
    for item in images:
        if not isinstance(item, dict):
            missing_images.append("invalid_image_item")
            continue
        relative = str(item.get("image_path", ""))
        image_path = ROOT / relative
        if not image_path.exists() or image_path.stat().st_size <= 0:
            missing_images.append(relative or "missing_image_path")

    add(bool(missing_images), blockers, f"images_missing:{len(missing_images)}")

    source_text = json.dumps(package.get("skill_sources", {}), ensure_ascii=False)
    missing_markers = [marker for marker in EXPECTED_SKILL_MARKERS if marker not in source_text]
    add(bool(missing_markers), blockers, "skill_chain_metadata_missing:" + ",".join(missing_markers))

    return {
        "exists": True,
        "status": package.get("status", ""),
        "images_ready": len(images) - len(missing_images),
        "images_total": len(images),
        "missing_images": missing_images,
        "skill_sources": package.get("skill_sources", {}),
    }


def check_feishu_env(blockers: list[str]) -> dict[str, Any]:
    path = ROOT / "feishu-delivery" / ".env"
    env = load_env(path)
    if not path.exists():
        blockers.append("feishu_env_missing")
        return {"exists": False}
    missing = [key for key in FEISHU_REQUIRED if not env.get(key)]
    add(bool(missing), blockers, "feishu_env_missing_keys:" + ",".join(missing))
    return {
        "exists": True,
        "receive_id_type": env.get("FEISHU_RECEIVE_ID_TYPE", ""),
        "receive_id_present": bool(env.get("FEISHU_RECEIVE_ID")),
        "missing_keys": missing,
        "network_checked": False,
    }


def check_risky_artifacts(blockers: list[str]) -> list[str]:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        lowered = relative.lower()
        if path.name in DANGEROUS_FILE_NAMES:
            hits.append(relative)
            continue
        if any(fragment in lowered for fragment in DANGEROUS_PATH_FRAGMENTS):
            hits.append(relative)
    add(bool(hits), blockers, "risky_artifacts_found:" + ",".join(hits[:5]))
    return hits


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XHS Feishu Delivery Doctor",
        "",
        f"- status: `{report['status']}`",
        f"- ready: `{str(report['ready']).lower()}`",
        f"- checked_at: `{report['checked_at']}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = report.get("blocked_reasons", [])
    if blockers:
        lines.extend(f"- `{item}`" for item in blockers)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- images: `{report['asset_package'].get('images_ready', 0)}/{report['asset_package'].get('images_total', 0)}`",
            f"- feishu_env: `{str(report['feishu_env'].get('exists', False)).lower()}`",
            f"- risky_artifacts: `{len(report.get('risky_artifacts', []))}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report() -> dict[str, Any]:
    blockers: list[str] = []
    check_structure(blockers)
    report = {
        "checked_at": now(),
        "workspace": str(ROOT),
        "structure_checked": True,
        "baoyu_config": check_baoyu_config(blockers),
        "content_spec": check_content_spec(blockers),
        "asset_package": check_asset_package(blockers),
        "feishu_env": check_feishu_env(blockers),
        "risky_artifacts": check_risky_artifacts(blockers),
    }
    report["blocked_reasons"] = sorted(set(blockers))
    report["ready"] = not report["blocked_reasons"]
    report["status"] = "ready_to_deliver" if report["ready"] else "blocked"
    return report


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    if report["blocked_reasons"]:
        print("blocked_reasons: " + ", ".join(report["blocked_reasons"]))
    print(f"report: {REPORT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
