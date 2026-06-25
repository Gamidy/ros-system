"""ROS 全模块 Schema: 认证 + Product + BOM + 项目 + 测试/认证/样机/品质"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import date, datetime


# ═══════════════ 认证 Schema ═══════════════

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "engineer"

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool = True
    created_at: datetime
    allowed_menus: list[str] = []
    allowed_paths: list[str] = []  # 前端路由路径（如 /dashboard），由服务端动态下发
    class Config: from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# 账号申请 Schema
class AccountApplicationCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6)
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=500)
    role: str = "engineer"  # 申请注册角色，仅允许非特权角色

class AccountApplicationOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    application_reason: Optional[str] = None
    application_status: str
    role: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

class AccountApplicationReview(BaseModel):
    action: str  # approve | reject

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)

# ═══════════════ 产品主线 (Product) ═══════════════

class PlatformCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    platform_type: str = Field(pattern="^(IDU|ODU)$")
    status: str = "active"
    description: Optional[str] = None
    dimensions: Optional[str] = None
    hard_constraints: Optional[str] = None

class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[str] = None
    hard_constraints: Optional[str] = None

class PlatformOut(PlatformCreate):
    id: int
    created_at: datetime
    products_count: int = 0
    class Config: from_attributes = True

class ProductCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    platform_id: int
    market: Optional[str] = None
    capacity: Optional[str] = None
    indoor_platform_id: Optional[int] = None
    outdoor_platform_id: Optional[int] = None
    indoor_product_code: Optional[str] = None
    outdoor_product_code: Optional[str] = None
    description: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[str] = None

class ProductOut(ProductCreate):
    id: int
    status: str
    platform_code: str = ""
    market_codes: list[str] = []
    created_at: datetime
    class Config: from_attributes = True

class VersionCreate(BaseModel):
    version_no: str = Field(min_length=1, max_length=50)
    reason: Optional[str] = None
    change_type: Optional[str] = None
    customer_perceivable: str = "false"
    effective_date: Optional[date] = None

class VersionStatusUpdate(BaseModel):
    status: str

class VersionOut(VersionCreate):
    id: int
    product_id: int
    status: str
    created_at: datetime
    class Config: from_attributes = True

class ManufacturingVariantCreate(BaseModel):
    factory_code: str
    factory_name: Optional[str] = None
    mbom_version: str
    description: Optional[str] = None

class ManufacturingVariantOut(ManufacturingVariantCreate):
    id: int
    version_id: int
    is_active: str = "true"
    created_at: datetime
    class Config: from_attributes = True

class MarketCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str
    region: Optional[str] = None
    energy_standard: Optional[str] = None
    energy_label: Optional[str] = None
    energy_unit: Optional[str] = None
    energy_standard_detail: Optional[str] = Field(None, max_length=100)
    national_standard: Optional[str] = Field(None, max_length=100)
    voltage_freq: Optional[str] = Field(None, max_length=50)
    cooling_max_temp: Optional[float] = None
    heating_min_temp: Optional[float] = None
    structure_type: Optional[str] = Field(None, max_length=100)
    main_selling_model: Optional[str] = Field(None, max_length=200)
    refrigerant: Optional[str] = Field(None, max_length=50)
    refrigerant_charge: Optional[float] = None
    is_active: Optional[str] = "true"

class MarketOut(MarketCreate):
    code: str
    name: str
    class Config: from_attributes = True

class ProductMarketAssign(BaseModel):
    market_codes: list[str]

class VersionRuleRequest(BaseModel):
    change_description: str = ""
    material_level: str = "minor"
    change_category: str = "bom_only"
    is_customer_perceivable: bool = False

class VersionRuleResponse(BaseModel):
    should_create: bool
    reason: str = ""
    change_type: Optional[str] = None
    customer_perceivable: bool = False
    product_action: Optional[str] = None

# ═══════════════ BOM 扩展 ═══════════════

class PartCreate(BaseModel):
    part_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str = "个"
    lifecycle: str = "developing"
    supplier_info: Optional[str] = None
    risk_level: str = "low"
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mrc_level: Optional[str] = None


class PartOut(BaseModel):
    id: int
    part_no: str
    name: str
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str
    lifecycle: str
    risk_level: str
    supplier_info: Optional[str] = None
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mq_status: Optional[str] = None
    mrc_level: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class PartAVLCreate(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=50)
    vendor_name: str = Field(min_length=1, max_length=200)
    is_primary: bool = False
    status: str = "approved"
    approved_date: Optional[date] = None
    remark: Optional[str] = None


class PartAVLOut(PartAVLCreate):
    id: int
    part_id: int
    created_at: datetime
    class Config: from_attributes = True


class PartUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    lifecycle: Optional[str] = None
    risk_level: Optional[str] = None
    is_cdf_item: Optional[bool] = None
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: Optional[bool] = None
    mrc_level: Optional[str] = None


class PartDetailOut(BaseModel):
    id: int
    part_no: str
    name: str
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: str
    lifecycle: str
    risk_level: str
    supplier_info: Optional[str] = None
    is_cdf_item: bool = False
    cdf_type: Optional[str] = None
    cdf_cert_no: Optional[str] = None
    cdf_expiry_date: Optional[date] = None
    market_cert_marks: Optional[str] = None
    mq_required: bool = False
    mq_status: Optional[str] = None
    mrc_level: Optional[str] = None
    avl_entries: list[PartAVLOut] = []
    created_at: datetime
    class Config: from_attributes = True


class BOMCreate(BaseModel):
    bom_no: str = Field(min_length=1, max_length=50)
    product_code: str = Field(min_length=1, max_length=50)
    version: str = "V1.0"
    bom_type: str = "MBOM"
    description: Optional[str] = None
    factory_code: Optional[str] = None


class BOMUpdate(BaseModel):
    version: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class BOMOut(BaseModel):
    id: int
    bom_no: str
    product_code: str
    version: str
    bom_type: str
    description: Optional[str] = None
    factory_code: Optional[str] = None
    status: str
    created_at: datetime
    class Config: from_attributes = True


class BOMItemCreate(BaseModel):
    parent_item_id: Optional[int] = None
    part_no: str
    part_name: Optional[str] = None
    item_type: str = "Part"
    level: int = Field(ge=1, le=6)
    quantity: float = 1.0
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    position_no: Optional[str] = None
    remark: Optional[str] = None


class BOMItemOut(BOMItemCreate):
    id: int
    bom_id: int
    children: Optional[list["BOMItemOut"]] = None
    created_at: datetime
    class Config: from_attributes = True


class AlternativeAssign(BaseModel):
    alternative_part_ids: list[int]


class BOMTreeItem(BaseModel):
    id: int
    part_no: str
    part_name: Optional[str] = None
    item_type: str
    level: int
    quantity: float
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    position_no: Optional[str] = None
    remark: Optional[str] = None
    children: list["BOMTreeItem"] = []


class BOMTreeOut(BaseModel):
    bom: BOMOut
    tree: list[BOMTreeItem]


# ═══════════════ BOM 成本汇总 ═══════════════

class BOMCostByLevel(BaseModel):
    """各级成本统计"""
    level: int
    level_name: str  # 如 "L1-整机", "L2-内外机"
    item_count: int
    total_cost: float


class BOMCostNode(BaseModel):
    """BOM树节点含成本 — 递归结构"""
    id: int
    part_no: str
    part_name: Optional[str] = None
    item_type: str
    level: int
    quantity: float
    unit: str = "个"
    unit_price: float = 0.0
    amount: float = 1.0
    node_cost: float = 0.0  # 本节点直接成本 = unit_price × amount × quantity
    subtree_cost: float = 0.0  # 子树总成本（含本节点+所有子节点）
    children: list["BOMCostNode"] = []


class BOMCostSummaryOut(BaseModel):
    """BOM成本汇总响应"""
    bom: BOMOut
    total_cost: float = 0.0
    cost_by_level: list[BOMCostByLevel] = []
    tree_with_cost: list[BOMCostNode] = []


# ═══════════════ 审批流 Schema ═══════════════

class ApprovalStepCreate(BaseModel):
    seq: int
    role: str
    name: str
    step_type: str = "sequential"

class ApprovalStepOut(ApprovalStepCreate):
    id: int
    chain_id: int
    created_at: datetime
    class Config: from_attributes = True

class ApprovalChainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None
    steps: list[ApprovalStepCreate] = []

class ApprovalChainOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    steps: list[ApprovalStepOut] = []
    created_at: datetime
    class Config: from_attributes = True

class ApprovalRequestCreate(BaseModel):
    chain_id: int
    request_type: str = Field(pattern="^(ecr|purchase|register|proposal)$")
    request_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    requester: Optional[str] = None

class ApprovalRequestOut(BaseModel):
    id: int
    chain_id: int
    request_type: str
    request_id: Optional[int] = None
    title: str
    requester: str
    status: str
    current_step: int
    step_meta: Optional[dict] = None
    steps: list[ApprovalStepOut] = []
    records: list["ApprovalRecordOut"] = []
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True

class ApprovalRecordOut(BaseModel):
    id: int
    request_id: int
    step_id: Optional[int] = None
    approver: str
    decision: str
    comment: Optional[str] = None
    decided_at: datetime
    class Config: from_attributes = True

class ApprovalDecision(BaseModel):
    comment: Optional[str] = None

# ═══════════════ 项目 扩展 ═══════════════

class ProgramCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProgramOut(ProgramCreate):
    id: int
    status: str
    created_at: datetime
    class Config: from_attributes = True


class ProjectCreate(BaseModel):
    code: Optional[str] = None
    name: str = Field(max_length=200)
    program_id: Optional[int] = None
    product_code: Optional[str] = None
    project_class: Optional[str] = Field(default='C', pattern="^(T|A|B|C)$")
    source: Optional[str] = None
    source_category: Optional[str] = None
    dev_modules: Optional[str] = None
    change_impacts: Optional[str] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    critical_path: Optional[str] = None
    market_policy: Optional[str] = None
    annual_planning_ref: Optional[str] = None
    budget: Optional[int] = None
    # Sheet 1 - 项目概述
    product_type: Optional[str] = None
    target_market: Optional[str] = None
    climate_zone: Optional[str] = None
    refrigerant: Optional[str] = None
    capacity_range: Optional[str] = None
    voltage_freq: Optional[str] = None
    series_name: Optional[str] = None
    energy_rating: Optional[str] = None
    ip_ownership: Optional[str] = None
    project_duration: Optional[str] = None
    dev_category: Optional[str] = None
    project_origin: Optional[str] = None
    background_basis: Optional[str] = None
    overall_goal: Optional[str] = None
    tech_goal: Optional[str] = None
    cost_goal: Optional[str] = None
    sales_goal: Optional[str] = None
    cert_goal: Optional[str] = None
    schedule_goal: Optional[str] = None
    patent_goal: Optional[str] = None
    other_goals: Optional[str] = None
    deliverables: Optional[str] = None
    sample_qty: Optional[int] = None
    required_date: Optional[date] = None
    # Sheet 2 - 市场与客户需求
    main_capacity: Optional[str] = None
    energy_efficiency_req: Optional[str] = None
    cert_requirements: Optional[str] = None
    target_price: Optional[str] = None
    customer_requirements: Optional[str] = None
    # Sheet 3 - 技术要求
    core_performance: Optional[str] = None
    safety_compliance: Optional[str] = None
    optional_config: Optional[str] = None
    # Sheet 4 - 成本核算
    dev_cost_items: Optional[str] = None
    economic_indicators: Optional[str] = None
    mold_costs: Optional[str] = None
    prototype_costs_detail: Optional[str] = None
    # Sheet 5 - 团队与职责
    team_members: Optional[str] = None
    # Draft 机制
    is_draft: Optional[bool] = True


class ProjectDraftSave(ProjectCreate):
    """草稿保存专用 Schema — 字段与 ProjectCreate 完全相同，语义区分"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新 - PATCH 请求体"""
    name: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    other_requirements: Optional[str] = None
    budget: Optional[int] = None


