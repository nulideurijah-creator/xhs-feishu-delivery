#!/usr/bin/env python3
"""Check that the skill directory contains no local secrets or publish automation.

This is intentionally simple and conservative. It catches the risky artifacts
that should never be shipped in the public skill repository.
"""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_NAMES = {
    # Files that commonly contain real account state or local credentials.
    ".env",
    "cookies.json",
    "xhs-login-qrcode.png",
    "render_current_cards.py",
}

FORBIDDEN_TEXT = [
    # Terms from removed auto-publish or callback flows. Their presence usually
    # means the repo is drifting away from manual-only Xiaohongshu posting.
    "publish_content",
    "--confirm-publish",
    "xiaohongshu-mcp",
    "ws_review_server",
    "callback_server",
    "localtunnel",
    "ngrok",
    "om_x100",
    "ai-acceptance-first",
    "replit-squidler",
    "D:\\VIBE CODING",
    "C:\\Users\\admin",
    "render_image_cards",
    "image-generation/render_current_cards.py",
    "账号收到小红书 AI 使用违规警报",
]

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}


def iter_text_files(root: Path):
    """Yield text-like files that should be scanned for risky content."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "validate_skill_safety.py":
            continue
        if path.name in FORBIDDEN_NAMES:
            raise ValueError(f"forbidden file name: {path}")
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def validate(root: Path) -> list[str]:
    """Return every forbidden-text hit found under the skill directory."""
    hits: list[str] = []
    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for item in FORBIDDEN_TEXT:
            if item in text:
                hits.append(f"{path}: {item}")
    return hits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate xhs-feishu-delivery skill safety")
    parser.add_argument("--skill-dir", required=True, help="Path to xhs-feishu-delivery skill directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.skill_dir).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    hits = validate(root)
    if hits:
        print("forbidden content found:")
        for hit in hits:
            print(f"- {hit}")
        return 1
    print("skill_safety_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
