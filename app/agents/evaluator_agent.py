"""
写作评测专家 (The Evaluator)
============================
职责：
  - 接收学生的写作内容（通过 HTTP POST /student/evaluate）
  - 根据当前 Block 的评测上下文构建专属 Prompt
  - 调用 Anthropic claude，返回伴学反馈文本

架构说明：
  - EvaluatorAgent   核心评测逻辑（Prompt 构建 + Anthropic 调用）
  - agent            全局单例，供路由层直接注入
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from app.core.config import settings
from app.schemas.schemas import EvaluatorPayload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 评测策略配置 —— 不同 component_type 对应不同的评测侧重点
# ---------------------------------------------------------------------------

COMPONENT_EVAL_STRATEGIES: dict[str, dict[str, Any]] = {
    "GuidedWritingArea": {
        "name": "仿写练习",
        "focus_prompt": (
            "你正在评测学生的仿写练习。重点关注：\n"
            "1. 是否抓住了范文的句式结构（如排比、比喻等修辞手法）\n"
            "2. 意象是否贴切，是否有画面感\n"
            "3. 语言是否通顺自然，是否有自己的创意\n"
            "评测时请先肯定亮点，再温和指出可改进的地方，最后给出具体修改建议。"
        ),
    },
    "ReadingGuide": {
        "name": "阅读感悟",
        "focus_prompt": (
            "你正在评测学生的阅读感悟记录。重点关注：\n"
            "1. 是否结合了文章的具体段落/细节来表达感受\n"
            "2. 情感是否真实，是否有个人体验的联结\n"
            "3. 是否有自己的思考，而不只是复述原文\n"
            "用苏格拉底式提问引导学生深入思考，避免直接给答案。"
        ),
    },
    "TaskDriven": {
        "name": "任务作答",
        "focus_prompt": (
            "你正在评测学生的任务作答。重点关注：\n"
            "1. 是否紧扣任务要求，内容是否切题\n"
            "2. 论据是否充分，逻辑是否清晰\n"
            "3. 语言表达是否准确、生动\n"
            "给出结构化反馈：先整体评价（1句），再分点指导（2-3点），最后鼓励。"
        ),
    },
    "EditableTable": {
        "name": "表格填写",
        "focus_prompt": (
            "你正在评测学生在表格中填写的内容。重点关注：\n"
            "1. 内容是否符合题目要求和示例格式\n"
            "2. 提炼是否准确，是否抓住了关键信息\n"
            "3. 表达是否简洁清晰\n"
            "给出简短、具体的改进建议。"
        ),
    },
}

DEFAULT_STRATEGY: dict[str, Any] = {
    "name": "通用写作",
    "focus_prompt": (
        "你正在评测学生的写作内容。请从内容、语言、结构三个维度给出建设性反馈，"
        "先肯定优点，再指出改进方向，语气亲切鼓励。"
    ),
}


# ---------------------------------------------------------------------------
# EvaluatorAgent
# ---------------------------------------------------------------------------

class EvaluatorAgent:
    """同步（非流式）写作评测智能体。"""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _build_prompt(self, payload: EvaluatorPayload) -> str:
        strategy = COMPONENT_EVAL_STRATEGIES.get(
            payload.component_type, DEFAULT_STRATEGY
        )
        ctx = payload.context

        parts = [
            "你是一位经验丰富的语文教师，专注于初中写作教学。",
            "",
            strategy["focus_prompt"],
            "",
        ]

        if ctx.get("instruction"):
            parts += [f"【写作任务要求】\n{ctx['instruction']}", ""]

        if ctx.get("reference_text"):
            parts += [f"【参考范文】\n{ctx['reference_text']}", ""]

        if ctx.get("evaluator_focus"):
            focuses = "\n".join(f"- {f}" for f in ctx["evaluator_focus"])
            parts += [f"【重点评测方向】\n{focuses}", ""]

        parts += [
            f"【学生作品】\n{payload.student_text}",
            "",
            "请给出评测反馈（200字以内，语气亲切，具体可操作）：",
        ]

        return "\n".join(parts)

    async def evaluate(self, payload: EvaluatorPayload) -> str:
        """调用 Anthropic API，返回评测反馈文本。"""
        prompt = self._build_prompt(payload)
        try:
            # 使用同步客户端包在异步中运行（Anthropic SDK 同步调用，FastAPI 用 run_in_executor 也可，
            # 此处直接调用足够，因为 Anthropic SDK 内部是线程安全的）
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    max_tokens=settings.ANTHROPIC_MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}],
                ),
            )
            return response.content[0].text
        except Exception as e:
            logger.exception("Anthropic API 调用失败: %s", e)
            raise


# 全局单例，供路由层注入
agent = EvaluatorAgent()
