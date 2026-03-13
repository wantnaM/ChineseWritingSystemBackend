"""
写作评测专家 (The Evaluator)
============================
职责：
  - 接收学生的实时写作内容（通过 WebSocket）
  - 根据当前 Block 的评测上下文，构建专属 Prompt
  - 调用 Anthropic claude-sonnet-4-6，流式返回伴学反馈
  - 支持不同 component_type 的差异化评测策略

架构说明：
  - EvaluatorAgent       核心评测逻辑（Prompt 构建 + 流式调用）
  - ConnectionManager    WebSocket 连接池管理（支持多学生并发）
  - ws_evaluate_endpoint WebSocket 路由处理器（注入到 FastAPI）

调用链：
  前端防抖 → WebSocket send(EvaluatorWSPayload)
           → ws_evaluate_endpoint
           → EvaluatorAgent.stream_feedback()
           → Anthropic stream → WebSocket send(delta chunks)
           → 前端打字机渲染
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

import anthropic
from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.schemas.schemas import EvaluatorWSPayload, EvaluatorWSResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 评测策略配置 —— 不同 component_type 对应不同的评测侧重点
# ---------------------------------------------------------------------------

COMPONENT_EVAL_STRATEGIES: dict[str, dict] = {
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
            "3. 语言是否简洁精准\n"
            "反馈要简短（3句以内），直接告诉学生哪里填得好，哪里可以更准确。"
        ),
    },
    "default": {
        "name": "写作练习",
        "focus_prompt": (
            "你正在评测学生的写作练习。请根据任务要求，给出建设性的反馈。\n"
            "先肯定学生的努力和亮点，再提出1-2个具体的改进建议。\n"
            "语气要温暖鼓励，像一位耐心的语文老师。"
        ),
    },
}


# ---------------------------------------------------------------------------
# Prompt 构建器
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    """构建 Evaluator Agent 的系统 Prompt。"""
    return """你是一位专业、温暖的语文写作伴学老师，专注于指导中学生的语文写作。

你的核心职责：
- 实时陪伴学生写作，给出即时、针对性的反馈
- 用鼓励性的语言激发学生的写作兴趣
- 引导学生发现自己的问题，而不是直接给出答案
- 关注"以读促写"的学习路径：感知 → 技法 → 练习 → 建构

反馈原则：
- 先肯定（找到真实的亮点），再引导（温和指出问题），最后激励
- 语言简洁，每次反馈不超过150字
- 使用学生能理解的语言，避免过于学术化的术语
- 多用具体例子，少用抽象评价（如避免说"写得不错"，而是说"你用了比喻，把X比作Y，让读者能感受到..."）

注意：你现在看到的是学生正在输入的内容，可能还未完成，请给出过程性鼓励和引导性建议，而非终结性评价。"""


def build_user_prompt(payload: EvaluatorWSPayload) -> str:
    """根据 payload 构建用户 Prompt，携带完整评测上下文。"""
    strategy = COMPONENT_EVAL_STRATEGIES.get(
        payload.component_type,
        COMPONENT_EVAL_STRATEGIES["default"]
    )

    # 解析 evaluator_focus（评测重点列表）
    focus_points = payload.context.get("evaluator_focus", [])
    focus_str = "\n".join(f"  - {p}" for p in focus_points) if focus_points else "  - 无特殊要求"

    # 参考范文/示例（可选）
    reference = payload.context.get("reference_text", "")
    reference_section = f"\n【参考范文/示例】\n{reference}\n" if reference else ""

    # 任务说明
    instruction = payload.context.get("instruction", "完成写作练习")

    prompt = f"""【任务类型】{strategy['name']}（第 {payload.current_step + 1} 步）

【任务要求】
{instruction}
{reference_section}
【本次评测重点】
{focus_str}

【评测策略】
{strategy['focus_prompt']}

【学生当前输入】
{payload.student_text if payload.student_text.strip() else "（学生还没有开始写...）"}

