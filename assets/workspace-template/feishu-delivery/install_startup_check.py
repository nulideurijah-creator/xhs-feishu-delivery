#!/usr/bin/env python3
"""Install or remove a Windows startup health check for Feishu delivery."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "feishu-delivery" / "outputs"
RUNNER = ROOT / "feishu-delivery" / "startup_feishu_check.cmd"
LOG_PATH = OUT / "startup-health.log"
RESULT_PATH = OUT / "startup-check-install-result.json"
TASK_NAME = "XHS-Feishu-Delivery-HealthCheck"
SYSTEM_TASK_NAME = "XHS-Feishu-Delivery-System-HealthCheck"
STARTUP_CMD_NAME = "XHS-Feishu-Delivery-HealthCheck.cmd"
ADMIN_INSTALL_CMD = ROOT / "feishu-delivery" / "install_system_startup_check_admin.cmd"


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not available")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def write_runner() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    python_exe = Path(sys.executable).resolve()
    check_script = ROOT / "feishu-delivery" / "check_feishu_ready.py"
    RUNNER.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal EnableDelayedExpansion",
                f'cd /d "{ROOT}"',
                f'echo [%date% %time%] Feishu health check started > "{LOG_PATH}"',
                "set CHECK_EXIT=1",
                "for /l %%i in (1,1,6) do (",
                f'  echo [%date% %time%] attempt %%i >> "{LOG_PATH}"',
                f'  "{python_exe}" "{check_script}" >> "{LOG_PATH}" 2>&1',
                "  set CHECK_EXIT=!ERRORLEVEL!",
                "  if \"!CHECK_EXIT!\"==\"0\" goto done",
                f'  echo [%date% %time%] attempt %%i failed with !CHECK_EXIT!, retrying in 30 seconds >> "{LOG_PATH}"',
                "  timeout /t 30 /nobreak >nul",
                ")",
                ":done",
                f'echo [%date% %time%] exit_code=!CHECK_EXIT! >> "{LOG_PATH}"',
                "exit /b !CHECK_EXIT!",
                "",
            ]
        ),
        encoding="utf-8",
    )


def register_task() -> dict:
    cmd_exe = os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe")
    cmd_arg = f'/c "{RUNNER}"'
    ps = "\n".join(
        [
            f"$Action = New-ScheduledTaskAction -Execute {ps_quote(cmd_exe)} -Argument {ps_quote(cmd_arg)}",
            "$Trigger = New-ScheduledTaskTrigger -AtLogOn",
            "$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)",
            f"Register-ScheduledTask -TaskName {ps_quote(TASK_NAME)} -Action $Action -Trigger $Trigger -Settings $Settings -Description {ps_quote('Check Feishu delivery credentials after Windows logon. Sends no message.')} -Force | Out-Null",
        ]
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return {"method": "scheduled_task", "task_name": TASK_NAME}


def register_system_task() -> dict:
    if not is_admin():
        write_admin_installer()
        return {
            "status": "admin_required",
            "method": "system_scheduled_task",
            "task_name": SYSTEM_TASK_NAME,
            "admin_installer": str(ADMIN_INSTALL_CMD),
            "message": "Run the admin installer as administrator to install an at-startup SYSTEM task.",
        }

    cmd_exe = os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe")
    cmd_arg = f'/c "{RUNNER}"'
    ps = "\n".join(
        [
            f"$Action = New-ScheduledTaskAction -Execute {ps_quote(cmd_exe)} -Argument {ps_quote(cmd_arg)}",
            "$Trigger = New-ScheduledTaskTrigger -AtStartup",
            "$Trigger.Delay = 'PT2M'",
            "$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 8)",
            "$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest",
            f"Register-ScheduledTask -TaskName {ps_quote(SYSTEM_TASK_NAME)} -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description {ps_quote('Check Feishu delivery credentials after Windows startup. Sends no message.')} -Force | Out-Null",
        ]
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return {"status": "installed", "method": "system_scheduled_task", "task_name": SYSTEM_TASK_NAME}


def write_admin_installer() -> None:
    python_exe = Path(sys.executable).resolve()
    script = Path(__file__).resolve()
    ADMIN_INSTALL_CMD.write_text(
        "\n".join(
            [
                "@echo off",
                "net session >nul 2>&1",
                "if not \"%errorlevel%\"==\"0\" (",
                "  echo Requesting administrator permission...",
                "  powershell -NoProfile -ExecutionPolicy Bypass -Command \"Start-Process -FilePath '%~f0' -Verb RunAs\"",
                "  exit /b",
                ")",
                "echo Installing XHS Feishu system startup health check...",
                f'"{python_exe}" "{script}" --system',
                "set INSTALL_EXIT=%ERRORLEVEL%",
                "echo.",
                "echo Querying installed task...",
                f"schtasks /Query /TN {SYSTEM_TASK_NAME} /FO LIST /V",
                "echo.",
                "if \"%INSTALL_EXIT%\"==\"0\" (",
                "  echo Install command finished successfully.",
                ") else (",
                "  echo Install command failed with exit code %INSTALL_EXIT%.",
                ")",
                "pause",
                "exit /b %INSTALL_EXIT%",
                "",
            ]
        ),
        encoding="utf-8",
    )


def install_startup_folder_fallback() -> dict:
    folder = startup_folder()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / STARTUP_CMD_NAME
    target.write_text(
        "\n".join(
            [
                "@echo off",
                f'call "{RUNNER}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"method": "startup_folder", "startup_cmd": str(target)}


def install_registry_run_fallback() -> dict:
    command = f'"{RUNNER}"'
    key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
    completed = subprocess.run(
        ["reg", "add", key, "/v", TASK_NAME, "/t", "REG_SZ", "/d", command, "/f"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return {"method": "registry_run", "registry_key": key, "registry_value": TASK_NAME}


def install() -> dict:
    write_runner()
    result: dict = {
        "status": "installed",
        "checked_at": now(),
        "runner": str(RUNNER),
        "log_path": str(LOG_PATH),
        "sends_message": False,
    }
    try:
        result.update(register_task())
    except Exception as exc:
        result["scheduled_task_error"] = str(exc)
        try:
            result.update(install_startup_folder_fallback())
        except Exception as fallback_exc:
            result["startup_folder_error"] = str(fallback_exc)
            result.update(install_registry_run_fallback())
    return result


def install_system() -> dict:
    write_runner()
    result: dict = {
        "checked_at": now(),
        "runner": str(RUNNER),
        "log_path": str(LOG_PATH),
        "sends_message": False,
        "requires_admin": True,
    }
    result.update(register_system_task())
    return result


def uninstall() -> dict:
    errors: list[str] = []
    ps = f"Unregister-ScheduledTask -TaskName {ps_quote(TASK_NAME)} -Confirm:$false -ErrorAction SilentlyContinue"
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        errors.append((completed.stderr or completed.stdout).strip())

    system_ps = f"Unregister-ScheduledTask -TaskName {ps_quote(SYSTEM_TASK_NAME)} -Confirm:$false -ErrorAction SilentlyContinue"
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", system_ps],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        errors.append((completed.stderr or completed.stdout).strip())

    try:
        fallback = startup_folder() / STARTUP_CMD_NAME
        if fallback.exists():
            fallback.unlink()
        if ADMIN_INSTALL_CMD.exists():
            ADMIN_INSTALL_CMD.unlink()
    except Exception as exc:
        errors.append(str(exc))

    completed = subprocess.run(
        ["reg", "delete", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "/v", TASK_NAME, "/f"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        errors.append((completed.stderr or completed.stdout).strip())

    return {
        "status": "removed" if not errors else "removed_with_warnings",
        "checked_at": now(),
        "task_name": TASK_NAME,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install Feishu startup health check")
    parser.add_argument("--uninstall", action="store_true", help="Remove the startup health check")
    parser.add_argument("--system", action="store_true", help="Install an at-startup SYSTEM task; requires administrator")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.uninstall:
        result = uninstall()
    elif args.system:
        result = install_system()
    else:
        result = install()
    write_json(RESULT_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
