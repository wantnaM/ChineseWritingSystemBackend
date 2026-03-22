# CLAUDE.md

## Project Overview

语文一体化写作学习系统后端 — AI 驱动的个性化支架式语文教学平台。

- **框架**: FastAPI + SQLAlchemy 2.x (async) + PostgreSQL + Alembic
- **Python**: >= 3.11
- **包管理**: pip + requirements.txt, 虚拟环境在 `.venv/`

## Quick Start

```bash
# 激活虚拟环境
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn main:app --reload --port 8000
```

## Project Structure

```
app/
├── core/config.py          # 环境变量配置 (pydantic-settings)
├── db/session.py           # 异步数据库会话
├── models/models.py        # ORM 模型 (Unit/Theme/Block/User/StudentStats/...)
├── schemas/schemas.py      # Pydantic v2 请求/响应 Schema
├── api/
│   ├── routes.py           # 课程内容 CRUD + 学生端路由 (api_router)
│   ├── teacher_routes.py   # 教师端: 学情分析 + 学生管理 (teacher_router)
│   └── auth_routes.py      # JWT 认证 (auth_router)
├── services/
│   └── stats_service.py    # 学生统计自动刷新 (UPSERT student_stats)
└── agents/
    ├── evaluator_agent.py  # AI 写作评测 (Anthropic API)
    └── chat_agent.py       # AI 伴学聊天 (Kimi/Moonshot API)

alembic/versions/           # 数据库迁移脚本
main.py                     # FastAPI 应用入口
```

## Key Conventions

### Database & ORM
- 使用 SQLAlchemy 2.x `Mapped` / `mapped_column` 风格
- 数据库连接使用 `asyncpg` 异步驱动
- 所有数据库操作通过 `AsyncSession` (依赖注入 `get_session`)
- 迁移使用 Alembic: `alembic revision --autogenerate -m "description"` + `alembic upgrade head`

### API Design
- 所有路由注册在 `/api/v1/` 前缀下
- 路由分三个 router: `api_router` (routes.py), `teacher_router` (teacher_routes.py), `auth_router` (auth_routes.py)
- 响应 Schema 遵循 `XxxBase → XxxCreate / XxxUpdate / XxxRead` 命名规范
- 分页使用 `PaginatedResponse[T]` 通用泛型

### Business Logic
- `student_id` 使用学号字符串 (对应 `users.username`)，非数据库自增 ID
- 学生提交作答 (`POST /student/responses`) 后自动触发:
  1. 主题完成判定 (`_check_and_complete_theme`)
  2. 统计数据刷新 (`refresh_student_stats`)
- `student_stats` 表按 `(student_id, unit_id)` 联合唯一约束，支持同一学生多单元各有统计行
- `ai_feedback` JSONB 字段有两种结构: 顶层 `dimension_feedback` 或按 `task_id` 嵌套，代码需兼容两种

### Authentication
- JWT 认证，密码使用 bcrypt 哈希
- 用户表 `users` 区分 `role`: "student" | "teacher"

### Environment Variables
- 配置在 `.env` 文件 (不提交 Git)
- 通过 `app/core/config.py` 的 `Settings` 类读取
- 关键变量: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `KIMI_API_KEY`, `JWT_SECRET`

## Common Tasks

```bash
# 查看 API 文档
open http://localhost:8000/docs

# 创建新迁移
alembic revision --autogenerate -m "描述"

# 回滚迁移
alembic downgrade -1

# 查看迁移状态
alembic current
```