class ProjectOut(ProjectCreate):
    id: int
    status: str
    gates: list["ProjectGateOut"] = []
    risks: list["RiskOut"] = []
    created_at: datetime
    class Config: from_attributes = True


class ProjectGateCreate(BaseModel):
    gate_code: str
    gate_name: str
    seq: int
    decision_level: Optional[str] = None
    pass_conditions: Optional[str] = None
    is_high_risk_zone: bool = False
    is_hidden: bool = False


class ProjectGateOut(ProjectGateCreate):
    id: int
    project_id: int
    status: str
    planned_date: Optional[date] = None
    actual_date: Optional[date] = None
    decision: Optional[str] = None
    reviewer: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class GateStatusUpdate(BaseModel):
    status: str
    actual_date: Optional[date] = None
    decision: Optional[str] = None


class MilestoneCreate(BaseModel):
    name: str
    planned_date: Optional[date] = None
    conditions: Optional[str] = None
    gate_code: Optional[str] = None


class MilestoneOut(MilestoneCreate):
    id: int
    project_id: int
    status: str
    actual_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class TaskCreate(BaseModel):
    title: str
    assignee: Optional[str] = None
    milestone_id: Optional[int] = None
    priority: str = "medium"
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    description: Optional[str] = None


class TaskOut(TaskCreate):
    id: int
    project_id: int
    status: str
    actual_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class RiskCreate(BaseModel):
    title: str
    risk_level: str = "B"
    risk_source: Optional[str] = None
    probability: str = "medium"
    impact: str = "medium"
    mitigation: Optional[str] = None


