---
name: xhs-feishu-delivery
description: Use when the user wants to create a Xiaohongshu image-text post package, validate the manual publishing workflow, or send a complete Feishu delivery card for manual Xiaohongshu posting. This skill never automates Xiaohongshu publishing.
metadata:
  short-description: Xiaohongshu post package to Feishu delivery
---

# XHS Feishu Delivery

Use this skill to operate the local workflow that creates a Xiaohongshu image-text content package and sends the complete package to Feishu for manual posting.

## Safety Rules

- Do not call Xiaohongshu MCP, browser publishing scripts, or any publish API.
- Do not create, read, or upload Xiaohongshu cookies.
- Do not open Xiaohongshu editor pages or click publish buttons.
- Do not add Feishu buttons, callbacks, WebSocket receivers, or approval state machines.
- Do not include music fields.
- Do not treat this workflow as data analytics, Obsidian memory, competitor analysis, or self-improvement tracking.

## Workflow

1. Confirm or create the target workspace that contains the four workflow directories:
   `asset-generation`, `image-generation`, `publish-mainline`, and `feishu-delivery`.
2. Make sure `asset-generation/content_spec.json` contains the current topic, title, body, tags, image slug, and exactly 6 image page definitions.
3. Make sure 6 approved PNG images exist under `image-generation/outputs/images/<image_slug>/`.
4. Run the wrapper:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only`
5. If Feishu credentials should be checked without sending:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --dry-run`
6. Only when the user explicitly wants delivery to Feishu:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --send`

## Content Standards

- Topic must stay in the AI/tools/dev productivity vertical unless the user explicitly changes the niche.
- Title must be 20 Chinese characters or fewer.
- Body must be 1000 characters or fewer.
- Tags must be a non-empty list.
- Image cards must be exactly 6 PNG files.
- Feishu card must contain only: topic, title, full body, image list, 6 image previews, and tags.

## References

- For the content spec shape, read `references/content_spec.md`.
- For a sanitized starter spec, copy from `assets/content_spec.example.json`.

## Validation

Before saying the workflow is ready, run:

```powershell
python scripts/validate_skill_safety.py --skill-dir "<skill-dir>"
python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only
```

For Feishu credential verification, run `--dry-run`. Do not run `--send` unless the user asks to send a real Feishu card.
