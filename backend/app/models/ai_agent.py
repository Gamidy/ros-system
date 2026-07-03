"""AIAgent — 智能体管理模型

记录系统中注册的 AI 智能体及其运行状态。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class AIAgent(Base):
    """智能体注册表 — 管理各类 AI 智能体的配置与运行状态"""
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), comment="智能体名称")
    agent_type = Column(String(50), comment="类型: chatbot/automation/analysis/assistant")
    status = Column(String(20), default="active")
    monthly_calls = Column(Integer, default=0, comment="月调用次数")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
