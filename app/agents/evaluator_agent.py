"""
写作评测专家 (The Evaluator)
============================
职责：
  - 接收学生的写作内容（通过 HTTP POST /student/evaluate）
  - 根据当前 Block 的评测上下文构建专属 Prompt
  - 调用 Kimi API（兼容 OpenAI 协议），返回结构化评测 JSON

架构说明：
  - EvaluatorAgent   核心评测逻辑（Prompt 构建 + Kimi 调用）
  - agent            全局单例，供路由层直接注入
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import json
import re

from openai import OpenAI  # pip install openai

from app.core.config import settings
from app.schemas.schemas import EvaluatorPayload

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 主题类型中文映射
# ---------------------------------------------------------------------------

THEME_TYPE_LABELS: dict[str, str] = {
    "themeReading": "主题阅读",
    "themeActivity": "主题活动",
    "techniqueLearning": "技法学习",
}

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
        "default_dimensions": ["句式仿写", "意象运用", "创意表达"],
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
        "default_dimensions": ["文本依据", "个人感悟", "思考深度"],
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
        "default_dimensions": ["内容切题", "语言表达", "思维深度"],
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
        "default_dimensions": ["内容准确", "提炼概括", "表达简洁"],
    },
}

DEFAULT_STRATEGY: dict[str, Any] = {
    "name": "通用写作",
    "focus_prompt": (
        "你正在评测学生的写作内容。请从内容、语言、结构三个维度给出建设性反馈，"
        "先肯定优点，再指出改进方向，语气亲切鼓励。"
    ),
    "default_dimensions": ["内容质量", "语言表达", "结构逻辑"],
}

# 参考文本最大字符数（防止 token 超限）
MAX_REFERENCE_TEXT_LEN = 2000


# ---------------------------------------------------------------------------
# EvaluatorAgent
# ---------------------------------------------------------------------------

class EvaluatorAgent:
    """同步（非流式）写作评测智能体，使用 Kimi API（兼容 OpenAI 协议）。"""

    def __init__(self) -> None:
        # OpenAI SDK 指向 Kimi 的兼容端点
        self._client = OpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_BASE_URL,
        )

    def _build_messages(
        self, payload: EvaluatorPayload, eval_context: dict[str, Any]
    ) -> list[dict[str, str]]:
        """构建符合 OpenAI messages 格式的对话列表，包含完整教学上下文。"""
        strategy = COMPONENT_EVAL_STRATEGIES.get(
            payload.component_type, DEFAULT_STRATEGY
        )

        # --- 教学背景 ---
        unit_title = eval_context.get("unit_title", "")
        theme_title = eval_context.get("theme_title", "")
        theme_type = eval_context.get("theme_type", "")
        theme_type_label = THEME_TYPE_LABELS.get(theme_type, theme_type)
        theme_description = eval_context.get("theme_description", "")

        # --- 任务信息 ---
        task_title = eval_context.get("task_title", "")
        instruction = eval_context.get("instruction", "")
        word_limit = eval_context.get("word_limit", "")
        component_type_label = strategy["name"]

        # --- 任务描述（可能是 list[str]）---
        task_description = eval_context.get("task_description", [])
        if isinstance(task_description, list):
            task_description = "\n".join(task_description)

        # --- 参考范文（截断保护）---
        reference_text = eval_context.get("reference_text", "")
        if reference_text and len(reference_text) > MAX_REFERENCE_TEXT_LEN:
            reference_text = reference_text[:MAX_REFERENCE_TEXT_LEN] + "……（已截断）"

        # --- 评测维度 ---
        evaluator_focus = eval_context.get("evaluator_focus", [])
        if not evaluator_focus:
            evaluator_focus = strategy.get("default_dimensions", [])
        focus_list = "\n".join(f"- {f}" for f in evaluator_focus)

        # --- 构建 System Prompt ---
        system_parts = [
            "你是一位经验丰富的初中语文教师，擅长通过建设性反馈帮助学生提升写作能力。",
            "",
            "== 教学背景 ==",
        ]
        if unit_title:
            system_parts.append(f"单元主题：{unit_title}")
        if theme_title:
            system_parts.append(f"主题：{theme_title}（{theme_type_label}）")
        if theme_description:
            system_parts.append(f"学习目标：{theme_description}")

        system_parts += ["", "== 任务信息 =="]
        if task_title:
            system_parts.append(f"任务标题：{task_title}")
        if instruction:
            system_parts.append(f"任务要求：{instruction}")
        elif task_description:
            system_parts.append(f"任务描述：{task_description}")
        system_parts.append(f"组件类型：{component_type_label}")
        if word_limit:
            system_parts.append(f"字数要求：{word_limit}")

        if reference_text:
            system_parts += [
                "",
                "== 参考范文 ==",
                reference_text,
            ]

        system_parts += [
            "",
            "== 评测策略 ==",
            strategy["focus_prompt"],
            "",
            "== 评测维度 ==",
            focus_list,
            "",
            "== 输出要求 ==",
            "请严格以 JSON 格式输出评测结果，结构如下：",
            json.dumps(
                {
                    "overall_comment": "总体评价，1-2句话，鼓励为主（100字以内）",
                    "dimension_feedback": [
                        {
                            "dimension": "维度名称",
                            "score": 85,
                            "comment": "该维度的具体评语（80字以内）",
                        }
                    ],
                    "suggestions": ["改进建议1", "改进建议2"],
                    "score": 87,
                    "score_rationale": "综合评分依据（50字以内）",
                },
                ensure_ascii=False,
                indent=2,
            ),
            "",
            "注意：",
            "1. 按上述评测维度逐一给出 dimension_feedback，每个维度都要有",
            "2. score 为 0-100 的整数",
            "3. 语气亲切、鼓励、具建设性，面向初中学生，避免过于学术化的表达",
            "4. 只输出 JSON，不要有其他内容",
        ]

        system_content = "\n".join(system_parts)

        # --- 构建 User Prompt ---
        user_content = f"学生作答：\n{payload.student_text}"

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        # --- 调试日志：打印完整提示词 ---
        logger.info("=== EvaluatorAgent Prompt Debug ===")
        logger.info("System Prompt:\n%s", system_content)
        logger.info("User Prompt:\n%s", user_content)
        logger.info("=== End Prompt Debug ===")

        return messages

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        """从 AI 返回中提取 JSON，处理 markdown fence 等情况。"""
        # 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ```
        match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # 最后兜底：提取第一个 { ... }
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法从 AI 返回中解析 JSON: {raw[:300]}")

    async def evaluate(
        self, payload: EvaluatorPayload, eval_context: dict[str, Any]
    ) -> dict:
        """调用 Kimi API，返回结构化评测结果。"""
        messages = self._build_messages(payload, eval_context)
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.chat.completions.create(
                    model=settings.KIMI_MODEL,
                    max_tokens=settings.KIMI_MAX_TOKENS,
                    messages=messages,
                    response_format={"type": "json_object"},
                    extra_body={"thinking": {"type": "disabled"}},
                ),
            )
            raw = response.choices[0].message.content
            logger.info("Kimi API raw response:\n%s", raw)

            parsed = self._parse_json_response(raw)
            overall = parsed.get("overall_comment", "")
            return {
                "overall_comment": overall,
                "dimension_feedback": parsed.get("dimension_feedback", []),
                "suggestions": parsed.get("suggestions", []),
                "score": parsed.get("score"),
                "score_rationale": parsed.get("score_rationale", ""),
                "feedback": overall,  # 向后兼容
            }
        except Exception as e:
            logger.exception("Kimi API 调用失败: %s", e)
            raise


# 全局单例，供路由层注入
agent = EvaluatorAgent()
