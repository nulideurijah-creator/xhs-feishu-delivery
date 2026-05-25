# content_spec.json

The workspace file `asset-generation/content_spec.json` is the single source of truth for one Xiaohongshu post.

Use this reference when editing the JSON file by hand. JSON does not support real comments, so explanatory notes live here and in `PROJECT_GUIDE.md`.

Before editing this file for a real post, follow the chain in `SKILL.md`: use `aihot` for AI-topic discovery unless the user already supplied a concrete topic/source, use `agent-reach` to verify material facts, pass the factual `writing_brief` plus `references/creator_prompt.md` to the current model to write the final title/body/tags directly, then use `baoyu-image-cards` plus `imagegen` for the final images.

Before automatic topic selection, inspect sent history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --history`

Before generating assets for the current spec, check duplicate history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-history`

For a new workspace, initialize the bundled template first:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --init-workspace`

The template does not include a starter `content_spec.json`. Create that file fresh for each real post from the current topic, verified facts, and final model-written copy. Do not copy old workspace outputs or old examples as the body source.

Required fields:

- `review_id`: stable delivery run id.
- `content_id`: stable post content id.
- `title`: final Xiaohongshu title, 20 Chinese characters or fewer.
- `summary`: short internal summary.
- `topic`: topic to explain.
- `hot_source`: source label for the topic, usually the selected `aihot` item or the user-supplied source.
- `source_urls`: list of source URLs.
- `source_verification`: source notes and factual caveats.
- `project_facts`: optional object for GitHub/open-source topics. Use verified values only; supported keys include `name`, `repo`, `github_stars`, `license`, `open_source`, `url`, and `description`.
- `history`: optional object for duplicate handling. Use `topic_key` to pin a stable dedupe key. Use `allow_repeat: true` only when the user explicitly asks to repeat a topic.
- `writing_brief`: required factual brief used by the model to write the final title/body/tags.
- `body_full`: final Xiaohongshu body, 1000 characters or fewer.
- `tags`: non-empty tag list, without leading `#`.
- `image_slug`: directory name for image prompts and output PNGs.
- `pages`: exactly 6 image-card page objects.

`writing_brief` must include:

- `facts`: at least two source-backed factual claims, each with `claim` and `source_url`.
- `do_not_say`: optional list of phrases, claims, or angles to avoid.

Keep `writing_brief` factual: facts plus source-backed cautions only.

Each `pages` item must include:

- `page_id`: image file stem, for example `01-cover`.
- `title`: short card title.
- `subtitle`: short card subtitle.
- `visual`: visual direction for the image prompt.
- `layout`: optional per-card baoyu layout override such as `flow`, `comparison`, `list`, or `balanced`.

The first page is the cover. Its `title` must match the current top-level `title`.
If a model rewrite changes `title`, refresh `pages` before running `generate_current_assets.py`.

Use `references/creator_prompt.md` before writing `body_full`. The body should feel like a real Xiaohongshu AI-tools creator sharing a useful discovery with a point of view.

For GitHub stars, open-source projects, or repo-based topics, fill `project_facts` before generating prompts. The cover prompt will then ask the image model to show the project card, star count, and open-source/license badge on the first image instead of hiding those facts in later cards.

Duplicate detection normalizes GitHub repos and source URLs. For example, `TauricResearch/TradingAgents`, `github.com/TauricResearch/TradingAgents`, and `https://github.com/TauricResearch/TradingAgents` are treated as the same sent topic key. `generate_current_assets.py` blocks duplicates unless `history.allow_repeat` is explicitly true.

The workflow writes prompt files from `content_spec.json`. Codex should then use `baoyu-image-cards` / `imagegen` to generate the final PNG files before packaging:

`image-generation/outputs/images/<image_slug>/<page_id>.png`

Use the workspace `.baoyu-skills/baoyu-image-cards/EXTEND.md` defaults directly when generating images: no watermark, `xhs-warm-cute-open-source`, balanced layout, macaron palette, Codex `imagegen`, and no extra preference questions.

Do not use a local drawing script, PIL renderer, SVG, HTML, or canvas output as the final image-card source.

Do not add music fields, auto-publish fields, Xiaohongshu login fields, or analytics fields.

Feishu delivery does not require a persistent connection. After restarting the machine, run:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu`

For long-term local use on Windows, install the logon health check once:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-startup-check`

For machine startup before any user logs in, use the administrator-only SYSTEM task installer:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-system-startup-check`
