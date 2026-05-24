# content_spec.json

The workspace file `asset-generation/content_spec.json` is the single source of truth for one Xiaohongshu post.

Required fields:

- `review_id`: stable delivery run id.
- `content_id`: stable post content id.
- `title`: final Xiaohongshu title, 20 Chinese characters or fewer.
- `summary`: short internal summary.
- `topic`: topic to explain.
- `hot_source`: source label for the topic.
- `source_urls`: list of source URLs.
- `source_verification`: source notes and factual caveats.
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

The workflow expects these images to exist:

`image-generation/outputs/images/<image_slug>/<page_id>.png`

Do not add music fields, auto-publish fields, Xiaohongshu login fields, or analytics fields.

Feishu delivery does not require a persistent connection. After restarting the machine, run:

`python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu`
