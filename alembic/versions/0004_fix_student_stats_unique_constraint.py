"""fix_student_stats_unique_constraint

去掉 student_stats.student_id 的 unique 约束，
改为 (student_id, unit_id) 联合唯一约束，
使同一学生可在不同 unit 下各有一行统计数据。

Revision ID: 0004_fix_student_stats_unique
Revises: 0003_refactor_student_progress
Create Date: 2026-03-22
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

# ---------------------------------------------------------------------------
revision = "0004_fix_student_stats_unique"
down_revision = "0003_refactor_student_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 安全地移除 student_id 的单列唯一约束（如果存在）
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'student_stats'::regclass "
            "AND contype = 'u' "
            "AND array_length(conkey, 1) = 1"
        )
    ).fetchall()
    for row in result:
        op.drop_constraint(row[0], "student_stats", type_="unique")

    # 添加 (student_id, unit_id) 联合唯一约束（如果不存在）
    existing = conn.execute(
        text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conrelid = 'student_stats'::regclass "
            "AND conname = 'uq_student_unit_stats'"
        )
    ).fetchone()
    if not existing:
        op.create_unique_constraint(
            "uq_student_unit_stats", "student_stats", ["student_id", "unit_id"]
        )


def downgrade() -> None:
    op.drop_constraint("uq_student_unit_stats", "student_stats", type_="unique")
    op.create_unique_constraint(
        "student_stats_student_id_key", "student_stats", ["student_id"]
    )
