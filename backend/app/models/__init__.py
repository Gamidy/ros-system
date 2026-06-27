"""模型初始化"""
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.product import Platform, Product, Version, Market, ManufacturingVariant
from app.models.bom import PartCategory, Part, PartAVL, BOM, BOMItem
from app.models.project import Program, Project, ProjectGate, Milestone, Task, Risk
from app.models.test import TestRequest, TestResult, MQVerification, Certification, Prototype, QualityIssue, ECR, ECN
from app.models.alert import AlertRule, Alert, Notification
from app.models.webhook import WebhookDeliveryLog
from app.models.webhook_subscription import WebhookSubscription
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.audit import AuditLog
from app.models.pm_config import CertStandard, PerfDefault, MarketCertification, MarketCompressor
from app.models.pm_accessory import AccessoryDefault, FeatureDefault
from app.models.competitor import CompetitorModel
from app.models.alert import Alert, AlertRule
from app.models.team_role_template import TeamRoleTemplate
from app.models.role_position_mapping import RolePositionMapping
from app.models.material_component_template import MaterialComponentTemplate
from app.models.capacity_unit_cost import CapacityUnitCost
from app.models.indirect_cost_config import IndirectCostConfig
from app.models.trial_qty_config import TrialQtyConfig
from app.models.annual_plan import AnnualPlan
from app.models.product_plan import ProductPlan, Cost, ProductPlanProjectLink, ProductPlanStage, CostType, BOMType, ProductRequirement, ProductPlanReview, ProductPlanHistory
from app.models.event_log import EventLog
from app.models.verification_requirement import VerificationRequirement
from app.models.test_execution import TestExecution
from app.models.gate_rule import GateRule, GateRuleItem, GateEvalRecord
from app.models.target_market import TargetMarket, RequiredTest, RequiredCertification, RequiredStandard
from app.models.certification import (
    CertificationRequirement,
    CertificationProject,
    CertificationSample,
    CertificationExecution,
    CertificationResult,
    Certificate,
    CertificateVersion,
)
from app.models.change_impact import ChangeImpactRule, ChangeImpactRecord
from app.models.cert_gate_rule import CertificationGateRule
from app.models.cert_auto_gen import CertAutoGenLog
from app.models.notification_channel import NotificationChannel
from app.models.notification_log import NotificationLog
from app.models.user_notification_pref import UserNotificationPref
from app.models.ecr_eco import ECRAttachment, ECRRequest, ECO, ECOItem
from app.models.safety import (
    SafetyStandard, SafetyInspectionItem,
    SupplierSafetyQualification, SupplierSafetyAuditRecord,
)
from app.models.manufacturability import (
    DFMChecklist, DFMReport, DFMReportItem, DFMScoreWeight,
)
from app.models.outsource import (
    OutsourcePartner, OutsourceOrder, OutsourceOrderItem,
    OutsourceQualityRecord, OutsourceQualityFile,
)
from app.models.product_plan_subs import (
    ProductPlanInitiation, ProductPlanMarket,
    ProductPlanTechSpec, ProductPlanTeam,
)
from app.models.cost_accounting import (
    CostAccountingPeriod, CostAccountingSheet, CostAccountingItem,
    LaborRateConfig, ProductLaborCost,
    OverheadAllocationRule, ProductOverheadCost,
)
from app.models.cost_alert_rule import CostAlertRule, AlertEvent
from app.models.ai_config import AIConfig
from app.models.ai_call_log import AICallLog
from app.models.password_reset import PasswordResetToken
from app.models.workflow_transition_spec import WorkflowTransitionSpec
from app.models.plan_validation import ValidationRule
from app.models.review_template import ReviewTemplate

__all__ = [
    "User",
    "Organization", "OrganizationMember",
    "Platform", "Product", "Version", "Market", "ManufacturingVariant",
    "PartCategory", "Part", "PartAVL", "BOM", "BOMItem",
    "Program", "Project", "ProjectGate", "Milestone", "Task", "Risk",
    "TestRequest", "TestResult", "MQVerification", "Certification", "Prototype", "QualityIssue", "ECR", "ECN",
    "AlertRule", "Alert", "Notification",
    "WebhookSubscription", "WebhookDeliveryLog",
    "ApprovalChain", "ApprovalStep", "ApprovalRequest", "ApprovalRecord",
    "PurchaseOrder", "PurchaseOrderItem", "Supplier",
    "AuditLog",
    "CertStandard", "PerfDefault", "MarketCertification", "MarketCompressor",
    "CompetitorModel",
    "AccessoryDefault", "FeatureDefault",
    "TeamRoleTemplate",
    "RolePositionMapping",
    "MaterialComponentTemplate",
    "CapacityUnitCost",
    "IndirectCostConfig",
    "TrialQtyConfig",
    "AnnualPlan",
    "ProductPlan", "Cost", "ProductPlanProjectLink", "ProductPlanStage", "CostType", "BOMType",
    "ProductRequirement",
    "VerificationRequirement",
    "TestExecution",
    "GateRule", "GateRuleItem", "GateEvalRecord",
    "TargetMarket", "RequiredTest", "RequiredCertification", "RequiredStandard",
    "CertificationRequirement",
    "CertificationProject",
    "CertificationSample",
    "CertificationExecution",
    "CertificationResult",
    "Certificate",
    "CertificateVersion",
    "ChangeImpactRule",
    "ChangeImpactRecord",
    "CertificationGateRule",
    "CertAutoGenLog",
    "NotificationChannel",
    "NotificationLog",
    "UserNotificationPref",
    "ECRAttachment",
    "ECRRequest",
    "ECO",
    "ECOItem",
    "SafetyStandard",
    "SafetyInspectionItem",
    "SupplierSafetyQualification",
    "SupplierSafetyAuditRecord",
    "DFMChecklist",
    "DFMReport",
    "DFMReportItem",
    "DFMScoreWeight",
    "OutsourcePartner",
    "OutsourceOrder",
    "OutsourceOrderItem",
    "OutsourceQualityRecord",
    "OutsourceQualityFile",

    # product plan subs
    "ProductPlanInitiation",
    "ProductPlanMarket",
    "ProductPlanTechSpec",
    "ProductPlanTeam",

    # cost accounting
    "CostAccountingPeriod",
    "CostAccountingSheet",
    "CostAccountingItem",
    "LaborRateConfig",
    "ProductLaborCost",
    "OverheadAllocationRule",
    "ProductOverheadCost",
    # cost alert
    "CostAlertRule",
    "AlertEvent",
    # ai
    "AIConfig",
    "AICallLog",
    "PasswordResetToken",
    "WorkflowTransitionSpec",
    "ValidationRule",
    "ReviewTemplate",
    "ProductPlanReview",
    "ProductPlanHistory",
]
