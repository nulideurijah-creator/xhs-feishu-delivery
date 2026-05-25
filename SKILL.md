---
name: xhs-feishu-delivery
description: Use when the user wants to create a Xiaohongshu image-text post package, validate the manual publishing workflow, or send a complete Feishu delivery card for manual Xiaohongshu posting. This skill never automates Xiaohongshu publishing.
metadata:
  short-description: Xiaohongshu post package to Feishu delivery
---

# XHS Feishu Delivery

Use this skill to create one AI/tools/dev Xiaohongshu image-text content package and deliver the complete manual posting package to Feishu.

## Safety Rules

- Do not call Xiaohongshu MCP, browser publishing scripts, or any publish API.
- Do not create, read, or upload Xiaohongshu cookies.
- Do not open Xiaohongshu editor pages or click publish buttons.
- Do not add Feishu buttons, callbacks, WebSocket receivers, or approval state machines.
- Do not include music fields.
- Do not treat this workflow as data analytics, Obsidian memory, competitor analysis, or self-improvement tracking.
- Do not ask the user to choose image watermark, visual style, layout, palette, image backend, or preference save scope. This workflow already pins those choices in `.baoyu-skills/baoyu-image-cards/EXTEND.md`.

## Mature Research + Model Writing Chain

This skill is the orchestrator and delivery layer. It keeps research and image generation on the agreed mature skills, but title and body are written directly by the current model from a clean factual brief.

Use this chain for a new post:

1. **Topic / source selection**:
   - Before selecting an automatic topic, inspect sent history:
     `python scripts/run_xhs_delivery.py --workspace "<workspace>" --history`
   - Avoid any topic that shares the same GitHub repo, source URL, `topic_key`, `content_id`, or `review_id` with sent history.
   - If the user gives a specific topic and source, use it.
   - If the user asks for an AI-circle topic, hot news, GitHub trend, major AI update, or gives no concrete topic, use `aihot` first to pull current AI news and choose one Xiaohongshu-suitable vertical topic.
   - If the chosen angle depends on GitHub stars, repo activity, or developer-platform facts, use `agent-reach` as an additional verification/research skill after `aihot`.
   - Do not invent a hot topic from general model knowledge when `aihot` is available.
2. **Fact verification**:
   - Use `agent-reach` for official sources, GitHub facts, repo activity, X posts, papers, or source URLs that materially affect the claim.
   - Do not rely on an `aihot` summary alone for concrete factual claims.
3. **Writing brief**:
   - Create `writing_brief` as factual input only. It must include source-backed facts, why the topic matters now, the creator angle, target audience, and optional phrases or claims to avoid.
   - Do not put a numbered outline, fixed framework, formula title, or section plan into `writing_brief`.
4. **Title, body, and tags**:
   - Read `references/creator_prompt.md`.
   - Use the current model to generate the final `title`, `body_full`, and `tags` directly from the verified facts and `writing_brief`.
   - Do not call a separate title formula, copywriting rewrite, humanizer, or report-writing skill for this step.
   - Privately rewrite once if the draft sounds like a report, listicle, product manual, SEO article, or AI summary.
5. **Image-card structure and prompts**: use `baoyu-image-cards` with the bundled `xhs-warm-cute-open-source` preference.
   - Build the 6 image pages from the final title/body/facts after the body is written. The image-card outline must not rewrite the title or body.
   - For GitHub stars, open-source projects, or repo-based topics, put the verified repo/project name, star count, license/open-source badge, and source cue on the first card. Do not hide these facts in later pages or invent unverified counts.
   - Use the bundled defaults non-interactively: no watermark, style `xhs-warm-cute-open-source`, layout `balanced`, palette `macaron`, backend `imagegen`, batch size `4`, and confirmation skipped with `--yes` or the runtime's equivalent "use defaults directly" instruction.
   - If `baoyu-image-cards` asks first-use preference questions, answer them from the bundled config instead of asking the user.
6. **Final PNG generation**: use Codex `imagegen` or the user's equivalent real image model as the raster backend.
7. **Packaging and Feishu delivery**: use this `xhs-feishu-delivery` workflow.

If `aihot`, `agent-reach`, `baoyu-image-cards`, or `imagegen` is unavailable in the current runtime, stop and state exactly which skill is missing. Do not silently replace it with shell scripts, browser screenshots, generic web guesses, or template rendering.

## Workflow

Authoritative rule: this skill packages model-generated cards. If any workspace note, old handoff, old script, or previous conversation says to create or run a local image renderer, treat that instruction as obsolete.

1. Confirm or create the target workspace. For a new workspace, initialize it from the bundled template:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --init-workspace`
2. The target workspace must contain the four workflow directories:
   `asset-generation`, `image-generation`, `publish-mainline`, and `feishu-delivery`.
3. For unattended Codex automations, acquire the whole-workflow lock before editing any workspace file:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --acquire-automation-lock`
   If the lock is busy, stop and report the active owner instead of continuing. Release it after successful send or a terminal blocker:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --release-automation-lock`
4. Create `asset-generation/content_spec.json` from the current topic using the chain above. The file must contain the current topic, verified sources, `writing_brief`, final title, final body, tags, image slug, source verification, and exactly 6 image page definitions.
5. Check the current spec against sent history before image work:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-history`
   If it reports `duplicate`, choose a new topic/angle/source. Only set `history.allow_repeat: true` when the user explicitly asks to repeat a topic.
