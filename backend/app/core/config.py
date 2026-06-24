"""ROS 系统配置 - 开发用SQLite"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ROS (R&D Operations System)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database - 开发用SQLite，生产切MySQL
    DB_TYPE: str = "mysql"  # sqlite | mysql
    DATABASE_URL: Optional[str] = None

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_TYPE == "mysql":
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        return "sqlite:///./ros.db"  # SQLite开发模式

    # MySQL配置 (生产用)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "ros"

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # JWT — 用 validation_alias 确保读 JWT_SECRET_KEY 而非 SECRET_KEY
    SECRET_KEY: str = Field(
        default="ros-secret-key-change-in-production",
        validation_alias="JWT_SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS — 允许的来源，逗号分隔，默认放开前端地址
    CORS_ORIGINS: str = "http://139.196.15.52,http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
