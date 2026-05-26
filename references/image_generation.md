# Image Generation Contract

This skill uses model-generated image cards. It does not ship or call a local
template renderer for final images.

## Required Flow

1. Run the DeepSeek image prompt planner after the DeepSeek copy writer:

   `python <workspace>/asset-generation/write_image_prompts_deepseek.py`

2. Run the asset generator:

   `python <workspace>/asset-generation/generate_current_assets.py`

3. Read the generated prompt package:

   `asset-generation/outputs/current-image-card-prompts.md`

4. Generate the six PNG files with the user's available image-generation stack:

   - preferred structure skill: `baoyu-image-cards`
   - preferred raster backend in Codex: `imagegen`
   - fallback: image2 or the user's own equivalent image model, if Codex imagegen is not available
   - bundled visual style: `xhs-warm-cute-open-source`

   When `baoyu-image-cards` and `imagegen` are available in the runtime, use
   those skills/tools directly. Do not replace this step with shell, Python,
   browser automation, or generated HTML.

   Use the bundled defaults without asking the user again:

   - watermark: none
   - style: `xhs-warm-cute-open-source`
   - layout: `balanced`
   - palette: `macaron`
   - backend: `imagegen`
   - batch size: `4`
   - confirmation: skipped with `--yes` or the runtime's equivalent

   If `baoyu-image-cards` asks first-use preference questions, answer from
   `.baoyu-skills/baoyu-image-cards/EXTEND.md`. Do not ask the user to pick a
   watermark, style, layout, palette, backend, or preference save scope for this
   workflow.

   If no real image model/backend is available, stop here and report the block.
   Do not write code that draws substitute cards locally.

   For GitHub stars, open-source projects, or repository-based topics, the first
   card should make the verified project facts visible: repo/project name, star
   count, license/open-source badge, and source cue. Do not invent missing
   counts or bury the project details on later pages.

5. Save every final PNG exactly to the `image_path` values listed in:

   `asset-generation/outputs/current-publish-assets.json`

6. Run packaging and Feishu validation:

   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only`

   Use `--dry-run` to verify Feishu credentials after packaging, and `--send`
   only when the user explicitly asks to send a real Feishu card.

## Rules

- Do not generate final cards with PIL, SVG, HTML, canvas, or a template drawing script.
- Do not let `generate_current_assets.py` recreate the old prompt brain. It may only wrap DeepSeek `image_prompt_plan` values with fixed baoyu metadata.
- Do not create, restore, edit, or run `render_current_cards.py`.
- Do not use screenshots, browser-rendered HTML, Mermaid, matplotlib, slide decks, or placeholder diagrams as final card substitutes.
- Do not use placeholder diagrams as final cards.
- Do not reuse old test images unless the user explicitly asks for a fixture-style dry run.
- If the image model saves files somewhere else first, move the selected final PNGs into the required workspace paths before packaging.
- If the image-generation backend is unavailable, stop before packaging and tell the user which backend is missing.

## Expected Output Paths

The image paths are deterministic:

`image-generation/outputs/images/<image_slug>/<page_id>.png`

The six `page_id` values come from `asset-generation/content_spec.json`.
