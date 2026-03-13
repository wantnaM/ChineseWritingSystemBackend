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
from app.schemas.schemas import (
    MessageResponse,
    PaginatedResponse, Pagination,
    StudentCreate, StudentUpdate, StudentListItem,
    ClassAnalyticsResponse, ClassOverviewStats, ScoreDistribution,
    StudentAnalyticsRow,
    StudentDetailResponse, StudentDetailProfile, SubmissionRecord,
    ChangePasswordRequest,
)

teacher_router = APIRouter(prefix="/teacher", tags=["教师端 Teacher"])
DB = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# 密码工具（与 auth_routes 保持一致）
# ---------------------------------------------------------------------------
try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def _hash(plain: str) -> str:
        return _pwd_ctx.hash(plain)
except ImportError:
    def _hash(plain: str) -> str:  # type: ignore[misc]
        return plain  # 开发 fallback


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
    - `overview` — 全班总人数、已完成、学习中、进度落后四项统计
    - `score_distribution` — AI 得分分段分布（90-100 / 80-89 / ...）
    - `students` — 每位学生的进度、AI 均分、状态、最后活跃时间
    """
    # 1. 获取单元信息
    unit = (await db.execute(select(Unit).where(Unit.id == unit_id))).scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="单元不存在")

    # 2. 获取所有学生账号（is_active=True）
    all_students = (
        await db.execute(select(User).where(User.role == "student", User.is_active == True))
    ).scalars().all()
    total = len(all_students)

    # 3. 从 student_stats 获取统计数据（按 unit_id 过滤）
    stats_rows = (
        await db.execute(
            select(StudentStats).where(StudentStats.unit_id == unit_id)
        )
    ).scalars().all()
    stats_map: dict[str, StudentStats] = {s.student_id: s for s in stats_rows}

    # 4. 构造学生行列表
    student_rows: list[StudentAnalyticsRow] = []
    completed = learning = behind = 0

    for student in all_students:
        stat = stats_map.get(student.username)
        row_status: str = stat.status if stat else "learning"
        if row_status == "completed":
            completed += 1
        elif row_status == "behind":
            behind += 1
        else:
            learning += 1

        student_rows.append(
            StudentAnalyticsRow(
                student_id=student.username,
                display_name=student.display_name,
                overall_progress=stat.overall_progress if stat else 0,
                avg_ai_score=stat.avg_ai_score if stat else None,
                status=row_status,  # type: ignore[arg-type]
                last_active_at=stat.last_active_at if stat else None,
            )
        )

    overview = ClassOverviewStats(
        total_students=total,
        completed_count=completed,
        learning_count=learning,
        behind_count=behind,
    )

    # 5. 分数段分布（从 StudentStats.avg_ai_score 统计）
    score_ranges = [
        ("90-100", 90, 101),
        ("80-89",  80, 90),
        ("70-79",  70, 80),
        ("60-69",  60, 70),
        ("60以下",  0, 60),
    ]
    all_scores = [s.avg_ai_score for s in stats_rows if s.avg_ai_score is not None]
    distribution: list[ScoreDistribution] = []
    for label, low, high in score_ranges:
        cnt = sum(1 for sc in all_scores if low <= sc < high)
        distribution.append(
            ScoreDistribution(
                range=label,
                count=cnt,
                percentage=round(cnt / len(all_scores) * 100, 1) if all_scores else 0.0,
            )
        )

    return ClassAnalyticsResponse(
        unit_id=unit_id,
        unit_title=unit.title,
        overview=overview,
        score_distribution=distribution,
        students=student_rows,
    )


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
            select(User).where(User.username == student_id, User.role == "student")
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
            select(User).where(User.username == student_id, User.role == "student")
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
            select(User).where(User.username == student_id, User.role == "student")
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
            select(User).where(User.username == student_id, User.role == "student")
        )
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 学生统计数据
    stat = (
        await db.execute(
            select(StudentStats).where(
                StudentStats.student_id == student_id,
                StudentStats.unit_id == unit_id if unit_id else True,
            )
        )
    ).scalar_one_or_none()

    profile = StudentDetailProfile(
        student_id=student_id,
        display_name=user.display_name,
        class_name=user.class_name,
        total_time_minutes=0,  # 可由前端埋点记录后存入 student_stats
        completed_tasks=stat.total_submit_count if stat else 0,
        avg_ai_score=stat.avg_ai_score if stat else None,
    )

    # 最近提交记录（带 Block / Theme 信息）
    resp_q = (
        select(StudentResponse)
        .where(StudentResponse.student_id == student_id)
        .options(
            selectinload(StudentResponse.block).selectinload(Block.theme)
        )
        .order_by(StudentResponse.submitted_at.desc())
        .limit(20)
    )
    responses = (await db.execute(resp_q)).scalars().all()

    submissions: list[SubmissionRecord] = []
    for r in responses:
        block: Block = r.block
        theme: Theme = block.theme if block else None
        feedback_text = None
        if r.ai_feedback and isinstance(r.ai_feedback, dict):
            feedback_text = r.ai_feedback.get("feedback") or r.ai_feedback.get("text")

        submissions.append(
            SubmissionRecord(
                response_id=r.id,
                submitted_at=r.submitted_at,
                theme_title=theme.title if theme else "—",
                task_title=block.title or "—" if block else "—",
                student_text=r.response_data.get("text", ""),
                ai_score=r.score,
                ai_feedback=feedback_text,
            )
        )

    return StudentDetailResponse(profile=profile, recent_submissions=submissions)