class RiskOut(RiskCreate):
    id: int
    project_id: int
    status: str
    raised_by: Optional[str] = None
    resolved_at: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 测试 & MQ ═══════════════

class TestResultCreate(BaseModel):
    item_name: str
    standard_value: Optional[str] = None
    actual_value: Optional[str] = None
    is_pass: Optional[bool] = None
    # Phase 6 增强字段
    prototype_id: Optional[int] = None
    execution_id: Optional[int] = None
    result: Optional[str] = None
    judgment_data: Optional[str] = None
    remark: Optional[str] = None
    tested_by: Optional[str] = None


class TestResultOut(TestResultCreate):
    id: int
    test_request_id: int
    tested_at: Optional[datetime] = None
    class Config: from_attributes = True


class TestRequestCreate(BaseModel):
    title: str
    project_code: Optional[str] = None
    product_code: Optional[str] = None
    test_type: str
    test_standard: Optional[str] = None
    trigger_mode: Optional[str] = None
    requester: str
    requirement: Optional[str] = None
    sample_info: Optional[str] = None
    priority: Optional[str] = None
    target_date: Optional[date] = None
    # Phase 6 增强字段
    vr_id: Optional[int] = None
    prototype_id: Optional[int] = None
    test_category: Optional[str] = None


class TestRequestOut(TestRequestCreate):
    id: int
    request_no: str
    status: str
    ng_count: int
    result_summary: Optional[str] = None
    results: list[TestResultOut] = []
    created_at: datetime
    class Config: from_attributes = True


