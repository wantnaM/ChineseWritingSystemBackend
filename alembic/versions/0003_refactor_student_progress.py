"""refactor student_progress: 移除 current_block_order / block.is_required，
   进度改由 submit_response 自动判定

Revision ID: 0003_refactor_student_progress
Revises: d92bc82eadb5
Create Date: 2026-03-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
revision = "0003_refactor_student_progress"
down_revision = "d92bc82eadb5"   # 指向上一条迁移的 revision id
branch_labels = None
depends_on = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. student_progress：删除 current_block_order 字段
    # ------------------------------------------------------------------
    op.drop_column("student_progress", "current_block_order")

    # ------------------------------------------------------------------
    # 2. blocks：删除 is_required 字段
    #    （全部 Block 现在都直接展示，task_driven 完成即计入进度）
    # ------------------------------------------------------------------
    op.drop_column("blocks", "is_required")


def downgrade() -> None:
    # 回滚：补回被删除的列（恢复原始默认值）
    op.add_column(
        "blocks",
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.add_column(
        "student_progress",
        sa.Column(
            "current_block_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="当前步骤索引（已废弃，仅用于回滚兼容）",
        ),
    )
