"""ROS 全模块 Schema: 认证 + Product + BOM + 项目 + 测试/认证/样机/品质"""
from pydantic import BaseModel, Field, EmailStr
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

class MarketOut(MarketCreate):
    is_active: str = "true"
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
    position_no: Optional[str] = None
    remark: Optional[str] = None
    children: list["BOMTreeItem"] = []


class BOMTreeOut(BaseModel):
    bom: BOMOut
    tree: list[BOMTreeItem]


# ═══════════════ 审批流 Schema ═══════════════

class ApprovalStepCreate(BaseModel):
    seq: int
    role: str
    name: str

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
    request_type: str = Field(pattern="^(ecr|purchase|register)$")
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
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    program_id: Optional[int] = None
    product_code: Optional[str] = None
    project_class: str = Field(pattern="^(T|A|B|C)$")
    source: Optional[str] = None
    source_category: Optional[str] = None
    dev_modules: Optional[str] = None
    change_impacts: Optional[str] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    critical_path: Optional[str] = None


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
    trigger_mode: str = "engineer"
    requester: str
    requirement: Optional[str] = None
    sample_info: Optional[str] = None
    priority: str = "medium"
    target_date: Optional[date] = None


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
