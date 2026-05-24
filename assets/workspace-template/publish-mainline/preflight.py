from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "publish-mainline" / "outputs"
REPORT_JSON = OUT / "preflight-report.json"
REPORT_MD = OUT / "preflight-report.md"
MANUAL_PACKAGE_JSON = OUT / "manual-publish-package.json"


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_step(name: str, args: list[str], timeout: int = 180) -> dict:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "name": name,
        "args": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "ok": completed.returncode == 0,
    }


def summarize(report: dict) -> str:
    package = report.get("manual_package", {})
    lines = [
        "# 小红书发布内容包 Preflight",
        "",
        f"- 状态：`{report.get('status')}`",
        f"- 阻断原因：{', '.join(report.get('blocked_reasons', [])) or '`无`'}",
        "- 小红书发布：`manual`",
        f"- 标题：{package.get('title', '')}",
        f"- 正文字数：`{package.get('body_char_count', 0)}`",
        f"- 图片数量：`{len(package.get('images', []))}`",
        f"- 标签：{', '.join(package.get('tags', []))}",
        f"- 自动发布：`disabled`",
        f"- 生成时间：`{report.get('checked_at')}`",
        "",
        "## 执行步骤",
        "",
    ]
    for step in report.get("steps", []):
        lines.append(f"- `{step.get('name')}`：returncode `{step.get('returncode')}`")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 状态为 `ready_manual_package` 时，生成飞书交付卡。",
            "- 本流程不会调用小红书接口、不会打开小红书网页、不会自动提交。",
            "- 飞书卡片只负责交付完整内容，不提供按钮。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    steps = [
        run_step(
            "build_manual_publish_package",
            ["python", ".\\publish-mainline\\build_manual_publish_package.py"],
        )
    ]
    package = load_json(MANUAL_PACKAGE_JSON)
    blocked_reasons = list(package.get("blocked_reasons", []))
    if not package:
        blocked_reasons.append("manual_package_missing")
    blocked_reasons = sorted(set(blocked_reasons))
    status = "ready_manual_package" if not blocked_reasons and all(step["ok"] for step in steps) else "blocked"
    report = {
        "status": status,
        "blocked_reasons": blocked_reasons,
        "checked_at": now(),
        "steps": steps,
        "manual_package": package,
        "scope": {
            "publish_mode": "manual_only",
            "auto_publish_enabled": False,
            "mcp_required": False,
            "browser_publish_required": False,
        },
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_MD.write_text(summarize(report), encoding="utf-8")
    print(f"status: {status}")
    print(f"blocked_reasons: {', '.join(blocked_reasons)}")
    return 0 if status == "ready_manual_package" else 2


if __name__ == "__main__":
    raise SystemExit(main())
