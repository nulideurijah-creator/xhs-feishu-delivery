#!/usr/bin/env python3
"""Install an on-demand Windows task that sends queued Feishu deliveries.

The task runs a no-space command wrapper from the user's Codex home. The wrapper
starts PowerShell, changes into this workspace, and calls
``python run_xhs_delivery.py --send-pending``. This keeps Feishu network I/O out
of Codex unattended automation sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"
RESULT_PATH = OUT / "pending-sender-install-result.json"
TASK_NAME = "XHS-Feishu-Pending-Sender"


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex"


def runner_dir() -> Path:
    return codex_home() / "xhs-feishu-local-sender"


def write_json(path: Path, data: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def ps_quote(value: Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def ensure_workspace_link(directory: Path) -> Path:
    """Create a runner-local junction for workspaces with spaces or non-ASCII."""
    link_path = directory / "workspace"
    if link_path.exists():
        if link_path.resolve() == ROOT.resolve():
            return link_path
        raise RuntimeError(f"refusing to replace existing runner workspace path: {link_path}")
    command = (
        "New-Item -ItemType Junction "
        f"-Path {ps_quote(link_path)} "
        f"-Target {ps_quote(ROOT)} "
        "-Force | Out-Null"
    )
    completed = run_command(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    )
    if completed.returncode != 0:
        raise RuntimeError(f"failed to create workspace junction: {completed.stderr or completed.stdout}")
    return link_path


def write_runners() -> tuple[Path, Path]:
    directory = runner_dir()
    directory.mkdir(parents=True, exist_ok=True)
    workspace_link = ensure_workspace_link(directory)
    ps1_path = directory / "run_pending_sender.ps1"
    cmd_path = directory / "run_pending_sender.cmd"
    log_path = directory / "pending-sender.log"
    ps1_path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                f"$Workspace = @'\n{workspace_link}\n'@",
                f"$Python = @'\n{sys.executable}\n'@",
                f"$Log = @'\n{log_path}\n'@",
                "New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null",
                "\"[$(Get-Date -Format o)] pending sender started\" | Out-File -FilePath $Log -Append -Encoding utf8",
                "Set-Location -LiteralPath $Workspace",
                "& $Python '.\\run_xhs_delivery.py' '--send-pending' 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8",
                "$ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }",
                "\"[$(Get-Date -Format o)] exit_code=$ExitCode\" | Out-File -FilePath $Log -Append -Encoding utf8",
                "exit $ExitCode",
                "",
            ]
        ),
        encoding="utf-8-sig",
    )
    cmd_path.write_text(
        "@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%~dp0run_pending_sender.ps1\"\r\n",
        encoding="ascii",
    )
    return ps1_path, cmd_path


def install() -> int:
    ps1_path, cmd_path = write_runners()
    completed = run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            (
                "$Action = New-ScheduledTaskAction "
                f"-Execute {ps_quote(cmd_path)}; "
                f"Register-ScheduledTask -TaskName {ps_quote(Path(TASK_NAME))} "
                "-Action $Action -Force | Out-Null"
            ),
        ]
    )
    result = {
        "status": "installed" if completed.returncode == 0 else "install_failed",
        "task_name": TASK_NAME,
        "trigger_mode": "on_demand",
        "runner_cmd": str(cmd_path),
        "runner_ps1": str(ps1_path),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "created_at": now(),
    }
    write_json(RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return completed.returncode


def uninstall() -> int:
    completed = run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    ok = completed.returncode == 0 or "cannot find" in (completed.stderr + completed.stdout).lower()
    result = {
        "status": "uninstalled" if ok else "uninstall_failed",
        "task_name": TASK_NAME,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "created_at": now(),
    }
    write_json(RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else completed.returncode


def status() -> int:
    completed = run_command(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"])
    result = {
        "status": "installed" if completed.returncode == 0 else "not_installed",
        "task_name": TASK_NAME,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "checked_at": now(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run_now() -> int:
    completed = run_command(["schtasks", "/Run", "/TN", TASK_NAME])
    result = {
        "status": "triggered" if completed.returncode == 0 else "trigger_failed",
        "task_name": TASK_NAME,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "created_at": now(),
    }
    write_json(RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install or manage the XHS Feishu pending sender")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", action="store_true", help="Install the scheduled pending sender")
    mode.add_argument("--uninstall", action="store_true", help="Remove the scheduled pending sender")
    mode.add_argument("--status", action="store_true", help="Query the scheduled pending sender")
    mode.add_argument("--run-now", action="store_true", help="Trigger the scheduled pending sender immediately")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.install:
        return install()
    if args.uninstall:
        return uninstall()
    if args.run_now:
        return run_now()
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