6. Run the asset generator first. It writes the copy package and the six prompt files:
   `python "<workspace>\\asset-generation\\generate_current_assets.py"`
7. Generate the six image cards with the mature image-card path used by the owner:
   use `baoyu-image-cards` to structure the series and Codex `imagegen` as the raster backend.
   If those skills/tools are available in the current runtime, explicitly use them; do not replace them with shell, Python, browser, or canvas code.
   Invoke `baoyu-image-cards` with the workspace `.baoyu-skills/baoyu-image-cards/EXTEND.md` defaults and `--yes` / equivalent direct-default confirmation. Do not pause to ask about watermark text, style, layout, palette, backend, or preference save location.
   Save each final PNG exactly to the `image_path` listed in `asset-generation/outputs/current-publish-assets.json`.
   If the user has a different image model available, use that model only if it can save final PNGs to the same paths.
   If a real image model/backend is not available, stop and report that image generation is blocked. Do not create a Python, PIL, SVG, HTML, canvas, screenshot, browser, or placeholder renderer to work around it.
   If generated images are saved outside the workspace by the image tool, copy the selected final PNGs into the required `image_path` locations before packaging.
8. After all six model-generated PNG files exist, run the wrapper. It must refresh the asset package, build the local package, build the Feishu card, and then validate or send:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only`
9. After a machine restart, check Feishu credentials without building or sending:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu`
10. Before using the workflow from a new Codex window, run read-only diagnostics:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --doctor`
11. Install a Windows logon health check when the workflow should recover after reboot:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-startup-check`
   If Task Scheduler or the Startup folder is blocked by local permissions, the workspace installer may fall back to the current user's Windows Run registry entry.
   For "machine booted but no user has logged in", install the administrator-only SYSTEM startup task:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --install-system-startup-check`
12. If Feishu credentials should be checked after building the package:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --dry-run`
13. Only when the user explicitly wants delivery to Feishu:
   `python scripts/run_xhs_delivery.py --workspace "<workspace>" --send`
   A successful send must append or update `content-history/sent-posts.jsonl` with the sent title, topic, source keys, Feishu `message_id`, and send time.

## Content Standards

- Topic must stay in the AI/tools/dev productivity vertical unless the user explicitly changes the niche.
- `writing_brief` must contain at least two source-backed facts with `claim` and `source_url`.
- The title must be 20 Chinese characters or fewer.
- The body must be 1000 characters or fewer.
- The body must give the reader a concrete understanding, use case, judgment, or save-worthy detail. It must not be only a news recap or generic reminder.
- GitHub/open-source posts should explain what the project does well, where it is useful, who should save it, and why it is worth trying.
- AI hot-news posts should turn the event into an understandable implication for AI users, builders, or developers.
- Tags must be a non-empty list.
- Image cards must be exactly 6 PNG files generated by an image model/skill.
- Do not create image cards with PIL, SVG, HTML, canvas, template drawing scripts, or placeholder diagrams.
- Do not create, restore, edit, or run any file named `render_current_cards.py`.
- Do not use screenshots, browser-rendered HTML, Mermaid, matplotlib, or presentation slides as final card substitutes.
- If a legacy local image renderer exists in a workspace, ignore it and remove it before delivery; it is not part of the accepted workflow.
- The Python wrapper is allowed to require the 6 final PNG files to exist because image generation is handled by `baoyu-image-cards`/`imagegen`, not by the packaging scripts.
- The wrapper must use the workspace lock `.xhs_delivery.lock`; do not run direct workflow and skill workflow concurrently in the same workspace.
- Feishu card must contain only: topic, title, full body, image list, 6 image previews, and tags.
- Cover cards for GitHub/open-source topics must expose the concrete project/source facts immediately while keeping the warm cute hand-drawn macaron style.
- Sent-history duplicate checks are mandatory before automatic topic selection and before final asset generation. Duplicate keys include normalized GitHub repo, source URL, `topic_key`, `content_id`, and `review_id`.

## References

- For repository structure and every tracked file, read `PROJECT_GUIDE.md`.
- For the content spec shape, read `references/content_spec.md`.
- For the model writing prompt, read `references/creator_prompt.md`.
- For the model-image handoff contract, read `references/image_generation.md`.

## Validation

Before saying the workflow is ready, run:

```powershell
python scripts/validate_skill_safety.py --skill-dir "<skill-dir>"
python scripts/run_xhs_delivery.py --workspace "<test-workspace>" --init-workspace
python scripts/smoke_test_skill.py --skill-dir "<skill-dir>"
python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-feishu
python scripts/run_xhs_delivery.py --workspace "<workspace>" --doctor
python scripts/run_xhs_delivery.py --workspace "<workspace>" --history
python scripts/run_xhs_delivery.py --workspace "<workspace>" --check-history
python "<workspace>\asset-generation\generate_current_assets.py"
# Generate the 6 PNG files with baoyu-image-cards/imagegen, then:
python scripts/run_xhs_delivery.py --workspace "<workspace>" --local-only
```

For Feishu credential verification, run `--dry-run`. Do not run `--send` unless the user asks to send a real Feishu card.
