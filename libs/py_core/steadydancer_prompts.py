from __future__ import annotations

"""
Predefined SteadyDancer prompt templates.

These templates are not wired into the main generation flow yet, but can be
referenced by API / Worker / Web to provide consistent default styles.

Design原则：
- 以「参考图 + 驱动视频跳舞」为前提，Prompt 主要负责整体风格与画面倾向；
- 保持简洁、稳定，不对主体身份和动作做过多假设；
- 中英双语各提供几档常用风格，后续可以根据产品形态再细化。
"""

# ---- Chinese templates ----

STEADYDANCER_PROMPT_ZH_REALISTIC = (
    "真实摄影风格的人像舞蹈视频，镜头以人物为主体，保持稳定、不晃动。"
    "画面曝光与对比度适中，色彩自然，皮肤质感细腻，整体氛围明亮干净。"
    "优先保证人物动作连贯清晰，背景不过度抢眼，适合社交媒体短视频。"
)

STEADYDANCER_PROMPT_ZH_STAGE = (
    "舞台演出风格的人像舞蹈视频，聚光灯打在人物身上，背景略暗。"
    "镜头跟随人物移动，保持稳定与流畅，重点突出肢体动作和节奏感。"
    "灯光和色彩具有舞台氛围，但不过度炫目，整体画面清晰、有层次。"
)

STEADYDANCER_PROMPT_ZH_STYLIZED = (
    "略带艺术滤镜的人像舞蹈视频，色彩略微偏暖或偏冷，具有统一的调色风格。"
    "保留人物动作与表情的真实感，同时在背景光影、颗粒感上做轻微强化，"
    "使整体画面更有电影感与氛围感，但不影响动作的清晰呈现。"
)


# ---- English templates ----

STEADYDANCER_PROMPT_EN_REALISTIC = (
    "A realistic dance video focusing on the performer as the main subject. "
    "The camera remains stable with smooth motion, avoiding shaky footage. "
    "Natural colors, balanced exposure and contrast, and clean lighting that keeps the dancer clear and sharp, "
    "with the background slightly understated. Suitable for social media short videos."
)

STEADYDANCER_PROMPT_EN_STAGE = (
    "A stage performance style dance video, with spotlights highlighting the performer against a slightly darker background. "
    "The camera smoothly follows the dancer, emphasizing body movement and rhythm. "
    "Lighting and colors create a stage-like atmosphere without being overly flashy, maintaining clarity and depth."
)

STEADYDANCER_PROMPT_EN_STYLIZED = (
    "A lightly stylized dance video with a consistent color grade, slightly warm or cool. "
    "The dancer's movements and expressions remain realistic and clear, "
    "while background lighting and subtle grain add a cinematic mood without obscuring the action."
)


DEFAULT_PROMPT_ZH = STEADYDANCER_PROMPT_ZH_REALISTIC
DEFAULT_PROMPT_EN = STEADYDANCER_PROMPT_EN_REALISTIC

