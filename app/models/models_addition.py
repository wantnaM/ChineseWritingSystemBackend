"""
新增 ORM 模型（追加到 app/models/models.py 末尾）

新增三张表:
  - users          : 统一用户表（学生 + 教师）
  - student_stats  : 学生统计快照（AI 均分、总用时、总提交数）
"""

# ---------------------------------------------------------------------------
# User（统一用户表 — 学生 & 教师）
# ---------------------------------------------------------------------------

class User(Base):
    """
    统一账号表。
    role = 'student' → 学生，role = 'teacher' → 教师。
    student_id / teacher_no 与原有业务字段对齐：
      student_id  → StudentProgress.student_id / StudentResponse.student_id
      teacher_no  → 教师工号（前端登录用）
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="登录账号")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="展示姓名")
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="student | teacher"
    )
    class_name: Mapped[Optional[str]] = mapped_column(String(100), comment="班级，仅学生有值")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
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
    """
    __tablename__ = "student_stats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True,
        comment="与 StudentProgress.student_id 对齐"
    )
    unit_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("units.id", ondelete="SET NULL"), nullable=True,
        comment="统计所属单元，NULL 表示全局汇总"
    )
    total_submit_count: Mapped[int] = mapped_column(Integer, default=0, comment="总提交次数")
    avg_ai_score: Mapped[Optional[float]] = mapped_column(comment="AI 平均分（0-100）")
    overall_progress: Mapped[int] = mapped_column(
        Integer, default=0, comment="总体进度百分比（0-100）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="learning",
        comment="completed | learning | behind"
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
