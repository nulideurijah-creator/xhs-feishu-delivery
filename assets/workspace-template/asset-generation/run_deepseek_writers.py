#!/usr/bin/env python3
"""Run the required DeepSeek copy and image-prompt writers.

This wrapper exists for unattended automations on Windows where Codex's
background process can be denied direct socket access. The automation triggers
an on-demand Windows task, and that normal local process runs this wrapper.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"
SPEC_PATH = WORK_DIR / "content_spec.json"
RESULT_PATH = OUT / "deepseek-writers-result.json"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_script(label: str, script_name: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(WORK_DIR / script_name)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return {
        "label": label,
        "script": f"asset-generation/{script_name}",
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "finished_at": now(),
    }


def spec_generation_status() -> dict[str, Any]:
    if not SPEC_PATH.exists():
        return {"copy_ready": False, "image_prompts_ready": False}
    spec = load_json(SPEC_PATH)
    copy_generation = spec.get("copy_generation")
    image_prompt_generation = spec.get("image_prompt_generation")
    return {
        "copy_ready": isinstance(copy_generation, dict)
        and str(copy_generation.get("provider", "")).lower() == "deepseek",
        "image_prompts_ready": isinstance(image_prompt_generation, dict)
        and str(image_prompt_generation.get("provider", "")).lower() == "deepseek",
        "title": spec.get("title", ""),
        "review_id": spec.get("review_id", ""),
        "content_id": spec.get("content_id", ""),
    }


def run_writers() -> int:
    write_json(
        RESULT_PATH,
        {
            "status": "running",
            "started_at": now(),
            **spec_generation_status(),
        },
    )
    steps: list[dict[str, Any]] = []
    for label, script_name in [
        ("copy", "write_copy_deepseek.py"),
        ("image_prompts", "write_image_prompts_deepseek.py"),
    ]:
        step = run_script(label, script_name)
        steps.append(step)
        if step["returncode"] != 0:
            result = {
                "status": "failed",
                "failed_step": label,
                "steps": steps,
                "finished_at": now(),
                **spec_generation_status(),
            }
            write_json(RESULT_PATH, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(step["returncode"]) or 1

    result = {
        "status": "completed",
        "steps": steps,
        "finished_at": now(),
        **spec_generation_status(),
    }
    write_json(RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    result = {
        "status": "not_run",
        "result_path": str(RESULT_PATH),
        "last_result": None,
        "checked_at": now(),
        **spec_generation_status(),
    }
    if RESULT_PATH.exists():
        result["last_result"] = load_json(RESULT_PATH)
        if isinstance(result["last_result"], dict):
            result["status"] = str(result["last_result"].get("status", "unknown"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or inspect DeepSeek writers")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true", help="Run copy and image prompt writers")
    mode.add_argument("--status", action="store_true", help="Show writer status")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.run:
            return run_writers()
        return status()
    except Exception as exc:  # noqa: BLE001 - CLI should report concise errors.
        result = {
            "status": "failed",
            "error": str(exc),
            "finished_at": now(),
        }
        write_json(RESULT_PATH, result)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
