"""
新增 Pydantic v2 Schemas（追加到 app/schemas/schemas.py）

涵盖:
  - 认证 (Auth)
  - 用户管理 (User / Teacher-side)
  - 学情分析 (Analytics)
  - 学生管理 (StudentManage)
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


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
