---
version: 1

watermark:
  enabled: false
  content: ""
  position: bottom-right
  opacity: 0.7

preferred_style:
  name: xhs-ai-hook-sketch
  description: "小红书 AI 圈图文卡专用：首图先给强钩子，内页讲清楚判断、证据和行动建议。整体要像高级手绘知识卡，不像低配模板图。"

preferred_layout: balanced
language: zh
preferred_image_backend: codex-imagegen
generation_batch_size: 4

custom_styles:
  - name: xhs-ai-hook-sketch
    description: "面向 AI 热点、GitHub 趋势、工具测评和工作流方法的高点击图卡风格。首页封面必须是爆点钩子：大标题短句、反差判断、风险提醒、强痛点或强收益，用户 1 秒内能看懂为什么要点进来。"
    color_palette:
      background: "#F7F0E6"
      primary: ["#A8D8EA", "#B5E5CF", "#F8D5C4", "#D5C6E0"]
      accents: ["#E8655A", "#24303A", "#F6D365"]
    visual_elements: "Warm cream paper background, soft watercolor macaron blocks, bold hand-drawn black outlines, creator desk scenes, AI assistant mascot, magnifier, warning sign, checklist, arrows, comment bubbles, small spark marks. The cover should feel like a swipe-stopping poster: one central metaphor, one emotional hook, one clear conflict."
    typography: "Large bold handwritten Chinese title, 8-14 Chinese characters preferred on the cover, high contrast, no dense paragraphs, short subtitle only. Use coral emphasis marks, underline, circle marks, and large handwritten keywords."
    best_for: "AI news commentary, AI tools, GitHub trends, developer productivity, workflow methods, warning/checklist posts, Xiaohongshu image-text cards."
---
