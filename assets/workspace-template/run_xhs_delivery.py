#!/usr/bin/env python3
"""Run the Xiaohongshu manual delivery workflow end to end.

This workspace-local runner is what users call after initializing a workspace.
It keeps all files in this workspace and never publishes to Xiaohongshu
automatically. It packages model-generated image cards; it does not draw image
cards with a local template script.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / ".xhs_delivery.lock"
LOCK_TTL_SECONDS = 2 * 60 * 60


def run_step(name: str, args: list[str]) -> None:
    """Run one workflow step and stop immediately on failure."""
    print(f"\n== {name} ==")
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


@contextmanager
def workflow_lock():
    """Prevent concurrent runs from corrupting image/package outputs."""
    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age > LOCK_TTL_SECONDS:
            LOCK_PATH.unlink()
        else:
            raise SystemExit(
                f"workflow already running or lock exists: {LOCK_PATH}. "
                "If no workflow is running, delete this lock file and retry."
            )
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"pid={os.getpid()}\n".encode("utf-8"))
    finally:
        os.close(fd)
    try:
        yield
    finally:
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run XHS delivery workflow")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-feishu", action="store_true", help="Check Feishu credentials without building or sending")
    mode.add_argument("--doctor", action="store_true", help="Run read-only workspace diagnostics and write a doctor report")
    mode.add_argument("--history", action="store_true", help="List recent sent Xiaohongshu delivery history")
    mode.add_argument("--check-history", action="store_true", help="Check current content_spec.json against sent history")
    mode.add_argument("--check-copy", action="store_true", help="Check current title/body/tags against the local copy quality gate")
    mode.add_argument("--install-startup-check", action="store_true", help="Install a Windows logon Feishu health check")
    mode.add_argument("--install-system-startup-check", action="store_true", help="Install a Windows startup health check; requires administrator")
    mode.add_argument("--uninstall-startup-check", action="store_true", help="Remove the Windows logon Feishu health check")
    mode.add_argument("--automation-lock-status", action="store_true", help="Show the workspace automation lock status")
    mode.add_argument("--acquire-automation-lock", action="store_true", help="Acquire the workspace automation lock")
    mode.add_argument("--release-automation-lock", action="store_true", help="Release the workspace automation lock")
    mode.add_argument("--local-only", action="store_true", help="Build and validate without Feishu credentials")
    mode.add_argument("--dry-run", action="store_true", help="Build and validate Feishu credentials")
    mode.add_argument("--send", action="store_true", help="Build and send the Feishu delivery card")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.check_feishu:
        run_step("check_feishu_ready", [sys.executable, ".\\feishu-delivery\\check_feishu_ready.py"])
        return 0
    if args.doctor:
        run_step("doctor", [sys.executable, ".\\diagnostics\\doctor.py"])
        return 0
    if args.history:
        run_step("history", [sys.executable, ".\\content-history\\check_history.py", "--list"])
        return 0
    if args.check_history:
        run_step("check_history", [sys.executable, ".\\content-history\\check_history.py", "--check-current"])
        return 0
    if args.check_copy:
        run_step("check_copy", [sys.executable, ".\\asset-generation\\copy_quality.py"])
        return 0
    if args.install_startup_check:
        run_step("install_startup_check", [sys.executable, ".\\feishu-delivery\\install_startup_check.py"])
        return 0
    if args.install_system_startup_check:
        run_step("install_system_startup_check", [sys.executable, ".\\feishu-delivery\\install_startup_check.py", "--system"])
        return 0
    if args.uninstall_startup_check:
        run_step("uninstall_startup_check", [sys.executable, ".\\feishu-delivery\\install_startup_check.py", "--uninstall"])
        return 0
    if args.automation_lock_status:
        run_step("automation_lock_status", [sys.executable, ".\\automation-lock\\automation_lock.py", "--status"])
        return 0
    if args.acquire_automation_lock:
        run_step("acquire_automation_lock", [sys.executable, ".\\automation-lock\\automation_lock.py", "--acquire"])
        return 0
    if args.release_automation_lock:
        run_step("release_automation_lock", [sys.executable, ".\\automation-lock\\automation_lock.py", "--release"])
        return 0

    send_mode = "--local-only"
    if args.dry_run:
        send_mode = "--dry-run"
    if args.send:
        send_mode = "--send"

    with workflow_lock():
        run_step("generate_assets", [sys.executable, ".\\asset-generation\\generate_current_assets.py"])
        run_step("build_manual_package", [sys.executable, ".\\publish-mainline\\build_manual_publish_package.py"])
        run_step("preflight", [sys.executable, ".\\publish-mainline\\preflight.py"])
        run_step("build_delivery_card", [sys.executable, ".\\feishu-delivery\\build_delivery_card.py"])
        run_step("send_delivery_card", [sys.executable, ".\\feishu-delivery\\send_delivery_card.py", send_mode])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
