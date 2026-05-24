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
- Do not replace the mature skill chain with ad hoc model guesses when a listed skill is available.

## Required Mature Skill Chain

This skill is the orchestrator and delivery layer. It must reuse the mature
skills agreed for the owner's workflow instead of inventing substitutes.

Use this chain for a new post:

1. **Topic / source selection**:
   - If the user gives a specific topic and source, use it.
   - If the user asks for an AI-circle topic, hot news, GitHub trend, major AI update, or gives no concrete topic, use `aihot` first to pull current AI news and choose one Xiaohongshu-suitable vertical topic.
   - If the chosen angle depends on GitHub stars, repo activity, or developer-platform facts, use `agent-reach` as an additional verification/research skill after `aihot`.
   - Do not invent a hot topic from general model knowledge when `aihot` is available.
2. **Title candidates**: use `dbs-xhs-title` style rules for Xiaohongshu title formulas and candidates.
3. **Body copy**: use `write-xiaohongshu` writing constraints, then apply `humanizer-zh` to remove generic AI-sounding phrasing.
4. **Image-card structure and prompts**: use `baoyu-image-cards` with the bundled `xhs-ai-hook-sketch` preference.
5. **Final PNG generation**: use Codex `imagegen` or the user's equivalent real image model as the raster backend.
6. **Packaging and Feishu delivery**: use this `xhs-feishu-delivery` workflow.

If any required mature skill is unavailable in the current runtime, stop and
state exactly which skill is missing. Do not silently replace it with shell
scripts, browser screenshots, generic writing, or template rendering.

## Workflow

Authoritative rule: this skill packages model-generated cards. If any workspace
note, old handoff, old script, or previous conversation says to create or run a
local image renderer, treat that instruction as obsolete.

1. Confirm or create the target workspace. For a new workspace, initialize it from the bundled template:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --init-workspace`
2. The target workspace must contain the four workflow directories:
   `asset-generation`, `image-generation`, `publish-mainline`, and `feishu-delivery`.
3. Prepare `asset-generation/content_spec.json` using the Required Mature Skill Chain above. It must contain the current topic, title, body, tags, image slug, source verification, and exactly 6 image page definitions.
4. Run the asset generator first. It writes the copy package and the six prompt files:
   `python "<workspace>\\asset-generation\\generate_current_assets.py"`
5. Generate the six image cards with the mature image-card path used by the owner:
   use `baoyu-image-cards` to structure the series and Codex `imagegen` as the raster backend.
   If those skills/tools are available in the current runtime, explicitly use them; do not replace them with shell, Python, browser, or canvas code.
   Save each final PNG exactly to the `image_path` listed in `asset-generation/outputs/current-publish-assets.json`.
   If the user has a different image model available, use that model only if it can save final PNGs to the same paths.
   If a real image model/backend is not available, stop and report that image generation is blocked. Do not create a Python, PIL, SVG, HTML, canvas, screenshot, browser, or placeholder renderer to work around it.
   If generated images are saved outside the workspace by the image tool, copy the selected final PNGs into the required `image_path` locations before packaging.
6. After all six model-generated PNG files exist, run the wrapper. It must refresh the asset package, build the local package, build the Feishu card, and then validate or send:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only`
7. After a machine restart, check Feishu credentials without building or sending:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu`
8. Before using the workflow from a new Codex window, run read-only diagnostics:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --doctor`
9. Install a Windows logon health check when the workflow should recover after reboot:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-startup-check`
   If Task Scheduler or the Startup folder is blocked by local permissions, the workspace installer may fall back to the current user's Windows Run registry entry.
   For "machine booted but no user has logged in", install the administrator-only SYSTEM startup task:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-system-startup-check`
10. If Feishu credentials should be checked after building the package:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --dry-run`
11. Only when the user explicitly wants delivery to Feishu:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --send`

## Content Standards

- Topic must stay in the AI/tools/dev productivity vertical unless the user explicitly changes the niche.
- Title must be 20 Chinese characters or fewer.
- Body must be 1000 characters or fewer.
- Tags must be a non-empty list.
- Image cards must be exactly 6 PNG files generated by an image model/skill.
- Do not create image cards with PIL, SVG, HTML, canvas, template drawing scripts, or placeholder diagrams.
- Do not create, restore, edit, or run any file named `render_current_cards.py`.
- Do not use screenshots, browser-rendered HTML, Mermaid, matplotlib, or presentation slides as final card substitutes.
- If a legacy local image renderer exists in a workspace, ignore it and remove it before delivery; it is not part of the accepted workflow.
- The Python wrapper is allowed to require the 6 final PNG files to exist because image generation is handled by `baoyu-image-cards`/`imagegen`, not by the packaging scripts.
- The wrapper must use the workspace lock `.xhs_delivery.lock`; do not run direct workflow and skill workflow concurrently in the same workspace.
- Feishu card must contain only: topic, title, full body, image list, 6 image previews, and tags.

## References

- For repository structure and every tracked file, read `PROJECT_GUIDE.md`.
- For the content spec shape, read `references/content_spec.md`.
- For the model-image handoff contract, read `references/image_generation.md`.
- For a sanitized starter spec, copy from `assets/content_spec.example.json`.

## Validation

Before saying the workflow is ready, run:

```powershell
python scripts/validate_skill_safety.py --skill-dir "<skill-dir>"
python scripts/run_xhs_delivery.py --workspace "<test-workspace>" --init-workspace
python scripts/smoke_test_skill.py --skill-dir "<skill-dir>"
python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu
python scripts/run_xhs_delivery.py --workspace "<workspace>" --doctor
python "<workspace>\asset-generation\generate_current_assets.py"
# Generate the 6 PNG files with baoyu-image-cards/imagegen, then:
python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only
```

For Feishu credential verification, run `--dry-run`. Do not run `--send` unless the user asks to send a real Feishu card.