class MQVerificationCreate(BaseModel):
    part_no: str
    part_name: Optional[str] = None
    project_code: Optional[str] = None
    product_code: Optional[str] = None
    mq_type: str = "full"
    test_items: Optional[str] = None


class MQVerificationOut(MQVerificationCreate):
    id: int
    status: str
    pass_items: int = 0
    fail_items: int = 0
    verified_by: Optional[str] = None
    verified_at: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 认证 & 样机 & 品质 ═══════════════

class CertificationCreate(BaseModel):
    product_code: str
    cert_type: str
    target_market: str
    cert_body: Optional[str] = None
    planned_date: Optional[date] = None
    cdf_doc_ref: Optional[str] = None
    remark: Optional[str] = None


class CertificationOut(CertificationCreate):
    id: int
    cert_no: str
    status: str
    submit_date: Optional[date] = None
    approved_date: Optional[date] = None
    expiry_date: Optional[date] = None
    result: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class PrototypeCreate(BaseModel):
    product_code: str
    project_code: Optional[str] = None
    proto_type: str
    stage: Optional[str] = None
    quantity: int = 1
    remark: Optional[str] = None
    # Phase 6 增强字段
    version: Optional[str] = None
    project_id: Optional[int] = None
    parent_prototype_id: Optional[int] = None
    bom_version: Optional[str] = None
    firmware_version: Optional[str] = None


class PrototypeOut(PrototypeCreate):
    id: int
    proto_no: str
    status: str
    material_status: Optional[str] = None
    produced_date: Optional[date] = None
    test_date: Optional[date] = None
    result: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class QualityIssueCreate(BaseModel):
    title: str
    product_code: Optional[str] = None
    project_code: Optional[str] = None
    issue_source: Optional[str] = None
    severity: str = "B"
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    target_date: Optional[date] = None


class QualityIssueOut(QualityIssueCreate):
    id: int
    issue_no: str
    status: str
    root_cause: Optional[str] = None
    solution: Optional[str] = None
    closed_date: Optional[date] = None
    created_at: datetime
    class Config: from_attributes = True


class ForgotPasswordRequest(BaseModel):
    """忘记密码 — 通过用户名发起重置"""
    username: str

class VerifyResetTokenRequest(BaseModel):
    """验证重置令牌并设置新密码"""
    token: str
    new_password: str = Field(min_length=6)

class AdminResetPasswordRequest(BaseModel):
    """管理员直接重置用户密码"""
    user_id: int
    new_password: str = Field(min_length=6)

class IssueUpdate(BaseModel):
    root_cause: str | None = None
    solution: str | None = None
    status: str | None = None


# ═══════════════ ECR/ECN ═══════════════

class ECRCreate(BaseModel):
    title: str
    product_code: Optional[str] = None
    change_type: str
    trigger: Optional[str] = None
    description: Optional[str] = None
    impact_analysis: Optional[str] = None


class ECROut(ECRCreate):
    id: int
    ecr_no: str
    status: str
    submitted_by: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class ECNCreate(BaseModel):
    ecr_id: Optional[int] = None
    title: str
    product_code: Optional[str] = None
    change_scope: Optional[str] = None
    bom_changes: Optional[str] = None
    cdf_impact: bool = False
    certification_impact: bool = False
    effective_date: Optional[date] = None


