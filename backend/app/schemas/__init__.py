"""ROS 全模块 Schema — 统一导入入口

所有 Schema 类按域拆分到独立文件，本文件负责 re-export。
使用方式不变：from app.schemas import UserCreate, PlatformOut, ...
"""

# ═══════════════ 认证与用户管理 ═══════════════
from .auth import (
    UserCreate,
    UserOut,
    LoginRequest,
    Token,
    AccountApplicationCreate,
    AccountApplicationOut,
    AccountApplicationReview,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    VerifyResetTokenRequest,
    AdminResetPasswordRequest,
)

# ═══════════════ 产品管理 ═══════════════
from .product import (
    PlatformCreate,
    PlatformUpdate,
    PlatformOut,
    ProductCreate,
    ProductUpdate,
    ProductOut,
    VersionCreate,
    VersionStatusUpdate,
    VersionOut,
    ManufacturingVariantCreate,
    ManufacturingVariantOut,
    MarketCreate,
    MarketOut,
    ProductMarketAssign,
    VersionRuleRequest,
    VersionRuleResponse,
)

# ═══════════════ BOM与物料管理 ═══════════════
from .bom import (
    PartCreate,
    PartOut,
    PartAVLCreate,
    PartAVLOut,
    PartUpdate,
    PartDetailOut,
    BOMCreate,
    BOMUpdate,
    BOMOut,
    BOMItemCreate,
    BOMItemOut,
    AlternativeAssign,
    BOMTreeItem,
    BOMTreeOut,
    BOMCostByLevel,
    BOMCostNode,
    BOMCostSummaryOut,
)

# ═══════════════ 审批工作流 ═══════════════
from .approval import (
    ApprovalStepCreate,
    ApprovalStepOut,
    ApprovalChainCreate,
    ApprovalChainOut,
    ApprovalRequestCreate,
    ApprovalRequestOut,
    ApprovalRecordOut,
    ApprovalDecision,
)

# ═══════════════ 项目管理 ═══════════════
from .project import (
    ProgramCreate,
    ProgramOut,
    ProjectCreate,
    ProjectDraftSave,
    ProjectUpdate,
    ProjectOut,
    ProjectGateCreate,
    ProjectGateOut,
    GateStatusUpdate,
    MilestoneCreate,
    MilestoneOut,
    TaskCreate,
    TaskOut,
    RiskCreate,
    RiskOut,
    IssueUpdate,
)

# ═══════════════ 测试与MQ验证 ═══════════════
from .testing import (
    TestResultCreate,
    TestResultOut,
    TestRequestCreate,
    TestRequestOut,
    MQVerificationCreate,
    MQVerificationOut,
)

# ═══════════════ 认证/样机/品质管理 ═══════════════
from .cert_proto_quality import (
    CertificationCreate,
    CertificationOut,
    PrototypeCreate,
    PrototypeOut,
    QualityIssueCreate,
    QualityIssueOut,
)

# ═══════════════ 安规管理 ═══════════════
from .safety import (
    SafetyStandardCreate,
    SafetyStandardUpdate,
    SafetyStandardOut,
    SafetyStandardListOut,
    SafetyInspectionItemCreate,
    SafetyInspectionItemUpdate,
    SafetyInspectionItemOut,
    SafetyInspectionItemListOut,
    SupplierSafetyQualificationCreate,
    SupplierSafetyQualificationUpdate,
    SupplierSafetyQualificationOut,
    SupplierSafetyQualificationListOut,
    SafetyAuditRecordCreate,
    SafetyAuditRecordUpdate,
    SafetyAuditRecordOut,
    SafetyAlertItem,
    SafetyAlertListOut,
)

# ═══════════════ 外协管理 ═══════════════
from .outsource import (
    OutsourcePartnerCreate,
    OutsourcePartnerUpdate,
    OutsourcePartnerOut,
    OutsourcePartnerListOut,
    OutsourceOrderItemBase,
    OutsourceOrderItemOut,
    OutsourceOrderCreate,
    OutsourceOrderUpdate,
    OutsourceOrderOut,
    OutsourceOrderListOut,
    OutsourceQualityRecordCreate,
    OutsourceQualityRecordUpdate,
    OutsourceQualityRecordOut,
    OutsourceQualityRecordListOut,
)

# ═══════════════ DFM可制造性分析 ═══════════════
from .manufacturability import (
    DFMChecklistCreate,
    DFMChecklistUpdate,
    DFMChecklistOut,
    DFMChecklistListOut,
    DFMReportCreate,
    DFMReportUpdate,
    DFMReportItemOut,
    DFMReportOut,
    DFMReportListOut,
    DFMReportItemCreate,
    DFMReportItemUpdate,
    DFMScoreWeightCreate,
    DFMScoreWeightUpdate,
    DFMScoreWeightOut,
    DFMScoreWeightListOut,
    DFMScoreResult,
)

# ═══════════════ 预警与通知 ═══════════════
from .alert import (
    AlertRuleCreate,
    AlertRuleOut,
    AlertOut,
    NotificationOut,
    NotificationPageOut,
    BatchDeleteRequest,
)

