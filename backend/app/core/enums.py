"""
ROS Phase 6 S1 — 领域枚举定义包

集中管理所有领域枚举，避免散落各处。
所有枚举使用 Python Enum + 数据库兼容 String 值。
"""

from enum import Enum


# ═══════════════ 样机相关 ═══════════════

class PrototypeType(str, Enum):
    """样机类型 — P0~P3 版本序列"""
    P0_HAND_SAMPLE = "P0"       # 手板
    P1_FIRST_SAMPLE = "P1"      # 首样（工程样机）
    P2_CERT_SAMPLE = "P2"       # 认证样机
    P3_MASS_PRODUCTION = "P3"   # 量产样机


class PrototypeStatus(str, Enum):
    """样机状态"""
    PLANNING = "planning"
    BUILDING = "building"
    TESTING = "testing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PrototypeResult(str, Enum):
    """样机结论"""
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"
    PENDING = "pending"


# ═══════════════ 验证需求相关 ═══════════════

class VerificationRequirementCategory(str, Enum):
    """验证需求分类 — 对应实际实验类型"""
    PERFORMANCE = "performance"             # 性能
    ENERGY = "energy"                       # 能效
    NOISE = "noise"                         # 噪音风量
    CONDENSATION = "condensation"           # 凝露
    DAMP_HEAT = "damp_heat"                 # 潮态
    HIGH_TEMP_COOL = "high_temp_cool"       # 高温制冷
    LOW_TEMP_HEAT = "low_temp_heat"         # 低温制热
    FROST_DEFROST = "frost_defrost"         # 冻结融霜
    LONG_RUN = "long_run"                   # 长时间运行
    ELEC_SAFETY_PRE = "elec_safety_pre"     # 电气安全预验证
    SAFETY = "safety"                       # 安全
    RELIABILITY = "reliability"             # 可靠性
    EMC = "emc"                             # EMC


class VerificationRequirementSource(str, Enum):
    """验证需求来源类型 — 必须支持来源追踪"""
    PRODUCT_PLAN = "product_plan"       # 产品策划
    CUSTOMER = "customer"               # 客户要求
    STANDARD = "standard"               # 标准要求
    CERTIFICATION = "certification"     # 认证要求
    GATE = "gate"                       # Gate决策
    ECR = "ecr"                         # 变更请求
    ENGINEER = "engineer"               # 工程师手动创建


class VerificationRequirementStatus(str, Enum):
    """验证需求状态"""
    PENDING = "pending"         # 待验证
    VERIFIED = "verified"       # 验证通过
    FAILED = "failed"           # 验证失败
    WAIVED = "waived"           # 豁免


# ═══════════════ 实验相关 ═══════════════

class TestRequestStatus(str, Enum):
    """实验申请状态"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    TESTING = "testing"
    DONE = "done"
    CANCELLED = "cancelled"


class TestExecutionStatus(str, Enum):
    """实验执行状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"


class TestResultStatus(str, Enum):
    """实验结果判定 (三态)"""
    PASS = "PASS"
    FAIL = "FAIL"
    WAIVER = "WAIVER"


class TestCategory(str, Enum):
    """实验分类 — 与 VR Category 同步"""
    PERFORMANCE = "performance"
    ENERGY = "energy"
    NOISE = "noise"
    CONDENSATION = "condensation"
    DAMP_HEAT = "damp_heat"
    HIGH_TEMP_COOL = "high_temp_cool"
    LOW_TEMP_HEAT = "low_temp_heat"
    FROST_DEFROST = "frost_defrost"
    LONG_RUN = "long_run"
    ELEC_SAFETY_PRE = "elec_safety_pre"


# ═══════════════ Gate 相关 ═══════════════

class GateCode(str, Enum):
    """Gate 编号 — 兼容 G0~G6 和 M1~M9 两套体系"""
    G0 = "G0"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"
    G5 = "G5"
    G6 = "G6"
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    M6 = "M6"
    M7 = "M7"
    M8 = "M8"
    M9 = "M9"


