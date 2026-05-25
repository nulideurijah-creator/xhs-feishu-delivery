# xhs-feishu-delivery

`xhs-feishu-delivery` is a Codex skill plus a ready-to-copy workspace template for producing Xiaohongshu image-text posts and delivering the complete posting package to Feishu.

The project is designed for creators who want an AI-assisted content production workflow but still want to post manually on Xiaohongshu. It generates copy and image prompts, uses mature image-generation skills/models for the 6 final image cards, builds a manual publishing package, and sends the full title/body/tags/images to Feishu so the user can publish from mobile.

It does **not** automate Xiaohongshu publishing, login, cookies, MCP, or browser control.

## What You Get

- A Codex skill entrypoint: `SKILL.md`.
- A clean workspace template under `assets/workspace-template`. It ships scripts and folders only, not a prewritten post.
- A wrapper for initializing, validating, packaging, and sending.
- A model-first image step: final image cards should come from `baoyu-image-cards`/Codex `imagegen`, using the bundled `xhs-warm-cute-open-source` style for warm cute Xiaohongshu covers that still expose GitHub/open-source facts clearly.
- A workspace-local sent history file that records successful Feishu deliveries and blocks repeated topics before the next asset generation.
- Feishu health checks that can run after Windows logon.
- Safety checks that prevent accidental Xiaohongshu automation or secret leakage.

## Mental Model

There are three layers:

| Layer | Example Path | Purpose |
|---|---|---|
| GitHub repository | `xhs-feishu-delivery` | Source of truth for the skill, scripts, workspace template, tests, and docs. |
| Installed Codex skill | `%USERPROFILE%\.codex\skills\xhs-feishu-delivery` | The copy Codex reads when you invoke this skill. Update it from the GitHub repo after pulling changes. |
| Local workspace | `D:\path\to\xhs-workspace` | Your production folder. It stores Feishu `.env`, current post spec, generated prompts, final images, and delivery outputs. Do not commit this folder. |

The GitHub repo gives other users the same workflow and image-prompt style. It does not include your Feishu credentials, generated images, or private post history. Private sent history stays in the local workspace under `content-history/sent-posts.jsonl`.

## Workflow

```mermaid
flowchart LR
  A["aihot selects AI topic"] --> B["agent-reach verifies facts"]
  B --> C["Model creates content type and insight pack"]
  C --> D["dbs-xhs-title creates title candidates"]
  D --> E["editor_prompt + model create body"]
  E --> G["content_spec.json"]
  G --> H["Check sent history for duplicates"]
  H --> I["baoyu-image-cards creates image prompts"]
  I --> J["imagegen creates 6 PNG cards"]
  J --> K["Build manual package"]
  K --> L["Send complete Feishu card"]
  L --> M["Record sent history"]
  M --> N["User posts manually on Xiaohongshu"]
```

## Mature Skills Used

- `aihot`: default source for AI-circle hot topics and news selection.
- `agent-reach`: verification for source URLs, GitHub stars, repo activity, official announcements, X posts, and developer-platform facts.
- `dbs-xhs-title`: Xiaohongshu title formulas and candidates.
- `references/editor_prompt.md`: owner's Xiaohongshu creator voice prompt for natural, non-template body copy.
- `baoyu-image-cards`: structures the 6-card Xiaohongshu image series.
- `imagegen`: generates the final raster PNG cards.
- `xhs-feishu-delivery`: packages the result and sends it to Feishu.

## Repository Guide

Every file in this repository is explained in [PROJECT_GUIDE.md](PROJECT_GUIDE.md).

The image-generation handoff is documented in [references/image_generation.md](references/image_generation.md).

## Prerequisites

- Windows PowerShell examples are shown below. The scripts are Python and can be adapted to other shells.
- Python 3.10+ available as `python`.
- Codex with local skills support.
- Supporting skills available in the Codex runtime:
  - `aihot`
  - `agent-reach`
  - `dbs-xhs-title`
  - `baoyu-image-cards`
  - `imagegen`
- A Feishu app or bot with credentials that can send messages/images to your target receiver.
- A real image-generation backend. This project prepares prompts and file paths; it does not draw final cards with local template code.

