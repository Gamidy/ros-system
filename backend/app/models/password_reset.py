"""密码重置令牌模型"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from app.core.database import Base


class PasswordResetToken(Base):
    """密码重置令牌表"""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
