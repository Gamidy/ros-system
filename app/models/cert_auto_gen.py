"""Phase 6 S2 — 认证自动生成日志模型

实体11 — 架构师批准设计
记录从TargetMarket自动生成CertificationRequirement/CertificationProject的日志
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CertAutoGenLog(Base):
    """自动生成日志 — 记录TargetMarket→认证需求的自动生成过程"""
    __tablename__ = "cert_auto_gen_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, comment="关联项目")
    target_market_id = Column(Integer, ForeignKey("target_markets.id"), nullable=False, comment="关联目标市场")
    generated_cert_requirements = Column(Text, nullable=True, comment="生成的认证需求JSON")
    generated_cert_project_id = Column(Integer, nullable=True, comment="生成的认证项目ID")
    status = Column(String(20), nullable=False, comment="success/partial/failed")
    message = Column(Text, nullable=True, comment="日志消息/错误信息")
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    # 关系
    project = relationship("Project")
    target_market = relationship("TargetMarket")