If any supporting skill or image backend is unavailable, stop and fix that first. Do not replace final images with PIL, SVG, HTML, browser screenshots, or placeholder diagrams.

## Stable Defaults

The workflow is intentionally opinionated so a new Codex window does not reopen old choices:

- Xiaohongshu posting is manual only.
- Feishu cards are buttonless and contain the complete title, body, tags, and six images.
- Final images use `baoyu-image-cards` plus `imagegen`; local drawing scripts are not part of the workflow.
- Image-card defaults come from `assets/workspace-template/.baoyu-skills/baoyu-image-cards/EXTEND.md`: no watermark, `xhs-warm-cute-open-source`, `balanced`, `macaron`, `imagegen`, batch size `4`.
- If the image-card skill asks first-use preference questions, answer from the bundled defaults and continue with `--yes` or the runtime's equivalent direct-default instruction.

## Quick Start

Use this path for a first clean install.

```powershell
# 1. Clone the source repo.
git clone https://github.com/nulideurijah-creator/xhs-feishu-delivery.git
cd .\xhs-feishu-delivery

# 2. Install the skill into Codex.
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force . "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery"
```

Restart Codex after installing the skill.

```powershell
# 3. Create a private local workspace.
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --init-workspace
cd "D:\path\to\xhs-workspace"
python -m pip install -r requirements.txt

# 4. Configure Feishu credentials.
Copy-Item .\feishu-delivery\.env.example .\feishu-delivery\.env
notepad .\feishu-delivery\.env
```

Fill these values in `.env`:

```text
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=
```

Verify Feishu credentials without sending a message:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-feishu
```

Create the post assets:

```powershell
# 5. Before automatic topic selection, inspect previous successful sends.
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --history

# 6. Let Codex create this file for the current topic from the mature skill chain.
#    Do not copy old outputs or starter posts into it.
notepad .\asset-generation\content_spec.json

# 7. Check this spec against sent history. Duplicate repo/source/topic keys are blocked.
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-history

# 8. Generate copy output and image prompt files.
python .\asset-generation\generate_current_assets.py
```

Generate the six image cards with `baoyu-image-cards` and Codex `imagegen`, then save each PNG to the `image_path` values listed in:

```text
asset-generation\outputs\current-publish-assets.json
```

Validate the complete local package:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --local-only
```

Validate Feishu access after the images are ready, without sending:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --dry-run
```

Send the complete delivery card to Feishu only when you are ready:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --send
```

## Command Reference: Install Skill

```powershell
git clone https://github.com/nulideurijah-creator/xhs-feishu-delivery.git
Copy-Item -Recurse -Force .\xhs-feishu-delivery "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery"
```

Restart Codex after installing.

## Command Reference: Create Workspace

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --init-workspace
cd "D:\path\to\xhs-workspace"
python -m pip install -r requirements.txt
```

Configure Feishu credentials:

```powershell
Copy-Item .\feishu-delivery\.env.example .\feishu-delivery\.env
notepad .\feishu-delivery\.env
```

Required variables:

```text
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=
```

## GitHub/Open-Source Cover Facts

For GitHub stars, open-source projects, or repo-based topics, add verified facts to `asset-generation/content_spec.json` before running `generate_current_assets.py`:

```json
{
  "project_facts": {
    "name": "models.dev",
    "repo": "github.com/example/repo",
    "github_stars": "4.1k stars",
    "license": "MIT",
    "open_source": "true",
    "url": "https://github.com/example/repo",
    "description": "Short factual project note"
  }
}
```

The bundled `xhs-warm-cute-open-source` style asks the cover prompt to show those facts as a visible GitHub-style project card: project name, star count, and open-source/license badge should be visible on the first image. Do not invent missing star counts, repo names, licenses, or logos.

## Sent History and Deduplication

Every successful `--send` appends or updates a private JSONL record:

```text
content-history\sent-posts.jsonl
```

Each record stores the title, topic, content type, Feishu `message_id`, send time, normalized `topic_key`, and normalized source keys. For GitHub/open-source posts, `TauricResearch/TradingAgents`, `github.com/TauricResearch/TradingAgents`, and `https://github.com/TauricResearch/TradingAgents` all normalize to the same key:

