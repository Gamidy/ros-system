"""AI提示词模板管理模型 — 用于动态管理AI辅助策划的System Prompt

prompt_templates 表存储可配置的AI提示词模板，支持版本管理和启用/禁用。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from app.core.database import Base


class PromptTemplate(Base):
    """AI提示词模板 — 动态管理AI system prompt"""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    name = Column(String(100), nullable=False, unique=True, index=True, comment="模板名称标识")
    content = Column(Text, nullable=False, comment="模板内容（支持变量占位符）")
    version = Column(Integer, nullable=False, default=1, comment="版本号")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self) -> str:
        return f"<PromptTemplate(name='{self.name}', version={self.version}, enabled={self.enabled})>"
