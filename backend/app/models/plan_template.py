"""PlanTemplate — 策划模板模型

预设的产品策划模板，在新建策划时提供一键填充表单功能。
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON, func
from app.core.database import Base
import uuid


def uuid4_str() -> str:
    """生成 UUID v4 字符串作为主键"""
    return str(uuid.uuid4())


class PlanTemplate(Base):
    """策划模板 — 预设字段值，新建策划时一键填充"""
    __tablename__ = "plan_templates"

    id = Column(String(36), primary_key=True, default=uuid4_str)
    product_type = Column(String(100), nullable=False, comment="产品类型")
    market = Column(String(100), nullable=False, comment="目标市场")
    name = Column(String(200), nullable=False, comment="模板名称")
    description = Column(String(500), nullable=True, comment="模板描述")
    preset_fields = Column(JSON, nullable=False, default=dict,
                           comment="预设字段值 JSON: {name, market, target_cost, cooling_capacity_w, ...}")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