class ECNOut(ECNCreate):
    id: int
    ecn_no: str
    status: str
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 预警/通知 ═══════════════

class AlertRuleCreate(BaseModel):
    name: str
    target_type: str
    rule_type: str
    condition: str
    level: int = 2
    is_enabled: bool = True
    notify_channels: Optional[str] = None
    notify_users: Optional[str] = None


class AlertRuleOut(AlertRuleCreate):
    id: int
    created_at: datetime
    class Config: from_attributes = True


class AlertOut(BaseModel):
    id: int
    rule_id: Optional[int] = None
    target_type: str
    target_id: int
    title: str
    level: int
    alert_type: str
    message: str
    is_read: bool = False
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True


class NotificationOut(BaseModel):
    id: int
    alert_id: Optional[int] = None
    target_user: str
    channel: str
    title: str
    content: str
    is_sent: bool = False
    is_read: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True


# ═══════════════ 预警 Schema ═══════════════

class AlertOut(BaseModel):
    id: int
    rule_id: Optional[int] = None
    target_type: str
    target_id: int
    title: str
    level: int
    alert_type: str
    message: str
    is_read: bool = False
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True


class AlertRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_type: str = Field(min_length=1, max_length=50)
    rule_type: str = Field(min_length=1, max_length=50)
    condition: str
    level: int = 2
    is_enabled: bool = True
    notify_channels: Optional[str] = None
    notify_users: Optional[str] = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    target_type: str
    rule_type: str
    condition: str
    level: int
    is_enabled: bool = True
    notify_channels: Optional[str] = None
    notify_users: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class DashboardSummary(BaseModel):
    total_products: int = 0
    active_projects: int = 0
    high_risk_projects: int = 0
    pending_tests: int = 0
    active_certifications: int = 0
    open_quality_issues: int = 0
    unresolved_alerts: int = 0
    cdf_expiring_soon: int = 0
    m4_m6_at_risk: int = 0


# ═══════════════ 驾驶舱 DashboardResponse（嵌套结构） ═══════════════

class Layer1SystemHealth(BaseModel):
    """L1 系统健康概览"""
    total_platforms: int = 0
    total_products: int = 0
    total_versions: int = 0
    active_projects: int = 0
    product_status_distribution: dict[str, int] = Field(default_factory=dict)


class RecentProjectSummary(BaseModel):
    """L2 近期项目摘要"""
    id: int
    code: Optional[str] = None
    name: str
    status: str
    project_class: Optional[str] = None
    target_end_date: Optional[date] = None
    owner: Optional[str] = None
    class Config: from_attributes = True


class Layer2ProjectOps(BaseModel):
    """L2 项目运营概览"""
    project_count: int = 0
    on_time_rate: float = 0.0
    overdue_count: int = 0
    pending_approvals_count: int = 0
    recent_projects: list[RecentProjectSummary] = Field(default_factory=list)
    project_status_distribution: dict[str, int] = Field(default_factory=dict)


class Layer4ACMetrics(BaseModel):
    """L4 进度-测试-品质-成本综合指标"""
    phase_progress: Optional[dict[str, float]] = Field(default_factory=dict)
    test_pass_rate: float = 0.0
    issue_close_rate: float = 0.0
    cost_execution_rate: float = 0.0
    generalization_rate: float = 0.0
    phase_progress_array: list[dict] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    """驾驶舱多层聚合响应"""
    layer1_system_health: Layer1SystemHealth = Field(default_factory=Layer1SystemHealth)
    layer2_project_ops: Layer2ProjectOps = Field(default_factory=Layer2ProjectOps)
    layer3_penetration: Optional[dict] = None
    layer4_ac_metrics: Layer4ACMetrics = Field(default_factory=Layer4ACMetrics)


# ═══════════════ 采购模块 Schema ═══════════════

# --- 供应商 ---

class SupplierCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: str = "active"
    remark: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    bank_info: Optional[str] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class SupplierOut(SupplierCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


# --- 采购订单 ---

class PurchaseOrderItemCreate(BaseModel):
    part_no: str = Field(min_length=1, max_length=50)
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: str = "个"
    quantity: float = 1.0
    unit_price: float = 0.0
    total_price: float = 0.0
    delivery_date: Optional[date] = None
    received_qty: float = 0.0
    remark: Optional[str] = None


class PurchaseOrderItemUpdate(BaseModel):
    part_no: Optional[str] = None
    part_name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    delivery_date: Optional[date] = None
    received_qty: Optional[float] = None
    remark: Optional[str] = None


class PurchaseOrderItemOut(PurchaseOrderItemCreate):
    id: int
    order_id: int
    created_at: datetime
    class Config: from_attributes = True


class PurchaseOrderCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=200)
    supplier_code: str = Field(min_length=1, max_length=50)
    total_amount: float = 0.0
    status: str = "draft"
    requester: str = Field(min_length=1, max_length=100)
    remark: Optional[str] = None
    items: list[PurchaseOrderItemCreate] = []


