"""数据模型聚合"""

from app.models.base import TimestampMixin, Base
from app.models.user import User, Role, user_roles
from app.models.product import Platform, Series, Model
from app.models.bom import Material, SuperBOMNode
from app.models.feature import FeatureFamily, FeatureOption
from app.models.project import Project, WBSNode, Task, Gate, PhaseEnum, GateDecision
from app.models.ecr_eco import ECRAttachment, ECRRequest, ECO, ECOItem
from app.models.config_rule import ConfigGroup, ConfigRule

__all__ = [
    "Base", "TimestampMixin",
    "User", "Role", "user_roles",
    "Platform", "Series", "Model",
    "Material", "SuperBOMNode",
    "FeatureFamily", "FeatureOption",
    "Project", "WBSNode", "Task", "Gate",
    "PhaseEnum", "GateDecision",
    "ECRAttachment", "ECRRequest", "ECO", "ECOItem",
    "ConfigGroup", "ConfigRule",
]
