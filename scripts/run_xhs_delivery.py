#!/usr/bin/env python3
"""Run the Xiaohongshu Feishu delivery workflow in a target workspace."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


BUILD_REQUIRED_FILES = [
    "asset-generation/content_spec.json",
    "asset-generation/generate_current_assets.py",
    "image-generation/render_current_cards.py",
    "publish-mainline/build_manual_publish_package.py",
    "publish-mainline/preflight.py",
    "feishu-delivery/build_delivery_card.py",
    "feishu-delivery/send_delivery_card.py",
]

CHECK_REQUIRED_FILES = [
    "feishu-delivery/check_feishu_ready.py",
]

STARTUP_REQUIRED_FILES = [
    "feishu-delivery/install_startup_check.py",
]


def resolve_workspace(raw: str) -> Path:
    workspace = Path(raw).expanduser().resolve()
    if not workspace.exists():
        raise FileNotFoundError(f"workspace does not exist: {workspace}")
    if not workspace.is_dir():
        raise NotADirectoryError(f"workspace is not a directory: {workspace}")
    return workspace


def require_files(workspace: Path, required_files: list[str]) -> None:
    missing = [path for path in required_files if not (workspace / path).exists()]
    if missing:
        raise FileNotFoundError("workspace is missing required files: " + ", ".join(missing))


def run_step(workspace: Path, name: str, args: list[str]) -> None:
    print(f"\n== {name} ==")
    completed = subprocess.run(
        args,
        cwd=workspace,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run XHS Feishu delivery workflow")
    parser.add_argument(
        "--workspace",
        required=True,
        help="Path to a workspace containing asset-generation, publish-mainline, and feishu-delivery.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-feishu", action="store_true", help="Check Feishu credentials without building or sending")
    mode.add_argument("--install-startup-check", action="store_true", help="Install a Windows logon Feishu health check")
    mode.add_argument("--uninstall-startup-check", action="store_true", help="Remove the Windows logon Feishu health check")
    mode.add_argument("--local-only", action="store_true", help="Build and validate without Feishu credentials")
    mode.add_argument("--dry-run", action="store_true", help="Build and validate Feishu credentials")
    mode.add_argument("--send", action="store_true", help="Build and send the Feishu delivery card")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    workspace = resolve_workspace(args.workspace)
    if args.check_feishu:
        require_files(workspace, CHECK_REQUIRED_FILES)
        run_step(workspace, "check_feishu_ready", [sys.executable, ".\\feishu-delivery\\check_feishu_ready.py"])
        return 0
    if args.install_startup_check:
        require_files(workspace, STARTUP_REQUIRED_FILES)
        run_step(workspace, "install_startup_check", [sys.executable, ".\\feishu-delivery\\install_startup_check.py"])
        return 0
    if args.uninstall_startup_check:
        require_files(workspace, STARTUP_REQUIRED_FILES)
        run_step(workspace, "uninstall_startup_check", [sys.executable, ".\\feishu-delivery\\install_startup_check.py", "--uninstall"])
        return 0

    require_files(workspace, BUILD_REQUIRED_FILES)
    send_mode = "--local-only"
    if args.dry_run:
        send_mode = "--dry-run"
    if args.send:
        send_mode = "--send"

    run_step(workspace, "generate_assets", [sys.executable, ".\\asset-generation\\generate_current_assets.py"])
    run_step(workspace, "render_image_cards", [sys.executable, ".\\image-generation\\render_current_cards.py"])
    run_step(workspace, "refresh_assets", [sys.executable, ".\\asset-generation\\generate_current_assets.py"])
    run_step(workspace, "build_manual_package", [sys.executable, ".\\publish-mainline\\build_manual_publish_package.py"])
    run_step(workspace, "preflight", [sys.executable, ".\\publish-mainline\\preflight.py"])
    run_step(workspace, "build_delivery_card", [sys.executable, ".\\feishu-delivery\\build_delivery_card.py"])
    run_step(workspace, "send_delivery_card", [sys.executable, ".\\feishu-delivery\\send_delivery_card.py", send_mode])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
