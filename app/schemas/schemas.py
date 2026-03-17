"""
Pydantic v2 Schemas — 前后端 API 数据契约

命名规范:
  XxxBase     - 公共字段
  XxxCreate   - 创建请求体
  XxxUpdate   - 更新请求体（全部字段 Optional）
  XxxRead     - 响应体（含 id、时间戳等）
  XxxDetail   - 含嵌套子资源的完整响应

【v2 变更】
  - BlockBase / BlockUpdate：删除 is_required 字段
  - StudentProgressRead：删除 current_block_order 字段
  - StudentProgressUpdate：整体删除（进度由后端自动判定，前端无需手动 PATCH）
  - SubmitResponseResult：新增，submit_response 响应中附带 theme_completed 字段
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ===========================================================================
# Block Schemas
# ===========================================================================

class BlockBase(BaseModel):
    block_type: str = Field(
        ...,
        description="前端 BlockType，如 description | reading_guide | task_driven | ..."
    )
    title: Optional[str] = None
    sort_order: int = 0
    config_json: dict[str, Any] = Field(
        ..., description="前端渲染所需的完整 JSON 配置，与前端 ThemeBlock 接口结构对齐"
    )
    # is_required 已删除（迁移 0003）


class BlockCreate(BlockBase):
    theme_id: int


class BlockUpdate(BaseModel):
    title: Optional[str] = None
    sort_order: Optional[int] = None
    config_json: Optional[dict[str, Any]] = None
    # is_required 已删除（迁移 0003）


class BlockRead(BlockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    theme_id: int
    created_at: datetime
    updated_at: datetime


# ===========================================================================
# Theme Schemas
# ===========================================================================

ThemeType = Literal["themeReading", "themeActivity", "techniqueLearning"]
ThemeStatus = Literal["draft", "reviewing", "published"]


class ThemeBase(BaseModel):
    title: str
    description: Optional[str] = None
    theme_type: ThemeType
    sort_order: int = 0
    is_published: bool = False


class ThemeCreate(ThemeBase):
    unit_id: int


class ThemeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    theme_type: Optional[ThemeType] = None
    sort_order: Optional[int] = None
    is_published: Optional[bool] = None
    status: Optional[ThemeStatus] = None


class ThemeRead(ThemeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    status: ThemeStatus
    langgraph_thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ThemeDetail(ThemeRead):
    """含完整 Block 列表的主题详情。"""
    blocks: list[BlockRead] = []


# ===========================================================================
# Unit Schemas
# ===========================================================================

class UnitBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_published: bool = False


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None
    is_published: Optional[bool] = None


class UnitRead(UnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    themes_count: int = 0
    themes: list["ThemeRead"] = []


class UnitDetail(UnitRead):
    """含完整主题列表（每个主题含 Blocks）的单元详情。"""
    themes: list[ThemeDetail] = []


# ===========================================================================
# Student Progress Schemas
# ===========================================================================

class StudentProgressRead(BaseModel):
    """
    【v2】移除 current_block_order，进度现在仅关注主题是否完成。
    is_completed 由后端在 submit_response 时自动判定。
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    theme_id: int
    # current_block_order 已删除（迁移 0003）
    is_completed: bool
    completed_at: Optional[datetime] = None
    updated_at: datetime


# StudentProgressUpdate 已删除：
#   前端不再需要手动 PATCH /student/progress。
#   进度由 POST /student/responses 提交后后端自动判定。


# ===========================================================================
# Student Response Schemas
# ===========================================================================

class StudentResponseCreate(BaseModel):
    """学生提交某 Block 的作答。"""
    student_id: str
    block_id: int
    response_data: dict[str, Any] = Field(
        ...,
        description="作答内容，如 {text: '...', images: ['url1', ...]}"
    )


class StudentResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    block_id: int
    response_data: dict[str, Any]
    ai_feedback: Optional[dict[str, Any]] = None
    score: Optional[int] = None
    submitted_at: datetime


class SubmitResponseResult(StudentResponseRead):
    """
    POST /student/responses 的响应体。

    在标准 StudentResponseRead 基础上，附加 theme_completed 字段：
      - True  → 本次提交后该主题下所有 task_driven Block 均已完成，前端可触发完成动画
      - False → 仍有未完成的任务组件
    """
    theme_completed: bool = False


# ===========================================================================
# Evaluator Payload
# ===========================================================================