# ═══════════════ 通知已读/未读跨渠道同步 ═══════════════
from .notification_read import (
    NotificationReadRequest,
    NotificationReadOut,
    NotificationReadStatusOut,
)

# ═══════════════ 驾驶舱仪表盘 ═══════════════
from .dashboard import (
    DashboardSummary,
    Layer1SystemHealth,
    RecentProjectSummary,
    Layer2ProjectOps,
    Layer4ACMetrics,
    DashboardResponse,
    KpiDetailItem,
    AlertItem,
    AlertsSummaryResponse,
)

# ═══════════════ 采购管理 ═══════════════
from .purchase import (
    SupplierCreate,
    SupplierUpdate,
    SupplierOut,
    EvaluationCreate,
    EvaluationOut,
    SupplierStatsOut,
    PurchaseOrderItemCreate,
    PurchaseOrderItemUpdate,
    PurchaseOrderItemOut,
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
    PurchaseOrderOut,
    PurchaseOrderDetailOut,
    PurchaseDashboardOut,
)

# ═══════════════ 外协送样管理 ═══════════════
from .outsource_sample import (
    OutsourceRequestCreate,
    OutsourceRequestUpdate,
    OutsourceRequestOut,
)

# ═══════════════ ECR/ECN 工程变更（旧版） ═══════════════
from .ecr_ecn import (
    ECRCreate as ECRCreateV1,
    ECROut as ECROutV1,
    ECNCreate,
    ECNOut,
)

# ═══════════════ Phase 6 S1 — 验证需求/测试执行/门控/目标市场 ═══════════════
from .phase6_s1 import (
    VerificationRequirementCreate,
    VerificationRequirementOut,
    VerificationRequirementGenerateRequest,
    TestExecutionCreate,
    TestExecutionOut,
    GateRuleItemCreate,
    GateRuleCreate,
    GateRuleItemOut,
    GateRuleOut,
    GateRuleEvalRequest,
    RequiredTestCreate,
    RequiredCertificationCreate,
    RequiredStandardCreate,
    TargetMarketCreate,
    RequiredTestOut,
    RequiredCertificationOut,
    RequiredStandardOut,
    TargetMarketOut,
)

# ═══════════════ Phase 6 S2 — 认证中心 ═══════════════
from .phase6_s2 import (
    CertificationRequirementCreate,
    CertificationRequirementUpdate,
    CertificationRequirementOut,
    CertificationProjectCreate,
    CertificationProjectUpdate,
    CertificationProjectOut,
    CertificationSampleCreate,
    CertificationSampleUpdate,
    CertificationSampleOut,
    CertificationExecutionCreate,
    CertificationExecutionUpdate,
    CertificationExecutionOut,
    CertificationResultCreate,
    CertificationResultUpdate,
    CertificationResultOut,
    CertificateCreate,
    CertificateUpdate,
    CertificateOut,
    CertificateVersionCreate,
    CertificateVersionOut,
    CertificationGateRuleCreate,
    CertificationGateRuleUpdate,
    CertificationGateRuleOut,
    ChangeImpactRuleCreate,
    ChangeImpactRuleUpdate,
    ChangeImpactRuleOut,
    ChangeImpactRecordOut,
)

# ═══════════════ Phase 6 S3 — ECR/ECO 工程变更控制 ═══════════════
from .ecr_eco import (
    ECRAttachmentOut,
    ECRCreate,
    ECRUpdate,
    ECROut,
    ECRDetailOut,
    ECRSummaryOut,
    ECRRejectRequest,
    ECOItemCreate,
    ECOItemUpdate,
    ECOItemOut,
    ECOCreate,
    ECOUpdate,
    ECOOut,
    ECODetailOut,
    ECOSummaryOut,
    ECOChDashboardOut,
)

# ═══════════════ 产品策划-项目关联 ═══════════════
from .product_plan_link import (
    ProductPlanProjectLinkOut,
    ProductPlanProjectLinkCreate,
    ProductPlanProjectLinkUpdate,
)

# ═══════════════ BI分析看板 ═══════════════
from .bi import (
    TrendItem,
    TrendResponse,
    FunnelItem,
    FunnelResponse,
    DistributionItem,
    DistributionResponse,
)

# ═══════════════════════════════════════════════════
# CIE v2.0 — Risk Engine / Impact Graph / Feedback
# ═══════════════════════════════════════════════════
from .ci_v2 import (
    RiskLevelEnum,
    RecommendationEnum,
    SignalInput,
    RiskAssessmentOut,
    ImpactNode,
    ImpactEdge,
    ImpactGraphOut,
    RipplePath,
    ApprovalAdvisorAction,
    ApprovalRecommendation,
    RiskAssessmentApiResponse,
    ACTUAL_OUTCOME_CHOICES,
    PredictionOutcomeCreate,
    PredictionOutcomeOut,
    ModelWeightsOut,
)
