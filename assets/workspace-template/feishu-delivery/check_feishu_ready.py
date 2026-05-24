#!/usr/bin/env python3
"""Check whether Feishu delivery credentials still work after restart.

This script only obtains a Feishu tenant token. It does not upload images and
does not send any Feishu message, so it is safe to run at startup.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


WORK_DIR = Path(__file__).resolve().parent
OUT = WORK_DIR / "outputs"
RESULT_PATH = OUT / "feishu-health-result.json"

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
REQUIRED_ENV = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_RECEIVE_ID_TYPE",
    "FEISHU_RECEIVE_ID",
]
ALLOWED_RECEIVE_ID_TYPES = {"chat_id", "open_id", "user_id", "union_id", "email"}


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def load_env() -> dict[str, str]:
    """Load Feishu settings from feishu-delivery/.env and environment variables."""
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
    errors = [key for key in REQUIRED_ENV if not env.get(key)]
    receive_id_type = env.get("FEISHU_RECEIVE_ID_TYPE", "")
    if receive_id_type and receive_id_type not in ALLOWED_RECEIVE_ID_TYPES:
        errors.append(
            "FEISHU_RECEIVE_ID_TYPE must be one of "
            + ", ".join(sorted(ALLOWED_RECEIVE_ID_TYPES))
        )
    return errors


def http_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
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
    """Request a Feishu tenant token to prove credentials are still valid."""
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


def write_result(result: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    try:
        env = load_env()
        env_errors = validate_env(env)
        if env_errors:
            result = {
                "status": "blocked",
                "ready": False,
                "blocked_reasons": env_errors,
                "checked_at": now(),
            }
            write_result(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2

        token = get_tenant_access_token(env)
        result = {
            "status": "feishu_ready",
            "ready": True,
            "tenant_token_obtained": bool(token),
            "receive_id_type": env["FEISHU_RECEIVE_ID_TYPE"],
            "receive_id_present": bool(env["FEISHU_RECEIVE_ID"]),
            "sends_message": False,
            "checked_at": now(),
        }
        write_result(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should return concise errors.
        result = {
            "status": "blocked",
            "ready": False,
            "blocked_reasons": [str(exc)],
            "checked_at": now(),
        }
        write_result(result)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