```text
github.com/tauricresearch/tradingagents
```

Before automatic topic selection, list the recent history:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --history
```

Before generating prompts for a new `content_spec.json`, check it:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-history
```

`generate_current_assets.py` also runs the same duplicate check, so a repeated repo/source/topic is blocked even if the manual check is skipped. To intentionally revisit a topic, add this only when the user explicitly asks for a repeat:

```json
{
  "history": {
    "allow_repeat": true,
    "topic_key": "custom-topic-key"
  }
}
```

## Body Quality Standard

Every post must include a structured `insight_pack` before `body_full` is written. The body should feel like a Xiaohongshu creator sharing a useful discovery, not a report, product manual, or training handout. Use [references/editor_prompt.md](references/editor_prompt.md) before writing the body.

Allowed content types:

- `github_project_recommendation`: positive discovery/recommendation tone for GitHub and open-source projects.
- `ai_product_release`: new AI model, product, or feature release.
- `ai_industry_shift`: funding, hiring, cost, regulation, platform, or market-change story.
- `ai_technical_breakthrough`: paper, architecture, benchmark, model capability, or technical method.

The final body must include at least one useful judgment, use case, or reader takeaway, but it should not force a rigid numbered checklist unless the topic naturally needs one. Avoid generic recap phrases such as "值得关注", "很有潜力", "它做的事很直接", "这个数据仅是一个参考", or empty reminders that do not tell the reader what to do next.

## Command Reference: Run

Validate without Feishu:

```powershell
# First create copy and image prompts:
python .\asset-generation\generate_current_assets.py

# Then generate the 6 PNG cards with baoyu-image-cards / Codex imagegen and
# save them to the image_path values in asset-generation\outputs\current-publish-assets.json.
# The bundled .baoyu-skills config prefers xhs-warm-cute-open-source: no
# watermark, warm hand-drawn macaron cards, and visible GitHub/open-source facts
# on the cover when a post is about a repo or starred project.
# If you use another image model, keep the same output paths.

# Finally package and validate:
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --local-only
```

Check Feishu credentials:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-feishu
```

Run a local doctor before using the workflow from a new Codex window:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --doctor
```

Send the complete package to Feishu:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --send
```

## Common Checks

Run the doctor before using a workspace from a new Codex window:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --doctor
```

Typical blocker meanings:

- `images_missing:6`: image prompts exist, but the six final PNG files have not been generated or copied into the required output paths.
- `feishu_env_missing`: create `feishu-delivery\.env` from `.env.example` and fill the required `FEISHU_` values.
- `feishu_env_missing_keys`: one or more required Feishu fields are empty.
- `tenant token request failed`: the Feishu app id/secret is wrong, expired, or lacks access in the tenant.
- `workflow already running or lock exists`: another run is active, or `.xhs_delivery.lock` was left behind after an interrupted run. Delete the lock only after confirming no workflow is running.

## Startup Check

Recommended long-term desktop setup: run the Feishu health check after Windows logon. This is the most reliable mode for normal creator workstations because it uses the same user account, Python install, workspace path, and network profile as the manual workflow.

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --install-startup-check
```

Machine-startup before any user logs in is possible only when Windows allows a SYSTEM scheduled task to access the workspace and Python install. Use this only for unattended-server style setups:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --install-system-startup-check
```

## Safety

- Manual Xiaohongshu posting only.
- No Xiaohongshu MCP.
- No Xiaohongshu cookies.
- No browser publishing automation.
- No local template drawing renderer for final cards.
- No Feishu buttons, callbacks, WebSocket receiver, or tunnel.
- Workspace runs are protected by `.xhs_delivery.lock`.

## Validate Skill

```powershell
python scripts\validate_skill_safety.py --skill-dir .
python -m compileall -q scripts assets\workspace-template tests
python -m unittest discover -s tests -v
python scripts\smoke_test_skill.py --skill-dir .
```

## License

MIT
