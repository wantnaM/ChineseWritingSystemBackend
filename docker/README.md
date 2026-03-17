# Docker 部署指南

## 目录结构

```
docker/
├── Dockerfile                  # FastAPI 应用镜像构建文件
├── docker-compose.yml          # 开发环境配置
├── docker-compose.prod.yml     # 生产环境配置
├── .env.docker                 # 环境变量模板
├── nginx/                      # Nginx 配置
│   └── nginx.conf
└── README.md                   # 本文件
```

## 快速开始

### 1. 配置环境变量

```bash
cd docker
cp .env.docker .env
# 编辑 .env 文件，填入必要的配置（API Key、密码等）
```

### 2. 开发环境启动

**重要**：必须在 `docker/` 目录下运行命令

```bash
cd docker

# 启动所有服务（PostgreSQL + Redis + API）
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v
```

### 3. 数据库迁移

```bash
cd docker

# 首次启动时需要运行迁移
docker-compose --profile migrate run --rm migrate

# 或者进入 API 容器手动执行
docker-compose exec api alembic upgrade head
```

### 4. 生产环境部署

```bash
cd docker

# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 常用命令

**注意**：以下命令都需要在 `docker/` 目录下执行

```bash
cd docker

# 构建镜像
docker-compose build

# 重启服务
docker-compose restart api

# 进入容器
docker-compose exec api bash

# 查看数据库
docker-compose exec postgres psql -U postgres -d writing_system

# 查看 Redis
docker-compose exec redis redis-cli

# 备份数据库
docker-compose exec postgres pg_dump -U postgres writing_system > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U postgres -d writing_system < backup.sql
```

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_USER` | 数据库用户名 | postgres |
| `POSTGRES_PASSWORD` | 数据库密码 | 必填 |
| `POSTGRES_DB` | 数据库名 | writing_system |
| `KIMI_API_KEY` | Kimi API 密钥 | 必填 |
| `JWT_SECRET` | JWT 签名密钥 | 必填 |
| `CORS_ORIGINS` | 允许跨域的来源 | ["http://localhost:5173"] |

## 注意事项

1. **安全性**: 生产环境务必修改默认密码和 JWT_SECRET
2. **SSL**: 生产环境建议配置 HTTPS（在 nginx/nginx.conf 中启用 SSL 配置）
3. **备份**: 定期备份 PostgreSQL 数据卷
4. **日志**: 生产环境日志会自动轮转，避免磁盘占满
