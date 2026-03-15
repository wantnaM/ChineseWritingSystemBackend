"""
FastAPI 路由定义
包含:
  - /api/v1/units     - 单元 CRUD
  - /api/v1/themes    - 主题 CRUD（含 Block 管理）
  - /api/v1/blocks    - Block CRUD
  - /api/v1/student   - 学生端接口（进度、作答、AI 评测）
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.models import (
    Badge, Block, StudentBadge, StudentProgress, StudentResponse, Theme, Unit
)
from app.schemas.schemas import (
    BlockCreate, BlockRead, BlockUpdate,
    EvaluatorPayload, EvaluatorResponse,
    MessageResponse,
    PaginatedResponse, Pagination,
    StudentProgressRead, StudentProgressUpdate,
    StudentResponseCreate, StudentResponseRead,
    ThemeCreate, ThemeDetail, ThemeRead, ThemeUpdate,
    UnitCreate, UnitDetail, UnitRead, UnitUpdate,
    StudentBadgeRead,
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
    """获取单元列表（分页）。"""
    q = select(Unit).order_by(Unit.sort_order, Unit.id)
    if is_published is not None:
        q = q.where(Unit.is_published == is_published)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return PaginatedResponse(
        items=items,
        pagination=Pagination(
            page=page, page_size=page_size, total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@unit_router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(body: UnitCreate, db: DB):
    """创建单元。"""
    unit = Unit(**body.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@unit_router.get("/{unit_id}", response_model=UnitDetail)
async def get_unit(unit_id: int, db: DB):
    """获取单元详情（含主题和 Block 列表）。"""
    unit = (
        await db.execute(
            select(Unit)
            .where(Unit.id == unit_id)
            .options(selectinload(Unit.themes).selectinload(Theme.blocks))
        )
    ).scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    return unit


@unit_router.patch("/{unit_id}", response_model=UnitRead)
async def update_unit(unit_id: int, body: UnitUpdate, db: DB):
    """更新单元信息。"""
    unit = await db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(unit, k, v)
    await db.commit()
    await db.refresh(unit)
    return unit


@unit_router.delete("/{unit_id}", response_model=MessageResponse)
async def delete_unit(unit_id: int, db: DB):
    """删除单元（级联删除主题和 Block）。"""
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
async def list_themes_by_unit(
    db: DB,
    unit_id: int = Query(..., description="所属单元 ID"),
):
    """获取某单元下的所有主题。"""
    themes = (
        await db.execute(
            select(Theme).where(Theme.unit_id ==
                                unit_id).order_by(Theme.sort_order)
        )
    ).scalars().all()
    return themes


@theme_router.post("", response_model=ThemeRead, status_code=status.HTTP_201_CREATED)
async def create_theme(
    body: ThemeCreate,
    db: DB,
    unit_id: int = Query(..., description="所属单元 ID"),
):
    """在指定单元下创建主题。"""
    unit = await db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")
    theme = Theme(**body.model_dump(), unit_id=unit_id)
    db.add(theme)
    await db.commit()
    await db.refresh(theme)
    return theme


@theme_router.patch("/{theme_id}", response_model=ThemeRead)
async def update_theme(theme_id: int, body: ThemeUpdate, db: DB):
    """更新主题信息。"""
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(theme, k, v)
    await db.commit()
    await db.refresh(theme)
    return theme


@theme_router.post("/{theme_id}/publish", response_model=ThemeRead)
async def publish_theme(theme_id: int, db: DB):
    """发布主题（解锁学生访问）。"""
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    theme.is_published = True  # type: ignore
    theme.status = "published"  # type: ignore
    await db.commit()
    await db.refresh(theme)
    return theme


@theme_router.delete("/{theme_id}", response_model=MessageResponse)
async def delete_theme(theme_id: int, db: DB):
    """删除主题（级联删除 Block）。"""
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    await db.delete(theme)
    await db.commit()
    return MessageResponse(message=f"主题 {theme_id} 已删除")


# ===========================================================================
# Block CRUD
# ===========================================================================

@block_router.get("", response_model=list[BlockRead])
async def list_blocks(
    db: DB,
    theme_id: int = Query(..., description="所属主题 ID"),
):
    """获取某主题下的所有 Block。"""
    blocks = (
        await db.execute(
            select(Block)
            .where(Block.theme_id == theme_id)
            .order_by(Block.sort_order)
        )
    ).scalars().all()
    return blocks


@block_router.post("", response_model=BlockRead, status_code=status.HTTP_201_CREATED)
async def create_block(
    body: BlockCreate,
    db: DB,
    theme_id: int = Query(..., description="所属主题 ID"),
):
    """在指定主题下创建 Block。"""
    theme = await db.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="主题不存在")
    block = Block(**body.model_dump(), theme_id=theme_id)
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
    """更新 Block（教师在低代码编辑器中修改 config_json 时调用）。"""
    block = await db.get(Block, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(block, k, v)
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

@student_router.get(
    "/themes/{theme_id}/blocks",
    response_model=list[BlockRead],
)
async def get_published_blocks(theme_id: int, db: DB):
    """
    学生端：获取已发布主题的 Block 列表。
    """
    theme = await db.get(Theme, theme_id)
    if not theme or not theme.is_published:
        raise HTTPException(status_code=404, detail="主题不存在或未发布")

    blocks = (
        await db.execute(
            select(Block).where(Block.theme_id ==
                                theme_id).order_by(Block.sort_order)
        )
    ).scalars().all()
    return blocks


@student_router.get(
    "/progress/{student_id}/theme/{theme_id}",
    response_model=StudentProgressRead,
)
async def get_progress(student_id: str, theme_id: int, db: DB):
    """获取学生在某主题的进度。若不存在则初始化。"""
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


@student_router.patch(
    "/progress/{student_id}/theme/{theme_id}",
    response_model=StudentProgressRead,
)
async def update_progress(
    student_id: str, theme_id: int, body: StudentProgressUpdate, db: DB
):
    """学生完成一个 Block 后调用，推进 current_block_order。"""
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

    progress.current_block_order = body.current_block_order  # type: ignore
    progress.is_completed = body.is_completed  # type: ignore
    if body.is_completed and not progress.completed_at:
        from datetime import datetime, timezone
        progress.completed_at = datetime.now(timezone.utc)  # type: ignore

    await db.commit()
    await db.refresh(progress)
    return progress


@student_router.post(
    "/responses",
    response_model=StudentResponseRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_response(body: StudentResponseCreate, db: DB):
    """学生提交 Block 作答。"""
    block = await db.get(Block, body.block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")

    response = StudentResponse(**body.model_dump())
    db.add(response)
    await db.commit()
    await db.refresh(response)
    return response


@student_router.get(
    "/responses/{student_id}/block/{block_id}",
    response_model=list[StudentResponseRead],
)
async def get_responses(student_id: str, block_id: int, db: DB):
    """获取学生在某 Block 的历史作答记录。"""
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


@student_router.get("/badges/{student_id}", response_model=list[StudentBadgeRead])
async def get_student_badges(student_id: str, db: DB):
    """获取学生已获得的徽章列表。"""
    rows = (
        await db.execute(
            select(StudentBadge)
            .where(StudentBadge.student_id == student_id)
            .options(selectinload(StudentBadge.badge))
        )
    ).scalars().all()
    return rows


@student_router.post("/evaluate", response_model=EvaluatorResponse)
async def evaluate_writing(body: EvaluatorPayload, db: DB):
    """
    触发 AI 写作评测，同步返回反馈文本。
    调用 EvaluatorAgent 构建 Prompt 并请求 Anthropic API。
    """
    # 验证 block 存在
    block = await db.get(Block, body.block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block 不存在")

    from app.agents.evaluator_agent import agent
    feedback = await agent.evaluate(body)
    return EvaluatorResponse(feedback=feedback)


# ===========================================================================
# 组装 main router
# ===========================================================================

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(unit_router)
api_router.include_router(theme_router)
api_router.include_router(block_router)
api_router.include_router(student_router)
