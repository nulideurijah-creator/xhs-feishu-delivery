# Image Generation Contract

This skill uses model-generated image cards. It does not ship or call a local
template renderer for final images.

## Required Flow

1. Run the asset generator:

   `python <workspace>/asset-generation/generate_current_assets.py`

2. Read the generated prompt package:

   `asset-generation/outputs/current-image-card-prompts.md`

3. Generate the six PNG files with the user's available image-generation stack:

   - preferred structure skill: `baoyu-image-cards`
   - preferred raster backend in Codex: `imagegen`
   - fallback: the user's own equivalent image model, if Codex imagegen is not available

   If no real image model/backend is available, stop here and report the block.
   Do not write code that draws substitute cards locally.

4. Save every final PNG exactly to the `image_path` values listed in:

   `asset-generation/outputs/current-publish-assets.json`

5. Run packaging and Feishu delivery:

   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only`

## Rules

- Do not generate final cards with PIL, SVG, HTML, canvas, or a template drawing script.
- Do not create, restore, edit, or run `render_current_cards.py`.
- Do not use placeholder diagrams as final cards.
- Do not reuse old test images unless the user explicitly asks for a fixture-style dry run.
- If the image model saves files somewhere else first, move the selected final PNGs into the required workspace paths before packaging.
- If the image-generation backend is unavailable, stop before packaging and tell the user which backend is missing.

## Expected Output Paths

The image paths are deterministic:

`image-generation/outputs/images/<image_slug>/<page_id>.png`

The six `page_id` values come from `asset-generation/content_spec.json`.
