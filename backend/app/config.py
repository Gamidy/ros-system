"""PLM 系统配置 — 多环境支持"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "allow"}

    # ── 应用 ──
    APP_NAME: str = "PLM System"
    APP_VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = True

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://plm:plm_dev_2026@localhost:5432/plm"

    # ── JWT ──
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
