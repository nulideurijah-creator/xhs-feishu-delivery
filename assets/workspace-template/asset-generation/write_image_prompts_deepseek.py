#!/usr/bin/env python3
"""Write image prompt plans with DeepSeek's OpenAI-compatible chat API."""

from __future__ import annotations

import hashlib
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
REPORT_PATH = ROOT / "asset-generation" / "outputs" / "deepseek-image-prompts-report.json"
DEFAULT_PROMPT_PATH = Path.home() / ".codex" / "skills" / "xhs-feishu-delivery" / "references" / "image_prompt_creator_prompt.md"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
IMAGE_PROMPT_WRITER = "asset-generation/write_image_prompts_deepseek.py"
COPY_WRITER = "asset-generation/write_copy_deepseek.py"
MAX_ATTEMPTS = 4

FORBIDDEN_PROMPT_FRAGMENTS = [
    "friendly but still high-click cover hook",
    "premium creator-economy tone",
    "Cover hook rules:",
    "Inner card rules:",
    "Main title, verbatim",
    "Small subtitle, verbatim",
    "Subject and visual:",
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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prompt_path() -> Path:
    raw = os.environ.get("XHS_IMAGE_PROMPT_CREATOR_PROMPT_PATH", "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_PROMPT_PATH


def active_model() -> str:
    return (
        os.environ.get("DEEPSEEK_IMAGE_PROMPT_MODEL", "").strip()
        or os.environ.get("DEEPSEEK_MODEL", "").strip()
        or DEFAULT_MODEL
    )


def body_hash(spec: dict[str, Any]) -> str:
    body = str(spec.get("body_full", "")).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def validate_copy_generation(copy_generation: Any) -> None:
    if not isinstance(copy_generation, dict):
        raise ValueError("copy_generation must record DeepSeek writing before image prompts")
    provider = str(copy_generation.get("provider", "")).strip().lower()
    writer = str(copy_generation.get("writer", "")).strip()
    model = str(copy_generation.get("model", "")).strip().lower()
    if provider != "deepseek" or COPY_WRITER not in writer or "deepseek" not in model:
        raise ValueError("copy_generation must record DeepSeek writing before image prompts")


def page_outline(spec: dict[str, Any]) -> list[dict[str, Any]]:
    pages = spec.get("pages", [])
    if not isinstance(pages, list) or len(pages) != 6:
        raise ValueError("content_spec must contain exactly 6 pages before image prompt writing")
    outline: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"content_spec.pages[{index}] must be an object")
        page_id = str(page.get("page_id", "")).strip()
        if not page_id:
            raise ValueError(f"content_spec.pages[{index}] missing page_id")
        outline.append(
            {
                "page_id": page_id,
                "layout": str(page.get("layout", "balanced")).strip() or "balanced",
                "existing_title_hint": str(page.get("title", "")).strip(),
                "existing_subtitle_hint": str(page.get("subtitle", "")).strip(),
                "existing_visual_hint": str(page.get("visual", "")).strip(),
            }
        )
    return outline


def build_user_prompt(spec: dict[str, Any], previous_error: str = "") -> str:
    payload = {
        "topic": spec.get("topic", ""),
        "title": spec.get("title", ""),
        "body_full": spec.get("body_full", ""),
        "tags": spec.get("tags", []),
        "source_urls": spec.get("source_urls", []),
        "source_verification": spec.get("source_verification", {}),
        "project_facts": spec.get("project_facts", {}),
        "writing_brief": spec.get("writing_brief", {}),
        "page_outline": page_outline(spec),
        "fixed_baoyu_settings": {
            "preset": "sketch-summary",
            "style": "xhs-warm-cute-open-source",
            "palette": "macaron",
            "ratio": "3:4",
            "backend": "image2",
        },
    }
    retry_note = ""
    if previous_error:
        retry_note = (
            "\n\nPrevious output was invalid:\n"
            f"{previous_error}\n"
            "Regenerate only the JSON object. Do not explain the failure."
        )
    return (
        "Create the DeepSeek-authored image prompt plan for this Xiaohongshu card series.\n"
        "Return exactly one JSON object, no Markdown and no commentary.\n"
        "Required schema:\n"
        '{"pages":[{"page_id":"01-cover","layout":"balanced","image_prompt_plan":{'
        '"card_role":"cover","visible_title":"...","visible_subtitle":"...",'
        '"visual_direction":"...","composition":"...","text_style":"...",'
        '"required_labels":["..."],"avoid":["..."]}}]}\n\n'
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        f"{retry_note}"
    )


def call_deepseek(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Set it in the current shell or in workspace .env.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    payload = {
        "model": active_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.72,
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
        raise ValueError("DeepSeek image prompt response must be a JSON object")
    return data


def normalize_string(value: Any, field: str, max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"image_prompt_plan missing {field}")
    if max_length and len(text) > max_length:
        raise ValueError(f"image_prompt_plan {field} too long: {len(text)}/{max_length}")
    return text


def normalize_string_list(value: Any, field: str, limit: int = 6) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"image_prompt_plan {field} must be a list")
    items = [str(item).strip() for item in value if str(item).strip()]
    if len(items) > limit:
        raise ValueError(f"image_prompt_plan {field} too long: {len(items)}/{limit}")
    return items


def normalize_plan(raw_plan: dict[str, Any]) -> dict[str, Any]:
    plan = {
        "card_role": normalize_string(raw_plan.get("card_role"), "card_role", 24),
        "visible_title": normalize_string(raw_plan.get("visible_title"), "visible_title", 22),
        "visible_subtitle": normalize_string(raw_plan.get("visible_subtitle"), "visible_subtitle", 36),
        "visual_direction": normalize_string(raw_plan.get("visual_direction"), "visual_direction"),
        "composition": normalize_string(raw_plan.get("composition"), "composition"),
        "text_style": normalize_string(raw_plan.get("text_style"), "text_style"),
        "required_labels": normalize_string_list(raw_plan.get("required_labels", []), "required_labels", 5),
        "avoid": normalize_string_list(raw_plan.get("avoid", []), "avoid", 8),
    }
    joined = json.dumps(plan, ensure_ascii=False)
    hits = [fragment for fragment in FORBIDDEN_PROMPT_FRAGMENTS if fragment in joined]
    if hits:
        raise ValueError(f"DeepSeek image prompt plan contains removed hardcoded fragments: {hits}")
    return plan


def normalize_image_prompt_response(response: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    expected = page_outline(spec)
    expected_ids = [page["page_id"] for page in expected]
    pages = response.get("pages")
    if not isinstance(pages, list) or len(pages) != len(expected_ids):
        raise ValueError(f"DeepSeek image prompt response must contain {len(expected_ids)} pages")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(pages):
        if not isinstance(item, dict):
            raise ValueError(f"DeepSeek image prompt page {index + 1} must be an object")
        page_id = str(item.get("page_id", "")).strip()
        if page_id != expected_ids[index]:
            raise ValueError(f"DeepSeek image prompt page_id mismatch: {page_id!r} != {expected_ids[index]!r}")
        raw_plan = item.get("image_prompt_plan", item)
        if not isinstance(raw_plan, dict):
            raise ValueError(f"DeepSeek image_prompt_plan for {page_id} must be an object")
        normalized.append(
            {
                "page_id": page_id,
                "layout": str(item.get("layout") or expected[index].get("layout") or "balanced").strip() or "balanced",
                "image_prompt_plan": normalize_plan(raw_plan),
            }
        )
    return normalized


def mark_image_prompt_generation(spec: dict[str, Any], prompt_file: Path) -> None:
    spec["image_prompt_generation"] = {
        "provider": "deepseek",
        "model": active_model(),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL,
        "writer": IMAGE_PROMPT_WRITER,
        "prompt_path": str(prompt_file),
        "source_title": str(spec.get("title", "")).strip(),
        "source_body_sha256": body_hash(spec),
        "created_at": now(),
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    spec = load_json(SPEC_PATH)
    validate_copy_generation(spec.get("copy_generation"))
    if not str(spec.get("title", "")).strip() or not str(spec.get("body_full", "")).strip():
        raise ValueError("title and body_full must exist before DeepSeek image prompt writing")
    prompt_file = prompt_path()
    if not prompt_file.exists():
        raise FileNotFoundError(f"image prompt creator prompt not found: {prompt_file}")
    system_prompt = prompt_file.read_text(encoding="utf-8")
    last_error = ""
    pages: list[dict[str, Any]] | None = None
    for _attempt in range(1, MAX_ATTEMPTS + 1):
        raw_content = call_deepseek(system_prompt, build_user_prompt(spec, last_error))
        try:
            pages = normalize_image_prompt_response(parse_model_json(raw_content), spec)
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
    if pages is None:
        raise ValueError(f"DeepSeek failed to produce valid image prompt plans after {MAX_ATTEMPTS} attempts: {last_error}")
    spec["pages"] = pages
    mark_image_prompt_generation(spec, prompt_file)
    write_json(SPEC_PATH, spec)
    report = {
        "status": "image_prompts_written",
        "model": active_model(),
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        "prompt_path": str(prompt_file),
        "page_count": len(pages),
        "source_title": spec["image_prompt_generation"]["source_title"],
        "source_body_sha256": spec["image_prompt_generation"]["source_body_sha256"],
        "created_at": now(),
    }
    write_json(REPORT_PATH, report)
    print("status: image_prompts_written")
    print(f"model: {report['model']}")
    print(f"pages: {len(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
