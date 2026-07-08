"""竞品版本快照模型 — 记录竞品参数的历史变更"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CompetitorVersion(Base):
    """竞品参数历史版本快照表"""
    __tablename__ = "competitor_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(
        Integer,
        ForeignKey("competitor_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="竞品ID",
    )
    changed_fields = Column(JSON, nullable=True, comment="变更字段 {field: {old: val, new: val}}")
    snapshot_data = Column(JSON, nullable=True, comment="变更后的完整参数快照")
    changed_by = Column(String(80), nullable=True, comment="修改人")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # relationship
    competitor = relationship("CompetitorModel", backref="versions")
