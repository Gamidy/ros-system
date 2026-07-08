"""ValidationRule 校验规则模型 — 策划完整性校验配置驱动"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func
from app.core.database import Base


class ValidationRule(Base):
    """校验规则配置 — 从数据库读取，非硬编码"""
    __tablename__ = "validation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    rule_type = Column(String(32), nullable=False, comment="规则类型: required|range|pattern|business_rule")
    target_field = Column(String(200), nullable=False, comment="目标字段名或JSON数组字符串")
    rule_config = Column(Text, nullable=True, comment="配置JSON: range存{min,max}, pattern存正则, business_rule存函数名")
    error_message = Column(String(500), nullable=False, comment="校验失败提示")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    description = Column(String(500), nullable=True, comment="规则说明")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)
