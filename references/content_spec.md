# content_spec.json

The workspace file `asset-generation/content_spec.json` is the single source of truth for one Xiaohongshu post.

Use this reference when editing the JSON file by hand. JSON does not support real comments, so explanatory notes live here and in `PROJECT_GUIDE.md`.

Before editing this file for a real post, follow the mature skill chain in
`SKILL.md`: use `aihot` for AI-topic discovery unless the user already supplied
a concrete topic/source, use `dbs-xhs-title` for title candidates, use
`write-xiaohongshu` plus `humanizer-zh` for the body, and use
`baoyu-image-cards` plus `imagegen` for the final images.

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

For GitHub stars, open-source projects, or repo-based topics, fill
`project_facts` before generating prompts. The cover prompt will then ask the
image model to show the project card, star count, and open-source/license badge
on the first image instead of hiding those facts in later cards.

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
