#!/usr/bin/env python3
"""Content history helpers for duplicate-safe Xiaohongshu topic selection."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "content-history"
HISTORY_PATH = HISTORY_DIR / "sent-posts.jsonl"


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_jsonl(path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise ValueError(f"{path}:{line_no} must contain a JSON object")
        records.append(data)
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records)
    path.write_text((text + "\n") if text else "", encoding="utf-8")


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"https?://", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_github_repo(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    text = raw.replace("\\", "/").strip().rstrip("/")
    if re.match(r"^[a-z]+://", text, re.IGNORECASE):
        parsed = urlparse(text)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc != "github.com":
            return ""
        text = parsed.path.strip("/")
    else:
        text = re.sub(r"^www\.", "", text, flags=re.IGNORECASE)
        if text.lower().startswith("github.com/"):
            text = text[len("github.com/") :]
        else:
            first_part = text.split("/", 1)[0]
            if "." in first_part:
                return ""
    text = text.split("#", 1)[0].split("?", 1)[0].strip("/")
    parts = [part for part in text.split("/") if part]
    if len(parts) < 2:
        return ""
    owner = parts[0].lower()
    repo = re.sub(r"\.git$", "", parts[1], flags=re.IGNORECASE).lower()
    if not re.fullmatch(r"[a-z0-9_.-]+", owner) or not re.fullmatch(r"[a-z0-9_.-]+", repo):
        return ""
    if not owner or not repo:
        return ""
    return f"github.com/{owner}/{repo}"


def normalize_source_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    github = normalize_github_repo(text)
    if github:
        return github
    parsed = urlparse(text if re.match(r"^[a-z]+://", text, re.IGNORECASE) else f"https://{text}")
    if not parsed.netloc:
        return normalize_text(text)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+", "/", parsed.path).rstrip("/").lower()
    return f"{netloc}{path}"


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def source_keys_from_spec(spec: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    project_facts = spec.get("project_facts")
    if isinstance(project_facts, dict):
        for field in ["repo", "url", "source_url"]:
            value = project_facts.get(field)
            _append_unique(keys, normalize_source_url(value))

    for value in spec.get("source_urls", []) if isinstance(spec.get("source_urls"), list) else []:
        _append_unique(keys, normalize_source_url(value))

    insight_pack = spec.get("insight_pack")
    if isinstance(insight_pack, dict):
        source_facts = insight_pack.get("source_facts")
        if isinstance(source_facts, list):
            for fact in source_facts:
                if isinstance(fact, dict):
                    _append_unique(keys, normalize_source_url(fact.get("source_url")))

    verification = spec.get("source_verification")
    if isinstance(verification, dict):
        for field in ["source_url", "url"]:
            _append_unique(keys, normalize_source_url(verification.get(field)))

    topic_key = topic_key_from_spec(spec, keys)
    _append_unique(keys, topic_key)
    return keys


def topic_key_from_spec(spec: dict[str, Any], source_keys: list[str] | None = None) -> str:
    history = spec.get("history")
    if isinstance(history, dict):
        for field in ["topic_key", "dedupe_key"]:
            value = normalize_source_url(history.get(field)) or normalize_text(history.get(field))
            if value:
                return value
    for field in ["topic_key", "dedupe_key"]:
        value = normalize_source_url(spec.get(field)) or normalize_text(spec.get(field))
        if value:
            return value
    keys = source_keys or []
    for key in keys:
        if key.startswith("github.com/"):
            return key
    if keys:
        return keys[0]
    base = f"{spec.get('content_type', '')}:{spec.get('topic', '')}"
    return normalize_text(base)


def allow_repeat(spec: dict[str, Any]) -> bool:
    history = spec.get("history")
    if isinstance(history, dict) and history.get("allow_repeat") is True:
        return True
    dedupe = spec.get("dedupe")
    return isinstance(dedupe, dict) and dedupe.get("allow_repeat") is True


def candidate_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    source_keys = source_keys_from_spec(spec)
    topic_key = topic_key_from_spec(spec, source_keys)
    return {
        "delivery_id": str(spec.get("review_id", "")).strip(),
        "content_id": str(spec.get("content_id", "")).strip(),
        "title": str(spec.get("title", "")).strip(),
        "topic": str(spec.get("topic", "")).strip(),
        "content_type": str(spec.get("content_type", "")).strip(),
        "topic_key": topic_key,
        "source_keys": source_keys,
    }


def keys_from_record(record: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for value in record.get("source_keys", []) if isinstance(record.get("source_keys"), list) else []:
        normalized = normalize_source_url(value) or normalize_text(value)
        if normalized:
            keys.add(normalized)
    for field in ["topic_key", "repo", "source_url"]:
        normalized = normalize_source_url(record.get(field)) or normalize_text(record.get(field))
        if normalized:
            keys.add(normalized)
    return keys


def check_duplicate_history(spec: dict[str, Any], records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    records = load_jsonl() if records is None else records
    candidate = candidate_from_spec(spec)
    candidate_keys = set(candidate["source_keys"])
    matches: list[dict[str, Any]] = []
    for record in records:
        reasons: list[str] = []
        if candidate["delivery_id"] and candidate["delivery_id"] == str(record.get("delivery_id", "")).strip():
            reasons.append("same_delivery_id")
        if candidate["content_id"] and candidate["content_id"] == str(record.get("content_id", "")).strip():
            reasons.append("same_content_id")
        record_keys = keys_from_record(record)
        shared_keys = sorted(candidate_keys & record_keys)
        if shared_keys:
            reasons.append("same_source_or_topic_key")
        if candidate["topic_key"] and candidate["topic_key"] == str(record.get("topic_key", "")).strip():
            reasons.append("same_topic_key")
        if reasons:
            matches.append(
                {
                    "reasons": sorted(set(reasons)),
                    "shared_keys": shared_keys,
                    "delivery_id": record.get("delivery_id", ""),
                    "content_id": record.get("content_id", ""),
                    "title": record.get("title", ""),
                    "topic": record.get("topic", ""),
                    "sent_at": record.get("sent_at", ""),
                    "message_id": record.get("message_id", ""),
                }
            )
    status = "duplicate" if matches else "ok"
    if matches and allow_repeat(spec):
        status = "allowed_repeat"
    return {
        "status": status,
        "candidate": candidate,
        "matches": matches,
        "history_path": str(HISTORY_PATH),
        "checked_at": now(),
    }


def assert_not_duplicate(spec: dict[str, Any]) -> dict[str, Any]:
    result = check_duplicate_history(spec)
    if result["status"] == "duplicate":
        details = []
        for match in result["matches"][:3]:
            shared = ",".join(match.get("shared_keys", []))
            details.append(
                f"{match.get('delivery_id') or match.get('content_id')} "
                f"{match.get('title')} [{shared}]"
            )
        raise ValueError("duplicate content history: " + "; ".join(details))
    return result


def build_sent_record(
    package: dict[str, Any],
    delivery: dict[str, Any],
    send_result: dict[str, Any],
) -> dict[str, Any]:
    source_keys = source_keys_from_spec(package)
    topic_key = topic_key_from_spec(package, source_keys)
    return {
        "schema_version": 1,
        "record_type": "xhs_sent_post",
        "delivery_id": str(send_result.get("delivery_id") or delivery.get("delivery_id") or package.get("review_id") or ""),
        "content_id": str(delivery.get("content_id") or package.get("content_id") or ""),
        "message_id": str(send_result.get("message_id") or ""),
        "title": str(delivery.get("title") or package.get("title") or ""),
        "topic": str(delivery.get("topic") or package.get("topic") or ""),
        "content_type": str(package.get("content_type") or delivery.get("content_type") or ""),
        "topic_key": topic_key,
        "source_keys": source_keys,
        "source_urls": package.get("source_urls", []),
        "image_slug": str(package.get("image_slug") or ""),
        "sent_at": str(send_result.get("created_at") or now()),
        "created_at": now(),
    }


def upsert_sent_record(record: dict[str, Any]) -> None:
    records = load_jsonl()
    delivery_id = str(record.get("delivery_id", "")).strip()
    content_id = str(record.get("content_id", "")).strip()
    next_records: list[dict[str, Any]] = []
    replaced = False
    for existing in records:
        same_delivery = delivery_id and delivery_id == str(existing.get("delivery_id", "")).strip()
        same_content = content_id and content_id == str(existing.get("content_id", "")).strip()
        if same_delivery or same_content:
            if not replaced:
                next_records.append(record)
                replaced = True
            continue
        next_records.append(existing)
    if not replaced:
        next_records.append(record)
    write_jsonl(next_records)
