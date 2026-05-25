#!/usr/bin/env python3
"""Deterministic copy-quality gate for Xiaohongshu creator-style posts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "asset-generation" / "outputs" / "copy-quality-report.json"

BLOCKED_PHRASES = [
    "它干的事很简单",
    "它做的事很简单",
    "它的好处是",
    "我会先看一件事",
    "我会把它收藏给三类人",
    "我觉得它最适合三类人",
    "要注意",
    "截至我这次核验",
    "真正值得看的",
    "值得单独开个 demo",
    "值得单独开一个 demo",
    "适合三类人",
    "首先，",
    "其次，",
    "最后，",
    "首先：",
    "其次：",
    "最后：",
    "综上",
    "总结一下",
    "值得关注",
    "很有潜力",
    "可以提升效率",
    "上手简单",
    "如果你是",
]

BLAND_TITLE_PATTERNS = [
    re.compile(r"介绍$"),
    re.compile(r"是什么$"),
    re.compile(r"使用指南$"),
    re.compile(r"教程$"),
    re.compile(r"^.+(项目|工具|框架)推荐$"),
]

TITLE_HOOK_SIGNALS = [
    "别",
    "真",
    "有点",
    "终于",
    "居然",
    "原来",
    "我",
    "你",
    "先",
    "顺",
    "香",
    "救",
    "坑",
    "烦",
    "稳",
    "藏",
    "收藏",
    "试",
    "看",
    "为什么",
    "怎么",
    "？",
    "?",
]

SCENE_SIGNALS = [
    "我最近",
    "最近在",
    "我本来",
    "翻到",
    "看到",
    "接 API",
    "比模型",
    "选 agent",
    "拿它试",
    "做 demo",
    "做项目",
    "调试",
]

JUDGMENT_SIGNALS = [
    "我觉得",
    "我挺",
    "我比较",
    "让我",
    "我会",
    "我想",
    "我不太",
    "别指望",
    "真的",
    "挺",
    "烦",
    "舒服",
    "顺",
    "不算重",
]

FRICTION_SIGNALS = [
    "烦",
    "麻烦",
    "坑",
    "累",
    "歪",
    "黑盒",
    "闭眼猜",
    "别指望",
    "不应该",
    "不用每次",
    "靠人手",
    "跑飞",
    "工程债",
]

MANUAL_STYLE_SIGNALS = [
    "是一个",
    "用户可以",
    "它支持",
    "该项目",
    "适用于",
    "核心包是",
]

WARNING_PATTERNS = [
    (re.compile(r"^我会", re.MULTILINE), "multiple creator-judgment sentences starting with 我会 can sound templated"),
    (re.compile(r"^它", re.MULTILINE), "paragraphs starting with 它 often read like product explanation"),
    (re.compile(r"^这个项目", re.MULTILINE), "paragraphs starting with 这个项目 often read like a report"),
]

LISTICLE_PATTERNS = [
    re.compile(r"三类人[:：]"),
    re.compile(r"三种(?:入口|方式|场景)"),
    re.compile(r"一类人[:：].*二类人[:：].*三类人", re.S),
]


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def write_report(result: dict[str, Any], path: Path = REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_copy_quality(spec: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic pass/fail report for human-feeling XHS copy."""
    title = str(spec.get("title", "")).strip()
    body = str(spec.get("body_full", "")).strip()
    tags = spec.get("tags", [])
    blockers: list[str] = []
    warnings: list[str] = []

    if not title:
        blockers.append("title_missing")
    if len(title) > 20:
        blockers.append(f"title_too_long:{len(title)}/20")
    if title and any(pattern.search(title) for pattern in BLAND_TITLE_PATTERNS):
        blockers.append("title_lacks_xhs_hook")
    elif title and not any(signal in title for signal in TITLE_HOOK_SIGNALS):
        blockers.append("title_lacks_xhs_hook")
    if not body:
        blockers.append("body_missing")
    if len(body) > 1000:
        blockers.append(f"body_too_long:{len(body)}/1000")
    if not isinstance(tags, list) or not 5 <= len([tag for tag in tags if str(tag).strip()]) <= 8:
        blockers.append("tags_count_must_be_5_to_8")

    for phrase in BLOCKED_PHRASES:
        if phrase in body:
            blockers.append(f"blocked_template_phrase:{phrase}")

    for pattern in LISTICLE_PATTERNS:
        if pattern.search(body):
            blockers.append(f"blocked_listicle_pattern:{pattern.pattern}")

    if body and not any(signal in body for signal in SCENE_SIGNALS):
        blockers.append("missing_creator_scene")
    if body and not any(signal in body for signal in JUDGMENT_SIGNALS):
        blockers.append("missing_personal_judgment")
    if body and not any(signal in body for signal in FRICTION_SIGNALS):
        blockers.append("missing_natural_friction")
    manual_hits = [signal for signal in MANUAL_STYLE_SIGNALS if signal in body]
    if len(manual_hits) >= 4:
        blockers.append("tool_manual_or_training_style")

    for pattern, message in WARNING_PATTERNS:
        hits = pattern.findall(body)
        if len(hits) >= 2:
            warnings.append(message)

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", body) if part.strip()]
    if len(paragraphs) >= 4:
        similar_openers = sum(1 for part in paragraphs if part.startswith(("它", "这个项目", "我会", "要注意")))
        if similar_openers >= 2:
            warnings.append("paragraph openings are too regular and report-like")

    score = 100 - 20 * len(blockers) - 5 * len(warnings)
    score = max(0, min(100, score))
    status = "pass" if not blockers and score >= 80 else "fail"
    return {
        "status": status,
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "checked_at": now(),
        "policy": "xhs_human_creator_hard_gate_v1",
    }


def assert_copy_quality(spec: dict[str, Any], *, report_path: Path = REPORT_PATH) -> dict[str, Any]:
    result = validate_copy_quality(spec)
    write_report(result, report_path)
    if result["status"] != "pass":
        blockers = "; ".join(result["blockers"][:8])
        raise ValueError(f"copy quality blocked: {blockers}")
    return result


def main() -> int:
    spec_path = ROOT / "asset-generation" / "content_spec.json"
    result = validate_copy_quality(load_json(spec_path))
    write_report(result)
    print(f"status: {'copy_ready' if result['status'] == 'pass' else 'copy_blocked'}")
    print(f"score: {result['score']}")
    if result["blockers"]:
        print("blockers: " + ", ".join(result["blockers"]))
    if result["warnings"]:
        print("warnings: " + ", ".join(result["warnings"]))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
