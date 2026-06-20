"""模型初始化"""
from app.models.user import User
from app.models.product import Platform, Product, Version, Market, ManufacturingVariant
from app.models.bom import PartCategory, Part, PartAVL, BOM, BOMItem
from app.models.project import Program, Project, ProjectGate, Milestone, Task, Risk
from app.models.test import TestRequest, TestResult, MQVerification, Certification, Prototype, QualityIssue, ECR, ECN
from app.models.alert import AlertRule, Alert, Notification
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.audit import AuditLog
from app.models.pm_config import CertStandard, PerfDefault
from app.models.pm_accessory import AccessoryDefault, FeatureDefault
from app.models.competitor import CompetitorModel
from app.models.proposal_approval import ProposalApproval
from app.models.team_role_template import TeamRoleTemplate
from app.models.role_position_mapping import RolePositionMapping
from app.models.material_component_template import MaterialComponentTemplate
from app.models.capacity_unit_cost import CapacityUnitCost
from app.models.indirect_cost_config import IndirectCostConfig
from app.models.trial_qty_config import TrialQtyConfig

__all__ = [
    "User",
    "Platform", "Product", "Version", "Market", "ManufacturingVariant",
    "PartCategory", "Part", "PartAVL", "BOM", "BOMItem",
    "Program", "Project", "ProjectGate", "Milestone", "Task", "Risk",
    "TestRequest", "TestResult", "MQVerification", "Certification", "Prototype", "QualityIssue", "ECR", "ECN",
    "AlertRule", "Alert", "Notification",
    "ApprovalChain", "ApprovalStep", "ApprovalRequest", "ApprovalRecord",
    "PurchaseOrder", "PurchaseOrderItem", "Supplier",
    "AuditLog",
    "CertStandard", "PerfDefault",
    "CompetitorModel",
    "AccessoryDefault", "FeatureDefault",
    "ProposalApproval",
    "TeamRoleTemplate",
    "RolePositionMapping",
    "MaterialComponentTemplate",
    "CapacityUnitCost",
    "IndirectCostConfig",
    "TrialQtyConfig",
]
