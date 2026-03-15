# 数据初始化 & 接口测试使用指南

## 文件说明

| 文件 | 用途 |
|---|---|
| `seed_data.py` | 将前端 Mock 数据完整导入数据库（幂等，可重复执行） |
| `tests/test_api.py` | 所有 REST 接口的 pytest 单元测试 |
| `tests/pytest.ini` | pytest 配置（asyncio_mode = auto） |

---

## 一、运行 Seed 脚本

### 前提
- 后端已配置 `.env`，`DATABASE_URL` 指向目标 PostgreSQL
- 已执行 `alembic upgrade head`（建表）

### 执行

```bash
cd backend
python seed_data.py
```

**预期输出：**
```
▶ 插入 Units ...
▶ 插入 Themes ...
▶ 插入 Blocks（主题阅读）...
▶ 插入 Blocks（主题活动）...
▶ 插入 Blocks（技法学习）...
▶ 插入 Badges ...
✅ Seed 完成！
   Units  : 1
   Themes : 3
   Blocks : 14
   Badges : 5
```

### 覆盖数据库地址

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mydb python seed_data.py
```

---

## 二、运行接口单元测试

### 安装测试依赖

```bash
pip install pytest pytest-asyncio httpx
```

### 执行测试

```bash
# 全量运行
pytest tests/test_api.py -v

# 只跑某个分组
pytest tests/test_api.py::TestUnitCRUD -v
pytest tests/test_api.py::TestStudentEndpoints -v

# 跑数据完整性验证（需先执行 seed）
pytest tests/test_api.py::TestSeedDataIntegrity -v
```

### 测试数据库配置

测试默认使用 `writing_system_test` 数据库，可通过环境变量覆盖：

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/writing_system_test \
pytest tests/test_api.py -v
```

---

## 三、Seed 数据结构概览

```
Unit: 亲近自然 (id=1)
├── Theme: 主题阅读 (id=1, themeReading)
│   ├── Block: 学习指引 [description]
│   ├── Block: 名著导读 [reading_guide]
│   ├── Block: 任务驱动 [task_driven] ← 含 2 个 tasks（必完成）
│   ├── Block: 课后任务 [description]
│   └── Block: 读后交流 [task_driven] ← 含 1 个 task（必完成）
│
├── Theme: 主题活动 (id=2, themeActivity)
│   ├── Block: 拍羊城秋色 [task_driven] ← 含 2 个 tasks
│   ├── Block: 写羊城秋色 [task_driven] ← 含 2 个 tasks
│   └── Block: 展羊城秋色 [task_driven] ← 含 1 个 task
│
└── Theme: 技法学习 (id=3, techniqueLearning)
    ├── Block: 语言风格描述 [description]
    ├── Block: 方法指导 [markdown]
    ├── Block: 小试身手 [editable_table]
    ├── Block: 实战操练 [task_driven] ← 含 1 个 task（必完成, aiEvaluate=true）
    ├── Block: 添枝加叶法描述 [description]
    └── Block: 方法指导-题目链接 [markdown]

Badges:
  🌿 自然观察家 (unitId=1)
  📚 文学爱好者 (unitId=1)
  ✨ 勤奋学习者 (全局)
  🏆 完美主义者 (全局)
  💪 坚持不懈 (全局)
```

---

## 四、接口测试覆盖范围

| 分组 | 接口 | 用例数 |
|---|---|---|
| `TestHealth` | GET /health | 1 |
| `TestUnitCRUD` | GET/POST/PATCH/DELETE /units | 7 |
| `TestThemeCRUD` | GET/POST/PATCH/DELETE /themes | 6 |
| `TestBlockCRUD` | GET/POST/PATCH/DELETE/PUT /blocks | 7 |
| `TestStudentEndpoints` | 所有 /student/* 接口 | 9 |
| `TestSeedDataIntegrity` | 验证 Seed 数据完整性 | 7 |
| **合计** | | **37** |
