"""多租户上下文管理

基于 contextvars 实现线程安全的 TenantContext，
通过 FastAPI Depends 中间件自动从 JWT 提取 org_id 并注入当前请求上下文。
"""
from contextvars import ContextVar
from typing import Optional

from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User
from app.core.permissions import SUPER_ORG_ADMIN_ROLES


class TenantContext:
    """线程安全的租户上下文 — 基于 contextvars

    使用方式:
        TenantContext.set_org_id(123)
        org_id = TenantContext.get_org_id()
        TenantContext.clear()
    """

    _org_id: ContextVar[Optional[int]] = ContextVar("tenant_org_id", default=None)

    @classmethod
    def set_org_id(cls, org_id: int) -> None:
        """设置当前请求的 org_id"""
        cls._org_id.set(org_id)

    @classmethod
    def get_org_id(cls) -> Optional[int]:
        """获取当前请求的 org_id，没有则返回 None"""
        return cls._org_id.get(None)

    @classmethod
    def clear(cls) -> None:
        """清除当前请求的 org_id"""
        cls._org_id.set(None)


def get_current_org(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """FastAPI Depends 中间件 — 从当前用户 JWT 中提取 org_id 并注入 TenantContext

    自动从当前已认证用户的 JWT payload 中读取 org_id，
    写入 TenantContext 供后续业务查询自动过滤。

    对于超级角色（admin / general_manager），允许跨组织访问，
    不强制绑定 org_id 过滤。
    """
    org_id = getattr(current_user, "org_id", None)
    if org_id is not None:
        TenantContext.set_org_id(org_id)
    return org_id


def require_org_admin(current_user: User = Depends(get_current_user)) -> User:
    """检查当前用户是否是组织管理员

    满足以下任一条件即放行：
    1. 超级角色（admin / general_manager）
    2. 用户 is_org_admin == True

    注意：这里检查的是「组织管理员」身份，
    不检查全局超级角色 SUPER_ORG_ADMIN_ROLES。
    """
    role = current_user.role
    if role in SUPER_ORG_ADMIN_ROLES:
        return current_user
    if getattr(current_user, "is_org_admin", False):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="需要组织管理员权限",
    )
