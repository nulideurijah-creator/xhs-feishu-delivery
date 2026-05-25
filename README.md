# xhs-feishu-delivery

`xhs-feishu-delivery` is a Codex skill plus a clean workspace template for producing Xiaohongshu image-text posts and delivering the complete manual posting package to Feishu.

It is built for creators who want an AI-assisted workflow but still want to publish manually on Xiaohongshu. The workflow researches an AI/tools/dev topic, lets the current model write the final title/body/tags directly, prepares six image-card prompts, expects real image-model PNGs, builds a manual publishing package, and sends the full package to Feishu.

It does **not** automate Xiaohongshu publishing, login, cookies, MCP, browser control, analytics, or Obsidian memory.

## What You Get

- A Codex skill entrypoint: `SKILL.md`.
- A clean workspace template under `assets/workspace-template`.
- A wrapper for initialization, diagnostics, Feishu checks, packaging, local validation, and sending.
- A direct model-writing flow using `references/creator_prompt.md`.
- A deterministic copy-quality gate that blocks tool-manual, report, and checklist copy before image work.
- A model-image handoff using `baoyu-image-cards` and Codex `imagegen`.
- A bundled `xhs-warm-cute-open-source` visual style for warm cute Xiaohongshu AI cards with visible GitHub/open-source facts on repo-based covers.
- Workspace-local sent history that records successful Feishu deliveries and blocks repeated topics.
- A workflow lock for unattended Codex automations.
- Safety checks that prevent accidental Xiaohongshu automation or secret leakage.

## Mental Model

| Layer | Example Path | Purpose |
|---|---|---|
| GitHub repository | `xhs-feishu-delivery` | Source of truth for the skill, scripts, workspace template, tests, and docs. |
| Installed Codex skill | `%USERPROFILE%\.codex\skills\xhs-feishu-delivery` | The copy Codex reads when you invoke this skill. Update it from the GitHub repo after pulling changes. |
| Local workspace | `D:\path\to\xhs-workspace` | Private production folder. It stores Feishu `.env`, current post spec, generated prompts, final images, and delivery outputs. Do not commit this folder. |

The GitHub repo does not include your Feishu credentials, generated images, or private post history.

## Workflow

```mermaid
flowchart LR
  A["aihot selects AI topic"] --> B["agent-reach verifies facts"]
  B --> C["Create factual writing_brief"]
  C --> D["creator_prompt + model write title/body/tags"]
  D --> E["content_spec.json"]
  E --> F["Check sent history for duplicates"]
  F --> G["Check copy quality gate"]
  G --> H["baoyu-image-cards prepares 6-card structure"]
  H --> I["imagegen creates 6 PNG cards"]
  I --> J["Build manual package"]
  J --> K["Send complete Feishu card"]
  K --> L["Record sent history"]
  L --> M["User posts manually on Xiaohongshu"]
```

## Skills Used

- `aihot`: default source for AI-circle hot topics and news selection.
- `agent-reach`: verification for source URLs, GitHub stars, repo activity, official announcements, X posts, and developer-platform facts.
- `baoyu-image-cards`: structures the 6-card Xiaohongshu image series.
- `imagegen`: generates the final raster PNG cards.
- `xhs-feishu-delivery`: packages the result and sends it to Feishu.

Title and body are written directly by the current model from `writing_brief` and `references/creator_prompt.md`. There is no formula-title layer and no extra rewrite layer.

## Prerequisites

- Python 3.10+ available as `python`.
- Codex with local skills support.
- Supporting skills available in the Codex runtime: `aihot`, `agent-reach`, `baoyu-image-cards`, and `imagegen`.
- A Feishu app or bot with credentials that can send messages/images to your target receiver.
- A real image-generation backend. This project prepares prompts and file paths; it does not draw final cards with local template code.

If any supporting skill or image backend is unavailable, stop and fix that first. Do not replace final images with PIL, SVG, HTML, browser screenshots, or placeholder diagrams.

## Quick Start

Install the skill:

```powershell
git clone https://github.com/nulideurijah-creator/xhs-feishu-delivery.git
cd .\xhs-feishu-delivery
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force . "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery"
```

Restart Codex after installing the skill.

Create a private workspace:

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

Required values:

```text
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=
```

Verify Feishu credentials without sending:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-feishu
```

## Creating a Post

1. Inspect previous successful sends:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --history
```

2. Let Codex use the skill to create `asset-generation/content_spec.json` for the current topic. The spec must include verified facts, `writing_brief`, final title, final body, tags, image slug, and exactly six image pages.

