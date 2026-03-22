"""
app/api/teacher_routes.py
教师端路由

前缀: /api/v1/teacher
包含:
  - GET  /analytics                            学情分析（全班汇总）
  - GET  /students                             学生账号列表
  - POST /students                             新建学生账号
  - PATCH /students/{student_id}               更新学生信息
  - POST  /students/{student_id}/reset-password 重置学生密码
  - DELETE /students/{student_id}              删除学生账号
  - GET  /students/{student_id}/detail         学生详情（含提交记录）
"""

from __future__ import annotations
import bcrypt

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.models import (
    User, StudentStats, StudentProgress, StudentResponse,
    Block, Theme, Unit,
)
from collections import defaultdict

from app.schemas.schemas import (
    MessageResponse,
    PaginatedResponse, Pagination,
    StudentCreate, StudentUpdate, StudentListItem,
    ClassAnalyticsResponse, TaskCompletionItem, DimensionSummaryItem,
    StudentAnalyticsRow,
    StudentDetailResponse, StudentDetailProfile, SubmissionRecord,
    ChangePasswordRequest,
)

teacher_router = APIRouter(prefix="/teacher", tags=["教师端 Teacher"])
DB = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# 密码工具（与 auth_routes 保持一致）
# ---------------------------------------------------------------------------


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# ===========================================================================
# 学情分析
# ===========================================================================

@teacher_router.get(
    "/analytics",
    response_model=ClassAnalyticsResponse,
    summary="获取全班学情分析数据",
)
async def get_class_analytics(
    db: DB,
    unit_id: int = Query(..., description="要分析的单元 ID"),
):
    """
    返回指定单元下全班学生的学情汇总数据，供 **TeacherAnalytics** 页面使用。

    响应包含：
    - `task_completion` — 该 unit 下每个 task_driven block 的全班提交情况
    - `dimension_summary` — 从 ai_feedback JSONB 中聚合全班维度均分
    - `students` — 每位学生的进度、AI 均分、未完成任务数
    """
    # 1. 验证 unit 存在
    unit = (await db.execute(select(Unit).where(Unit.id == unit_id))).scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")

    # 2. 获取全班活跃学生数
    all_students = (
        await db.execute(select(User).where(User.role == "student", User.is_active == True))
    ).scalars().all()
    total_students = len(all_students)

    # 3. 查询该 unit 下所有 theme 及其 task_driven blocks
    themes = (
        await db.execute(
            select(Theme)
            .where(Theme.unit_id == unit_id)
            .options(selectinload(Theme.blocks))
        )
    ).scalars().all()

    task_blocks: list[tuple[Block, Theme]] = []
    for theme in themes:
        for block in theme.blocks:
            if block.block_type == "task_driven":
                task_blocks.append((block, theme))

    task_block_ids = [b.id for b, _ in task_blocks]

    # 4. 统计每个 task_driven block 的提交人数 → task_completion
    submitted_counts: dict[int, int] = {}
    if task_block_ids:
        count_rows = (
            await db.execute(
                select(
                    StudentResponse.block_id,
                    func.count(func.distinct(StudentResponse.student_id)),
                )
                .where(StudentResponse.block_id.in_(task_block_ids))
                .group_by(StudentResponse.block_id)
            )
        ).all()
        submitted_counts = {row[0]: row[1] for row in count_rows}

    task_completion = [
        TaskCompletionItem(
            block_id=block.id,
            task_title=block.title or "—",
            theme_title=theme.title,
            theme_type=theme.theme_type,
            submitted_count=submitted_counts.get(block.id, 0),
            total_students=total_students,
        )
        for block, theme in task_blocks
    ]

    # 5. 聚合 dimension_summary：从该 unit 下所有 response 的 ai_feedback 提取
    all_responses = (
        await db.execute(
            select(StudentResponse)
            .where(StudentResponse.block_id.in_(task_block_ids))
        )
    ).scalars().all() if task_block_ids else []

    dimension_scores: dict[str, list[float]] = defaultdict(list)
    for response in all_responses:
        fb = response.ai_feedback
        if not fb or not isinstance(fb, dict):
            continue
        _extract_dimension_scores(fb, dimension_scores)

    dimension_summary = [
        DimensionSummaryItem(
            dimension=dim,
            avg_score=round(sum(scores) / len(scores), 1),
            sample_count=len(scores),
        )
        for dim, scores in sorted(
            dimension_scores.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
        )
    ]

    # 6. 构造 students 列表
    # 查每个学生已提交的 task_driven block_id 集合
    student_submitted: dict[str, set[int]] = defaultdict(set)
    for response in all_responses:
        student_submitted[response.student_id].add(response.block_id)

    # 从 student_stats 获取均分和进度
    stats_rows = (
        await db.execute(
            select(StudentStats).where(StudentStats.unit_id == unit_id)
        )
    ).scalars().all()
    stats_map: dict[str, StudentStats] = {s.student_id: s for s in stats_rows}

    total_task_count = len(task_blocks)
    student_rows: list[StudentAnalyticsRow] = []
    for student in all_students:
        stat = stats_map.get(student.username)
        completed_count = len(student_submitted.get(student.username, set()))
        pending = max(0, total_task_count - completed_count)
        student_rows.append(
            StudentAnalyticsRow(
                student_id=student.username,
                display_name=student.display_name,
                overall_progress=stat.overall_progress if stat else 0,
                avg_ai_score=stat.avg_ai_score if stat else None,
                pending_tasks=pending,
                last_active_at=stat.last_active_at if stat else None,
            )
        )

    return ClassAnalyticsResponse(
        unit_id=unit_id,
        unit_title=unit.title,
        total_students=total_students,
        task_completion=task_completion,
        dimension_summary=dimension_summary,
        students=student_rows,
    )


