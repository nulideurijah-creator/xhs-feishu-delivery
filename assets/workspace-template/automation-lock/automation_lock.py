#!/usr/bin/env python3
"""Workspace-level lock for Codex automation runs.

Codex automations may do research, write content_spec.json, and generate images
before the normal packaging runner starts. The runner's own lock only protects
the final packaging steps, so this separate lock covers the whole automation.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / ".xhs_automation.lock"
DEFAULT_TTL_SECONDS = 3 * 60 * 60


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def read_lock() -> dict:
    if not LOCK_PATH.exists():
        return {}
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def lock_age_seconds() -> float:
    return time.time() - LOCK_PATH.stat().st_mtime


def acquire(owner: str, ttl_seconds: int) -> int:
    if LOCK_PATH.exists() and lock_age_seconds() <= ttl_seconds:
        data = read_lock()
        print(
            json.dumps(
                {
                    "status": "busy",
                    "lock_path": str(LOCK_PATH),
                    "owner": data.get("owner", ""),
                    "pid": data.get("pid", ""),
                    "created_at": data.get("created_at", ""),
                    "age_seconds": int(lock_age_seconds()),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    if LOCK_PATH.exists():
        LOCK_PATH.unlink()

    payload = {
        "owner": owner,
        "pid": os.getpid(),
        "created_at": now(),
        "ttl_seconds": ttl_seconds,
    }
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except FileExistsError:
        return acquire(owner, ttl_seconds)
    print(json.dumps({"status": "acquired", "lock_path": str(LOCK_PATH), **payload}, ensure_ascii=False, indent=2))
    return 0


def release(owner: str) -> int:
    if not LOCK_PATH.exists():
        print(json.dumps({"status": "not_found", "lock_path": str(LOCK_PATH)}, ensure_ascii=False, indent=2))
        return 0
    data = read_lock()
    existing_owner = str(data.get("owner", ""))
    if existing_owner and existing_owner != owner:
        print(
            json.dumps(
                {
                    "status": "owner_mismatch",
                    "lock_path": str(LOCK_PATH),
                    "owner": existing_owner,
                    "requested_owner": owner,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    LOCK_PATH.unlink()
    print(json.dumps({"status": "released", "lock_path": str(LOCK_PATH), "owner": owner}, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    if not LOCK_PATH.exists():
        print(json.dumps({"status": "free", "lock_path": str(LOCK_PATH)}, ensure_ascii=False, indent=2))
        return 0
    data = read_lock()
    print(json.dumps({"status": "locked", "lock_path": str(LOCK_PATH), **data}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the XHS automation workspace lock")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--acquire", action="store_true", help="Acquire the automation lock")
    mode.add_argument("--release", action="store_true", help="Release the automation lock")
    mode.add_argument("--status", action="store_true", help="Print lock status")
    parser.add_argument("--owner", default="xhs-automation", help="Automation id or owner name")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS, help="Stale lock TTL")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.acquire:
        return acquire(args.owner, args.ttl_seconds)
    if args.release:
        return release(args.owner)
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
