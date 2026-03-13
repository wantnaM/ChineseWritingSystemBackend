"""
Pydantic v2 Schemas — 前后端 API 数据契约

命名规范:
  XxxBase     - 公共字段
  XxxCreate   - 创建请求体
  XxxUpdate   - 更新请求体（全部字段 Optional）
  XxxRead     - 响应体（含 id、时间戳等）
  XxxDetail   - 含嵌套子资源的完整响应

涵盖:
  - 认证 (Auth)
  - 用户管理 (User / Teacher-side)
  - 学情分析 (Analytics)
  - 学生管理 (StudentManage)
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
    is_required: bool = True


class BlockCreate(BlockBase):
    pass


class BlockUpdate(BaseModel):
    title: Optional[str] = None
    sort_order: Optional[int] = None
    config_json: Optional[dict[str, Any]] = None
    is_required: Optional[bool] = None


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
    pass


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


class UnitDetail(UnitRead):
    """含完整主题列表（每个主题含 Blocks）的单元详情。"""
    themes: list[ThemeDetail] = []


# ===========================================================================
# Student Progress Schemas
# ===========================================================================

class StudentProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: str
    theme_id: int
    current_block_order: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    updated_at: datetime


class StudentProgressUpdate(BaseModel):
    """学生完成一个 Block 后，前端调用此接口推进步骤。"""
    current_block_order: int
    is_completed: bool = False


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


# ===========================================================================
# WebSocket Evaluator Payload
# ===========================================================================

class EvaluatorWSPayload(BaseModel):
    """学生端 WebSocket 发送给 Evaluator Agent 的请求体。"""
    student_id: str
    theme_id: int
    block_id: int
    current_step: int
    component_type: str
    student_text: str
    context: dict[str, Any] = Field(
        ...,
        description="包含 instruction、evaluator_focus 等评改上下文"
    )


class EvaluatorWSResponse(BaseModel):
    """Evaluator Agent 返回给前端的流式片段。"""
    type: Literal["delta", "done", "error"]
    content: str = ""


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
    username: str          # 学号
    display_name: str      # 姓名
    class_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None


# ===========================================================================
# Analytics Schemas（学情分析）
# ===========================================================================

class ClassOverviewStats(BaseModel):
    """全班概况统计卡片（TeacherAnalytics 页面顶部 4 张卡片）。"""
    total_students: int
    completed_count: int      # 已完成全部任务
    learning_count: int       # 学习中
    behind_count: int         # 进度落后


class ScoreDistribution(BaseModel):
    """分数段分布（用于柱状图）。"""
    range: str                # 如 "90-100"
    count: int
    percentage: float


class StudentAnalyticsRow(BaseModel):
    """学情分析列表中每行学生的数据（TeacherAnalytics 页面表格）。"""
    student_id: str           # 学号
    display_name: str         # 姓名
    overall_progress: int     # 0-100
    avg_ai_score: Optional[float] = None
    status: Literal["completed", "learning", "behind"]
    last_active_at: Optional[datetime] = None


class ClassAnalyticsResponse(BaseModel):
    """
    GET /api/v1/teacher/analytics?unit_id=
    完整学情分析响应体。
    """
    unit_id: int
    unit_title: str
    overview: ClassOverviewStats
    score_distribution: list[ScoreDistribution]
    students: list[StudentAnalyticsRow]


# ===========================================================================
# Student Detail（TeacherStudentDetail 页面）
# ===========================================================================

class StudentDetailProfile(BaseModel):
    """学生详情页头部信息。"""
    student_id: str
    display_name: str
    class_name: Optional[str] = None
    total_time_minutes: int = Field(..., description="总学习时长（分钟）")
    completed_tasks: int
    avg_ai_score: Optional[float] = None


class SubmissionRecord(BaseModel):
    """学生历史提交记录（TeacherStudentDetail 列表项）。"""
    response_id: int
    submitted_at: datetime
    theme_title: str
    task_title: str
    student_text: str
    ai_score: Optional[int] = None
    ai_feedback: Optional[str] = None


class StudentDetailResponse(BaseModel):
    """
    GET /api/v1/teacher/students/{student_id}/detail
    """
    profile: StudentDetailProfile
    recent_submissions: list[SubmissionRecord]
