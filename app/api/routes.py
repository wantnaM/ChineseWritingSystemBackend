"""
FastAPI 路由定义
包含:
  - /api/v1/units     - 单元 CRUD
  - /api/v1/themes    - 主题 CRUD（含 Block 管理）
  - /api/v1/blocks    - Block CRUD
  - /api/v1/student   - 学生端接口（进度查询、作答提交、AI 评测）

【v2 变更 - student 端】
  - 删除 PATCH /student/progress：进度不再由前端手动推送
  - submit_response 提交后自动判定主题是否完成
  - GET /student/progress 返回的数据结构去掉 current_block_order
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.models import (
    Badge, Block, StudentBadge, StudentProgress, StudentResponse, Theme, Unit,
)
from app.schemas.schemas import (
    BlockCreate, BlockRead, BlockUpdate,
    EvaluatorPayload, EvaluatorResponse,
    MessageResponse,
    PaginatedResponse, Pagination,
    StudentProgressRead,
    StudentResponseCreate, StudentResponseRead,
    ThemeCreate, ThemeDetail, ThemeRead, ThemeUpdate,
    UnitCreate, UnitDetail, UnitRead, UnitUpdate,
    BadgeRead, UnitWithProgressRead, ThemeProgressSummary
)

# ---------------------------------------------------------------------------
# Dependency alias
# ---------------------------------------------------------------------------
DB = Annotated[AsyncSession, Depends(get_session)]

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
unit_router = APIRouter(prefix="/units",   tags=["单元 Unit"])
theme_router = APIRouter(prefix="/themes",  tags=["主题 Theme"])
block_router = APIRouter(prefix="/blocks",  tags=["内容块 Block"])
student_router = APIRouter(prefix="/student", tags=["学生端 Student"])


# ===========================================================================
# Unit CRUD
# ===========================================================================

@unit_router.get("", response_model=PaginatedResponse[UnitRead])
async def list_units(
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_published: bool | None = None,
):
    """获取单元列表（分页），含每个单元的主题列表（用于前端渲染进度）。"""
    q = select(Unit).order_by(Unit.sort_order, Unit.id)
    if is_published is not None:
        q = q.where(Unit.is_published == is_published)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    q = q.options(selectinload(Unit.themes))
    units = (await db.execute(q)).scalars().all()

    unit_reads = []
    for u in units:
        ur = UnitRead.model_validate(u)
        ur.themes_count = len(u.themes)
        unit_reads.append(ur)

    return PaginatedResponse(
        items=unit_reads,
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@unit_router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(body: UnitCreate, db: DB):
    unit = Unit(**body.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@unit_router.get("/{unit_id}", response_model=UnitDetail)
async def get_unit(unit_id: int, db: DB):
    unit = (
        await db.execute(
            select(Unit)
            .where(Unit.id == unit_id)
            .options(
                selectinload(Unit.themes).selectinload(Theme.blocks)
            )
        )
    ).scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    return unit


@unit_router.patch("/{unit_id}", response_model=UnitRead)
async def update_unit(unit_id: int, body: UnitUpdate, db: DB):
    unit = await db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(unit, field, value)
    await db.commit()
    await db.refresh(unit)
    return unit


@unit_router.delete("/{unit_id}", response_model=MessageResponse)
async def delete_unit(unit_id: int, db: DB):
    unit = await db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    await db.delete(unit)
    await db.commit()
    return MessageResponse(message=f"单元 {unit_id} 已删除")


# ===========================================================================
# Theme CRUD
# ===========================================================================

@theme_router.get("", response_model=list[ThemeRead])
@theme_router.get("", response_model=list[ThemeRead])
async def list_themes(db: DB, unit_id: int = Query(...)):
    themes = (
        await db.execute(
            select(Theme).where(Theme.unit_id ==
                                unit_id).order_by(Theme.sort_order)
        )
    ).scalars().all()
    return themes


@theme_router.post("", response_model=ThemeRead, status_code=status.HTTP_201_CREATED)
async def create_theme(body: ThemeCreate, db: DB):
    theme = Theme(**body.model_dump())
    db.add(theme)
    await db.commit()
    await db.refresh(theme)
    return theme


@theme_router.get("/{theme_id}", response_model=ThemeDetail)
async def get_theme(theme_id: int, db: DB):
    theme = (
        await db.execute(
            select(Theme)
            .where(Theme.id == theme_id)
            .options(selectinload(Theme.blocks))
        )
    ).scalar_one_or_none()
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    return theme


@theme_router.patch("/{theme_id}", response_model=ThemeRead)
async def update_theme(theme_id: int, body: ThemeUpdate, db: DB):
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(theme, field, value)
    await db.commit()
    await db.refresh(theme)
    return theme


@theme_router.delete("/{theme_id}", response_model=MessageResponse)
async def delete_theme(theme_id: int, db: DB):
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    await db.delete(theme)
    await db.commit()
    return MessageResponse(message=f"主题 {theme_id} 已删除")


# ===========================================================================
# Block CRUD
# ===========================================================================

@block_router.post("", response_model=BlockRead, status_code=status.HTTP_201_CREATED)
async def create_block(body: BlockCreate, db: DB):
    block = Block(**body.model_dump())
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


@block_router.get("/{block_id}", response_model=BlockRead)
async def get_block(block_id: int, db: DB):
    block = await db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")
    return block


@block_router.patch("/{block_id}", response_model=BlockRead)
async def update_block(block_id: int, body: BlockUpdate, db: DB):
    block = await db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(block, field, value)
    await db.commit()
    await db.refresh(block)
    return block


@block_router.delete("/{block_id}", response_model=MessageResponse)
async def delete_block(block_id: int, db: DB):
    block = await db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")
    await db.delete(block)
    await db.commit()
    return MessageResponse(message=f"Block {block_id} 已删除")


@block_router.put("/reorder", response_model=MessageResponse)
async def reorder_blocks(
    db: DB,
    theme_id: int = Query(...),
    ordered_ids: list[int] = Query(...),
):
    """批量更新同一主题内 Block 的排序。传入有序的 block_id 列表。"""
    for idx, block_id in enumerate(ordered_ids):
        block = await db.get(Block, block_id)
        if block and block.theme_id == theme_id:
            block.sort_order = idx  # type: ignore
    await db.commit()
    return MessageResponse(message="排序更新成功")


# ===========================================================================
# Student API（学生端）
# ===========================================================================

# ---------------------------------------------------------------------------
# 内部工具：判定主题是否全部完成，若完成则更新 student_progress
# ---------------------------------------------------------------------------

async def _check_and_complete_theme(
    student_id: str,
    theme_id: int,
    db: AsyncSession,
) -> StudentProgress:
    """
    提交作答后自动调用。
    逻辑：
      1. 查出该主题下所有 block_type='task_driven' 的 Block id 集合
      2. 查出该学生在这些 Block 中已提交过的 block_id 集合
      3. 若二者相等（全部覆盖），则将 student_progress.is_completed 置 True
      4. 无论是否完成，都保证 student_progress 行存在并返回
    """
    # ── 1. 该主题所有 task_driven block id ──
    task_block_rows = (
        await db.execute(
            select(Block.id).where(
                Block.theme_id == theme_id,
                Block.block_type == "task_driven",
            )
        )
    ).scalars().all()
    task_block_ids: set[int] = set(task_block_rows)

    # ── 2. 该学生已提交的 task_driven block id ──
    submitted_rows = (
        await db.execute(
            select(StudentResponse.block_id)
            .where(
                StudentResponse.student_id == student_id,
                StudentResponse.block_id.in_(task_block_ids),
            )
            .distinct()
        )
    ).scalars().all()
    submitted_ids: set[int] = set(submitted_rows)

    # ── 3. 获取或初始化 progress 行 ──
    progress = (
        await db.execute(
            select(StudentProgress).where(
                StudentProgress.student_id == student_id,
                StudentProgress.theme_id == theme_id,
            )
        )
    ).scalar_one_or_none()

    if not progress:
        progress = StudentProgress(student_id=student_id, theme_id=theme_id)
        db.add(progress)

    # ── 4. 判定是否全部完成 ──
    #  task_block_ids 为空（主题下没有任务组件）时，不视为完成
    if task_block_ids and task_block_ids == submitted_ids:
        if not progress.is_completed:
            progress.is_completed = True  # type: ignore
            progress.completed_at = datetime.now(timezone.utc)  # type: ignore

    await db.commit()
    await db.refresh(progress)
    return progress


# ---------------------------------------------------------------------------
# GET /student/themes/{theme_id}/blocks
# ---------------------------------------------------------------------------

@student_router.get(
    "/themes/{theme_id}/blocks",
    response_model=list[BlockRead],
    summary="获取主题下全部 Block（学生端）",
)
async def get_published_blocks(theme_id: int, db: DB):
    """
    学生端：获取已发布主题的全部 Block 列表，按 sort_order 排序。
    所有 Block 直接展示，不再逐步解锁。
    """
    theme = await db.get(Theme, theme_id)
    if not theme or not theme.is_published:
        raise HTTPException(status_code=404, detail="主题不存在或未发布")

    blocks = (
        await db.execute(
            select(Block)
            .where(Block.theme_id == theme_id)
            .order_by(Block.sort_order)
        )
    ).scalars().all()
    return blocks


# ---------------------------------------------------------------------------
# GET /student/progress/{student_id}/theme/{theme_id}
# ---------------------------------------------------------------------------

@student_router.get(
    "/progress/{student_id}/theme/{theme_id}",
    response_model=StudentProgressRead,
    summary="获取学生在某主题的完成状态",
)
async def get_progress(student_id: str, theme_id: int, db: DB):
    """
    获取学生在某主题的进度记录。若记录不存在则自动初始化。
    返回的 is_completed 字段反映主题是否已完成。
    """
    progress = (
        await db.execute(
            select(StudentProgress).where(
                StudentProgress.student_id == student_id,
                StudentProgress.theme_id == theme_id,
            )
        )
    ).scalar_one_or_none()

    if not progress:
        progress = StudentProgress(student_id=student_id, theme_id=theme_id)
        db.add(progress)
        await db.commit()
        await db.refresh(progress)

    return progress


# ---------------------------------------------------------------------------
# POST /student/responses  ← 核心：提交后自动判定主题完成
# ---------------------------------------------------------------------------

class SubmitResponseResult(StudentResponseRead):
    """提交作答的响应，附带最新的主题完成状态。"""
    theme_completed: bool = False


@student_router.post(
    "/responses",
    response_model=SubmitResponseResult,
    status_code=status.HTTP_201_CREATED,
    summary="学生提交 Block 作答（自动判定主题完成）",
)
async def submit_response(body: StudentResponseCreate, db: DB):
    """
    学生提交某 Block 的作答。

    提交后后端自动执行：
      1. 存储作答记录（student_responses）
      2. 检查该主题下所有 task_driven Block 是否均已提交
      3. 若全部完成，将 student_progress.is_completed 置 True
      4. 在响应中返回 theme_completed 字段，前端据此展示完成动画

    """
    # ── 验证 block 存在 ──
    block = await db.get(Block, body.block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")

    # ── 存储作答 ──
    response = StudentResponse(**body.model_dump())
    db.add(response)
    await db.commit()
    await db.refresh(response)

    # ── 自动判定主题完成状态（通过 block 找 theme_id）──
    progress = await _check_and_complete_theme(
        student_id=body.student_id,
        theme_id=block.theme_id,
        db=db,
    )

    return SubmitResponseResult(
        id=response.id,
        student_id=response.student_id,
        block_id=response.block_id,
        response_data=response.response_data,
        ai_feedback=response.ai_feedback,
        score=response.score,
        submitted_at=response.submitted_at,
        theme_completed=progress.is_completed,
    )


# ---------------------------------------------------------------------------
# GET /student/responses/{student_id}/block/{block_id}
# ---------------------------------------------------------------------------

@student_router.get(
    "/responses/{student_id}/block/{block_id}",
    response_model=list[StudentResponseRead],
    summary="获取学生在某 Block 的历史作答",
)
async def get_responses(student_id: str, block_id: int, db: DB):
    """获取学生在某 Block 的全部历史作答记录，按提交时间倒序。"""
    responses = (
        await db.execute(
            select(StudentResponse)
            .where(
                StudentResponse.student_id == student_id,
                StudentResponse.block_id == block_id,
            )
            .order_by(StudentResponse.submitted_at.desc())
        )
    ).scalars().all()
    return responses


# ---------------------------------------------------------------------------
# GET /student/badges/{student_id}
# ---------------------------------------------------------------------------

@student_router.get(
    "/badges/{student_id}",
    response_model=list[BadgeRead],
    summary="获取学生徽章列表（含未获得）",
)
async def get_student_badges(student_id: str, db: DB):
    """
    获取全部徽章列表，并标注该学生是否已获得（earned 字段）。
    未获得的徽章 earned=False，前端渲染为灰色锁定状态。
    """
    all_badges = (
        await db.execute(
            select(Badge).order_by(Badge.unit_id.nulls_last(), Badge.id)
        )
    ).scalars().all()

    earned_rows = (
        await db.execute(
            select(StudentBadge.badge_id).where(
                StudentBadge.student_id == student_id
            )
        )
    ).scalars().all()
    earned_ids: set[int] = set(earned_rows)

    return [
        BadgeRead(
            id=b.id,
            unit_id=b.unit_id,
            name=b.name,
            icon=b.icon,
            description=b.description,
            earned=b.id in earned_ids,
        )
        for b in all_badges
    ]


# ---------------------------------------------------------------------------
# POST /student/evaluate
# ---------------------------------------------------------------------------

@student_router.post(
    "/evaluate",
    response_model=EvaluatorResponse,
    summary="触发 AI 写作评测",
)
async def evaluate_writing(body: EvaluatorPayload, db: DB):
    """
    触发 AI 写作评测，同步返回反馈文本。
    调用 EvaluatorAgent 构建 Prompt 并请求 Anthropic API。
    """
    block = await db.get(Block, body.block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")

    from app.agents.evaluator_agent import agent
    result = await agent.evaluate(body)

    return EvaluatorResponse(**result)


@student_router.get(
    "/units/{student_id}",
    response_model=PaginatedResponse[UnitWithProgressRead],
    summary="学生端获取单元列表（含学习进度）",
)
async def list_units_for_student(
    student_id: str,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # 1. 查单元列表（与原 list_units 逻辑一致）
    q = select(Unit).where(Unit.is_published ==
                           True).order_by(Unit.sort_order, Unit.id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.offset(
        (page - 1) * page_size).limit(page_size).options(selectinload(Unit.themes))
    units = (await db.execute(q)).scalars().all()

    # 2. 查该学生所有已完成的主题 id
    all_theme_ids = [t.id for u in units for t in u.themes]
    completed_rows = (await db.execute(
        select(StudentProgress.theme_id).where(
            StudentProgress.student_id == student_id,
            StudentProgress.theme_id.in_(all_theme_ids),
            StudentProgress.is_completed == True,
        )
    )).scalars().all()
    completed_set = set(completed_rows)

    # 3. 组装响应
    result = []
    for u in units:
        ur = UnitWithProgressRead.model_validate(u)
        ur.themes_count = len(u.themes)
        ur.theme_progress = [
            ThemeProgressSummary(
                theme_id=t.id, is_completed=t.id in completed_set)
            for t in u.themes
        ]
        result.append(ur)

    return PaginatedResponse(items=result, pagination=Pagination(
        page=page, page_size=page_size, total=total,
        total_pages=(total + page_size - 1) // page_size,
    ))

# ===========================================================================
# 组装 main router
# ===========================================================================

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(unit_router)
api_router.include_router(theme_router)
api_router.include_router(block_router)
api_router.include_router(student_router)
