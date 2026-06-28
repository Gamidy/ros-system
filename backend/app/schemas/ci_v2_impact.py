"""M2 Impact Graph — Pydantic Schema 定义

用于 ImpactGraphEngine 的输入/输出序列化。
全类型注解，无 Any。

注意: 本文件与 M1 Risk Engine 的 ci_v2.py 共存，各司其职。
"""
from pydantic import BaseModel, ConfigDict


class ImpactNode(BaseModel):
    """DAG 节点 — 代表变更传播链上的一个环节"""
    id: str
    node_type: str
    label: str
    impact_score: float
    affected_objects: list[dict]
    depth: int
    model_config = ConfigDict(from_attributes=True)


class ImpactEdge(BaseModel):
    """DAG 边 — 代表变更传播关系"""
    source_id: str
    target_id: str
    weight: float
    label: str
    model_config = ConfigDict(from_attributes=True)


class ImpactGraphOut(BaseModel):
    """变更影响图完整输出"""
    nodes: list[ImpactNode]
    edges: list[ImpactEdge]
    ripple_score: float
    max_depth: int
    node_count: int
    edge_count: int
    model_config = ConfigDict(from_attributes=True)


class RipplePath(BaseModel):
    """从根节点到叶子节点的一条完整传播路径"""
    path: list[str]
    total_score: float
    node_count: int
    model_config = ConfigDict(from_attributes=True)
