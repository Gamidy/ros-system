"""AI 服务配置 — 多供应商 LLM 连接凭据表"""
import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func, LargeBinary
from app.core.database import Base
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    """获取 Fernet 加密器 — 密钥优先从环境变量 AI_ENCRYPT_KEY 读取，
    若未设置则 fallback 到 SECRET_KEY 派生出的 32 字节 base64 key。

    生产环境必须通过 AI_ENCRYPT_KEY 环境变量显式传入密钥。
    """
    raw = os.environ.get("AI_ENCRYPT_KEY") or os.environ.get("SECRET_KEY", "")
    if not raw:
        raise RuntimeError(
            "AI config encryption: neither AI_ENCRYPT_KEY nor SECRET_KEY is set"
        )
    # Fernet 要求 32 字节 url-safe base64 编码密钥
    # 若 raw 不是合法 Fernet key，从 raw 的 SHA-256 派生一个
    import hashlib, base64
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


_fernet: Fernet | None = None


def _get_cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


def encrypt_api_key(plaintext: str) -> bytes:
    """加密 API Key"""
    return _get_cipher().encrypt(plaintext.encode("utf-8"))


def decrypt_api_key(ciphertext: bytes) -> str:
    """解密 API Key"""
    return _get_cipher().decrypt(ciphertext).decode("utf-8")


class AIConfig(Base):
    """AI 供应商配置 — 存储 LLM 连接信息"""

    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True, comment="供应商标识，如 openai / deepseek / qwen")
    model = Column(String(100), nullable=False, comment="模型名称，如 gpt-4o / deepseek-chat / qwen-plus")
    api_key = Column(LargeBinary, nullable=False, comment="API Key（Fernet 加密存储）")
    api_base = Column(String(500), nullable=True, comment="API 端点 Base URL，不填则使用默认")
    temperature = Column(Float, default=0.7, comment="默认温度参数")
    max_tokens = Column(Integer, default=4096, comment="默认最大 Token 数")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def set_api_key(self, plain: str) -> None:
        """设置加密后的 API Key"""
        self.api_key = encrypt_api_key(plain)

    def get_api_key(self) -> str:
        """获取解密后的明文 API Key"""
        return decrypt_api_key(self.api_key)
