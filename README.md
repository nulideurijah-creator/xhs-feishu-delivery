# xhs-feishu-delivery

A Codex skill for preparing Xiaohongshu image-text post packages and sending complete delivery cards to Feishu for manual publishing.

This workflow is intentionally manual-publish only. It does not automate Xiaohongshu login, upload, editor control, or publishing.

## What It Does

- Validates a Xiaohongshu content spec.
- Renders 6 deterministic PNG image cards from the content spec.
- Builds a local post package from an existing workspace.
- Validates title, body, tags, and exactly 6 image cards.
- Builds a buttonless Feishu delivery card.
- Sends the full title, body, tags, image list, and 6 image previews to Feishu.
- Can install a Windows logon health check for Feishu credentials.

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
│   ├── render_current_cards.py
│   └── outputs/images/<image_slug>/<page_id>.png
├── publish-mainline/
│   ├── build_manual_publish_package.py
│   └── preflight.py
└── feishu-delivery/
    ├── check_feishu_ready.py
    ├── install_startup_check.py
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
python scripts/run_xhs_delivery.py --workspace "D:\path\to\workspace" --check-feishu
```

Install automatic Feishu health check after Windows logon:

```powershell
python scripts/run_xhs_delivery.py --workspace "D:\path\to\workspace" --install-startup-check
```

Build the package and validate Feishu credentials without sending:

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

Feishu delivery does not use a persistent connection. Reboots do not break a daemon because there is no daemon; each send fetches a fresh tenant token. For long-term desktop use, install the logon health check once. If Windows blocks Task Scheduler or the Startup folder, the workspace installer may fall back to the current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` startup entry.

## License

MIT
