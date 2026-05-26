# content_spec.json

The workspace file `asset-generation/content_spec.json` is the single source of truth for one Xiaohongshu post.

Use this reference when editing the JSON file by hand. JSON does not support real comments, so explanatory notes live here and in `PROJECT_GUIDE.md`.

Before editing this file for a real post, follow the chain in `SKILL.md`: use `aihot` for AI-topic discovery unless the user already supplied a concrete topic/source, use `agent-reach` to verify material facts, create a factual `writing_brief`, run `asset-generation/write_copy_deepseek.py` to write the final title/body/tags with DeepSeek, run `asset-generation/write_image_prompts_deepseek.py` to write the image-card prompt plans with DeepSeek, then use `baoyu-image-cards` plus `imagegen`/image2 for the final images.

Before automatic topic selection, inspect sent history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --history`

Before generating assets for the current spec, check duplicate history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-history`

For a new workspace, initialize the bundled template first:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --init-workspace`

The template does not include a starter `content_spec.json`. Create that file fresh for each real post from the current topic, verified facts, and final DeepSeek-written copy. Do not copy old workspace outputs or old examples as the body source.

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
- `writing_brief`: required factual brief used by DeepSeek to write the final title/body/tags.
- `body_full`: final Xiaohongshu body, 1000 characters or fewer.
- `tags`: non-empty tag list, without leading `#`.
- `copy_generation`: required object written by `asset-generation/write_copy_deepseek.py`; must include `provider: "deepseek"`, a DeepSeek model name, and `writer: "asset-generation/write_copy_deepseek.py"`.
- `image_prompt_generation`: required object written by `asset-generation/write_image_prompts_deepseek.py`; must include `provider: "deepseek"`, a DeepSeek model name, `writer: "asset-generation/write_image_prompts_deepseek.py"`, `source_title`, and `source_body_sha256`.
- `image_slug`: directory name for image prompts and output PNGs.
- `pages`: exactly 6 image-card page objects.

`writing_brief` must include:

- `facts`: at least two source-backed factual claims, each with `claim` and `source_url`.
- `do_not_say`: optional list of phrases, claims, or angles to avoid.

Keep `writing_brief` factual: facts plus source-backed cautions only.

Before `asset-generation/write_image_prompts_deepseek.py`, each `pages` item must include:

- `page_id`: image file stem, for example `01-cover`.
- `layout`: optional per-card baoyu layout override such as `flow`, `comparison`, `list`, or `balanced`.

Optional old `title`, `subtitle`, and `visual` fields may be present as planning hints before the DeepSeek image prompt writer runs, but `generate_current_assets.py` does not use them as the prompt brain.

After `asset-generation/write_image_prompts_deepseek.py`, each `pages` item must include:

- `page_id`: preserved from the input outline.
- `layout`: preserved or simplified by DeepSeek.
- `image_prompt_plan`: DeepSeek-authored object with `card_role`, `visible_title`, `visible_subtitle`, `visual_direction`, `composition`, `text_style`, `required_labels`, and `avoid`.

Use `references/creator_prompt.md` through `asset-generation/write_copy_deepseek.py` before writing `body_full`. Use `references/image_prompt_creator_prompt.md` through `asset-generation/write_image_prompts_deepseek.py` before generating image prompt files. Asset generation rejects specs where `title`, `body_full`, and `tags` are not marked as DeepSeek-generated, and it also rejects image prompt plans not marked as DeepSeek-generated.

For GitHub stars, open-source projects, or repo-based topics, fill `project_facts` before generating DeepSeek image prompt plans. DeepSeek must use only these verified facts when deciding whether a project card, star count, or open-source/license badge belongs on the first image.

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
