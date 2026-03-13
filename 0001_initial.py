"""
Alembic 数据库迁移脚本
手动生成的初始迁移，创建所有表

运行:
  alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # units
    # ------------------------------------------------------------------
    op.create_table(
        "units",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False, comment="单元标题"),
        sa.Column("description", sa.Text(), nullable=True, comment="单元描述"),
        sa.Column("image_url", sa.String(500), nullable=True, comment="封面图 URL"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # themes
    # ------------------------------------------------------------------
    op.create_table(
        "themes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("theme_type", sa.String(50), nullable=False,
                  comment="themeReading | themeActivity | techniqueLearning"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft",
                  comment="draft | reviewing | published"),
        sa.Column("langgraph_thread_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_themes_unit_id", "themes", ["unit_id"])

    # ------------------------------------------------------------------
    # blocks
    # ------------------------------------------------------------------
    op.create_table(
        "blocks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blocks_theme_id", "blocks", ["theme_id"])

    # ------------------------------------------------------------------
    # badges
    # ------------------------------------------------------------------
    op.create_table(
        "badges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("unit_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(20), nullable=False, server_default="🏅"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # student_progress
    # ------------------------------------------------------------------
    op.create_table(
        "student_progress",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(100), nullable=False),
        sa.Column("theme_id", sa.BigInteger(), nullable=False),
        sa.Column("current_block_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "theme_id", name="uq_student_theme"),
    )
    op.create_index("ix_student_progress_student_id", "student_progress", ["student_id"])

    # ------------------------------------------------------------------
    # student_responses
    # ------------------------------------------------------------------
    op.create_table(
        "student_responses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(100), nullable=False),
        sa.Column("block_id", sa.BigInteger(), nullable=False),
        sa.Column("response_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_responses_student_id", "student_responses", ["student_id"])

    # ------------------------------------------------------------------
    # student_badges
    # ------------------------------------------------------------------
    op.create_table(
        "student_badges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.String(100), nullable=False),
        sa.Column("badge_id", sa.BigInteger(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),
    )
    op.create_index("ix_student_badges_student_id", "student_badges", ["student_id"])


def downgrade() -> None:
    op.drop_table("student_badges")
    op.drop_table("student_responses")
    op.drop_table("student_progress")
    op.drop_table("badges")
    op.drop_table("blocks")
    op.drop_table("themes")
    op.drop_table("units")
