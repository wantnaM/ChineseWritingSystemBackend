"""
app/db/session.py
创建 SQLAlchemy 2.x 异步引擎，提供 FastAPI 依赖注入用的 get_session。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ------------------------------------------------------------------
# 异步引擎
# ------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),  # 开发环境打印 SQL
    pool_pre_ping=True,                         # 自动检测断开的连接
    pool_size=10,
    max_overflow=20,
)

# ------------------------------------------------------------------
# Session 工厂
# ------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期对象，避免 lazy-load 报错
    autoflush=False,
    autocommit=False,
)


# ------------------------------------------------------------------
# FastAPI 依赖注入：async with 保证会话始终被关闭
# ------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    用法示例::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
