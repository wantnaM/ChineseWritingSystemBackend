"""
伴学小助手 (Chat Agent)
========================
职责：
  - 接收学生的对话消息（通过 HTTP POST /student/chat）
  - 根据可选的任务上下文构建苏格拉底式教学 Prompt
  - 调用 Kimi API（兼容 OpenAI 协议），返回引导式回复

架构说明：
  - ChatAgent   核心对话逻辑（Prompt 构建 + Kimi 调用）
  - agent       全局单例，供路由层直接注入
"""

from __future__ import annotations

import asyncio
import logging

from openai import OpenAI

from app.core.config import settings
from app.schemas.schemas import ChatContext, ChatMessage, ChatRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 系统提示词（苏格拉底式教学）
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是一位专业的中学语文写作教学助手，名叫"伴学小助手"。你的角色是引导学生思考，而非直接给出答案。

## 教学方法：苏格拉底式提问
1. 先肯定学生已有的思考和观点
2. 通过追问帮助学生深入思考（"你能具体说说...？"、"为什么你这样想？"、"如果从另一个角度看呢？"）
3. 引导学生联系课文原文和个人经验
4. 给予方向性的启发，而非直接示范答案
5. 每次只提1-2个问题，避免信息过载

## 语气要求
- 像一位亲切的学长/学姐，不要过于正式
- 用鼓励性语言开头（"这个想法很有意思"、"你观察得很仔细"）
- 适当使用口语化表达
- 回复控制在100字以内，简洁明了

## 绝对禁止
- 不要直接写出完整答案或范文
- 不要逐字逐句修改学生的文字
- 不要替学生总结观点
- 如果学生要求直接给答案，温和拒绝并继续引导\
"""


# ---------------------------------------------------------------------------
# ChatAgent
# ---------------------------------------------------------------------------

class ChatAgent:
    """无状态对话智能体，使用 Kimi API（兼容 OpenAI 协议）。"""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url=settings.KIMI_BASE_URL,
        )

    @staticmethod
    def _build_system_prompt(
        context: ChatContext | None,
        theme_title: str | None,
    ) -> str:
        """基础提示词 + 可选的任务上下文注入。"""
        parts = [SYSTEM_PROMPT]

        if context:
            ctx_parts = ["\n\n## 当前任务信息"]
            if theme_title:
                ctx_parts.append(f"- 所属主题：{theme_title}")
            if context.task_title:
                ctx_parts.append(f"- 任务名称：{context.task_title}")
            if context.task_description:
                ctx_parts.append(f"- 任务要求：{context.task_description}")
            if context.evaluator_focus:
                ctx_parts.append(f"- 评价维度：{'、'.join(context.evaluator_focus)}")

            student_text = context.student_text or "（学生尚未作答）"
            ctx_parts.append(f"\n## 学生当前作答\n{student_text}")
            ctx_parts.append("\n请根据以上信息，用苏格拉底式提问引导学生。")
            parts.append("\n".join(ctx_parts))

        return "\n".join(parts)

    @staticmethod
    def _map_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
        """将前端消息格式映射为 OpenAI messages 格式。"""
        return [
            {
                "role": "assistant" if msg.role == "ai" else "user",
                "content": msg.content,
            }
            for msg in messages
        ]

    async def chat(self, request: ChatRequest) -> str:
        """调用 Kimi API，返回助手回复文本。"""
        system_prompt = self._build_system_prompt(request.context, request.theme_title)
        mapped = self._map_messages(request.messages)
        messages = [{"role": "system", "content": system_prompt}] + mapped

        logger.info("=== ChatAgent Prompt Debug ===")
        logger.info("System Prompt:\n%s", system_prompt)
        logger.info("Messages (%d):\n%s", len(mapped), "\n".join(
            f"  [{m['role']}] {m['content']}" for m in mapped
        ))
        logger.info("=== End Prompt Debug ===")

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.chat.completions.create(
                    model=settings.KIMI_CHAT_MODEL,
                    max_tokens=settings.KIMI_CHAT_MAX_TOKENS,
                    messages=messages,
                    extra_body={"thinking": {"type": "disabled"}},
                ),
            )
            content = response.choices[0].message.content
            logger.info("Kimi Chat response:\n%s", content)
            return content
        except Exception as e:
            logger.exception("Kimi Chat API 调用失败: %s", e)
            raise


# 全局单例，供路由层注入
agent = ChatAgent()
