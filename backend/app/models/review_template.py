"""ReviewTemplate — 复盘模板模型

定义不同产品类型的复盘字段配置模板。
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON, func
from app.core.database import Base
import uuid


def uuid4_str() -> str:
    """生成 UUID v4 字符串作为主键"""
    return str(uuid.uuid4())


class ReviewTemplate(Base):
    """复盘模板 — 定义不同产品类型的复盘字段配置"""
    __tablename__ = "review_templates"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    product_type = Column(String(100), nullable=False, comment="产品类型")
    name = Column(String(200), nullable=False, comment="模板名称")
    template_fields = Column(JSON, nullable=False,
                             comment="字段配置JSON: [{field, label, required, max_length}]")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
