#!/usr/bin/env python3
"""Render deterministic PNG image cards for the current content spec."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "asset-generation" / "content_spec.json"
OUT_ROOT = ROOT / "image-generation" / "outputs" / "images"

W = 1080
H = 1440
M = 76

FONT_REG = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")
FONT_LIGHT = Path("C:/Windows/Fonts/msyhl.ttc")

BG = "#F6F0E6"
INK = "#24303A"
MUTED = "#63707A"
CORAL = "#E8655A"
BLUE = "#A8D8EA"
MINT = "#B5E5CF"
PEACH = "#F8D5C4"
LAV = "#D5C6E0"
YELLOW = "#F6D365"
WHITE = "#FFFDF8"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.truetype(str(FONT_REG), size)


F_TITLE = font(FONT_BOLD, 84)
F_TITLE_SMALL = font(FONT_BOLD, 70)
F_SUB = font(FONT_REG, 39)
F_PILL = font(FONT_BOLD, 26)
F_LABEL = font(FONT_BOLD, 36)
F_BODY = font(FONT_REG, 31)
F_BODY_BOLD = font(FONT_BOLD, 32)
F_SMALL = font(FONT_REG, 24)
F_FOOT = font(FONT_LIGHT, 21)


def load_spec() -> dict:
    data = json.loads(SPEC_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("content_spec.json must contain an object")
    return data


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    fnt: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        line = ""
        for ch in paragraph:
            trial = line + ch
            if text_size(draw, trial, fnt)[0] <= max_width or not line:
                line = trial
            else:
                lines.append(line)
                line = ch
        if line:
            lines.append(line)
    return lines


def draw_multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_gap: int = 14,
    align: str = "left",
) -> int:
    x, y = xy
    for line in wrap_text(draw, text, fnt, max_width):
        if line:
            tw, th = text_size(draw, line, fnt)
            tx = x
            if align == "center":
                tx = x + (max_width - tw) // 2
            draw.text((tx, y), line, font=fnt, fill=fill)
            y += th + line_gap
        else:
            y += line_gap
    return y


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str | None = None,
    width: int = 2,
    radius: int = 28,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def card_shadow(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    rounded(draw, (x1 + 12, y1 + 14, x2 + 12, y2 + 14), "#E7D9C9", radius=32)
    rounded(draw, box, WHITE, outline="#30363B", width=3, radius=32)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str = INK) -> None:
    draw.line([start, end], fill=fill, width=6)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 18
    points = [
        end,
        (
            int(end[0] - size * math.cos(angle - math.pi / 6)),
            int(end[1] - size * math.sin(angle - math.pi / 6)),
        ),
        (
            int(end[0] - size * math.cos(angle + math.pi / 6)),
            int(end[1] - size * math.sin(angle + math.pi / 6)),
        ),
    ]
    draw.polygon(points, fill=fill)


def draw_check(draw: ImageDraw.ImageDraw, x: int, y: int, color: str = CORAL) -> None:
    draw.line([(x, y + 16), (x + 14, y + 30), (x + 42, y)], fill=color, width=7)


def decorate_background(draw: ImageDraw.ImageDraw) -> None:
    rounded(draw, (-120, 95, 250, 360), BLUE, radius=88)
    rounded(draw, (820, 70, 1190, 275), PEACH, radius=78)
    rounded(draw, (770, 1150, 1190, 1500), MINT, radius=96)
    rounded(draw, (-140, 1180, 290, 1505), LAV, radius=100)
    for x, y, r, color in [
        (132, 526, 9, CORAL),
        (948, 472, 10, CORAL),
        (204, 1044, 7, "#77A9B8"),
        (888, 944, 8, "#8A73A8"),
    ]:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def header(draw: ImageDraw.ImageDraw, spec: dict, page: dict, index: int) -> None:
    rounded(draw, (M, 64, M + 238, 118), fill=WHITE, outline="#333333", width=2, radius=24)
    draw.text((M + 28, 78), "AI 工作流", font=F_PILL, fill=INK)
    draw.text((W - M - 75, 80), f"{index:02d}/06", font=F_FOOT, fill=MUTED)

    title = str(page["title"])
    title_font = F_TITLE if len(title) <= 9 else F_TITLE_SMALL
    draw_multiline(draw, (M, 172), title, title_font, INK, W - 2 * M, line_gap=10)
    draw_multiline(draw, (M, 340), str(page["subtitle"]), F_SUB, MUTED, W - 2 * M, line_gap=10)


def footer(draw: ImageDraw.ImageDraw, spec: dict) -> None:
    draw.line([(M, H - 98), (W - M, H - 98)], fill="#DED2C3", width=2)
    draw.text((M, H - 70), str(spec["title"]), font=F_FOOT, fill=MUTED)
    tag = " / ".join(str(tag) for tag in spec.get("tags", [])[:3])
    tw, _ = text_size(draw, tag, F_FOOT)
    draw.text((W - M - tw, H - 70), tag, font=F_FOOT, fill=MUTED)


def visual_cover(draw: ImageDraw.ImageDraw) -> None:
    card_shadow(draw, (132, 500, 948, 1020))
    rounded(draw, (190, 572, 500, 655), MINT, outline=INK, width=3, radius=25)
    draw.text((225, 591), "任务", font=F_LABEL, fill=INK)
    arrow(draw, (512, 614), (618, 614), CORAL)
    rounded(draw, (635, 532, 890, 695), BLUE, outline=INK, width=3, radius=34)
    draw.text((686, 562), "AI", font=font(FONT_BOLD, 70), fill=INK)
    draw.text((704, 635), "开始前", font=F_SMALL, fill=MUTED)
    rounded(draw, (222, 760, 860, 930), "#FFF6D8", outline=INK, width=3, radius=28)
    draw.text((270, 792), "先写验收标准", font=F_LABEL, fill=INK)
    draw_check(draw, 695, 790)
    draw_check(draw, 745, 790)


def visual_problem(draw: ImageDraw.ImageDraw) -> None:
    card_shadow(draw, (120, 488, 960, 1028))
    rounded(draw, (172, 560, 610, 918), "#F9FAFB", outline=INK, width=3, radius=24)
    for y in [615, 685, 755, 825]:
        draw.line([(215, y), (545, y)], fill="#C8D0D8", width=8)
    draw.text((230, 902), "看起来完整", font=F_SMALL, fill=MUTED)
    draw.ellipse((650, 586, 855, 791), outline=CORAL, width=12)
    draw.line([(808, 744), (918, 850)], fill=CORAL, width=16)
    for label, pos, color in [
        ("方向偏", (648, 858), PEACH),
        ("边界漏", (510, 490), LAV),
        ("细节错", (738, 452), MINT),
    ]:
        rounded(draw, (pos[0], pos[1], pos[0] + 150, pos[1] + 58), color, outline=INK, width=2, radius=25)
        draw.text((pos[0] + 22, pos[1] + 11), label, font=F_SMALL, fill=INK)


def visual_template(draw: ImageDraw.ImageDraw) -> None:
    labels = [
        ("1", "交付物", "最终要拿到什么"),
        ("2", "覆盖点", "必须包含哪 3 点"),
        ("3", "禁区", "不能出现什么"),
        ("4", "可用标准", "怎样才算完成"),
    ]
    colors = [BLUE, MINT, PEACH, LAV]
    y = 484
    for i, (num, label, body) in enumerate(labels):
        rounded(draw, (130, y, 950, y + 130), colors[i], outline=INK, width=3, radius=34)
        draw.ellipse((178, y + 35, 238, y + 95), fill=WHITE, outline=INK, width=3)
        tw, th = text_size(draw, num, F_BODY_BOLD)
        draw.text((208 - tw // 2, y + 62 - th // 2), num, font=F_BODY_BOLD, fill=INK)
        draw.text((275, y + 29), label, font=F_LABEL, fill=INK)
        draw.text((275, y + 82), body, font=F_BODY, fill="#34414A")
        y += 150


def visual_example(draw: ImageDraw.ImageDraw) -> None:
    card_shadow(draw, (92, 500, 498, 1038))
    card_shadow(draw, (582, 500, 988, 1038))
    draw.text((170, 548), "模糊写法", font=F_LABEL, fill=INK)
    draw.text((668, 548), "可检查写法", font=F_LABEL, fill=INK)
    rounded(draw, (165, 650, 425, 778), "#F0ECE4", outline="#B8AA9B", width=3, radius=28)
    draw_multiline(draw, (202, 680), "写得\n自然一点", F_BODY_BOLD, MUTED, 190, line_gap=8, align="center")
    for y, text in [
        (632, "标题 <= 20 字"),
        (714, "正文 <= 800 字"),
        (796, "开头有痛点"),
        (878, "结尾留问题"),
    ]:
        draw_check(draw, 635, y + 4, CORAL)
        draw.text((700, y), text, font=F_BODY, fill=INK)


def visual_iterate(draw: ImageDraw.ImageDraw) -> None:
    nodes = [
        ("输出", 442, 492, BLUE),
        ("检查", 690, 692, MINT),
        ("指出第几条", 442, 900, PEACH),
        ("再迭代", 190, 692, LAV),
    ]
    centers: list[tuple[int, int]] = []
    for label, x, y, color in nodes:
        rounded(draw, (x, y, x + 210, y + 108), color, outline=INK, width=3, radius=36)
        draw.text((x + 56, y + 32), label, font=F_BODY_BOLD, fill=INK)
        centers.append((x + 105, y + 54))
    for a, b in zip(centers, centers[1:] + centers[:1]):
        arrow(draw, a, b, CORAL)
    rounded(draw, (255, 805, 825, 875), WHITE, outline=INK, width=2, radius=28)
    draw.text((310, 822), "不是“重写”，是“第 2 条没过”", font=F_BODY, fill=INK)


def visual_warning(draw: ImageDraw.ImageDraw) -> None:
    card_shadow(draw, (135, 505, 945, 1018))
    draw.polygon([(540, 590), (270, 930), (810, 930)], fill="#FFF0CF", outline=INK)
    draw.line([(540, 690), (540, 800)], fill=CORAL, width=18)
    draw.ellipse((528, 835, 552, 859), fill=CORAL)
    for text, y in [
        ("别直接上线", 976),
        ("先看边界和风险", 1034),
    ]:
        tw, _ = text_size(draw, text, F_BODY_BOLD if y == 976 else F_BODY)
        draw.text((W // 2 - tw // 2, y), text, font=F_BODY_BOLD if y == 976 else F_BODY, fill=INK)


def visual_comment(draw: ImageDraw.ImageDraw) -> None:
    rounded(draw, (135, 505, 945, 1018), WHITE, outline=INK, width=3, radius=42)
    draw.text((232, 575), "你最常返工的原因？", font=F_LABEL, fill=INK)
    bubbles = [
        ("方向", 210, 692, BLUE),
        ("边界", 590, 692, MINT),
        ("细节", 210, 842, PEACH),
        ("验收", 590, 842, LAV),
    ]
    for label, x, y, color in bubbles:
        rounded(draw, (x, y, x + 280, y + 96), color, outline=INK, width=3, radius=38)
        tw, th = text_size(draw, label, F_LABEL)
        draw.text((x + 140 - tw // 2, y + 48 - th // 2), label, font=F_LABEL, fill=INK)
    draw.text((450, 957), "留言区见", font=F_BODY, fill=MUTED)


def render_page(spec: dict, page: dict, index: int, out_path: Path) -> None:
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    decorate_background(draw)
    header(draw, spec, page, index)

    page_id = str(page["page_id"])
    if page_id == "01-cover":
        visual_cover(draw)
    elif page_id == "02-problem":
        visual_problem(draw)
    elif page_id in {"03-template", "04-checklist"}:
        visual_template(draw)
    elif page_id == "04-example":
        visual_example(draw)
    elif page_id in {"03-qa-loop", "05-iterate"}:
        visual_iterate(draw)
    elif page_id == "05-warning":
        visual_warning(draw)
    elif page_id == "06-comment":
        visual_comment(draw)
    else:
        fallback_visuals = [visual_cover, visual_problem, visual_template, visual_example, visual_warning, visual_comment]
        fallback_visuals[min(index - 1, len(fallback_visuals) - 1)](draw)

    footer(draw, spec)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG", optimize=True)


def iter_pages(spec: dict) -> Iterable[tuple[int, dict]]:
    pages = spec.get("pages", [])
    if not isinstance(pages, list) or len(pages) != 6:
        raise ValueError("content_spec must contain exactly 6 pages")
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"page #{index} must be an object")
        yield index, page


def main() -> int:
    spec = load_spec()
    slug = str(spec["image_slug"])
    out_dir = OUT_ROOT / slug
    for index, page in iter_pages(spec):
        out_path = out_dir / f"{page['page_id']}.png"
        render_page(spec, page, index, out_path)
        print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
