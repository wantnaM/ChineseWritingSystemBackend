# 语文一体化学习平台 · API 接口文档

> **版本**: v1.1  
> **Base URL**: `http://localhost:8000`  
> **API 前缀**: `/api/v1`  
> **文档生成日期**: 2026-03-13  
> **对应前端页面**: Login、TeacherAnalytics、TeacherStudentManage、TeacherStudentDetail

---

## 目录

1. [通用约定](#1-通用约定)
2. [认证模块 Auth](#2-认证模块-auth)
3. [教师端 — 学情分析](#3-教师端--学情分析)
4. [教师端 — 学生账号管理](#4-教师端--学生账号管理)
5. [现有接口（学生端）参考](#5-现有接口学生端参考)
6. [错误码说明](#6-错误码说明)
7. [数据模型速查](#7-数据模型速查)
8. [前端对接指引](#8-前端对接指引)

---

## 1. 通用约定

### 请求格式

所有请求体使用 `Content-Type: application/json`。

### 认证方式

登录成功后，前端将 Token 存入 `localStorage`，后续请求在 Header 中携带：

```
Authorization: Bearer <access_token>
```

> **开发期免认证说明**：当前路由层暂未强制校验 Token，开发阶段可不携带 Authorization Header，直接调用所有接口。后续上线前会统一加上依赖注入守卫。

### 统一响应结构

**成功（200 / 201）**：直接返回 Schema 对应的 JSON 对象或数组。

**失败**：

```json
{
  "detail": "错误描述文本"
}
```

### 分页参数（通用）

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 当前页（从 1 开始） |
| `page_size` | int | 20 | 每页条数，最大 100 |

**分页响应体**：

```json
{
  "items": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

---

## 2. 认证模块 Auth

### 2.1 用户登录

```
POST /api/v1/auth/login
```

**对应前端页面**：`Login.tsx`（学生端 / 教师端统一入口）

**请求体**：

```json
{
  "username": "S001",
  "password": "123456",
  "role": "student"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 学号（学生）或工号（教师） |
| `password` | string | ✅ | 登录密码 |
| `role` | `"student"` \| `"teacher"` | ✅ | 角色，需与账号类型匹配 |

**成功响应 200**：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "S001",
    "display_name": "张三",
    "role": "student",
    "class_name": "七年级一班",
    "is_active": true,
    "last_login_at": "2026-03-13T10:30:00+08:00"
  }
}
```

**失败响应**：

| 状态码 | detail | 原因 |
|--------|--------|------|
| 401 | 账号或密码错误 | 账号不存在或密码错误 |
| 403 | 账号已被禁用，请联系教师 | `is_active = false` |

**前端对接示例**：

```typescript
// src/hooks/useAuth.ts
const login = async (username: string, password: string, role: 'student' | 'teacher') => {
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }
  const data = await res.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  // 登录成功后根据 role 跳转
  if (role === 'student') navigate('/');
  else navigate('/teacher/analytics');
};
```

---

### 2.2 退出登录

```
POST /api/v1/auth/logout
```

**说明**：服务端无状态，前端清除本地 Token 即可。此接口始终返回成功。

**成功响应 200**：

```json
{ "message": "已退出登录", "success": true }
```

---

## 3. 教师端 — 学情分析

### 3.1 获取全班学情分析

```
GET /api/v1/teacher/analytics?unit_id={unit_id}
```

**对应前端页面**：`TeacherAnalytics.tsx`

**Query 参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `unit_id` | int | ✅ | 要分析的单元 ID |

**成功响应 200**：

```json
{
  "unit_id": 1,
  "unit_title": "第一单元：鲁迅散文阅读与写作练习",
  "overview": {
    "total_students": 45,
    "completed_count": 32,
    "learning_count": 10,
    "behind_count": 3
  },
  "score_distribution": [
    { "range": "90-100", "count": 15, "percentage": 46.9 },
    { "range": "80-89",  "count": 10, "percentage": 31.3 },
    { "range": "70-79",  "count": 5,  "percentage": 15.6 },
    { "range": "60-69",  "count": 1,  "percentage": 3.1  },
    { "range": "60以下",  "count": 1,  "percentage": 3.1  }
  ],
  "students": [
    {
      "student_id": "S001",
      "display_name": "张三",
      "overall_progress": 100,
      "avg_ai_score": 92.5,
      "status": "completed",
      "last_active_at": "2026-03-13T10:30:00+08:00"
    },
    {
      "student_id": "S002",
      "display_name": "李四",
      "overall_progress": 85,
      "avg_ai_score": 88.0,
      "status": "learning",
      "last_active_at": "2026-03-13T09:15:00+08:00"
    }
  ]
}
```

**字段说明**：

`overview` 对象：

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_students` | int | 全班总人数 |
| `completed_count` | int | 已完成全部任务的学生数 |
| `learning_count` | int | 学习中（正常进度）的学生数 |
| `behind_count` | int | 进度落后的学生数 |

`students` 数组每项：

| 字段 | 类型 | 说明 |
|------|------|------|
| `student_id` | string | 学号 |
| `display_name` | string | 姓名 |
| `overall_progress` | int | 总体进度百分比（0-100） |
| `avg_ai_score` | float \| null | AI 评测均分，无提交记录时为 null |
| `status` | `"completed"` \| `"learning"` \| `"behind"` | 当前学习状态 |
| `last_active_at` | datetime \| null | 最后活跃时间 |

**前端对接示例**：

```typescript
// TeacherAnalytics.tsx
const { data } = useQuery({
  queryKey: ['teacher-analytics', selectedUnitId],
  queryFn: async () => {
    const res = await fetch(
      `${API_BASE}/api/v1/teacher/analytics?unit_id=${selectedUnitId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return res.json();
  },
});

// 统计卡片数据
const stats = [
  { label: '全班总人数',      value: data.overview.total_students },
  { label: '已完成全部任务',  value: data.overview.completed_count },
  { label: '学习中',          value: data.overview.learning_count },
  { label: '进度落后',        value: data.overview.behind_count },
];
```

---

## 4. 教师端 — 学生账号管理

### 4.1 获取学生列表

```
GET /api/v1/teacher/students
```

**对应前端页面**：`TeacherStudentManage.tsx`

**Query 参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | ❌ | 默认 1 |
| `page_size` | int | ❌ | 默认 20，最大 100 |
| `search` | string | ❌ | 按姓名或学号模糊搜索 |

**成功响应 200**：

```json
{
  "items": [
    {
      "id": 1,
      "username": "S001",
      "display_name": "张三",
      "class_name": "七年级一班",
      "is_active": true,
      "last_login_at": "2026-03-13T10:30:00+08:00"
    },
    {
      "id": 2,
      "username": "S002",
      "display_name": "李四",
      "class_name": "七年级一班",
      "is_active": true,
      "last_login_at": "2026-03-13T09:15:00+08:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

**前端对接示例**：

```typescript
// TeacherStudentManage.tsx
const fetchStudents = async (search?: string) => {
  const params = new URLSearchParams({ page: '1', page_size: '50' });
  if (search) params.append('search', search);
  const res = await fetch(`${API_BASE}/api/v1/teacher/students?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  setStudents(data.items);
};
```

---

### 4.2 新建学生账号

```
POST /api/v1/teacher/students
```

**请求体**：

```json
{
  "username": "S046",
  "display_name": "新同学",
  "password": "123456",
  "class_name": "七年级一班"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 学号，系统内唯一 |
| `display_name` | string | ✅ | 姓名 |
| `password` | string | ✅ | 初始密码（至少 6 位） |
| `class_name` | string | ❌ | 班级 |

**成功响应 201**：返回新建的 `StudentListItem` 对象（同列表行结构）。

**失败响应**：

| 状态码 | detail | 原因 |
|--------|--------|------|
| 409 | 学号 S046 已存在 | 学号重复 |

---

### 4.3 更新学生信息

```
PATCH /api/v1/teacher/students/{student_id}
```

`student_id` 为学号（如 `S001`）。

**请求体**（所有字段均可选）：

```json
{
  "display_name": "张三（已改名）",
  "class_name": "七年级二班",
  "is_active": false
}
```

**成功响应 200**：返回更新后的 `StudentListItem` 对象。

**前端对接示例（禁用账号）**：

```typescript
await fetch(`${API_BASE}/api/v1/teacher/students/${student.username}`, {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ is_active: false }),
});
```

---

### 4.4 重置学生密码

```
POST /api/v1/teacher/students/{student_id}/reset-password
```

**请求体**：

```json
{ "new_password": "newpass123" }
```

**成功响应 200**：

```json
{ "message": "密码已重置", "success": true }
```

---

### 4.5 删除学生账号

```
DELETE /api/v1/teacher/students/{student_id}
```

**成功响应 200**：

```json
{ "message": "学生账号已删除", "success": true }
```

> ⚠️ 历史学习记录（`student_progress` / `student_responses`）不会级联删除，仍可通过 `student_id` 字符串查询。

---

### 4.6 查看学生详情

```
GET /api/v1/teacher/students/{student_id}/detail
```

**对应前端页面**：`TeacherStudentDetail.tsx`

**Query 参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `unit_id` | int | ❌ | 不传则返回全部单元的提交记录 |

**成功响应 200**：

```json
{
  "profile": {
    "student_id": "S001",
    "display_name": "张三",
    "class_name": "七年级一班",
    "total_time_minutes": 750,
    "completed_tasks": 15,
    "avg_ai_score": 92.0
  },
  "recent_submissions": [
    {
      "response_id": 101,
      "submitted_at": "2026-03-13T10:30:00+08:00",
      "theme_title": "第一单元 - 技法学习",
      "task_title": "人物描写小练笔",
      "student_text": "他那原本红润的脸庞此刻像蒙上了一层灰色的纱...",
      "ai_score": 95,
      "ai_feedback": "人物的神态和动作描写非常细腻！..."
    },
    {
      "response_id": 98,
      "submitted_at": "2026-03-12T15:20:00+08:00",
      "theme_title": "第一单元 - 主题活动",
      "task_title": "《朝花夕拾》读后感片段",
      "student_text": "读完《从百草园到三味书屋》...",
      "ai_score": 88,
      "ai_feedback": "情感表达真挚，准确抓住了文章的核心意象..."
    }
  ]
}
```

**前端对接示例**：

```typescript
// TeacherStudentDetail.tsx
const { id } = useParams(); // student_id
const { data } = useQuery({
  queryKey: ['student-detail', id],
  queryFn: async () => {
    const res = await fetch(
      `${API_BASE}/api/v1/teacher/students/${id}/detail`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return res.json();
  },
});

// profile 用于顶部卡片
const { profile, recent_submissions } = data;
```

---

## 5. 现有接口（学生端）参考

以下为已有接口，不需要新增，仅作对接参考：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/units` | 获取单元列表（分页） |
| GET | `/api/v1/units/{id}` | 单元详情（含主题） |
| GET | `/api/v1/student/themes/{id}/blocks` | 获取主题的 Block 列表 |
| POST | `/api/v1/student/responses` | 学生提交作答 |
| GET | `/api/v1/student/responses/{student_id}/block/{block_id}` | 获取历史作答 |
| POST | `/api/v1/student/evaluate` | 触发 AI 写作评测 |
| PATCH | `/api/v1/student/progress` | 更新学习进度 |
| GET | `/api/v1/student/badges/{student_id}` | 获取已获得徽章 |

---

## 6. 错误码说明

| HTTP 状态码 | 含义 | 常见场景 |
|-------------|------|----------|
| 200 | 成功 | 普通 GET / PATCH |
| 201 | 创建成功 | POST 新建资源 |
| 400 | 请求参数错误 | 必填字段缺失、类型不匹配 |
| 401 | 未认证 | Token 无效或账号密码错误 |
| 403 | 无权限 | 账号被禁用 |
| 404 | 资源不存在 | ID 对应记录不存在 |
| 409 | 冲突 | 学号已存在 |
| 422 | 请求体校验失败 | Pydantic 字段校验错误（detail 含字段级错误信息） |
| 500 | 服务器内部错误 | 数据库连接失败等 |

**422 错误示例**：

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "username"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

---

## 7. 数据模型速查

### User（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `username` | string | 学号 / 工号，唯一 |
| `display_name` | string | 展示姓名 |
| `role` | `student` \| `teacher` | 角色 |
| `class_name` | string? | 班级（仅学生） |
| `is_active` | bool | 账号是否启用 |
| `last_login_at` | datetime? | 最后登录时间 |

### StudentStats（学生统计快照）

| 字段 | 类型 | 说明 |
|------|------|------|
| `student_id` | string | 学号（与 users.username 对齐） |
| `unit_id` | int? | 所属单元（null 为全局汇总） |
| `total_submit_count` | int | 总提交次数 |
| `avg_ai_score` | float? | AI 评测均分 |
| `overall_progress` | int | 总体进度（0-100） |
| `status` | string | `completed` \| `learning` \| `behind` |
| `last_active_at` | datetime? | 最后活跃时间 |

---

## 8. 前端对接指引

### 8.1 环境变量

在 `frontend/.env.local` 中设置：

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 8.2 封装通用请求工具

```typescript
// src/lib/api.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL;

export const apiClient = {
  get: (path: string) =>
    fetch(`${API_BASE}${path}`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
    }).then((r) => r.json()),

  post: (path: string, body: unknown) =>
    fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify(body),
    }).then((r) => r.json()),

  patch: (path: string, body: unknown) =>
    fetch(`${API_BASE}${path}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
      body: JSON.stringify(body),
    }).then((r) => r.json()),

  delete: (path: string) =>
    fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('access_token')}`,
      },
    }).then((r) => r.json()),
};
```

### 8.3 页面与接口映射

| 前端页面 | 使用的接口 |
|----------|-----------|
| `Login.tsx` | `POST /api/v1/auth/login` |
| `TeacherAnalytics.tsx` | `GET /api/v1/teacher/analytics?unit_id=` |
| `TeacherStudentManage.tsx` | `GET /api/v1/teacher/students`、`POST /api/v1/teacher/students`、`PATCH /api/v1/teacher/students/{id}`、`POST .../reset-password`、`DELETE .../students/{id}` |
| `TeacherStudentDetail.tsx` | `GET /api/v1/teacher/students/{id}/detail` |

### 8.4 Zustand 用户状态建议

```typescript
// src/store/useAuthStore.ts
import { create } from 'zustand';

interface AuthState {
  user: { id: number; username: string; display_name: string; role: string } | null;
  token: string | null;
  setAuth: (token: string, user: AuthState['user']) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('access_token'),
  setAuth: (token, user) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ token, user });
  },
  clearAuth: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    set({ token: null, user: null });
  },
}));
```

### 8.5 数据库迁移说明（后端）

新增 `users` 和 `student_stats` 两张表后，需运行：

```bash
alembic revision --autogenerate -m "add_users_and_student_stats"
alembic upgrade head
```

新增路由注册到 `main.py`：

```python
# main.py
from app.api.auth_routes import auth_router
from app.api.teacher_routes import teacher_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(teacher_router, prefix="/api/v1")
```

---

*文档结束 — 如有接口变更请同步更新此文档*
