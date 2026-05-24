#!/usr/bin/env python3
"""Inspect or validate Xiaohongshu sent-post history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from history_utils import HISTORY_PATH, check_duplicate_history, load_jsonl


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check XHS content history")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-current", action="store_true", help="Check asset-generation/content_spec.json against sent history")
    mode.add_argument("--list", action="store_true", help="List recent sent history records")
    parser.add_argument("--spec", default=str(ROOT / "asset-generation" / "content_spec.json"), help="Path to content_spec.json")
    parser.add_argument("--limit", type=int, default=20, help="Maximum records to print in list mode")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.list:
        records = load_jsonl()
        recent = records[-max(args.limit, 1) :]
        if args.json:
            print(json.dumps({"history_path": str(HISTORY_PATH), "records": recent}, ensure_ascii=False, indent=2))
        else:
            print(f"history_path: {HISTORY_PATH}")
            print(f"records: {len(records)}")
            for record in recent:
                print(
                    f"- {record.get('sent_at', '')} | {record.get('title', '')} | "
                    f"{record.get('topic_key', '')} | {record.get('message_id', '')}"
                )
        return 0

    spec = load_json(Path(args.spec))
    result = check_duplicate_history(spec)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"history_path: {result['history_path']}")
        print(f"topic_key: {result['candidate']['topic_key']}")
        print(f"source_keys: {', '.join(result['candidate']['source_keys'])}")
        for match in result["matches"]:
            shared = ",".join(match.get("shared_keys", []))
            print(f"match: {match.get('delivery_id') or match.get('content_id')} | {match.get('title')} | {shared}")
    return 2 if result["status"] == "duplicate" else 0


if __name__ == "__main__":
    raise SystemExit(main())
