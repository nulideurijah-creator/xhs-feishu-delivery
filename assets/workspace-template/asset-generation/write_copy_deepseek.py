#!/usr/bin/env python3
"""Write title/body/tags with DeepSeek's OpenAI-compatible chat API."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "asset-generation" / "content_spec.json"
REPORT_PATH = ROOT / "asset-generation" / "outputs" / "deepseek-copy-report.json"
DEFAULT_PROMPT_PATH = Path.home() / ".codex" / "skills" / "xhs-feishu-delivery" / "references" / "creator_prompt.md"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
COPY_WRITER = "asset-generation/write_copy_deepseek.py"
MAX_ATTEMPTS = 4
FORBIDDEN_COPY_FRAGMENTS = [
    "性感",
    "该项目",
    "本项目",
    "本工具",
    "据悉",
    "据了解",
    "综上所述",
    "由此可见",
    "总体而言",
    "总体来说",
    "颇具优势",
    "首先",
    "其次",
    "最后",
    "总结一下",
]


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prompt_path() -> Path:
    raw = os.environ.get("XHS_CREATOR_PROMPT_PATH", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_PROMPT_PATH


def build_user_prompt(spec: dict[str, Any], previous_error: str = "") -> str:
    facts = {
        "topic": spec.get("topic", ""),
        "source_urls": spec.get("source_urls", []),
        "source_verification": spec.get("source_verification", {}),
        "project_facts": spec.get("project_facts", {}),
        "writing_brief": spec.get("writing_brief", {}),
    }
    retry_note = ""
    if previous_error:
        retry_note = (
            "\n\n上一次输出不合格，原因："
            f"{previous_error}\n"
            "请重新生成，不要解释，不要保留任何失败稿里的禁用表达。"
        )
    return (
        "请严格按照系统提示词，基于下面已核查事实生成小红书笔记。\n"
        "只返回一个 JSON 对象，不要 Markdown，不要解释。\n"
        "JSON 结构必须是："
        '{"title":"...","body_full":"...","tags":["..."]}\n\n'
        f"{json.dumps(facts, ensure_ascii=False, indent=2)}"
        f"{retry_note}"
    )


def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. Set it in the current shell or in workspace .env."
        )
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.85,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {detail}") from exc
    choices = result.get("choices", [])
    if not choices:
        raise RuntimeError(f"DeepSeek API returned no choices: {result}")
    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError(f"DeepSeek API returned empty content: {result}")
    return content


def parse_model_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(0)
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError("DeepSeek response must be a JSON object")
    return data


def normalize_copy(copy: dict[str, Any]) -> dict[str, Any]:
    title = str(copy.get("title", "")).strip()
    body = str(copy.get("body_full", "")).strip()
    tags_raw = copy.get("tags", [])
    tags = [str(tag).strip().lstrip("#") for tag in tags_raw if str(tag).strip()]
    if not title:
        raise ValueError("DeepSeek response missing title")
    if len(title) > 20:
        raise ValueError(f"DeepSeek title too long: {len(title)}/20")
    if not body:
        raise ValueError("DeepSeek response missing body_full")
    if len(body) > 1000:
        raise ValueError(f"DeepSeek body too long: {len(body)}/1000")
    if not 5 <= len(tags) <= 8:
        raise ValueError(f"DeepSeek tags must contain 5-8 items, got {len(tags)}")
    combined = f"{title}\n{body}"
    forbidden_hits = [fragment for fragment in FORBIDDEN_COPY_FRAGMENTS if fragment in combined]
    if forbidden_hits:
        raise ValueError(f"DeepSeek copy contains forbidden fragments: {forbidden_hits}")
    return {"title": title, "body_full": body, "tags": tags}


def sync_cover_page(spec: dict[str, Any]) -> bool:
    """Keep image-card cover metadata aligned after DeepSeek updates copy."""
    pages = spec.get("pages")
    if not isinstance(pages, list) or not pages or not isinstance(pages[0], dict):
        return False
    pages[0]["title"] = spec["title"]
    return True


def mark_copy_generation(spec: dict[str, Any], prompt_file: Path) -> None:
    """Record that the current title/body/tags came from the DeepSeek writer."""
    spec["copy_generation"] = {
        "provider": "deepseek",
        "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL,
        "writer": COPY_WRITER,
        "prompt_path": str(prompt_file),
        "created_at": now(),
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    spec = load_json(SPEC_PATH)
    prompt_file = prompt_path()
    if not prompt_file.exists():
        raise FileNotFoundError(f"creator prompt not found: {prompt_file}")
    system_prompt = prompt_file.read_text(encoding="utf-8")
    last_error = ""
    copy: dict[str, Any] | None = None
    for _attempt in range(1, MAX_ATTEMPTS + 1):
        raw_content = call_deepseek(system_prompt, build_user_prompt(spec, last_error))
        try:
            copy = normalize_copy(parse_model_json(raw_content))
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
    if copy is None:
        raise ValueError(f"DeepSeek failed to produce valid copy after {MAX_ATTEMPTS} attempts: {last_error}")
    spec.update(copy)
    mark_copy_generation(spec, prompt_file)
    cover_title_synced = sync_cover_page(spec)
    write_json(SPEC_PATH, spec)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "copy_written",
        "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        "prompt_path": str(prompt_file),
        "title": copy["title"],
        "body_char_count": len(copy["body_full"]),
        "tag_count": len(copy["tags"]),
        "cover_title_synced": cover_title_synced,
        "created_at": now(),
    }
    write_json(REPORT_PATH, report)
    print("status: copy_written")
    print(f"title: {copy['title']}")
    print(f"body_char_count: {len(copy['body_full'])}")
    print(f"tags: {', '.join(copy['tags'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