class PurchaseOrderStatusUpdate(BaseModel):
    status: str


class PurchaseOrderOut(BaseModel):
    id: int
    order_no: str
    supplier_name: str
    supplier_code: str
    total_amount: float
    status: str
    requester: str
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True


class PurchaseOrderDetailOut(PurchaseOrderOut):
    items: list[PurchaseOrderItemOut] = []
    class Config: from_attributes = True


class PurchaseDashboardOut(BaseModel):
    pending_approval: int = 0
    month_total_amount: float = 0.0
    month_order_count: int = 0
    pending_received: int = 0
    total_orders: int = 0
    total_suppliers: int = 0
    status_breakdown: dict[str, int] = {}


# ═══════════════ 外协送样 Schema ═══════════════

class OutsourceRequestCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=50)
    part_name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1)
    target_factory: str = Field(min_length=1, max_length=100)
    required_date: Optional[date] = None
    description: Optional[str] = None


class OutsourceRequestUpdate(BaseModel):
    status: Optional[str] = None
    required_date: Optional[date] = None
    description: Optional[str] = None


class OutsourceRequestOut(OutsourceRequestCreate):
    id: int
    request_no: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


# ═══════════════ Phase 6 S1 — VerificationRequirement ═══════════════

class VerificationRequirementCreate(BaseModel):
    title: str
    category: str
    target_value: str | None = None
    unit: str | None = None
    source_type: str
    source_id: str | None = None
    source_detail: str | None = None
    project_id: int | None = None
    product_plan_id: int | None = None
    gate_code: str | None = None
    remark: str | None = None


class VerificationRequirementOut(VerificationRequirementCreate):
    id: int
    vr_code: str
    status: str
    org_id: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VerificationRequirementGenerateRequest(BaseModel):
    product_plan_id: int
    auto_generate: bool = True


# ═══════════════ Phase 6 S1 — TestExecution ═══════════════

class TestExecutionCreate(BaseModel):
    test_request_id: int
    lab: str | None = None
    equipment: str | None = None
    operator: str | None = None
    start_time: datetime | None = None
    notes: str | None = None


class TestExecutionOut(TestExecutionCreate):
    id: int
    end_time: datetime | None = None
    duration_minutes: int | None = None
    status: str
    org_id: int | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ Phase 6 S1 — GateRule ═══════════════

class GateRuleItemCreate(BaseModel):
    required_vr_category: str
    required_prototype_type: str | None = None
    is_required: bool = True
    sort_order: int = 0


class GateRuleCreate(BaseModel):
    name: str
    description: str | None = None
    product_line: str | None = None
    customer: str | None = None
    gate_code: str
    all_pass: bool = True
    auto_block: bool = False
    priority: int = 100
    items: list[GateRuleItemCreate] = []


class GateRuleItemOut(GateRuleItemCreate):
    id: int
    rule_id: int
    model_config = ConfigDict(from_attributes=True)


class GateRuleOut(GateRuleCreate):
    id: int
    status: str
    created_by: str | None = None
    org_id: int | None = None
    created_at: datetime
    updated_at: datetime
    items: list[GateRuleItemOut] = []
    model_config = ConfigDict(from_attributes=True)


class GateRuleEvalRequest(BaseModel):
    project_id: int
    gate_code: str
    product_line: str | None = None
    customer: str | None = None


# ═══════════════ Phase 6 S1 — TargetMarket ═══════════════

class RequiredTestCreate(BaseModel):
    test_category: str
    standard: str | None = None
    is_required: bool = True
    sort_order: int = 0


class RequiredCertificationCreate(BaseModel):
    cert_type: str
    cert_body: str | None = None
    is_mandatory: bool = True
    sort_order: int = 0


class RequiredStandardCreate(BaseModel):
    standard_code: str
    standard_name: str | None = None
    is_core: bool = True
    sort_order: int = 0


class TargetMarketCreate(BaseModel):
    market_code: str
    market_name: str
    description: str | None = None


