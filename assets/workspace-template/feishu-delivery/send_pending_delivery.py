#!/usr/bin/env python3
"""Queue and send Feishu deliveries outside Codex automation networking.

Codex background automations can prepare a complete local package but may run
under a Windows network context that blocks sockets to open.feishu.cn. This
module lets the automation write a local pending marker, then a normal Windows
scheduled task sends that exact package through send_delivery_card.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"

REQUEST_PATH = OUT / "delivery-request.json"
CARD_PATH = OUT / "delivery-card.json"
ASSET_PACKAGE_PATH = ROOT / "asset-generation" / "outputs" / "current-publish-assets.json"
PENDING_PATH = OUT / "pending-send.json"
PENDING_RESULT_PATH = OUT / "pending-send-result.json"
PENDING_HISTORY_PATH = OUT / "pending-send-history.jsonl"
SEND_RESULT_PATH = OUT / "send-result.json"
AUTOMATION_LOCK_PATH = ROOT / ".xhs_automation.lock"
DELIVERY_LOCK_PATH = ROOT / ".xhs_delivery.lock"
HISTORY_PATH = ROOT / "content-history" / "sent-posts.jsonl"

sys.path.insert(0, str(WORK_DIR))
import send_delivery_card  # noqa: E402


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sent_record_exists(delivery_id: str, content_id: str) -> bool:
    if not HISTORY_PATH.exists():
        return False
    for line in HISTORY_PATH.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        has_message = bool(record.get("message_id"))
        if has_message and delivery_id and record.get("delivery_id") == delivery_id:
            return True
        if has_message and content_id and record.get("content_id") == content_id:
            return True
    return False


def load_validated_package() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    delivery = send_delivery_card.load_json(REQUEST_PATH)
    card = send_delivery_card.load_json(CARD_PATH)
    asset_package = load_json(ASSET_PACKAGE_PATH) if ASSET_PACKAGE_PATH.exists() else {}
    send_delivery_card.validate_card(card)
    image_paths = send_delivery_card.validate_images(delivery)
    return delivery, card, asset_package, len(image_paths)


def build_marker() -> dict[str, Any]:
    delivery, _card, _asset_package, image_count = load_validated_package()
    delivery_id = str(delivery.get("delivery_id") or "")
    content_id = str(delivery.get("content_id") or "")
    if not delivery_id:
        raise ValueError("delivery_id is required before queueing")
    if sent_record_exists(delivery_id, content_id):
        return {
            "status": "already_sent",
            "queued": False,
            "delivery_id": delivery_id,
            "content_id": content_id,
            "title": delivery.get("title", ""),
            "image_count": image_count,
            "created_at": now(),
        }
    previous = load_json(PENDING_PATH) if PENDING_PATH.exists() else {}
    attempts = int(previous.get("attempts", 0)) if previous.get("delivery_id") == delivery_id else 0
    return {
        "status": "pending",
        "queued": True,
        "delivery_id": delivery_id,
        "content_id": content_id,
        "title": delivery.get("title", ""),
        "image_count": image_count,
        "workspace": str(ROOT),
        "request_sha256": file_sha256(REQUEST_PATH),
        "card_sha256": file_sha256(CARD_PATH),
        "asset_package_sha256": file_sha256(ASSET_PACKAGE_PATH) if ASSET_PACKAGE_PATH.exists() else "",
        "attempts": attempts,
        "queued_at": now(),
    }


def queue_current() -> int:
    marker = build_marker()
    if marker["status"] == "already_sent":
        if PENDING_PATH.exists():
            PENDING_PATH.unlink()
        write_json(PENDING_RESULT_PATH, marker)
        print(json.dumps(marker, ensure_ascii=False, indent=2))
        return 0
    write_json(PENDING_PATH, marker)
    result = {**marker, "status": "queued", "created_at": now()}
    write_json(PENDING_RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def lock_active() -> str:
    if DELIVERY_LOCK_PATH.exists():
        return str(DELIVERY_LOCK_PATH)
    if AUTOMATION_LOCK_PATH.exists():
        return str(AUTOMATION_LOCK_PATH)
    return ""


def current_hashes_match(marker: dict[str, Any]) -> bool:
    if not REQUEST_PATH.exists() or not CARD_PATH.exists():
        return False
    if marker.get("request_sha256") != file_sha256(REQUEST_PATH):
        return False
    if marker.get("card_sha256") != file_sha256(CARD_PATH):
        return False
    expected_asset_hash = marker.get("asset_package_sha256") or ""
    if expected_asset_hash and (
        not ASSET_PACKAGE_PATH.exists() or expected_asset_hash != file_sha256(ASSET_PACKAGE_PATH)
    ):
        return False
    return True


def complete_pending(marker: dict[str, Any], result: dict[str, Any]) -> None:
    record = {**marker, **result, "completed_at": now()}
    append_jsonl(PENDING_HISTORY_PATH, record)
    write_json(PENDING_RESULT_PATH, record)
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()


def send_pending() -> int:
    if not PENDING_PATH.exists():
        result = {"status": "no_pending", "pending": False, "created_at": now()}
        write_json(PENDING_RESULT_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    marker = load_json(PENDING_PATH)
    delivery_id = str(marker.get("delivery_id") or "")
    content_id = str(marker.get("content_id") or "")
    active_lock = lock_active()
    if active_lock:
        result = {
            **marker,
            "status": "deferred_lock_active",
            "pending": True,
            "lock_path": active_lock,
            "checked_at": now(),
        }
        write_json(PENDING_RESULT_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if sent_record_exists(delivery_id, content_id):
        result = {**marker, "status": "already_sent", "pending": False}
        complete_pending(marker, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not current_hashes_match(marker):
        result = {
            **marker,
            "status": "blocked_current_package_changed",
            "pending": True,
            "checked_at": now(),
        }
        write_json(PENDING_RESULT_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    completed = subprocess.run(
        [sys.executable, str(WORK_DIR / "send_delivery_card.py"), "--send"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    marker["attempts"] = int(marker.get("attempts", 0)) + 1
    marker["last_attempt_at"] = now()

    if completed.returncode != 0:
        result = {
            **marker,
            "status": "send_failed",
            "pending": True,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
        write_json(PENDING_PATH, marker)
        write_json(PENDING_RESULT_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return completed.returncode

    send_result = load_json(SEND_RESULT_PATH) if SEND_RESULT_PATH.exists() else {}
    result = {
        **marker,
        "status": "sent",
        "pending": False,
        "message_id": send_result.get("message_id", ""),
        "image_count": send_result.get("image_count", marker.get("image_count", 0)),
        "stdout": completed.stdout[-4000:],
    }
    complete_pending(marker, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    result = {
        "status": "pending" if PENDING_PATH.exists() else "no_pending",
        "pending_path": str(PENDING_PATH),
        "pending": load_json(PENDING_PATH) if PENDING_PATH.exists() else None,
        "last_result": load_json(PENDING_RESULT_PATH) if PENDING_RESULT_PATH.exists() else None,
        "checked_at": now(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Queue or send pending Feishu delivery")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--queue", action="store_true", help="Queue current local package for the Windows sender")
    mode.add_argument("--send-pending", action="store_true", help="Send the queued package if one exists")
    mode.add_argument("--status", action="store_true", help="Show pending-send status")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.queue:
            return queue_current()
        if args.send_pending:
            return send_pending()
        return status()
    except Exception as exc:  # noqa: BLE001 - CLI should return concise errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