def _extract_dimension_scores(
    fb: dict, dimension_scores: dict[str, list[float]]
) -> None:
    """从 ai_feedback 中提取维度分数，兼容顶层和按 task_id 嵌套两种结构。"""
    if "dimension_feedback" in fb:
        for d in fb["dimension_feedback"]:
            if isinstance(d, dict) and "dimension" in d and "score" in d:
                dimension_scores[d["dimension"]].append(d["score"])
    else:
        for key, val in fb.items():
            if isinstance(val, dict) and "dimension_feedback" in val:
                for d in val["dimension_feedback"]:
                    if isinstance(d, dict) and "dimension" in d and "score" in d:
                        dimension_scores[d["dimension"]].append(d["score"])


# ===========================================================================
# 学生管理
# ===========================================================================

@teacher_router.get(
    "/students",
    response_model=PaginatedResponse[StudentListItem],
    summary="获取学生账号列表",
)
async def list_students(
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="按姓名或学号模糊搜索"),
):
    """
    分页获取全部学生账号，供 **TeacherStudentManage** 页面使用。
    支持通过 `search` 参数按姓名或学号进行模糊搜索。
    """
    q = select(User).where(User.role == "student").order_by(User.id)
    if search:
        like = f"%{search}%"
        q = q.where(
            (User.username.ilike(like)) | (User.display_name.ilike(like))
        )

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(q.offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    return PaginatedResponse(
        items=[StudentListItem.model_validate(r) for r in rows],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, -(-total // page_size)),
        ),
    )


@teacher_router.post(
    "/students",
    response_model=StudentListItem,
    status_code=status.HTTP_201_CREATED,
    summary="新建学生账号",
)
async def create_student(body: StudentCreate, db: DB):
    """
    教师新建学生账号（添加学生）。
    - `username` 即学号，系统内唯一
    - 密码会以 bcrypt 哈希后存储
    """
    existing = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"学号 {body.username} 已存在",
        )
    user = User(
        username=body.username,
        hashed_password=_hash(body.password),
        display_name=body.display_name,
        role="student",
        class_name=body.class_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return StudentListItem.model_validate(user)


@teacher_router.patch(
    "/students/{student_id}",
    response_model=StudentListItem,
    summary="更新学生信息（姓名 / 班级 / 启用状态）",
)
async def update_student(student_id: str, body: StudentUpdate, db: DB):
    """
    `student_id` 为学号（users.username）。
    可更新姓名、班级、账号启用/禁用状态。
    """
    user = (
        await db.execute(
            select(User).where(User.username ==
                               student_id, User.role == "student")
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="学生不存在")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(user, field, val)
    await db.commit()
    await db.refresh(user)
    return StudentListItem.model_validate(user)


@teacher_router.post(
    "/students/{student_id}/reset-password",
    response_model=MessageResponse,
    summary="重置学生密码",
)
async def reset_student_password(
    student_id: str, body: ChangePasswordRequest, db: DB
):
    """
    教师重置指定学生的登录密码。
    `student_id` 为学号（users.username）。
    """
    user = (
        await db.execute(
            select(User).where(User.username ==
                               student_id, User.role == "student")
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="学生不存在")

    user.hashed_password = _hash(body.new_password)
    await db.commit()
    return MessageResponse(message="密码已重置")


@teacher_router.delete(
    "/students/{student_id}",
    response_model=MessageResponse,
    summary="删除学生账号",
)
async def delete_student(student_id: str, db: DB):
    """
    删除学生账号（硬删除）。
    **注意**：此操作不会级联删除 student_progress / student_responses，
    历史学习记录仍通过 student_id 字符串可查询。
    """
    user = (
        await db.execute(
            select(User).where(User.username ==
                               student_id, User.role == "student")
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="学生不存在")

    await db.delete(user)
    await db.commit()
    return MessageResponse(message="学生账号已删除")


# ===========================================================================
# 学生详情
# ===========================================================================

@teacher_router.get(
    "/students/{student_id}/detail",
    response_model=StudentDetailResponse,
    summary="查看单个学生详情（含提交记录）",
)
async def get_student_detail(
    student_id: str,
    db: DB,
    unit_id: Optional[int] = Query(None, description="过滤到某单元，不传则返回全部"),
):
    """
    供 **TeacherStudentDetail** 页面使用。

    - `profile` — 学生基础信息 + 统计摘要
    - `recent_submissions` — 最近 20 条提交记录（含 AI 评测反馈）
    """
    user = (
        await db.execute(
            select(User).where(User.username ==
                               student_id, User.role == "student")
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 学生统计数据 — 修复 unit_id 过滤条件
    stat_q = select(StudentStats).where(StudentStats.student_id == student_id)
    if unit_id:
        stat_q = stat_q.where(StudentStats.unit_id == unit_id)
    stat = (await db.execute(stat_q)).scalar_one_or_none()

    profile = StudentDetailProfile(
        student_id=student_id,
        display_name=user.display_name,
        class_name=user.class_name,
        total_time_minutes=0,
        completed_tasks=stat.total_submit_count if stat else 0,
        avg_ai_score=stat.avg_ai_score if stat else None,
    )

    # 最近提交记录（带 Block / Theme 信息），按 unit_id 过滤
    resp_q = (
        select(StudentResponse)
        .join(Block, StudentResponse.block_id == Block.id)
        .join(Theme, Block.theme_id == Theme.id)
        .where(StudentResponse.student_id == student_id)
        .options(
            selectinload(StudentResponse.block).selectinload(Block.theme)
        )
        .order_by(StudentResponse.submitted_at.desc())
    )
    if unit_id:
        resp_q = resp_q.where(Theme.unit_id == unit_id)
    resp_q = resp_q.limit(20)
    responses = (await db.execute(resp_q)).scalars().all()

    submissions: list[SubmissionRecord] = []
    for r in responses:
        block: Block = r.block
        theme: Theme = block.theme if block else None
        feedback_text = None
        dim_feedback: list[dict] = []
        suggestions: list[str] = []

        if r.ai_feedback and isinstance(r.ai_feedback, dict):
            fb = r.ai_feedback
            feedback_text = fb.get("overall_comment") or fb.get("feedback") or fb.get("text")
            # 提取 dimension_feedback 和 suggestions，兼容两种结构
            if "dimension_feedback" in fb:
                dim_feedback = fb["dimension_feedback"] if isinstance(fb["dimension_feedback"], list) else []
                suggestions = fb.get("suggestions", []) if isinstance(fb.get("suggestions"), list) else []
            else:
                # 按 task_id 嵌套结构：合并所有子任务的反馈
                for key, val in fb.items():
                    if isinstance(val, dict):
                        if "dimension_feedback" in val and isinstance(val["dimension_feedback"], list):
                            dim_feedback.extend(val["dimension_feedback"])
                        if "suggestions" in val and isinstance(val["suggestions"], list):
                            suggestions.extend(val["suggestions"])

        submissions.append(
            SubmissionRecord(
                response_id=r.id,
                submitted_at=r.submitted_at,
                theme_title=theme.title if theme else "—",
                task_title=block.title or "—" if block else "—",
                student_text=r.response_data.get("text", ""),
                ai_score=r.score,
                ai_feedback=feedback_text,
                dimension_feedback=dim_feedback,
                suggestions=suggestions,
            )
        )

    return StudentDetailResponse(profile=profile, recent_submissions=submissions)
