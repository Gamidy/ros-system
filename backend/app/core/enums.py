"""Phase 2 — 工程变更枚举: ECR/ECO 状态机"""

from enum import Enum


class ECRStatus(str, Enum):
    """ECR 状态: DRAFT → SUBMITTED → REVIEWING → APPROVED/REJECTED → CONVERTED"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"


class ECOStatus(str, Enum):
    """ECO 状态: DRAFT → IMPLEMENTING → VERIFIED → EFFECTIVE → CLOSED/CANCELLED"""
    DRAFT = "draft"
    IMPLEMENTING = "implementing"
    VERIFIED = "verified"
    EFFECTIVE = "effective"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ECRType(str, Enum):
    """变更类型"""
    DESIGN_CHANGE = "design_change"       # 设计变更
    PROCESS_CHANGE = "process_change"     # 工艺变更
    MATERIAL_CHANGE = "material_change"   # 物料变更
    QUALITY_FIX = "quality_fix"           # 品质整改
    COST_REDUCTION = "cost_reduction"     # 降本
    REGULATORY = "regulatory"             # 法规要求
    OTHER = "other"


class ECRUrgency(str, Enum):
    """紧急程度"""
    CRITICAL = "critical"   # 紧急（24h内）
    HIGH = "high"           # 高（48h内）
    MEDIUM = "medium"       # 中（1周内）
    LOW = "low"             # 低（2周内）


class ECOChangeType(str, Enum):
    """ECO 变更类型"""
    ADD = "add"             # 新增
    MODIFY = "modify"       # 修改
    DELETE = "delete"       # 删除
    REPLACE = "replace"     # 替换


class ECOObjectType(str, Enum):
    """ECO 变更对象类型"""
    BOM = "bom"
    MATERIAL = "material"
    DRAWING = "drawing"
    SPECIFICATION = "specification"
    PROCESS = "process"
    OTHER = "other"
