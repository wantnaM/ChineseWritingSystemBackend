"""
alembic/env.py
适配 FastAPI + SQLAlchemy 2.x 异步引擎（asyncpg）
数据库 URL 从项目的 app.core.config.settings 读取，无需在 alembic.ini 中硬编码。
"""

from app.core.config import settings        # pydantic-settings 单例
from app.models.models import Base          # SQLAlchemy DeclarativeBase
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# 读取 alembic.ini 的日志配置
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# 导入项目 ORM 元数据 & 数据库 URL
# ---------------------------------------------------------------------------

# 把异步 URL（postgresql+asyncpg://...）转成同步 URL 供 --autogenerate 使用
# 运行迁移时用异步引擎；autogenerate 时两者都支持
target_metadata = Base.metadata

# 将 asyncpg URL 注入 alembic 配置（覆盖 alembic.ini 中的 sqlalchemy.url）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


# ---------------------------------------------------------------------------
# 离线模式（不连接数据库，只生成 SQL 文本）
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# 在线模式（连接数据库执行迁移）—— 使用异步引擎
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步引擎：创建连接后交给同步回调执行迁移。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
