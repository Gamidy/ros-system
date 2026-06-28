"""M2 Impact Graph — 变更传播图快照模型

存储每一次 ECR 的完整变更影响 DAG 快照。
包含序列化的图结构、ripple effect 分数、节点/边统计。
"""
import sqlalchemy
from sqlalchemy import Column, Integer, DateTime, JSON, ForeignKey, func
from app.core.database import Base


class ImpactGraphSnapshot(Base):
    """变更影响图快照 — 每次 build_graph 的结果持久化"""
    __tablename__ = "ci_impact_graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ecr_id = Column(Integer, ForeignKey("ecr_requests.id"), nullable=False, index=True)
    graph_data = Column(JSON, nullable=False, comment="完整DAG序列化")
    ripple_score = Column(sqlalchemy.Numeric(5, 2), default=0)
    node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    max_depth = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