class RequiredTestOut(RequiredTestCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class RequiredCertificationOut(RequiredCertificationCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class RequiredStandardOut(RequiredStandardCreate):
    id: int
    target_market_id: int
    model_config = ConfigDict(from_attributes=True)


class TargetMarketOut(TargetMarketCreate):
    id: int
    org_id: int | None = None
    created_at: datetime
    updated_at: datetime
    required_tests: list[RequiredTestOut] = []
    required_certifications: list[RequiredCertificationOut] = []
    required_standards: list[RequiredStandardOut] = []
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ Phase 6 S2 — 认证中心核心 Schema ═══════════════

# --- CertificationRequirement ---

class CertificationRequirementCreate(BaseModel):
    project_id: int
    target_market_id: int
    cert_type: str
    cert_body: Optional[str] = None
    is_mandatory: bool = True
    status: Optional[str] = None
    source_type: Optional[str] = None
    org_id: Optional[int] = None


class CertificationRequirementUpdate(BaseModel):
    cert_body: Optional[str] = None
    is_mandatory: Optional[bool] = None
    status: Optional[str] = None


class CertificationRequirementOut(BaseModel):
    id: int
    project_id: int
    target_market_id: int
    cert_type: str
    cert_body: Optional[str] = None
    is_mandatory: bool = True
    status: str
    source_type: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificationProject ---

class CertificationProjectCreate(BaseModel):
    code: Optional[str] = None
    name: str
    project_id: int
    target_market_id: int
    cert_types: Optional[str] = None
    status: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificationProjectUpdate(BaseModel):
    name: Optional[str] = None
    cert_types: Optional[str] = None
    status: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None


class CertificationProjectOut(BaseModel):
    id: int
    code: str
    name: str
    project_id: int
    target_market_id: int
    cert_types: Optional[str] = None
    status: str
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificationSample ---

class CertificationSampleCreate(BaseModel):
    cert_project_id: int
    prototype_id: int
    cert_type: str
    sample_no: Optional[str] = None
    status: Optional[str] = None
    submitted_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificationSampleUpdate(BaseModel):
    cert_type: Optional[str] = None
    status: Optional[str] = None
    submitted_date: Optional[date] = None
    remark: Optional[str] = None


class CertificationSampleOut(BaseModel):
    id: int
    cert_project_id: int
    prototype_id: int
    cert_type: str
    sample_no: str
    status: str
    submitted_date: Optional[date] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificationExecution ---

class CertificationExecutionCreate(BaseModel):
    cert_sample_id: int
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    result_summary: Optional[str] = None
    org_id: Optional[int] = None


class CertificationExecutionUpdate(BaseModel):
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    result_summary: Optional[str] = None


class CertificationExecutionOut(BaseModel):
    id: int
    cert_sample_id: int
    lab: Optional[str] = None
    agency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    result_summary: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificationResult ---

class CertificationResultCreate(BaseModel):
    cert_execution_id: int
    status: Optional[str] = None
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None


class CertificationResultUpdate(BaseModel):
    status: Optional[str] = None
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None


class CertificationResultOut(BaseModel):
    id: int
    cert_execution_id: int
    status: str
    result_date: Optional[date] = None
    summary: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Certificate ---

class CertificateCreate(BaseModel):
    cert_result_id: int
    cert_no: str
    cert_type: str
    issuing_body: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    attachments: Optional[str] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None


class CertificateUpdate(BaseModel):
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    attachments: Optional[str] = None
    remark: Optional[str] = None


class CertificateOut(BaseModel):
    id: int
    cert_result_id: int
    cert_no: str
    cert_type: str
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    attachments: Optional[str] = None
    remark: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificateVersion ---

class CertificateVersionCreate(BaseModel):
    certificate_id: int
    version_no: str
    cert_no: str
    issuing_body: Optional[str] = None
    issue_date: date
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    change_reason: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None


class CertificateVersionOut(BaseModel):
    id: int
    certificate_id: int
    version_no: str
    cert_no: str
    issuing_body: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    change_reason: Optional[str] = None
    attachments: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- CertificationGateRule ---

class CertificationGateRuleCreate(BaseModel):
    name: str
    gate_code: str
    target_market_id: Optional[int] = None
    cert_type: str
    is_required: bool = True
    auto_block: bool = False
    priority: int = 100
    status: Optional[str] = None
    org_id: Optional[int] = None


class CertificationGateRuleUpdate(BaseModel):
    name: Optional[str] = None
    gate_code: Optional[str] = None
    target_market_id: Optional[int] = None
    cert_type: Optional[str] = None
    is_required: Optional[bool] = None
    auto_block: Optional[bool] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class CertificationGateRuleOut(BaseModel):
    id: int
    name: str
    gate_code: str
    target_market_id: Optional[int] = None
    cert_type: str
    is_required: bool = True
    auto_block: bool = False
    priority: int = 100
    status: str
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- ChangeImpactRule ---

class ChangeImpactRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_value: str
    affected_cert_types: str
    impact_level: str
    is_active: bool = True
    org_id: Optional[int] = None


class ChangeImpactRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    affected_cert_types: Optional[str] = None
    impact_level: Optional[str] = None
    is_active: Optional[bool] = None


class ChangeImpactRuleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_value: str
    affected_cert_types: str
    impact_level: str
    is_active: bool = True
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- ChangeImpactRecord (只读) ---

class ChangeImpactRecordOut(BaseModel):
    id: int
    ecr_id: Optional[int] = None
    prototype_id: int
    changed_part: Optional[str] = None
    matched_rule_id: Optional[int] = None
    impact_level: str
    affected_cert_types: str
    analysis_detail: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ═══════════════ Phase 6 S3 — ECR/ECO 工程变更控制 ═══════════════

# --- ECR 附件 ---

class ECRAttachmentOut(BaseModel):
    """ECR附件输出"""
    id: int
    ecr_id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: int = 0
    uploaded_by: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- ECR ---

class ECRCreate(BaseModel):
    """创建ECR"""
    title: str = Field(min_length=1, max_length=200)
    ecr_type: str = "other"
    reason: str = Field(min_length=1)
    urgency: str = "medium"
    affected_products: Optional[str] = None
    affected_documents: Optional[str] = None
    description: Optional[str] = None


class ECRUpdate(BaseModel):
    """更新ECR"""
    title: Optional[str] = None
    ecr_type: Optional[str] = None
    reason: Optional[str] = None
    urgency: Optional[str] = None
    affected_products: Optional[str] = None
    affected_documents: Optional[str] = None
    description: Optional[str] = None


class ECROut(BaseModel):
    """ECR列表输出"""
    id: int
    code: str
    title: str
    ecr_type: str
    reason: str
    urgency: str
    affected_products: Optional[dict] = None
    affected_documents: Optional[dict] = None
    description: Optional[str] = None
    status: str
    workflow_id: Optional[int] = None
    submitter_id: int
    submitter_name: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    attachment_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ECRDetailOut(ECROut):
    """ECR详情输出（含附件+关联ECO）"""
    attachments: list[ECRAttachmentOut] = []
    eco_code: Optional[str] = None
    eco_id: Optional[int] = None
    eco_status: Optional[str] = None


class ECRSummaryOut(BaseModel):
    """ECR简要信息（用于ECO关联展示）"""
    id: int
    code: str
    title: str
    ecr_type: str
    status: str
    submitter_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ECRRejectRequest(BaseModel):
    """驳回ECR"""
    rejection_reason: str = Field(min_length=1)


# --- ECO 明细项 ---

class ECOItemCreate(BaseModel):
    """创建ECO明细项"""
    change_type: str
    object_type: str
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemUpdate(BaseModel):
    """更新ECO明细项"""
    change_type: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[int] = None
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: Optional[str] = None


class ECOItemOut(ECOItemCreate):
    """ECO明细项输出"""
    id: int
    eco_id: int
    seq: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- ECO ---

class ECOCreate(BaseModel):
    """创建ECO"""
    ecr_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    change_summary: str = Field(min_length=1)
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None
    items: list[ECOItemCreate] = []


class ECOUpdate(BaseModel):
    """更新ECO"""
    title: Optional[str] = None
    change_summary: Optional[str] = None
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None


class ECOOut(BaseModel):
    """ECO列表输出"""
    id: int
    code: str
    ecr_id: Optional[int] = None
    title: str
    change_summary: str
    implementation_plan: Optional[str] = None
    effective_date: Optional[date] = None
    status: str
    created_by: int
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    closed_at: Optional[datetime] = None
    org_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class ECODetailOut(ECOOut):
    """ECO详情输出（含明细项+关联ECR）"""
    items: list[ECOItemOut] = []
    ecr_code: Optional[str] = None
    ecr_title: Optional[str] = None


class ECOSummaryOut(BaseModel):
    """ECO简要信息（用于ECR关联展示）"""
    id: int
    code: str
    title: str
    status: str
    effective_date: Optional[date] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ECOChDashboardOut(BaseModel):
    """ECO变更看板"""
    status_summary: dict[str, int] = {}
    type_distribution: dict[str, int] = {}
    this_month_new: int = 0
    pending_verification: int = 0
    changes: list[ECOOut] = []
