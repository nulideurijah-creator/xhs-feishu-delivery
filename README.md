# xhs-feishu-delivery

A Codex skill for preparing Xiaohongshu image-text post packages and sending complete delivery cards to Feishu for manual publishing.

This workflow is intentionally manual-publish only. It does not automate Xiaohongshu login, upload, editor control, or publishing.

## What It Does

- Validates a Xiaohongshu content spec.
- Builds a local post package from an existing workspace.
- Validates title, body, tags, and exactly 6 image cards.
- Builds a buttonless Feishu delivery card.
- Sends the full title, body, tags, image list, and 6 image previews to Feishu.

## What It Does Not Do

- No Xiaohongshu MCP.
- No browser automation for Xiaohongshu.
- No cookies or login state.
- No auto-publishing.
- No Feishu approval buttons, callbacks, WebSocket receivers, or tunnels.
- No Obsidian, analytics, competitor scraping, or self-improvement loop.

## Install

Copy this repository into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force . "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery"
```

Restart Codex or open a new session, then call:

```text
$xhs-feishu-delivery prepare and validate my Xiaohongshu Feishu delivery package
```

## Workspace Layout

The skill expects a workspace with these directories:

```text
workspace/
├── asset-generation/
│   ├── content_spec.json
│   └── generate_current_assets.py
├── image-generation/
│   └── outputs/images/<image_slug>/<page_id>.png
├── publish-mainline/
│   ├── build_manual_publish_package.py
│   └── preflight.py
└── feishu-delivery/
    ├── build_delivery_card.py
    ├── send_delivery_card.py
    └── .env
```

Use `assets/content_spec.example.json` as a starter for `asset-generation/content_spec.json`.

## Run

Validate locally:

```powershell
python scripts/run_xhs_delivery.py --workspace "D:\path\to\workspace" --local-only
```

Validate Feishu credentials without sending:

```powershell
python scripts/run_xhs_delivery.py --workspace "D:\path\to\workspace" --dry-run
```

Send the Feishu delivery card:

```powershell
python scripts/run_xhs_delivery.py --workspace "D:\path\to\workspace" --send
```

## Feishu Env

Keep Feishu credentials only in the workspace:

```text
workspace/feishu-delivery/.env
```

Do not commit `.env`.

Required variables:

```text
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=
```

## Validate This Skill

```powershell
python scripts/validate_skill_safety.py --skill-dir .
python -m py_compile scripts/run_xhs_delivery.py scripts/validate_skill_safety.py
```

## License

MIT
