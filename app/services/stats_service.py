"""
学生统计数据自动刷新服务。

在学生提交作答后调用 refresh_student_stats，
自动更新该学生在对应 unit 下的 student_stats 行。
"""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.models import (
    Block, Theme, StudentResponse, StudentStats,
)


async def refresh_student_stats(
    db: AsyncSession, student_id: str, unit_id: int
) -> None:
    """
    在学生提交作答后调用，更新该学生在该 unit 下的统计数据。

    计算逻辑：
    1. 查询该 unit 下所有 theme
    2. 每个 theme 下所有 block_type='task_driven' 的 block → total_task_blocks
    3. 查询该学生对这些 block 的 distinct response 数量 → completed_task_blocks
    4. progress = completed_task_blocks / total_task_blocks * 100
    5. 查询该学生在这些 block 下所有 response 的 score，计算均值 → avg_score
    6. status = "completed" if progress == 100 else "learning"
    7. UPSERT 到 student_stats 表
    """
    # 1-2. 获取该 unit 下所有 task_driven block ids
    task_block_ids_result = (
        await db.execute(
            select(Block.id)
            .join(Theme, Block.theme_id == Theme.id)
            .where(
                Theme.unit_id == unit_id,
                Block.block_type == "task_driven",
            )
        )
    ).scalars().all()
    task_block_ids = set(task_block_ids_result)
    total_task_blocks = len(task_block_ids)

    if total_task_blocks == 0:
        progress = 0
        avg_score = None
        submit_count = 0
    else:
        # 3. 该学生已提交的 distinct task_driven block 数量
        completed_blocks_result = (
            await db.execute(
                select(func.count(func.distinct(StudentResponse.block_id)))
                .where(
                    StudentResponse.student_id == student_id,
                    StudentResponse.block_id.in_(task_block_ids),
                )
            )
        ).scalar_one()
        completed_task_blocks = completed_blocks_result or 0

        # 4. progress
        progress = round(completed_task_blocks / total_task_blocks * 100)

        # 5. 该学生在这些 block 下所有 response 的 score 均值
        score_result = (
            await db.execute(
                select(func.avg(StudentResponse.score))
                .where(
                    StudentResponse.student_id == student_id,
                    StudentResponse.block_id.in_(task_block_ids),
                    StudentResponse.score.isnot(None),
                )
            )
        ).scalar_one()
        avg_score = round(float(score_result), 1) if score_result is not None else None

        # 提交总数
        submit_count_result = (
            await db.execute(
                select(func.count())
                .where(
                    StudentResponse.student_id == student_id,
                    StudentResponse.block_id.in_(task_block_ids),
                )
            )
        ).scalar_one()
        submit_count = submit_count_result or 0

    # 6. status
    status = "completed" if progress == 100 else "learning"
    now = datetime.now(timezone.utc)

    # 7. UPSERT
    stmt = pg_insert(StudentStats).values(
        student_id=student_id,
        unit_id=unit_id,
        total_submit_count=submit_count,
        avg_ai_score=avg_score,
        overall_progress=progress,
        status=status,
        last_active_at=now,
        updated_at=now,
    )
    stmt = stmt.on_conflict_on_constraint("uq_student_unit_stats").do_update(
        set_={
            "total_submit_count": stmt.excluded.total_submit_count,
            "avg_ai_score": stmt.excluded.avg_ai_score,
            "overall_progress": stmt.excluded.overall_progress,
            "status": stmt.excluded.status,
            "last_active_at": stmt.excluded.last_active_at,
            "updated_at": stmt.excluded.updated_at,
        }
    )
    await db.execute(stmt)
    await db.commit()
