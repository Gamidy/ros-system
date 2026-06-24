"""ROS 系统配置 — 多profile支持（开发/生产）"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    APP_NAME: str = "ROS (R&D Operations System)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 环境标识: development / staging / production
    ENV: str = "development"

    # ── 安全配置 ──
    ALLOW_PUBLIC_REGISTER: bool = False

    # ── 数据库 ──
    DB_TYPE: str = "sqlite"  # sqlite | mysql
    DATABASE_URL: Optional[str] = None

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_TYPE == "mysql":
            return (f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                    f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4")
        return "sqlite:///./ros.db"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "ros"

    # ── Redis / Celery ──
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # ── JWT ──
    SECRET_KEY: str = Field(
        default="ros-secret-key-change-in-production",
        validation_alias="JWT_SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── CORS ──
    CORS_ORIGINS: List[str] = [
        "http://139.196.15.52",
        "http://localhost:3000",
        "http://localhost:4173",
    ]

    # ── 服务器 ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def server_url(self) -> str:
        """服务器访问地址"""
        return f"http://{self.HOST}:{self.PORT}"

    class Config:
        env_file = ".env", ".env.development"
        extra = "allow"


settings = Settings()