class EvaluatorPayload(BaseModel):
    """POST /api/v1/student/evaluate 请求体。"""
    student_id: str
    block_id: int
    theme_id: int
    task_id: Optional[str] = Field(     # ← 新增
        default=None,
        description="对应的 task.id，用于按子任务存储 AI 反馈"
    )
    component_type: str = Field(
        default="TaskDriven",
        description="对应前端组件类型，决定评测策略"
    )
    student_text: str = Field(..., description="学生写作内容")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="评测上下文，如 {instruction, evaluator_focus, reference_text}"
    )


class EvaluatorResponse(BaseModel):
    """POST /api/v1/student/evaluate 响应体。"""
    feedback: str = Field(..., description="AI 评测反馈文本")


# ===========================================================================
# Badge Schemas
# ===========================================================================

class BadgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: Optional[int] = None
    name: str
    icon: str
    description: Optional[str] = None
    earned: bool = False  # 由业务层注入，非 DB 字段


class StudentBadgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    badge_id: int
    earned_at: datetime
    badge: BadgeRead


# ===========================================================================
# Common Response Wrappers
# ===========================================================================

class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PaginatedResponse[T](BaseModel):
    items: list[T]
    pagination: Pagination


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ===========================================================================
# Auth Schemas
# ===========================================================================

class LoginRequest(BaseModel):
    """POST /api/v1/auth/login"""
    username: str = Field(..., description="学号（学生）或工号（教师）")
    password: str
    role: Literal["student", "teacher"]


class TokenResponse(BaseModel):
    """登录成功后返回的 JWT 令牌。"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="有效期（秒）")
    user: "UserRead"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: Literal["student", "teacher"]
    class_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None


class ChangePasswordRequest(BaseModel):
    """教师为学生重置密码 / 学生修改自身密码。"""
    new_password: str = Field(..., min_length=6)


# ===========================================================================
# User Management (Teacher side)
# ===========================================================================

class StudentCreate(BaseModel):
    """教师新建学生账号。"""
    username: str = Field(..., description="学号，系统内唯一")
    display_name: str = Field(..., description="姓名")
    password: str = Field(..., min_length=6)
    class_name: Optional[str] = None


class StudentUpdate(BaseModel):
    """教师更新学生基础信息。"""
    display_name: Optional[str] = None
    class_name: Optional[str] = None
    is_active: Optional[bool] = None


class StudentListItem(BaseModel):
    """学生管理列表行数据（TeacherStudentManage 页面）。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    class_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None


# ===========================================================================
# Analytics Schemas（学情分析）
# ===========================================================================

class ClassOverviewStats(BaseModel):
    """全班概况统计卡片（TeacherAnalytics 页面顶部 4 张卡片）。"""
    total_students: int
    completed_count: int
    learning_count: int
    behind_count: int


class ScoreDistribution(BaseModel):
    """分数段分布（用于柱状图）。"""
    range: str
    count: int
    percentage: float


class StudentAnalyticsRow(BaseModel):
    """学情分析列表中每行学生的数据（TeacherAnalytics 页面表格）。"""
    student_id: str
    display_name: str
    overall_progress: int
    avg_ai_score: Optional[float] = None
    status: Literal["completed", "learning", "behind"]
    last_active_at: Optional[datetime] = None


class ClassAnalyticsResponse(BaseModel):
    """GET /api/v1/teacher/analytics?unit_id= 完整学情分析响应体。"""
    unit_id: int
    unit_title: str
    overview: ClassOverviewStats
    score_distribution: list[ScoreDistribution]
    students: list[StudentAnalyticsRow]


# ===========================================================================
# Student Detail（TeacherStudentDetail 页面）
# ===========================================================================

class StudentDetailProfile(BaseModel):
    student_id: str
    display_name: str
    class_name: Optional[str] = None
    total_time_minutes: int = Field(..., description="总学习时长（分钟）")
    completed_tasks: int
    avg_ai_score: Optional[float] = None


class SubmissionRecord(BaseModel):
    response_id: int
    submitted_at: datetime
    theme_title: str
    task_title: str
    student_text: str
    ai_score: Optional[int] = None
    ai_feedback: Optional[str] = None


class StudentDetailResponse(BaseModel):
    """GET /api/v1/teacher/students/{student_id}/detail"""
    profile: StudentDetailProfile
    recent_submissions: list[SubmissionRecord]
