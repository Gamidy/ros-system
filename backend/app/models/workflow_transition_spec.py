"""WorkflowTransitionSpec — 流程阶段转换规则定义

每个产品策划流程阶段之间可以配置一条转换规则，
包含前置条件检查、必填字段、角色权限等。
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from app.core.database import Base


class WorkflowTransitionSpec(Base):
    """流程阶段转换规则"""
    __tablename__ = "workflow_transition_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_stage = Column(String(30), nullable=False, comment="源阶段 (ProductPlanStage 枚举值)")
    to_stage = Column(String(30), nullable=False, comment="目标阶段 (ProductPlanStage 枚举值)")
    required_fields = Column(Text, nullable=True, comment="必填字段 JSON 数组，如 '[\"name\",\"series\"]'")
    required_condition = Column(Text, nullable=True, comment="Python 表达式字符串条件，如 \"plan.competitor_id is not None\"")
    required_label = Column(String(200), nullable=True, comment="条件描述（给前端展示），如 '请先选择竞品'")
    auto_advance = Column(Boolean, default=False, comment="是否自动推进")
    roles_allowed = Column(Text, nullable=True, comment="允许推进的角色 JSON 数组，如 '[\"admin\",\"pm\"]'")
    sort_order = Column(Integer, default=0, comment="排序")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
