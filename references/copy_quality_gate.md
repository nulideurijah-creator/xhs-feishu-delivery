# Copy Quality Gate

This workflow uses a deterministic local hard gate to stop report-like, manual-like, or checklist-like Xiaohongshu copy before image generation or Feishu delivery.

## Goal

The copy must read like a real AI/dev creator sharing a useful discovery, not like a generic project report, AI tool manual, or training slide deck.

The gate is intentionally conservative. If it blocks a draft, rewrite the title/body before generating cards.

## Hard Blockers

Block the package when `title`, `body_full`, or `tags` violates core format rules:

- title is empty or longer than 20 Chinese characters
- body is empty or longer than 1000 characters
- tags are not 5-8 non-empty items

Block the package when the body contains these template phrases:

- `它干的事很简单`
- `它做的事很简单`
- `它的好处是`
- `我会先看一件事`
- `我会把它收藏给三类人`
- `我觉得它最适合三类人`
- `要注意`
- `截至我这次核验`
- `真正值得看的`
- `值得单独开个 demo`
- `值得单独开一个 demo`
- `适合三类人`
- `首先，` / `其次，` / `最后，`
- `综上`
- `总结一下`
- `值得关注`
- `很有潜力`
- `可以提升效率`
- `上手简单`
- `如果你是`

Block bland titles that look like documentation headings:

- titles ending in `介绍`
- titles ending in `是什么`
- titles ending in `使用指南`
- titles ending in `教程`
- titles like `AI工具推荐` or `<项目/工具/框架>推荐`

Require the title to carry a Xiaohongshu hook signal such as pain point, discovery, creator judgment, curiosity, or mild emotion. Examples: `这个Agent框架有点顺`, `别再手画Agent流程`, `它把Agent流程理顺了`.

Block listicle/report patterns such as:

- `三类人：...`
- `三种入口`
- `一类人...二类人...三类人...`

Block tool-manual style copy when it lacks a first-person discovery scene, personal judgment, or natural friction. A valid scene usually contains phrasing such as `我最近`, `最近在`, `我本来`, `翻到`, `看到`, `接 API`, `比模型`, `选 agent`, `做 demo`, `做项目`, or `调试`.

Natural friction means a small, non-mean-spirited complaint or workflow pain such as `烦`, `麻烦`, `黑盒`, `闭眼猜`, `跑飞`, `工程债`, `靠人手`, or `不用每次`.

## Warnings

Warnings reduce the quality score but do not block by themselves:

- multiple paragraphs begin with `它`
- multiple paragraphs begin with `我会`
- multiple paragraphs begin with `这个项目`
- paragraph openings are too regular

## Pass Standard

A draft passes only when:

- no hard blockers are present
- score is at least 80
- title/body/tags satisfy format constraints
- the title has a Xiaohongshu hook without fake exaggeration
- the body has a concrete first-person discovery scene, personal judgment, a natural complaint or friction point, and a grounded save-worthy judgment
- useful facts are embedded in story and judgment instead of listed as a standard checklist

## Commands

Run the copy gate only:

```powershell
python .\run_xhs_delivery.py --check-copy
```

The command writes:

```text
asset-generation/outputs/copy-quality-report.json
```

It exits `0` with `copy_ready` and exits `2` with `copy_blocked`.

## Placement In Workflow

The gate must run before:

- image prompt package generation
- local-only validation
- Feishu delivery card build
- Feishu send

Do not bypass the gate by editing downstream JSON outputs.