class GateRuleStatus(str, Enum):
    """Gate规则状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class GateEvalResult(str, Enum):
    """Gate评估结果"""
    PASS = "pass"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


# ═══════════════ 目标市场相关 ═══════════════

class TargetMarketCode(str, Enum):
    """目标市场代码"""
    CN = "CN"       # 中国
    EU = "EU"       # 欧盟
    US = "US"       # 美国
    AU = "AU"       # 澳洲
    SA = "SA"       # 沙特
    JP = "JP"       # 日本
    KR = "KR"       # 韩国
    IN = "IN"       # 印度
    BR = "BR"       # 巴西
    RU = "RU"       # 俄罗斯
    AE = "AE"       # 阿联酋
    ZA = "ZA"       # 南非
    OTHER = "OTHER" # 其他


class CertType(str, Enum):
    """认证类型"""
    CCC = "CCC"
    CB = "CB"
    CE = "CE"
    UL = "UL"
    AHRI = "AHRI"
    SAA = "SAA"
    SASO = "SASO"
    NOM = "NOM"
    EAC = "EAC"
    BIS = "BIS"
    KC = "KC"
    TISI = "TISI"
    INMETRO = "INMETRO"
    OTHER = "OTHER"


class StandardLevel(str, Enum):
    """标准层级"""
    INTERNATIONAL = "international"     # 国际: IEC, ISO, UL
    NATIONAL = "national"               # 国家: GB, EN, AHRI, JIS
    CUSTOMER = "customer"               # 客户: 小米, 格力


# ═══════════════ Phase 6 S3 — ECR/ECO 工程变更控制 ═══════════════

class ECRStatus(str, Enum):
    """ECR状态机"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"  # 已转为ECO


class ECOStatus(str, Enum):
    """ECO状态机"""
    DRAFT = "draft"
    IMPLEMENTING = "implementing"
    VERIFIED = "verified"
    EFFECTIVE = "effective"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ECRType(str, Enum):
    """ECR变更类型"""
    DESIGN_CHANGE = "design_change"       # 设计变更
    MATERIAL_CHANGE = "material_change"   # 物料变更
    PROCESS_CHANGE = "process_change"     # 工艺变更
    CERT_CHANGE = "cert_change"           # 认证变更
    STANDARD_CHANGE = "standard_change"   # 标准变更
    BOM_CHANGE = "bom_change"             # BOM变更
    OTHER = "other"                       # 其他


class ECRUrgency(str, Enum):
    """ECR紧急度"""
    EMERGENCY = "emergency"  # 紧急
    HIGH = "high"            # 高
    MEDIUM = "medium"        # 中
    LOW = "low"              # 低


class ECOChangeType(str, Enum):
    """ECO变更操作类型"""
    ADD = "add"           # 新增
    MODIFY = "modify"     # 修改
    REPLACE = "replace"   # 替换
    DELETE = "delete"     # 删除
    DISABLE = "disable"   # 禁用


class ECOObjectType(str, Enum):
    """ECO变更对象类型"""
    PART = "part"               # 物料
    BOM = "bom"                 # BOM
    DOCUMENT = "document"       # 文档
    CERTIFICATION = "certification"  # 认证
    PROCESS = "process"         # 工艺
    OTHER = "other"             # 其他


# ═══════════════ 业务对象状态（通用） ═══════════════

class ActiveStatus(str, Enum):
    """启用/停用状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class RecordStatus(str, Enum):
    """记录通用状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


# ═══════════════ 辅助工具 ═══════════════

def get_enum_values(enum_cls) -> list[str]:
    """获取枚举的所有值列表（用于 DB column check 约束）"""
    return [e.value for e in enum_cls]


def get_enum_choices(enum_cls) -> list[tuple[str, str]]:
    """获取枚举的选择项（用于表单下拉）"""
    return [(e.value, e.name) for e in enum_cls]
