# Project Guide

This guide explains every tracked file in the repository so a new user can understand what to edit, what to run, and what should remain untouched.

## Top-Level Files

| File | Purpose |
|---|---|
| `README.md` | Main project introduction, installation guide, workflow diagram, and common commands. Start here. |
| `SKILL.md` | Codex skill instructions. Codex reads this when the skill is invoked. |
| `LICENSE` | Standard MIT license text. Kept unmodified so the legal text remains recognizable. |
| `.gitignore` | Prevents secrets, generated outputs, images, logs, caches, and local environment files from being committed. |
| `PROJECT_GUIDE.md` | This file. It documents what each repository file is for. |

## Skill Metadata

| File | Purpose |
|---|---|
| `agents/openai.yaml` | Display metadata used by Codex UI: name, short description, and default prompt. |
| `references/content_spec.md` | Field-by-field reference for `content_spec.json`, the single source of truth for a post. |
| `references/image_generation.md` | Contract for generating the 6 final PNG cards with `baoyu-image-cards`, Codex `imagegen`, or the user's equivalent image model. |

## Skill Scripts

| File | Purpose |
|---|---|
| `scripts/run_xhs_delivery.py` | Main wrapper used by the skill. It initializes workspaces, checks Feishu, installs startup checks, and runs the full package workflow. |
| `scripts/init_workspace.py` | Copies `assets/workspace-template` into a user-selected local workspace. |
| `scripts/validate_skill_safety.py` | Scans the skill folder to make sure secrets and Xiaohongshu auto-publish artifacts are not present. |
| `scripts/smoke_test_skill.py` | Creates a temporary workspace and verifies the installed skill can initialize, generate asset metadata, and preserve the mature skill chain. |

## Example Assets

| File | Purpose |
|---|---|
| `assets/content_spec.example.json` | Small standalone example of the post schema. Useful for understanding required fields. |

## Workspace Template

These files are copied into a user workspace by `--init-workspace`. The copied workspace is what actually generates posts and sends Feishu cards.

| File | Purpose |
|---|---|
| `assets/workspace-template/.gitignore` | Keeps local Feishu credentials, generated outputs, caches, and lock files out of git. |
| `assets/workspace-template/.baoyu-skills/baoyu-image-cards/EXTEND.md` | Bundled `baoyu-image-cards` preference file. It disables watermarks, pins Codex image generation, and defines the `xhs-warm-cute-open-source` style for warm cute cards with visible GitHub/open-source facts on repo-based covers. |
| `assets/workspace-template/requirements.txt` | Python dependency list for the generated workspace. It is intentionally empty by default because final cards are model-generated, not drawn locally. |
| `assets/workspace-template/run_xhs_delivery.py` | Workspace-local packaging and Feishu runner. It mirrors the skill wrapper but does not require `--workspace`. |
| `assets/workspace-template/asset-generation/content_spec.json` | Editable post specification. Users change this file to create a new post. |
| `assets/workspace-template/asset-generation/generate_current_assets.py` | Validates the spec, writes copy/title/prompt outputs, and prepares image paths for model-generated cards. |
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
| `.github/workflows/validate.yml` | GitHub Actions workflow that compiles scripts, validates JSON examples, runs the safety scan, runs unit tests, and runs the smoke test on every push and pull request. |

## Tests

| File | Purpose |
|---|---|
| `tests/test_skill_stability.py` | Regression tests for mature skill chain rules, workspace initialization, doctor diagnostics, prompt metadata, and safety scanning. |

## What Users Usually Edit

- `asset-generation/content_spec.json` in their generated workspace.
- `feishu-delivery/.env` in their generated workspace.

## What Users Usually Do Not Edit

- Skill scripts in `scripts/`.
- Template workflow scripts under `assets/workspace-template`.
- Generated `outputs/` folders.
- `.xhs_delivery.lock`.