请根据以上信息，给出简洁、温暖、有针对性的伴学反馈（不超过150字）："""

    return prompt


# ---------------------------------------------------------------------------
# EvaluatorAgent
# ---------------------------------------------------------------------------

class EvaluatorAgent:
    """
    核心评测智能体。
    使用 Anthropic claude-sonnet-4-6 流式 API 生成反馈。
    """

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def stream_feedback(
        self, payload: EvaluatorWSPayload
    ) -> AsyncIterator[EvaluatorWSResponse]:
        """
        流式生成评测反馈。
        逐块 yield EvaluatorWSResponse，最后 yield type='done'。

        用法：
            async for chunk in agent.stream_feedback(payload):
                await websocket.send_json(chunk.model_dump())
        """
        # 学生还没写内容时，直接给鼓励提示
        if not payload.student_text.strip():
            yield EvaluatorWSResponse(
                type="delta",
                content="开始写吧，不用担心写错～把你脑海中第一个浮现的想法写下来就好。"
            )
            yield EvaluatorWSResponse(type="done")
            return

        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(payload)

        try:
            async with self._client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text_chunk in stream.text_stream:
                    yield EvaluatorWSResponse(type="delta", content=text_chunk)

            yield EvaluatorWSResponse(type="done")

        except anthropic.APIConnectionError as e:
            logger.error("Anthropic 连接失败: %s", e)
            yield EvaluatorWSResponse(type="error", content="网络连接异常，请稍后重试。")
        except anthropic.RateLimitError:
            logger.warning("Anthropic 触发限流")
            yield EvaluatorWSResponse(type="error", content="服务繁忙，请稍等片刻再试。")
        except anthropic.APIStatusError as e:
            logger.error("Anthropic API 错误 status=%s: %s", e.status_code, e.message)
            yield EvaluatorWSResponse(type="error", content="AI 服务暂时不可用。")
        except Exception as e:
            logger.exception("EvaluatorAgent 未知错误: %s", e)
            yield EvaluatorWSResponse(type="error", content="评测时发生未知错误。")


# ---------------------------------------------------------------------------
# ConnectionManager —— WebSocket 连接池
# ---------------------------------------------------------------------------

@dataclass
class ConnectionManager:
    """
    管理所有活跃的 WebSocket 连接。
    key: student_id，支持同一学生多标签页（用 connection_id 区分）。
    """
    # {connection_id: WebSocket}
    _connections: dict[str, WebSocket] = field(default_factory=dict)
    # {student_id: set[connection_id]}
    _student_index: dict[str, set[str]] = field(default_factory=dict)
    # 防止同一连接同时处理多个请求
    _locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    def _make_conn_id(self, student_id: str, websocket: WebSocket) -> str:
        return f"{student_id}_{id(websocket)}"

    async def connect(self, student_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = self._make_conn_id(student_id, websocket)
        self._connections[conn_id] = websocket
        self._student_index.setdefault(student_id, set()).add(conn_id)
        self._locks[conn_id] = asyncio.Lock()
        logger.info("WS 连接建立: student=%s conn=%s", student_id, conn_id)
        return conn_id

    def disconnect(self, conn_id: str) -> None:
        ws = self._connections.pop(conn_id, None)
        if ws:
            # 从 student_index 中清理
            for sid, conns in self._student_index.items():
                conns.discard(conn_id)
            self._locks.pop(conn_id, None)
            logger.info("WS 连接断开: conn=%s", conn_id)

    async def send(self, conn_id: str, response: EvaluatorWSResponse) -> None:
        ws = self._connections.get(conn_id)
        if ws:
            await ws.send_text(response.model_dump_json())

    def get_lock(self, conn_id: str) -> asyncio.Lock:
        return self._locks.get(conn_id) or asyncio.Lock()

    @property
    def active_count(self) -> int:
        return len(self._connections)


# 全局单例
manager = ConnectionManager()
agent = EvaluatorAgent()


# ---------------------------------------------------------------------------
# WebSocket 路由处理器（供 FastAPI 注册）
# ---------------------------------------------------------------------------

async def ws_evaluate_endpoint(websocket: WebSocket, student_id: str) -> None:
    """
    WebSocket 端点处理函数。

    URL: /ws/evaluate?student_id=xxx

    协议（双向 JSON）：
      Client → Server:
        {
          "student_id": "user_123",
          "theme_id": 1,
          "block_id": 5,
          "current_step": 2,
          "component_type": "GuidedWritingArea",
          "student_text": "校园的早晨，雾气像...",
          "context": {
            "instruction": "请模仿上述句式描写晨曦",
            "evaluator_focus": ["是否使用了比喻", "意境是否相符"],
            "reference_text": "（可选）范文原文"
          }
        }

      Server → Client (流式):
        {"type": "delta",  "content": "写得"}
        {"type": "delta",  "content": "很有意境！"}
        {"type": "done",   "content": ""}
        {"type": "error",  "content": "错误信息"}  ← 仅出错时
    """
    conn_id = await manager.connect(student_id, websocket)

    try:
        while True:
            # 接收客户端消息
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                payload = EvaluatorWSPayload(**data)
            except (json.JSONDecodeError, ValueError) as e:
                await manager.send(
                    conn_id,
                    EvaluatorWSResponse(type="error", content=f"消息格式错误: {e}")
                )
                continue

            # 使用每连接锁，防止并发请求乱序
            lock = manager.get_lock(conn_id)
            async with lock:
                async for chunk in agent.stream_feedback(payload):
                    # 连接可能已在流式传输中断开
                    if conn_id not in manager._connections:
                        break
                    await manager.send(conn_id, chunk)

    except WebSocketDisconnect:
        logger.info("客户端主动断开: conn=%s", conn_id)
    except Exception as e:
        logger.exception("WebSocket 处理异常: %s", e)
        try:
            await manager.send(
                conn_id,
                EvaluatorWSResponse(type="error", content="服务端发生异常，连接即将关闭。")
            )
        except Exception:
            pass
    finally:
        manager.disconnect(conn_id)
