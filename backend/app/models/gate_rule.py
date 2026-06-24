"""GateRule（Gate规则引擎）模型 — 必须配置化，不可写死

设计：GateRule + GateRuleItem 双表结构
- GateRule: 规则主表（匹配条件）
- GateRuleItem: 规则条目（每个条目定义一个实验分类要求）

架构师要求：
{
  "gate":"M4",
  "required_tests":[
      "PERFORMANCE",
      "NOISE",
      "CONDENSATION",
      "HUMIDITY"
  ]
}
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import GateCode, GateRuleStatus, GateEvalResult


class GateRule(Base):
    """Gate规则主表 — 按 product_line + customer + gate_code 匹配"""
    __tablename__ = "gate_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    description = Column(Text, nullable=True)

    # 匹配条件（null = 通配）
    product_line = Column(String(50), nullable=True, comment="适用产品线，null=通配")
    customer = Column(String(50), nullable=True, comment="适用客户，null=通配")
    gate_code = Column(String(10), nullable=False, comment=f"Gate编号: {[e.value for e in GateCode]}")

    # 行为
    all_pass = Column(Boolean, default=True, comment="是否全部必须通过")
    auto_block = Column(Boolean, default=False, comment="不符合时自动阻塞Gate")

    # 优先级（数字越小越优先）
    priority = Column(Integer, default=100, comment="匹配优先级")

    # 状态
    status = Column(String(20), nullable=False, default=GateRuleStatus.ACTIVE.value,
                    comment=f"状态: {[e.value for e in GateRuleStatus]}")
    created_by = Column(String(50), nullable=True)

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")

    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    items = relationship("GateRuleItem", back_populates="rule", cascade="all, delete-orphan")


class GateRuleItem(Base):
    """Gate规则条目 — 每个条目定义一个实验分类要求"""
    __tablename__ = "gate_rule_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("gate_rules.id"), nullable=False, comment="关联规则")

    # 要求的实验分类
    required_vr_category = Column(String(30), nullable=False, comment="要求的验证需求分类（如 performance）")
    required_prototype_type = Column(String(10), nullable=True, comment="要求的样机类型（如 P2）")
    required_cert_type = Column(String(20), nullable=True, comment="必需的认证类型（CE/CB/UL/SAA）")
    is_required = Column(Boolean, default=True, comment="是否强制要求")
    sort_order = Column(Integer, default=0, comment="排序")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    # 关系
    rule = relationship("GateRule", back_populates="items")


class GateEvalRecord(Base):
    """Gate评估记录 — 每次评估的日志"""
    __tablename__ = "gate_eval_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("gate_rules.id"), nullable=True, comment="匹配的规则")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="评估的项目")
    gate_code = Column(String(10), nullable=False, comment="评估的Gate")

    # 评估结果
    result = Column(String(20), nullable=False, comment=f"结果: {[e.value for e in GateEvalResult]}")
    detail = Column(Text, nullable=True, comment="评估明细JSON")

    # 时间
    evaluated_at = Column(DateTime, server_default=func.now())
    evaluated_by = Column(String(50), nullable=True, comment="评估人/自动")

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
