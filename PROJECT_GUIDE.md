# Project Guide

This guide explains every tracked file in the repository so a new user can understand what to edit, what to run, and what should remain untouched.

## Top-Level Files

| File | Purpose |
|---|---|
| `README.md` | Main project introduction, installation guide, workflow diagram, and common commands. Start here. |
| `SKILL.md` | Codex skill instructions. Codex reads this when the skill is invoked. |
| `LICENSE` | Standard MIT license text. |
| `.gitignore` | Prevents secrets, generated outputs, images, logs, caches, and local environment files from being committed. |
| `PROJECT_GUIDE.md` | This file. It documents what each repository file is for. |

## Skill Metadata

| File | Purpose |
|---|---|
| `agents/openai.yaml` | Display metadata used by Codex UI: name, short description, and default prompt. |
| `references/content_spec.md` | Field-by-field reference for the current post spec, including `writing_brief`, final title/body/tags, image pages, and source verification. |
| `references/creator_prompt.md` | Owner-approved model-writing prompt for direct Xiaohongshu title/body/tag generation. |
| `references/copy_quality_gate.md` | Hard delivery gate that defines the required human-creator tone, blocked phrases, hook-title rule, and `--check-copy` command. |
| `references/image_generation.md` | Contract for generating the 6 final PNG cards with `baoyu-image-cards`, Codex `imagegen`, or the user's equivalent image model. |

## Skill Scripts

| File | Purpose |
|---|---|
| `scripts/run_xhs_delivery.py` | Main wrapper used by the skill. It initializes workspaces, checks Feishu, installs startup checks, and runs the full package workflow. |
| `scripts/init_workspace.py` | Copies `assets/workspace-template` into a user-selected local workspace. |
| `scripts/validate_skill_safety.py` | Scans the skill folder to make sure secrets, legacy content chains, and Xiaohongshu auto-publish artifacts are not present. |
| `scripts/smoke_test_skill.py` | Creates a temporary workspace and verifies the installed skill can initialize, generate asset metadata, and preserve the clean model-writing chain. |

## Workspace Template

These files are copied into a user workspace by `--init-workspace`. The copied workspace is what actually generates posts and sends Feishu cards.

| File | Purpose |
|---|---|
| `assets/workspace-template/.gitignore` | Keeps local Feishu credentials, generated outputs, caches, and lock files out of git. |
| `assets/workspace-template/.baoyu-skills/baoyu-image-cards/EXTEND.md` | Bundled `baoyu-image-cards` preference file. It disables watermarks, pins Codex image generation, and defines the `xhs-warm-cute-open-source` style. |
| `assets/workspace-template/requirements.txt` | Python dependency list for the generated workspace. It is intentionally empty by default because final cards are model-generated, not drawn locally. |
| `assets/workspace-template/run_xhs_delivery.py` | Workspace-local packaging and Feishu runner. It mirrors the skill wrapper but does not require `--workspace`. |
| `assets/workspace-template/automation-lock/automation_lock.py` | Whole-workflow lock for unattended Codex automations. |
| `assets/workspace-template/asset-generation/copy_quality.py` | Deterministic validator for title/body/tags that blocks report-like, manual-like, and checklist-like Xiaohongshu copy. |
| `assets/workspace-template/asset-generation/generate_current_assets.py` | Validates the spec, writes copy and prompt outputs, and prepares image paths for model-generated cards. |
| `assets/workspace-template/content-history/check_history.py` | Lists sent post history and checks the current spec against previous Feishu deliveries. |
| `assets/workspace-template/content-history/history_utils.py` | Shared duplicate-key normalization, history read/write, and sent-record helpers. |
| `assets/workspace-template/diagnostics/doctor.py` | Read-only workspace doctor. It writes diagnostics reports without sending Feishu messages or generating images. |
| `assets/workspace-template/image-generation/.gitkeep` | Keeps the model-image directory in the template. Prompt files and PNG outputs are generated here at runtime. |
| `assets/workspace-template/publish-mainline/build_manual_publish_package.py` | Builds the local manual publishing package from generated assets. |
| `assets/workspace-template/publish-mainline/preflight.py` | Checks whether the manual package is ready and records any blocking issues. |
| `assets/workspace-template/feishu-delivery/.env.example` | Template for Feishu credentials. Copy it to `.env` and fill in local values. |
| `assets/workspace-template/feishu-delivery/check_feishu_ready.py` | Checks Feishu credentials and token access without sending messages. |
| `assets/workspace-template/feishu-delivery/install_startup_check.py` | Installs Windows startup health checks for Feishu readiness. |
| `assets/workspace-template/feishu-delivery/build_delivery_card.py` | Builds the buttonless Feishu interactive card JSON. |
| `assets/workspace-template/feishu-delivery/send_delivery_card.py` | Validates locally, performs dry-runs, uploads images, and sends the final Feishu card. |

## GitHub Automation

| File | Purpose |
|---|---|
| `.github/workflows/validate.yml` | GitHub Actions workflow that compiles scripts, runs the safety scan, runs unit tests, and runs the smoke test on every push and pull request. |

## Tests

| File | Purpose |
|---|---|
| `tests/test_skill_stability.py` | Regression tests for clean model-writing rules, workspace initialization, doctor diagnostics, prompt metadata, history dedupe, Feishu card building, and safety scanning. |
| `tests/test_copy_quality.py` | Regression tests for the local copy gate and its integration with asset generation. |

## What Users Usually Edit

- `asset-generation/content_spec.json` in their generated workspace. Codex creates this file for each real post from the current topic and verified facts.
- `feishu-delivery/.env` in their generated workspace.
- `content-history/sent-posts.jsonl` is generated automatically after successful sends; users normally inspect it but do not hand-edit it.

## What Users Usually Do Not Edit

- Skill scripts in `scripts/`.
- Template workflow scripts under `assets/workspace-template`.
- Generated `outputs/` folders.
- `.xhs_delivery.lock`.
