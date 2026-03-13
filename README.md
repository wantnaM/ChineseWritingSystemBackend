# 📖 语文一体化写作学习系统 · 后端

> AI 驱动的个性化支架式语文教学平台 —— 将静态教辅材料转化为沉浸式互动学习体验。

---

## 目录

- [系统描述与核心理念](#一系统描述与核心理念)
- [整体架构](#二整体架构)
- [运行流程](#三运行流程)

---

## 一、系统描述与核心理念

### 系统定位

本系统是一个面向中学语文教学的 **AI 驱动个性化支架式学习平台**。核心目标是将教师编写的教学内容，转化为结构清晰、交互丰富的沉浸式学习页面，实现"以读促写"的语文学习闭环。

系统分为**教师端**与**学生端**两个视角：

- **教师端**：编排单元、主题与内容块，安排课时计划，发布给学生
- **学生端**：按主题浏览学习内容，完成任务，提交作答，获得 AI 写作评测反馈

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
│  │  (规划中)    │        │                                   │   │
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
│   /api/v1/student/...                                             │
│                  ↓                                                │
│          业务逻辑层  ←→  PostgreSQL (ORM)                         │
│                  ↓                                                │
│          AI 智能体层  ←→  Anthropic API (评测 / 生成)             │
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
| LangGraph | 多智能体编排（Human-in-the-Loop） |
| Alembic | 数据库迁移 |

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
POST /api/v1/student/evaluate（触发 AI 写作评测，返回反馈）
    ↓
PATCH /api/v1/student/progress（更新任务完成状态）
    ↓
后端检查：该主题所有 task_driven Block 均已提交？
    → 是：主题标记为完成，可能触发徽章发放
    → 否：继续等待其他任务提交
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
