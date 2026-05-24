#!/usr/bin/env python3
"""Validate or send the Feishu delivery card.

Modes:
- local-only: validate files only, no Feishu credentials needed.
- dry-run: validate Feishu credentials, no image upload or message send.
- send: upload images to Feishu and send the final interactive card.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"
REQUEST_PATH = OUT / "delivery-request.json"
CARD_PATH = OUT / "delivery-card.json"
LOCAL_RESULT_PATH = OUT / "local-validation-result.json"
DRY_RUN_RESULT_PATH = OUT / "dry-run-result.json"
SEND_RESULT_PATH = OUT / "send-result.json"
SENT_CARD_PATH = OUT / "delivery-card.sent.json"
DELIVERY_STATE_PATH = OUT / "delivery-state.json"

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
IMAGE_URL = "https://open.feishu.cn/open-apis/im/v1/images"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

REQUIRED_ENV = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_RECEIVE_ID_TYPE",
    "FEISHU_RECEIVE_ID",
]
ALLOWED_RECEIVE_ID_TYPES = {"chat_id", "open_id", "user_id", "union_id", "email"}
CARD_FORBIDDEN_TERMS = ["发布方式", "人工发布包", "发布前检查", "**状态**"]


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
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_env() -> dict[str, str]:
    result: dict[str, str] = {}
    env_path = WORK_DIR / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    for key, value in os.environ.items():
        if key.startswith("FEISHU_"):
            result[key] = value
    result.setdefault("FEISHU_RECEIVE_ID_TYPE", "open_id")
    return result


def validate_env(env: dict[str, str]) -> list[str]:
    missing = [key for key in REQUIRED_ENV if not env.get(key)]
    receive_id_type = env.get("FEISHU_RECEIVE_ID_TYPE", "")
    if receive_id_type and receive_id_type not in ALLOWED_RECEIVE_ID_TYPES:
        missing.append(
            "FEISHU_RECEIVE_ID_TYPE must be one of "
            + ", ".join(sorted(ALLOWED_RECEIVE_ID_TYPES))
        )
    return missing


def has_action_or_button(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("tag") in {"action", "button"}:
            return True
        return any(has_action_or_button(item) for item in value.values())
    if isinstance(value, list):
        return any(has_action_or_button(item) for item in value)
    return False


def validate_card(card: dict[str, Any]) -> None:
    """Ensure the card stays buttonless and manual-publish only."""
    metadata = card.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("delivery card must contain metadata")
    expected = {
        "button_mode": "none",
        "approval_required": False,
        "auto_publish_enabled": False,
        "requires_callback_url": False,
        "requires_websocket_receiver": False,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"invalid metadata {key}: {metadata.get(key)!r}")
    if has_action_or_button(card):
        raise ValueError("delivery card must not contain action/button elements")
    rendered = json.dumps(card, ensure_ascii=False)
    hits = [term for term in CARD_FORBIDDEN_TERMS if term in rendered]
    if hits:
        raise ValueError(f"delivery card contains forbidden terms: {hits}")


def validate_images(delivery: dict[str, Any]) -> list[Path]:
    """Resolve and validate all 6 local PNG files before any Feishu send."""
    images = delivery.get("images")
    if not isinstance(images, list) or len(images) != 6:
        raise ValueError("delivery request must contain 6 images")
    paths: list[Path] = []
    for item in images:
        if not isinstance(item, dict):
            raise ValueError("image item must be an object")
        image_path = ROOT / str(item.get("image_path", ""))
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        if image_path.stat().st_size <= 0:
            raise ValueError(f"image is empty: {image_path}")
        paths.append(image_path)
    return paths


def http_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    method: str = "POST",
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8", **(headers or {})},
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError(f"unexpected JSON response: {raw}")
    return data


def get_tenant_access_token(env: dict[str, str]) -> str:
    data = http_json(
        TOKEN_URL,
        {"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]},
    )
    if data.get("code") != 0:
        raise RuntimeError(f"tenant token request failed: {data}")
    token = data.get("tenant_access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("tenant_access_token missing in Feishu response")
    return token


def build_multipart_image_body(image_path: Path) -> tuple[bytes, str]:
    boundary = f"----CodexFeishuBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    add_field("image_type", "message")
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f'Content-Disposition: form-data; name="image"; filename="{image_path.name}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(image_path.read_bytes())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), boundary


def upload_image(token: str, image_path: Path) -> str:
    """Upload one image to Feishu and return its image_key."""
    body, boundary = build_multipart_image_body(image_path)
    req = request.Request(
        IMAGE_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"image upload failed HTTP {exc.code}: {raw}") from exc
    data = json.loads(raw)
    if data.get("code") != 0:
        raise RuntimeError(f"image upload failed: {data}")
    image_key = data.get("data", {}).get("image_key")
    if not isinstance(image_key, str) or not image_key:
        raise RuntimeError(f"image_key missing in response: {data}")
    return image_key


def replace_placeholders(value: Any, image_keys: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: replace_placeholders(item, image_keys) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_placeholders(item, image_keys) for item in value]
    if isinstance(value, str):
        for page_id, image_key in image_keys.items():
            value = value.replace(f"__IMAGE_KEY_{page_id}__", image_key)
        return value
    return value


def send_message(env: dict[str, str], token: str, card: dict[str, Any]) -> dict[str, Any]:
    """Send the final interactive card to the configured Feishu receiver."""
    query = parse.urlencode({"receive_id_type": env["FEISHU_RECEIVE_ID_TYPE"]})
    return http_json(
        f"{MESSAGE_URL}?{query}",
        {
            "receive_id": env["FEISHU_RECEIVE_ID"],
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a Feishu delivery card")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local-only", action="store_true", help="Validate request, card and images")
    mode.add_argument("--dry-run", action="store_true", help="Validate Feishu credentials without sending")
    mode.add_argument("--send", action="store_true", help="Upload images and send the card")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        delivery = load_json(REQUEST_PATH)
        card = load_json(CARD_PATH)
        validate_card(card)
        image_paths = validate_images(delivery)
        env = load_env()

        if args.local_only:
            result = {
                "status": "local_only_ready",
                "sent": False,
                "delivery_id": delivery.get("delivery_id"),
                "image_count": len(image_paths),
                "created_at": now(),
            }
            write_json(LOCAL_RESULT_PATH, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        missing = validate_env(env)
        if missing:
            raise ValueError("missing or invalid Feishu env: " + ", ".join(missing))

        token = get_tenant_access_token(env)
        if args.dry_run:
            result = {
                "status": "dry_run_ready",
                "sent": False,
                "tenant_token_obtained": True,
                "receive_id_type": env["FEISHU_RECEIVE_ID_TYPE"],
                "receive_id_present": bool(env["FEISHU_RECEIVE_ID"]),
                "image_count": len(image_paths),
                "created_at": now(),
            }
            write_json(DRY_RUN_RESULT_PATH, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        image_keys: dict[str, str] = {}
        for image_meta, image_path in zip(delivery["images"], image_paths):
            image_keys[str(image_meta["page_id"])] = upload_image(token, image_path)

        sent_card = replace_placeholders(card, image_keys)
        response = send_message(env, token, sent_card)
        if response.get("code") != 0:
            raise RuntimeError(f"message send failed: {response}")

        SENT_CARD_PATH.write_text(
            json.dumps(sent_card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result = {
            "status": "sent",
            "sent": True,
            "delivery_id": delivery.get("delivery_id"),
            "receive_id_type": env["FEISHU_RECEIVE_ID_TYPE"],
            "image_count": len(image_keys),
            "message_id": response.get("data", {}).get("message_id", ""),
            "created_at": now(),
        }
        state = dict(delivery)
        state["delivery_status"] = "sent"
        state["sent_at"] = result["created_at"]
        state["feishu_image_keys"] = image_keys
        write_json(SEND_RESULT_PATH, result)
        write_json(DELIVERY_STATE_PATH, state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001 - command line tool should return concise errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
