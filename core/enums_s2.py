"""
ROS Phase 6 S2 — 认证中心 核心枚举扩展
"""
from enum import Enum


class CertRequirementSource(str, Enum):
    """认证需求来源"""
    TARGET_MARKET = "target_market"  # 从TargetMarket自动生成（唯一允许的方式）
    MANUAL = "manual"  # 仅用于特殊/异常情况


class CertProjectStatus(str, Enum):
    """认证项目状态"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class CertResultStatus(str, Enum):
    """认证结果状态"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"


class CertSampleStatus(str, Enum):
    """认证样机状态"""
    PENDING = "pending"
    PREPARING = "preparing"
    SUBMITTED = "submitted"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"


class CertificateStatus(str, Enum):
    """证书状态"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class CertExecutionStatus(str, Enum):
    """认证执行状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ImpactLevel(str, Enum):
    """变更影响等级"""
    CRITICAL = "critical"   # 认证失效
    MAJOR = "major"         # 需重新测试
    MINOR = "minor"         # 需重新申报
    NONE = "none"           # 无影响


class CertType(str, Enum):
    """认证类型（第一批+预留）"""
    CE = "CE"           # 欧盟
    CB = "CB"           # 国际CB体系
    UL = "UL"           # 美国
    SAA = "SAA"         # 澳洲
    ROHS = "RoHS"       # 欧盟RoHS（预留）
    REACH = "REACH"     # 欧盟REACH（预留）


class GateCode(str, Enum):
    """Gate编号（扩展认证门禁）"""
    M4 = "M4"
    M5 = "M5"
    M6 = "M6"
    M7 = "M7"
    M8 = "M8"
    M9 = "M9"
