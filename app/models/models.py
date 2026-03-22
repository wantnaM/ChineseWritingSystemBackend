"""
数据库 ORM 模型
数据库: PostgreSQL
ORM: SQLAlchemy 2.x (Mapped / mapped_column 风格)

表关系:
  Unit (单元)
    └── Theme (主题, 1个单元包含多个主题)
          └── Block (内容块, 1个主题包含多个 Block)

其他独立表:
  StudentProgress  - 学生在主题中的完成状态
                     【v2】移除 current_block_order / is_required：
                     所有 Block 全部展示，当主题下全部 task_driven Block
                     均有提交记录时，由后端自动将 is_completed 置为 True。
  StudentResponse  - 学生在 Block 中的答题/作答记录（是判定完成的核心数据）
  Badge            - 徽章定义
  StudentBadge     - 学生已获得的徽章
  User             - 统一用户表（学生 + 教师）
  StudentStats     - 学生统计快照（AI 均分、总用时、总提交数）
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Unit（单元）
# ---------------------------------------------------------------------------

class Unit(Base):
    """
    顶层学习单元，例如"亲近自然"。
    一个单元可以包含多个主题（Theme）。
    """
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="单元标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="单元描述")
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500), comment="封面图 URL")
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="排序权重，越小越靠前")
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否发布")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    themes: Mapped[list["Theme"]] = relationship(
        "Theme", back_populates="unit", cascade="all, delete-orphan",
        order_by="Theme.sort_order"
    )
    badges: Mapped[list["Badge"]] = relationship(
        "Badge", back_populates="unit")

    def __repr__(self) -> str:
        return f"<Unit id={self.id} title={self.title!r}>"


# ---------------------------------------------------------------------------
# Theme（主题）
# ---------------------------------------------------------------------------

THEME_TYPE_CHOICES = ("themeReading", "themeActivity", "techniqueLearning")


class Theme(Base):
    """
    单元下的主题，例如"主题阅读"、"主题活动"、"技法学习"。
    一个主题包含多个 Block（内容块）。
    """
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="主题标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="主题描述")
    theme_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="类型: themeReading | themeActivity | techniqueLearning"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="在单元内的排序")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft",
        comment="draft | reviewing | published"
    )
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="themes")
    blocks: Mapped[list["Block"]] = relationship(
        "Block", back_populates="theme", cascade="all, delete-orphan",
        order_by="Block.sort_order"
    )
    student_progress: Mapped[list["StudentProgress"]] = relationship(
        "StudentProgress", back_populates="theme"
    )

    def __repr__(self) -> str:
        return f"<Theme id={self.id} type={self.theme_type!r} title={self.title!r}>"


# ---------------------------------------------------------------------------
# Block（内容块）
# ---------------------------------------------------------------------------

BLOCK_TYPE_CHOICES = (
    "description",
    "reading_guide",
    "task_driven",           # ← 唯一计入"主题完成"判定的类型
    "reading_recommendation",
    "appreciation_list",
    "knowledge_card",
    "evaluation_table",
    "markdown",
    "editable_table",
)


class Block(Base):
    """
    主题下的内容块（Schema-Driven UI 的最小渲染单元）。
    config_json 存储该 Block 的完整 JSON 配置，由前端渲染引擎解析。

    【v2 变更】
    - 删除 is_required 字段：所有 Block 全部直接展示，不再逐步解锁。
    - block_type == 'task_driven' 的 Block 是学生需要提交作答的任务组件，
      当一个主题下所有 task_driven Block 均有 student_responses 记录时，
      该主题自动标记为完成。
    """
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    block_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="对应前端 BlockType: description | reading_guide | task_driven | ..."
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200), comment="Block 标题（冗余字段，方便列表展示）")
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="在主题内的渲染顺序")
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="前端渲染所需的完整 JSON 配置"
    )
    # is_required 已删除（迁移 0003）
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    theme: Mapped["Theme"] = relationship("Theme", back_populates="blocks")
    student_responses: Mapped[list["StudentResponse"]] = relationship(
        "StudentResponse", back_populates="block"
    )

    def __repr__(self) -> str:
        return f"<Block id={self.id} type={self.block_type!r} order={self.sort_order}>"


# ---------------------------------------------------------------------------
# StudentProgress（学生主题完成状态）
# ---------------------------------------------------------------------------

class StudentProgress(Base):
    """
    记录学生在某个主题（Theme）下的完成状态。

    【v2 变更】
    - 删除 current_block_order：不再有"解锁到第几步"的概念。
    - is_completed 由后端在 submit_response 时自动判定：
      当该主题下所有 block_type='task_driven' 的 Block 均存在
      对应 student_responses 记录时，自动置 True 并记录 completed_at。
    """
    __tablename__ = "student_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "theme_id", name="uq_student_theme"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="主题下所有 task_driven Block 均已提交时自动置 True"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    theme: Mapped["Theme"] = relationship(
        "Theme", back_populates="student_progress")


# ---------------------------------------------------------------------------
# StudentResponse（学生答题记录）
# ---------------------------------------------------------------------------

class StudentResponse(Base):
    """
    学生在某个 Block 中的具体作答/提交记录。
    response_data 存储学生输入（文本、图片 URL、选项等）。
    ai_feedback 存储 Evaluator Agent 返回的批改反馈。

    这张表同时是"主题完成"判定的数据来源：
    对某个 task_driven Block 只要存在任意一条该学生的记录，即视为已完成。
    """
    __tablename__ = "student_responses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False
    )
    response_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="作答内容，如 {text: '...', images: ['url1', ...]}"
    )
    ai_feedback: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, comment="Evaluator Agent 输出的批改反馈")
    score: Mapped[Optional[int]] = mapped_column(
        Integer, comment="AI 打分（0-100，可选）")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    # relationships
    block: Mapped["Block"] = relationship(
        "Block", back_populates="student_responses")


# ---------------------------------------------------------------------------
# Badge / StudentBadge（徽章）
# ---------------------------------------------------------------------------

class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    unit_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="🏅",
        comment="Emoji 图标"
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, comment="获取条件，如 {type: 'complete_unit', unit_id: 1}")

    # relationships
    unit: Mapped[Optional["Unit"]] = relationship(
        "Unit", back_populates="badges")


class StudentBadge(Base):
    __tablename__ = "student_badges"
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    badge_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    # relationships
    badge: Mapped["Badge"] = relationship("Badge")


# ---------------------------------------------------------------------------
# User（统一用户表）
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, comment="登录账号")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="展示姓名")
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="student | teacher"
    )
    class_name: Mapped[Optional[str]] = mapped_column(
        String(100), comment="班级，仅学生有值")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# StudentStats（学生统计快照）
# ---------------------------------------------------------------------------

class StudentStats(Base):
    """
    学生维度的统计汇总（由后台任务定期更新，或在提交时触发更新）。
    student_id 与 users.username 对齐（均使用学号字符串）。
    一个学生在不同 unit 下各有一行统计数据。
    """
    __tablename__ = "student_stats"
    __table_args__ = (
        UniqueConstraint("student_id", "unit_id", name="uq_student_unit_stats"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="与 StudentProgress.student_id 对齐"
    )
    unit_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="SET NULL"), nullable=True,
        comment="统计所属单元，NULL 表示全局汇总"
    )
    total_submit_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="总提交次数")
    avg_ai_score: Mapped[Optional[float]] = mapped_column(
        comment="AI 平均分（0-100）")
    overall_progress: Mapped[int] = mapped_column(
        Integer, default=0, comment="总体进度百分比（0-100）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="learning",
        comment="completed | learning | behind"
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