3. Check duplicate history:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-history
```

4. Check the title/body/tags against the local creator-copy gate:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --check-copy
```

5. Generate copy output and image prompt files:

```powershell
python .\asset-generation\generate_current_assets.py
```

6. Generate six PNG cards with `baoyu-image-cards` and Codex `imagegen`, then save each PNG to the `image_path` values listed in:

```text
asset-generation\outputs\current-publish-assets.json
```

7. Validate the complete local package:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --local-only
```

8. Dry-run Feishu access after the images are ready:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --dry-run
```

9. Send the complete delivery card to Feishu:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --send
```

## content_spec.json Shape

The workspace does not ship a starter post. Create a fresh `asset-generation/content_spec.json` for each run.

Minimum shape:

```json
{
  "review_id": "publish-example",
  "content_id": "example-topic",
  "title": "20字以内标题",
  "topic": "AI 圈具体选题",
  "summary": "内部摘要",
  "hot_source": "aihot or user supplied",
  "source_urls": ["https://example.com/source"],
  "source_verification": {"source": "verified source notes"},
  "writing_brief": {
    "facts": [
      {"claim": "事实 1", "source_url": "https://example.com/source-1"},
      {"claim": "事实 2", "source_url": "https://example.com/source-2"}
    ],
    "why_now": "现在为什么值得写",
    "creator_angle": "博主这篇要怎么讲",
    "audience": "谁应该看或收藏",
    "do_not_say": []
  },
  "project_facts": {
    "name": "optional project name",
    "repo": "optional GitHub repo",
    "github_stars": "optional verified star count",
    "license": "optional license"
  },
  "body_full": "最终正文",
  "tags": ["AI工具", "小红书运营"],
  "image_slug": "example-topic",
  "pages": [
    {"page_id": "01-cover", "title": "封面标题", "subtitle": "封面副标题", "visual": "cover visual direction"},
    {"page_id": "02-point", "title": "第2张", "subtitle": "副标题", "visual": "visual direction"},
    {"page_id": "03-point", "title": "第3张", "subtitle": "副标题", "visual": "visual direction"},
    {"page_id": "04-point", "title": "第4张", "subtitle": "副标题", "visual": "visual direction"},
    {"page_id": "05-point", "title": "第5张", "subtitle": "副标题", "visual": "visual direction"},
    {"page_id": "06-save", "title": "第6张", "subtitle": "副标题", "visual": "visual direction"}
  ]
}
```

See [references/content_spec.md](references/content_spec.md) for details.

## Quality Standard

- Stay inside the AI/tools/dev productivity vertical.
- Ground the post in at least two source-backed facts.
- Let the current model write the final title/body/tags directly from the brief.
- The title must have a Xiaohongshu hook, not a documentation heading like "项目介绍" or "使用指南".
- The body should sound like a real Xiaohongshu AI creator sharing a discovery, with a concrete scene, personal judgment, and a small natural friction point.
- GitHub/open-source posts should make useful facts visible through the creator's story and judgment, not a fixed checklist.
- The title/body/tags must pass the local copy-quality gate before image generation, local packaging, or Feishu delivery.
- Avoid empty phrases like "值得关注", "很有潜力", "它干的事很简单", "它的好处是", "首先/其次/最后", or report-style transitions.

## Sent History

Every successful `--send` appends or updates:

```text
content-history\sent-posts.jsonl
```

Duplicate detection normalizes GitHub repos and source URLs. To intentionally revisit a topic, add this only when the user explicitly asks for a repeat:

```json
{
  "history": {
    "allow_repeat": true,
    "topic_key": "custom-topic-key"
  }
}
```

## Startup Check

Recommended desktop setup:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --install-startup-check
```

Machine-startup before any user logs in requires administrator permissions:

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --install-system-startup-check
```

## Common Checks

```powershell
python "$env:USERPROFILE\.codex\skills\xhs-feishu-delivery\scripts\run_xhs_delivery.py" --workspace "D:\path\to\xhs-workspace" --doctor
```

Typical blockers:

- `images_missing:6`: image prompts exist, but the six final PNG files have not been generated or copied into the required output paths.
- `feishu_env_missing`: create `feishu-delivery\.env` from `.env.example` and fill the required `FEISHU_` values.
- `feishu_env_missing_keys`: one or more required Feishu fields are empty.
- `tenant token request failed`: the Feishu app id/secret is wrong, expired, or lacks access in the tenant.
- `workflow already running or lock exists`: another run is active, or `.xhs_delivery.lock` was left behind after an interrupted run. Delete the lock only after confirming no workflow is running.

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
