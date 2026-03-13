"""
数据库 ORM 模型
数据库: PostgreSQL
ORM: SQLAlchemy 2.x (Mapped / mapped_column 风格)

表关系:
  Unit (单元)
    └── Theme (主题, 1个单元包含多个主题)
          └── Block (内容块, 1个主题包含多个 Block)

其他独立表:
  StudentProgress  - 学生在主题中的进度
  StudentResponse  - 学生在 Block 中的答题/作答记录
  Badge            - 徽章定义
  StudentBadge     - 学生已获得的徽章
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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="单元标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="单元描述")
    image_url: Mapped[Optional[str]] = mapped_column(String(500), comment="封面图 URL")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序权重，越小越靠前")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否发布")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    themes: Mapped[list["Theme"]] = relationship(
        "Theme", back_populates="unit", cascade="all, delete-orphan", order_by="Theme.sort_order"
    )
    badges: Mapped[list["Badge"]] = relationship("Badge", back_populates="unit")

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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="主题标题")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="主题描述")
    theme_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="类型: themeReading | themeActivity | techniqueLearning"
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="在单元内的排序")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    # AI 生成后，教师微调前为 draft，发布后为 published
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="draft | reviewing | published"
    )
    # LangGraph thread_id，用于暂停/恢复 Human-in-the-loop
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    unit: Mapped["Unit"] = relationship("Unit", back_populates="themes")
    blocks: Mapped[list["Block"]] = relationship(
        "Block", back_populates="theme", cascade="all, delete-orphan", order_by="Block.sort_order"
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
    "task_driven",
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

    Block 是系统的核心数据结构：
      - 教师可在低代码编辑器中修改 config_json
      - 学生按 sort_order 逐步解锁
    """
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="对应前端 BlockType: description | reading_guide | task_driven | ..."
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), comment="Block 标题（冗余字段，方便列表展示）")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="在主题内的渲染顺序")
    # 完整的前端渲染配置，结构与前端 ThemeBlock 接口完全一致
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, comment="前端渲染所需的完整 JSON 配置"
    )
    # 学生是否必须完成此 Block 才能解锁下一个
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
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
# StudentProgress（学生进度）
# ---------------------------------------------------------------------------

class StudentProgress(Base):
    """
    记录学生在某个主题（Theme）下的整体进度。
    current_block_order 表示学生当前解锁到第几个 Block。
    """
    __tablename__ = "student_progress"
    __table_args__ = (
        UniqueConstraint("student_id", "theme_id", name="uq_student_theme"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    current_block_order: Mapped[int] = mapped_column(Integer, default=0, comment="当前步骤索引")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    theme: Mapped["Theme"] = relationship("Theme", back_populates="student_progress")


# ---------------------------------------------------------------------------
# StudentResponse（学生答题记录）
# ---------------------------------------------------------------------------

class StudentResponse(Base):
    """
    学生在某个 Block 中的具体作答/提交记录。
    response_data 存储学生输入（文本、图片 URL、选项等）。
    ai_feedback 存储 Evaluator Agent 返回的批改反馈。
    """
    __tablename__ = "student_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("blocks.id", ondelete="CASCADE"), nullable=False
    )
    # 学生提交的内容（支持文本、图片列表等多种结构）
    response_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # AI 批改反馈（Evaluator Agent 输出）
    ai_feedback: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    score: Mapped[Optional[int]] = mapped_column(Integer, comment="AI 打分（可选）")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    block: Mapped["Block"] = relationship("Block", back_populates="student_responses")


# ---------------------------------------------------------------------------
# Badge（徽章）
# ---------------------------------------------------------------------------

class Badge(Base):
    """徽章定义，关联到某个单元。"""
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    unit_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(20), default="🏅", comment="Emoji 图标")
    description: Mapped[Optional[str]] = mapped_column(Text)
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, comment="获取条件，如 {type: 'complete_unit', unit_id: 1}"
    )

    # relationships
    unit: Mapped[Optional["Unit"]] = relationship("Unit", back_populates="badges")
    student_badges: Mapped[list["StudentBadge"]] = relationship("StudentBadge", back_populates="badge")


class StudentBadge(Base):
    """学生已获得的徽章。"""
    __tablename__ = "student_badges"
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_student_badge"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    badge_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False
    )
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationships
    badge: Mapped["Badge"] = relationship("Badge", back_populates="student_badges")
