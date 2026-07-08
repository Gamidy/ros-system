"""AI API 调用日志 — 记录每次 LLM 请求的用量与状态"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, func
from app.core.database import Base


class AICallLog(Base):
    """AI 调用日志 — 记录每次 LLM API 调用的用量、耗时与结果"""

    __tablename__ = "ai_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    request_id = Column(String(64), nullable=False, index=True, unique=True, comment="请求唯一 ID（UUID）")
    provider = Column(String(50), nullable=False, comment="供应商标识")
    model = Column(String(100), nullable=False, comment="模型名称")
    prompt_tokens = Column(Integer, default=0, comment="输入 Token 数")
    completion_tokens = Column(Integer, default=0, comment="输出 Token 数")
    cost = Column(Float, default=0.0, comment="本次调用费用（元/美元）")
    response_time_ms = Column(Integer, default=0, comment="响应耗时（毫秒）")
    success = Column(Boolean, default=True, comment="是否成功")
    error = Column(Text, nullable=True, comment="错误信息（失败时记录）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
