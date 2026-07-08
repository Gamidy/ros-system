"""角色-菜单权限映射模块 — 权限校验函数"""
from typing import Optional

from .permissions_data import (
    ALL_ROLES,
    SUPER_ROLES,
    SUPER_ORG_ADMIN_ROLES,
    ALL_MENUS,
    ROLE_MENU_MAP,
    MENU_PATH_MAP,
)


def get_allowed_menus(role: str) -> list[str]:
    """根据角色返回允许访问的菜单列表；超级角色返回全部菜单"""
    if role in SUPER_ROLES:
        return list(ALL_MENUS)
    return ROLE_MENU_MAP.get(role, [])


def is_valid_role(role: str) -> bool:
    """检查角色是否在合法角色列表中"""
    return role in ALL_ROLES


def is_super_role(role: str) -> bool:
    """检查是否为超级角色（admin 或 general_manager）"""
    return role in SUPER_ROLES


def get_allowed_paths(role: str) -> list[str]:
    """根据角色返回允许访问的前端路由路径列表，用于动态下发权限"""
    menus = get_allowed_menus(role)
    return [MENU_PATH_MAP[m] for m in menus if m in MENU_PATH_MAP]


def require_menu(menu_name: str):
    """
    FastAPI 依赖：检查当前用户角色是否有权限访问指定菜单。
    用法: @router.get("/path", dependencies=[Depends(require_menu("menu_name"))])
    """
    from fastapi import Depends, HTTPException
    from app.core.security import get_current_user

    def _check(user = Depends(get_current_user)):
        role = user.role if hasattr(user, 'role') else getattr(user, 'role', 'engineer')
        # 超级角色直接放行
        if role in SUPER_ROLES:
            return user
        allowed = ROLE_MENU_MAP.get(role, [])
        if menu_name not in allowed:
            raise HTTPException(status_code=403, detail="权限不足，无法访问该资源")
        return user
    return _check


def require_role(*roles: str):
    """FastAPI 依赖：检查当前用户角色是否在指定角色列表中

    admin / general_manager 为超级角色，自动放行。
    用法: @router.get(\"/path\", dependencies=[Depends(require_role(\"admin\", \"manager\"))])
    """
    from fastapi import Depends, HTTPException, status
    from app.core.security import get_current_user
    from app.models.user import User

    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role in SUPER_ROLES:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return current_user
    return checker


def require_org_access(required_org_id: int):
    """FastAPI 依赖：检查当前用户是否属于指定组织

    超级角色（admin / general_manager）不受组织限制，自动放行。
    普通用户必须 org_id 与 required_org_id 一致。

    用法: @router.get("/org/{org_id}/items", dependencies=[Depends(require_org_access(org_id))])
    """
    from fastapi import Depends, HTTPException
    from app.core.security import get_current_user

    def _check(current_user = Depends(get_current_user)):
        role = current_user.role
        if role in SUPER_ROLES:
            return current_user
        user_org_id = getattr(current_user, "org_id", None)
        if user_org_id != required_org_id:
            raise HTTPException(
                status_code=403,
                detail="无权访问该组织的资源",
            )
        return current_user
    return _check


def get_org_scoped_query(db_query, org_id: Optional[int] = None):
    """为 SQLAlchemy 查询自动添加 org_id 过滤

    如果传入了 org_id，则添加 WHERE org_id = <org_id> 条件。
    如果未传入，尝试从 TenantContext 获取当前请求的 org_id。
    如果都没有，返回原始查询（超级角色场景）。

    用法:
        query = db.query(ProductPlan)
        query = get_org_scoped_query(query, org_id=123)
        # 或从 TenantContext 自动获取
        query = get_org_scoped_query(query)
    """
    from app.core.tenant_context import TenantContext

    if org_id is None:
        org_id = TenantContext.get_org_id()
    if org_id is not None:
        # 检查模型是否有 org_id 列
        mapper = db_query.column_descriptions[0]["entity"]
        if hasattr(mapper, "org_id"):
            query = db_query.filter(mapper.org_id == org_id)
    return db_query
