# content_spec.json

The workspace file `asset-generation/content_spec.json` is the single source of truth for one Xiaohongshu post.

Use this reference when editing the JSON file by hand. JSON does not support real comments, so explanatory notes live here and in `PROJECT_GUIDE.md`.

Before editing this file for a real post, follow the mature skill chain in
`SKILL.md`: use `aihot` for AI-topic discovery unless the user already supplied
a concrete topic/source, use `agent-reach` to verify material facts, use
`content-strategy` to choose the content type, use `hv-analysis` in lightweight
mode to create the insight pack, use `dbs-xhs-title` for title candidates, use
read `references/editor_prompt.md`, use `write-xiaohongshu` plus
`humanizer-zh` only for final expression, and use `baoyu-image-cards` plus
`imagegen` for the final images.

Before automatic topic selection, inspect sent history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --history`

Before generating assets for the current spec, check duplicate history:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-history`

For a new workspace, initialize the bundled template first:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --init-workspace`

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
- `content_type`: one of `github_project_recommendation`, `ai_product_release`, `ai_industry_shift`, or `ai_technical_breakthrough`.
- `insight_pack`: required structured insight pack created before writing the body. It is the content brain, not Feishu output.
- `body_full`: final Xiaohongshu body, 1000 characters or fewer.
- `tags`: non-empty tag list, without leading `#`.
- `title_candidates`: optional title alternatives.
- `image_slug`: directory name for image prompts and output PNGs.
- `pages`: exactly 6 image-card page objects.

Each `pages` item must include:

- `page_id`: image file stem, for example `01-cover`.
- `title`: short card title.
- `subtitle`: short card subtitle.
- `visual`: visual direction for the image prompt.
- `layout`: optional per-card baoyu layout override such as `flow`, `comparison`, `list`, or `balanced`.

`insight_pack` must include:

- `core_hook`: the high-click Xiaohongshu angle.
- `one_sentence_event`: what happened, in one sentence.
- `why_it_matters`: why the reader should care.
- `key_takeaways`: non-empty list of concrete insights.
- `use_cases`: non-empty list of practical use cases or affected scenarios.
- `actionable_framework`: object with `name` and non-empty `items` list. This is the save-worthy method, formula, checklist, or judgment framework.
- `source_facts`: list of at least two source-backed factual claims, each with `claim` and `source_url`.
- `boundaries`: non-empty list of caveats or scope limits.
- `reader_payoff`: what the reader can do or understand after reading.

Use `references/editor_prompt.md` before writing `body_full`. The `content_type`
should guide the angle, but it must not force a rigid numbered template. The
body should feel like a real Xiaohongshu AI-tools creator sharing a useful
discovery with a point of view.

Choose the body angle from `content_type`:

- `github_project_recommendation`: discovery, one-sentence value, strengths, use cases, who should save it, why it is worth trying. Default to a positive recommendation tone and do not force risks or drawbacks.
- `ai_product_release`: what changed, what pain it solves, what is useful, who should try it, how to judge whether it is worth using.
- `ai_industry_shift`: what happened, what change it signals, how it affects users/developers, and one judgment framework.
- `ai_technical_breakthrough`: one-sentence explanation, what limitation changed, why it matters, possible applications, and current boundaries.

For GitHub stars, open-source projects, or repo-based topics, fill
`project_facts` before generating prompts. The cover prompt will then ask the
image model to show the project card, star count, and open-source/license badge
on the first image instead of hiding those facts in later cards.

Duplicate detection normalizes GitHub repos and source URLs. For example,
`TauricResearch/TradingAgents`, `github.com/TauricResearch/TradingAgents`, and
`https://github.com/TauricResearch/TradingAgents` are treated as the same sent
topic key. `generate_current_assets.py` blocks duplicates unless
`history.allow_repeat` is explicitly true.

The workflow writes prompt files from `content_spec.json`. Codex should then use
`baoyu-image-cards` / `imagegen` to generate the final PNG files before
packaging:

`image-generation/outputs/images/<image_slug>/<page_id>.png`

Do not use a local drawing script, PIL renderer, SVG, HTML, or canvas output as
the final image-card source.

Do not add music fields, auto-publish fields, Xiaohongshu login fields, or analytics fields.

Feishu delivery does not require a persistent connection. After restarting the machine, run:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu`

For long-term local use on Windows, install the logon health check once:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-startup-check`

For machine startup before any user logs in, use the administrator-only SYSTEM task installer:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-system-startup-check`
