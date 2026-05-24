#!/usr/bin/env python3
"""Create a local workspace from the bundled workflow template."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "workspace-template"


def copy_template(workspace: Path, force: bool) -> list[str]:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"workspace template missing: {TEMPLATE}")
    workspace.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in TEMPLATE.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(TEMPLATE)
        target = workspace / relative
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(relative.as_posix())
    return copied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize an XHS Feishu delivery workspace")
    parser.add_argument("--workspace", required=True, help="Target workspace path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    copied = copy_template(workspace, args.force)
    print(f"workspace: {workspace}")
    print(f"copied_files: {len(copied)}")
    for item in copied:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
