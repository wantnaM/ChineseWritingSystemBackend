# 📖 语文一体化写作学习系统 · 后端

> AI 驱动的个性化支架式语文教学平台 —— 将静态教辅材料转化为沉浸式互动学习体验。

---

## 目录

- [系统描述与核心理念](#一、系统描述与核心理念)
- [整体架构](#二、整体架构)
- [运行流程](#三、运行流程)
- [项目工程目录树](#四、项目工程目录树)
- [开发运行步骤](#五、开发运行步骤)
- [API 接口概览](#六、api-接口概览)

---

## 一、系统描述与核心理念

### 系统定位

本系统是一个面向中学语文教学的 **AI 驱动个性化支架式学习平台**。核心目标是将教师编写的教学内容，转化为结构清晰、交互丰富的沉浸式学习页面，实现"以读促写"的语文学习闭环。

系统分为**教师端**与**学生端**两个视角：

- **教师端**：编排单元、主题与内容块，安排课时计划，发布给学生；查看全班学情分析与维度报告；管理学生账号
- **学生端**：按主题浏览学习内容，完成任务，提交作答，获得 AI 写作评测反馈；与 AI 伴学助手对话

---

### 三大核心设计理念

#### 1. 以读促写（Reading-to-Writing）

建立"**感知与沉浸 → 技法拆解 → 片段练习 → 整体建构**"的四阶段标准教学路径。每个单元围绕三类主题组织内容：

| 主题类型 | 说明 |
|---|---|
| 📖 主题阅读 | 品读名家美文，赏析文学经典，建立语感 |
| 🎯 主题活动 | 综合实践任务，将阅读所得转化为真实产出 |
| ✍️ 技法学习 | 聚焦具体写作技法，通过练习巩固内化 |

#### 2. Schema-Driven UI（模式驱动界面）

前端**不硬编码页面内容**。所有教学内容通过后端返回的 Block JSON 配置动态渲染。`BlockRenderer` 组件根据 `block_type` 字段映射到对应的 React 交互组件，实现内容与界面的彻底解耦。

```
后端 JSON config  →  BlockRenderer  →  对应 React 组件
{ type: "task_driven", ... }  →  <TaskDrivenBlock />
{ type: "reading_guide", ... }  →  <ReadingGuideBlock />
```

#### 3. 任务驱动的主题完成判定（Task-Driven Completion）

系统不采用步进解锁机制，而采用**任务完成度判定**：

- 学生可自由浏览同一主题下的所有内容
- 教师可灵活安排课时（如第一课学"名著导读"+ "主题活动一"，第二课学"美文赏析"）
- **当一个主题下所有 `task_driven` 类型 Block 的任务均已提交，后端自动判定该主题完成**

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端 (React + Vite)                     │
│                                                                   │
│  ┌──────────────┐        ┌──────────────────────────────────┐   │
│  │  教师端视图   │        │           学生端视图              │   │
│  │  学情分析    │        │                                   │   │
│  │              │        │  Home → LessonList → Theme Page  │   │
│  └──────────────┘        │  ↓                               │   │
│                           │  BlockRenderer                   │   │
│                           │  ↓ 根据 block_type 映射          │   │
│                           │  DescriptionBlock                │   │
│                           │  ReadingGuideBlock               │   │
│                           │  TaskDrivenBlock  ←── 触发提交   │   │
│                           │  AppreciationListBlock           │   │
│                           │  EditableTableBlock              │   │
│                           │  ...                             │   │
│                           └──────────────────────────────────┘   │
│                                        │                          │
│                               React Query / fetch                 │
└────────────────────────────────────────┼──────────────────────────┘
                                         │ HTTP REST API
┌────────────────────────────────────────┼──────────────────────────┐
│                    后端 (FastAPI + Python)                         │
│                                         │                         │
│   /api/v1/units      /api/v1/themes    /api/v1/blocks            │
│   /api/v1/student/...  /api/v1/teacher/...  /api/v1/auth/...    │
│                  ↓                                                │
│          业务逻辑层 + 服务层  ←→  PostgreSQL (ORM)                │
│                  ↓                                                │
│          AI 智能体层  ←→  Kimi API (伴学) / Anthropic API (评测)  │
└───────────────────────────────────────────────────────────────────┘
```

### 前端技术栈

| 技术 | 用途 |
|---|---|
| React 18 + Vite | 前端框架与构建工具 |
| React Router v7 | 客户端路由 |
| Tailwind CSS | 原子化样式 |
| shadcn/ui | 基础 UI 组件库 |
| Motion (Framer) | 动画与过渡效果 |
| Zustand | 全局状态管理（用户信息、主题进度） |
| React Query (TanStack) | 服务端数据请求与缓存 |
| Lucide React | 图标库 |

### 后端技术栈（配套）

| 技术 | 用途 |
|---|---|
| FastAPI (Python) | REST API 框架 |
| SQLAlchemy 2.x | ORM，异步数据库操作 |
| PostgreSQL | 业务数据 + JSONB Block 配置 |
| Redis | LangGraph Checkpoint 缓存 |
| Anthropic API | 写作评测 + 课件解析生成 |
| Kimi (Moonshot) API | 伴学聊天（苏格拉底式引导） |
| LangGraph | 多智能体编排（Human-in-the-Loop） |
| Alembic | 数据库迁移 |
| bcrypt | 密码哈希 |
| JWT (PyJWT) | 用户认证与授权 |

---

## 三、运行流程

### 教师端流程

```
教师创建单元
    ↓
创建主题（主题阅读 / 主题活动 / 技法学习）
    ↓
上传课件 → 触发 AI 生成流水线（Reader → Architect → UI Orchestrator）
    ↓
LangGraph 挂起，教师在低代码编辑器中微调 Block 配置
    ↓
教师确认发布 → 主题 status = "published"
    ↓
学生端可访问
```

### 学生端流程

```
学生打开首页 → 选择单元 → 进入单元主题列表
    ↓
选择主题（主题阅读 / 主题活动 / 技法学习）
    ↓
前端调用 GET /api/v1/student/themes/{id}/blocks
    ↓
BlockRenderer 根据 config_json 渲染所有内容块
学生可自由切换 Tab（各章节），无步骤限制
    ↓
遇到 task_driven 类型 Block → 学生填写内容 → 点击"提交"按钮
    ↓
POST /api/v1/student/responses（保存作答）
    ↓
后端自动执行：
  ① 判定主题完成状态（所有 task_driven Block 均已提交？）
  ② 刷新 student_stats 统计数据（进度、均分、提交数）
    ↓
POST /api/v1/student/evaluate（触发 AI 写作评测，返回结构化反馈）
    ↓
POST /api/v1/student/chat（可选：与 AI 伴学助手对话，获取苏格拉底式引导）
```

### 写作评测流程（HTTP 接口，非 WebSocket）

```
学生点击"提交"按钮
    ↓
前端发送 POST /api/v1/student/evaluate
    {
      student_id, block_id, theme_id,
      component_type, student_text,
      context: { instruction, evaluator_focus }
    }
    ↓
后端 EvaluatorAgent 构建 Prompt → 调用 Anthropic API
    ↓
返回 AI 评测反馈文本
    ↓
前端在提交区域展示评测结果
```

---


## 四、项目工程目录树

```
backend/
│
├── main.py                          # FastAPI 应用入口，挂载路由与中间件
├── requirements.txt                 # Python 依赖清单
├── .env                             # 环境变量（本地开发，不提交 Git）
├── .env.example                     # 环境变量模板
├── alembic.ini                      # Alembic 数据库迁移配置
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # 全局配置与基础设施
│   │   ├── __init__.py
│   │   └── config.py                # 读取 .env，暴露 settings 单例
│   │
│   ├── db/                          # 数据库连接层
│   │   ├── __init__.py
│   │   └── session.py               # 异步 AsyncSession 工厂 + get_session 依赖
│   │
│   ├── models/                      # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   └── models.py                # Unit / Theme / Block / StudentProgress /
│   │                                #   StudentResponse / Badge / StudentBadge /
│   │                                #   User / StudentStats
│   │
│   ├── schemas/                     # Pydantic v2 请求/响应 Schema
│   │   ├── __init__.py
│   │   └── schemas.py               # XxxCreate / XxxRead / XxxUpdate /
│   │                                #   EvaluatorPayload / ClassAnalyticsResponse /
│   │                                #   PaginatedResponse ...
│   │
│   ├── api/                         # HTTP 路由层
│   │   ├── __init__.py
│   │   ├── routes.py                # 课程内容 + 学生端路由（unit / theme / block /
│   │   │                            #   student）汇总并注册至 api_router
│   │   ├── teacher_routes.py        # 教师端路由（学情分析 / 学生管理 CRUD）
│   │   └── auth_routes.py           # 认证路由（登录 / JWT）
│   │
│   ├── services/                    # 业务服务层
│   │   ├── __init__.py
│   │   └── stats_service.py         # 学生统计自动刷新（提交作答后触发 UPSERT）
│   │
│   └── agents/                      # AI 智能体层
│       ├── __init__.py
│       ├── evaluator_agent.py       # EvaluatorAgent：写作评测，调用 Anthropic API
│       └── chat_agent.py            # ChatAgent：伴学聊天，调用 Kimi API
│
└── alembic/                         # 数据库迁移脚本
    ├── env.py                       # Alembic 运行环境配置
    ├── script.py.mako               # 迁移脚本模板
    └── versions/
        ├── 0001_initial.py          # 初始建表迁移
        ├── 0003_refactor_student_progress.py  # 重构进度模型（去掉步进解锁）
        └── 0004_fix_student_stats_unique_constraint.py  # StudentStats 联合唯一约束
```

### 模块职责说明

| 模块 | 职责 |
|---|---|
| `main.py` | 应用入口，配置 CORS、挂载路由，提供 `/health` 检查 |
| `app/core/config.py` | 使用 `pydantic-settings` 读取环境变量，暴露全局 `settings` 对象 |
| `app/db/session.py` | 创建异步数据库引擎，提供 FastAPI 依赖注入用的 `get_session` |
| `app/models/models.py` | 定义全部 ORM 表结构（含 User、StudentStats），使用 SQLAlchemy 2.x `Mapped` 类型注解 |
| `app/schemas/schemas.py` | 定义前后端数据契约，遵循 `XxxBase → XxxCreate/Update/Read` 命名规范 |
| `app/api/routes.py` | 课程内容 CRUD + 学生端路由（unit / theme / block / student），最终合并注册 |
| `app/api/teacher_routes.py` | 教师端路由：学情分析（analytics）、学生管理 CRUD、学生详情 |
| `app/api/auth_routes.py` | JWT 认证：登录、令牌签发 |
| `app/services/stats_service.py` | 学生统计自动刷新服务，在作答提交后 UPSERT `student_stats` |
| `app/agents/evaluator_agent.py` | AI 写作评测智能体，返回结构化维度反馈 |
| `app/agents/chat_agent.py` | AI 伴学聊天智能体，苏格拉底式引导，调用 Kimi API |
| `alembic/versions/` | 版本化数据库迁移，保持 schema 与 ORM 同步 |

---

## 五、开发运行步骤

### 环境要求

- Python `>= 3.11`
- PostgreSQL `>= 15`
- Redis `>= 7`（LangGraph Checkpoint 缓存）

### 1. 克隆项目

```bash
git clone <repository-url>
cd backend
```

### 2. 创建并激活虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制模板并填入真实配置：

```bash
cp .env.example .env
```

`.env` 关键字段说明：

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/writing_system

# Redis
REDIS_URL=redis://localhost:6379/0

# Anthropic（写作评测）
ANTHROPIC_API_KEY=sk-ant-...

# Kimi / Moonshot（伴学聊天）
KIMI_API_KEY=sk-...
KIMI_BASE_URL=https://api.moonshot.cn/v1

# JWT
JWT_SECRET=your-random-secret-string

# CORS（前端地址）
CORS_ORIGINS=["http://localhost:5173"]
```

### 5. 运行数据库迁移

确保 PostgreSQL 已启动并且 `DATABASE_URL` 配置正确：

```bash
alembic upgrade head
```

### 6. 启动开发服务器

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：

- API 文档（Swagger UI）：`http://localhost:8000/docs`
- ReDoc 文档：`http://localhost:8000/redoc`
- 健康检查：`http://localhost:8000/health`

### 7. 创建新的数据库迁移（修改模型后执行）

```bash
alembic revision --autogenerate -m "描述本次变更"
alembic upgrade head
```

### 常用开发命令

```bash
# 启动开发服务器（热重载）
uvicorn main:app --reload

# 查看迁移历史
alembic history

# 回滚一个版本
alembic downgrade -1

# 检查当前迁移状态
alembic current
```

---

## 六、API 接口概览

### 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 登录（学生/教师），返回 JWT |

### 课程内容管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/units` | 获取单元列表（分页，教师端不传 is_published 返回全部） |
| POST | `/api/v1/units` | 创建单元 |
| GET | `/api/v1/units/{id}` | 获取单元详情（含主题和 Block） |
| PATCH | `/api/v1/units/{id}` | 更新单元 |
| DELETE | `/api/v1/units/{id}` | 删除单元（级联） |
| GET | `/api/v1/themes?unit_id=` | 获取主题列表 |
| POST | `/api/v1/themes` | 创建主题 |
| GET | `/api/v1/themes/{id}` | 获取主题详情（含 Block 列表） |
| PATCH | `/api/v1/themes/{id}` | 更新主题 |
| DELETE | `/api/v1/themes/{id}` | 删除主题 |
| POST | `/api/v1/blocks` | 创建 Block |
| GET | `/api/v1/blocks/{id}` | 获取 Block 详情 |
| PATCH | `/api/v1/blocks/{id}` | 更新 Block（含 config_json） |
| DELETE | `/api/v1/blocks/{id}` | 删除 Block |
| PUT | `/api/v1/blocks/reorder` | 批量更新 Block 排序 |

### 教师端 — 学情分析与学生管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/teacher/analytics?unit_id=` | 全班学情分析（任务完成、维度均分、学生列表） |
| GET | `/api/v1/teacher/students` | 学生账号列表（分页、模糊搜索） |
| POST | `/api/v1/teacher/students` | 新建学生账号（学号重复返回 409） |
| PATCH | `/api/v1/teacher/students/{id}` | 更新学生信息（姓名/班级/启用状态） |
| POST | `/api/v1/teacher/students/{id}/reset-password` | 重置学生密码 |
| DELETE | `/api/v1/teacher/students/{id}` | 删除学生账号 |
| GET | `/api/v1/teacher/students/{id}/detail?unit_id=` | 学生详情（含提交记录、AI 维度反馈） |

### 学生端

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/student/units/{student_id}` | 学生单元列表（含各主题完成进度） |
| GET | `/api/v1/student/units/{student_id}/detail/{unit_id}` | 学生单元详情 |
| GET | `/api/v1/student/themes/{id}/blocks` | 获取主题的 Block 列表 |
| GET | `/api/v1/student/progress/{student_id}/theme/{theme_id}` | 获取学生主题完成状态 |
| POST | `/api/v1/student/responses` | 提交作答（自动判定完成 + 刷新统计） |
| GET | `/api/v1/student/responses/{student_id}/block/{block_id}` | 获取历史作答 |
| POST | `/api/v1/student/evaluate` | 触发 AI 写作评测，返回结构化维度反馈 |
| POST | `/api/v1/student/chat` | AI 伴学聊天（苏格拉底式引导） |
| GET | `/api/v1/student/badges/{student_id}` | 获取徽章列表（含未获得） |

### 写作评测调用示例

```bash
POST /api/v1/student/evaluate
Content-Type: application/json

{
  "student_id": "S001",
  "block_id": 5,
  "theme_id": 1,
  "task_id": "task_01",
  "component_type": "TaskDriven",
  "student_text": "校园的早晨，雾气像轻纱一样笼罩着操场...",
  "context": {
    "instruction": "请模仿上述句式描写晨景",
    "evaluator_focus": ["是否使用了比喻", "意境是否相符"]
  }
}
```

### 学情分析响应示例

```json
{
  "unit_id": 1,
  "unit_title": "第一讲：亲近自然",
  "total_students": 45,
  "task_completion": [
    { "block_id": 10, "task_title": "任务一：读一读汪曾祺的\"草木情\"", "theme_title": "主题阅读", "theme_type": "themeReading", "submitted_count": 38, "total_students": 45 }
  ],
  "dimension_summary": [
    { "dimension": "文本依据", "avg_score": 82.3, "sample_count": 92 }
  ],
  "students": [
    { "student_id": "S001", "display_name": "张三", "overall_progress": 100, "avg_ai_score": 92.5, "pending_tasks": 0, "last_active_at": "2026-03-13T10:30:00+08:00" }
  ]
}
```
