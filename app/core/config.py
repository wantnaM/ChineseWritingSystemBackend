"""
app/core/config.py
使用 pydantic-settings 从环境变量 / .env 文件读取配置，暴露全局 settings 单例。
"""

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # 数据库
    # ------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/writing_system"
    )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 1000

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET: str = "dev-secret-please-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_SECONDS: int = 86400  # 24 小时

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """支持从环境变量读取 JSON 数组字符串，例如 '["http://localhost:5173"]'"""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ------------------------------------------------------------------
    # 应用基础配置
    # ------------------------------------------------------------------
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    # ------------------------------------------------------------------
    # 便捷属性：同步 DB URL（alembic 离线模式使用）
    # ------------------------------------------------------------------
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """将 asyncpg URL 转换为同步 psycopg2 URL（供 alembic 离线模式使用）。"""
        return self.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )

    # ------------------------------------------------------------------
    # Kimi (Moonshot AI) —— 兼容 OpenAI 协议
    # ------------------------------------------------------------------
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "kimi-k2.5"
    KIMI_MAX_TOKENS: int = 32768
    KIMI_CHAT_MODEL: str = "kimi-k2.5"
    KIMI_CHAT_MAX_TOKENS: int = 8192


# 全局单例 —— 其他模块直接 from app.core.config import settings
settings = Settings()
