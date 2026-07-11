"""PLM 系统配置 — 多环境支持 (无硬编码密钥)"""
import os
import secrets
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
    DATABASE_URL: str = "sqlite+aiosqlite:///./plm_dev.db"

    # ── JWT ──
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            if self.ENV == "production":
                raise ValueError("SECRET_KEY 必须设置，不可为空")
            self.SECRET_KEY = secrets.token_urlsafe(32)
        if "change-me" in self.SECRET_KEY.lower():
            raise ValueError("请通过环境变量设置真实的 SECRET_KEY")


settings = Settings()
