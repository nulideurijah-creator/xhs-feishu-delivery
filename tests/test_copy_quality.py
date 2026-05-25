import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "assets" / "workspace-template"
ASSET_DIR = ROOT / "asset-generation"
sys.path.insert(0, str(ASSET_DIR))
sys.path.insert(0, str(ROOT / "content-history"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CURRENT_TEMPLATE_BODY = """最近看多智能体框架，我会先看一件事：它是不是还停在“你自己把流程图画好”，还是能从一个目标开始，把任务拆出来、并行跑、最后合成结果。

open-multi-agent 这点挺明确。它是 TypeScript 项目，核心包叫 @open-multi-agent/core。README 里给的心智模型不是“先建节点再连线”，而是给一个 goal，coordinator 会拆成 task DAG，能并行的任务并行，最后再汇总。对做后端自动化的人，这比手写固定流程更接近真实需求：今天是合同审查，明天是竞品监控，后天是代码评审，每次任务形状都不一样。

我会把它收藏给三类人：正在用 Node 做 agent 后端的人；想把 MCP 工具、文件工具、grep、bash 接进团队流程的人；以及需要看清每一步 token、任务状态、trace 的人。它还有 runAgent、runTeam、runTasks 三种入口，想自动编排用 runTeam，想自己定义图就用 runTasks。

要注意，它不是“把复杂工程问题一键变简单”的魔法。生产里还是要管预算、重试、上下文压缩、循环检测和人工 review。但如果你正在找一个 TS 里比较轻的多智能体编排层，这个项目值得单独开个 demo 跑一下。

截至我这次核验，仓库约 6241 stars，MIT，最新 release 是 v1.4.2。star 只是热度参考，真正值得看的，是它把 goal -> DAG -> trace 这条线做得很顺。"""


HUMAN_BODY = """我最近在整理一个多 agent demo，本来以为 open-multi-agent 又是“多放几个 agent”的框架。翻到 README 里的 runTeam 示例才停了一下：它关心的不是 agent 数量，而是目标变了以后，流程图不用每次靠人手重画。

这个点我挺喜欢。你给一个 goal，coordinator 临时拆成 task DAG，能并行的任务先跑，最后再把结果合起来。像代码评审、合同审查、竞品监控这种任务，麻烦就麻烦在每次形状都变，硬画固定流程真的很累。

我会先拿它试 runTeam，再看 runTasks 能不能保留一点手写图的控制感。MCP、bash/file/grep 这些工具能接进来，trace、任务状态和 token 信息也能看，调试时至少不是闭眼猜，做 agent 最烦的就是跑飞了还不知道哪一步开始歪。

预算、重试、上下文压缩、循环检测、人审还是要自己管，别指望它替你把工程债一起擦掉。仓库这次核验约 6241 stars，MIT，v1.4.2。star 只当热度信号，真正让我想保存的是 goal 到 DAG 这条线，放在 TS 后端里不算重。"""


TOOL_MANUAL_BODY = """open-multi-agent 是一个 TypeScript 多智能体编排框架，核心包是 @open-multi-agent/core。

用户可以传入一个 goal，coordinator 会拆成 task DAG，并自动执行可并行任务。它支持 runAgent、runTeam、runTasks，也支持 MCP、bash、file、grep、trace 和 token 信息。

该项目适用于 Node 后端自动化、多智能体工作流、代码评审、合同审查和竞品监控等场景。仓库约 6241 stars，MIT，版本 v1.4.2。"""


NEW_FORBIDDEN_BODY = """它干的事很简单，就是把目标拆成任务。

它的好处是可以提升效率，也很有潜力。如果你是做 AI 开发的人，可以重点看一下。

首先，它支持 runTeam。其次，它支持 MCP。最后，总结一下，这个项目值得关注。"""


NO_FRICTION_BODY = """我最近在做一个多 agent demo，翻到 open-multi-agent 的 runTeam 示例时停了一下：它不是只强调 agent 数量，而是把目标拆成 task DAG。

我觉得这个思路适合 TS 后端，因为任务形状经常变化，自动拆分和并行执行会让编排更自然。MCP、bash/file/grep、trace 和 token 信息也能接进同一条链路。

我会先用它跑一个小 demo，看 runTeam 和 runTasks 在控制感上的差异。仓库约 6241 stars，MIT，v1.4.2。star 只是热度信号，让我想保存的是 goal 到 DAG 这条线。"""


def make_spec(body: str) -> dict:
    return {
        "title": "Agent流程别手画",
        "body_full": body,
        "tags": ["AI开源项目", "多智能体", "TypeScript", "AI开发", "GitHub项目", "MCP"],
        "writing_brief": {
            "facts": [
                {
                    "claim": "open-multi-agent turns a goal into a task DAG.",
                    "source_url": "https://github.com/open-multi-agent/open-multi-agent/blob/main/README.md",
                },
                {
                    "claim": "The repository had 6241 stars and MIT license.",
                    "source_url": "https://api.github.com/repos/open-multi-agent/open-multi-agent",
                },
            ],
            "why_now": "Agent workflows are becoming more dynamic.",
            "creator_angle": "真人发现口吻，不写工具说明书。",
            "audience": "TypeScript AI builders.",
        },
    }


def make_spec_with_title(title: str, body: str = HUMAN_BODY) -> dict:
    spec = make_spec(body)
    spec["title"] = title
    return spec


class CopyQualityTests(unittest.TestCase):
    def test_template_style_body_is_blocked(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec(CURRENT_TEMPLATE_BODY))

        self.assertEqual(result["status"], "fail")
        self.assertLess(result["score"], 80)
        blockers = "\n".join(result["blockers"])
        self.assertIn("我会先看一件事", blockers)
        self.assertIn("我会把它收藏给三类人", blockers)
        self.assertIn("截至我这次核验", blockers)

    def test_human_discovery_body_passes(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec(HUMAN_BODY))

        self.assertEqual(result["status"], "pass")
        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["blockers"], [])

    def test_tool_manual_without_scene_or_judgment_is_blocked(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec(TOOL_MANUAL_BODY))

        self.assertEqual(result["status"], "fail")
        blockers = "\n".join(result["blockers"])
        self.assertIn("missing_creator_scene", blockers)
        self.assertIn("missing_personal_judgment", blockers)

    def test_new_forbidden_phrases_are_blocked(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec(NEW_FORBIDDEN_BODY))

        self.assertEqual(result["status"], "fail")
        blockers = "\n".join(result["blockers"])
        self.assertIn("它干的事很简单", blockers)
        self.assertIn("它的好处是", blockers)
        self.assertIn("如果你是", blockers)

    def test_body_without_natural_friction_is_blocked(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec(NO_FRICTION_BODY))

        self.assertEqual(result["status"], "fail")
        self.assertIn("missing_natural_friction", "\n".join(result["blockers"]))

    def test_bland_or_formula_title_is_blocked(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec_with_title("open-multi-agent介绍"))

        self.assertEqual(result["status"], "fail")
        self.assertIn("title_lacks_xhs_hook", "\n".join(result["blockers"]))

    def test_clickable_xhs_title_passes(self):
        copy_quality = load_module(ASSET_DIR / "copy_quality.py", "copy_quality")

        result = copy_quality.validate_copy_quality(make_spec_with_title("这个Agent框架有点顺"))

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["blockers"], [])

    def test_asset_generator_rejects_blocked_copy(self):
        generator = load_module(ASSET_DIR / "generate_current_assets.py", "generate_current_assets")
        spec = {
            "review_id": "test-review",
            "content_id": "test-content",
            "title": "Agent流程别手画",
            "topic": "open-multi-agent",
            "writing_brief": make_spec(CURRENT_TEMPLATE_BODY)["writing_brief"],
            "body_full": CURRENT_TEMPLATE_BODY,
            "tags": ["AI开源项目", "多智能体", "TypeScript", "AI开发", "GitHub项目", "MCP"],
            "image_slug": "test-slug",
            "pages": [
                {"page_id": f"{index:02d}-page", "title": f"第{index}页", "subtitle": "测试", "visual": "测试"}
                for index in range(1, 7)
            ],
        }

        with self.assertRaisesRegex(ValueError, "copy quality blocked"):
            generator.validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
