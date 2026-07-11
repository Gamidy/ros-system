"""数据模型聚合 — 确保所有表在 Base.metadata 中注册"""

from app.models.base import TimestampMixin, Base
from app.models.user import User, Role, user_roles
from app.models.product import Platform, Series, Model
from app.models.bom import Material, SuperBOMNode

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Role",
    "user_roles",
    "Platform",
    "Series",
    "Model",
    "Material",
    "SuperBOMNode",
]
