"""角色-菜单权限映射模块"""
from typing import Optional

# 全部有效角色（21种正式角色 + engineer 为向后兼容的默认角色）
ALL_ROLES = [
    "admin",
    "general_manager",
    "rd_director",
    "product_manager",
    "systems_engineer",
    "structural_engineer",
    "electrical_control_engineer",
    "electrical_engineer",
    "procurement",
    "quality_engineer",
    "process_engineer",
    "project_admin",
    "production",
    "module_manager",          # 模块经理（通用）
    "module_manager_struct",   # 结构模块经理
    "module_manager_sys",      # 系统模块经理
    "finance_manager",         # 财务经理
    "process_manager",         # 工艺经理
    "procurement_director",    # 采购总监
    "security_officer",        # IT安全员
    "engineer",                # 向后兼容：原系统默认角色
]

# 超级角色 — 拥有全部菜单权限
SUPER_ROLES = ["admin", "general_manager"]

# 组织管理员角色 — 拥有组织级管理权限
SUPER_ORG_ADMIN_ROLES = ["admin", "general_manager"]

# 全部菜单列表
ALL_MENUS = [
    "dashboard",        # 驾驶舱
    "products",         # 产品主线
    "bom",              # BOM物料
    "projects",         # 项目
    "tests",            # 实验测试
    "alerts",           # 预警
    "certifications",   # 认证
    "prototypes",       # 样机
    "quality",          # 质量
    "changes",          # 变更
    "approvals",        # 审批
    "pm-workspace",     # 产品经理工作台
    "competitor_bench", # 竞品对标
    "market_mgmt",      # 市场管理
    "purchases",        # 采购
    "rd_dashboard",     # 研发总监
    "product-plans",     # 产品策划
    "mm",               # 模块管理
    "event-timeline",   # 事件时间线
    "saga-viewer",      # Saga事务
    "risk-dashboard",   # 智能决策看板
    "admin-config",     # 系统设置（仅admin）
    "verification-requirements",  # 验证需求
    "gate-rules",       # Gate规则引擎
    "target-markets",   # 目标市场
    "test-executions",  # 实验执行
    # Phase 6 S2 — 认证中心菜单
    "cert-requirements",       # 认证需求
    "cert-projects",           # 认证项目
    "cert-samples",            # 认证样机
    "cert-executions",         # 认证执行
    "cert-results",            # 认证结果
    "certificates",            # 证书管理
    "cert-gate-rules",         # 认证门禁规则
    # Phase 6 S3 — ECR/ECO 工程变更控制
    "ecr",                     # ECR变更申请
    "eco",                     # ECO变更指令
    # P0-6 — 安规管理
    "safety-standards",        # 安全标准库
    "safety-inspection-items", # 安规检测项
    "safety-supplier-qual",    # 供应商安规
    "safety-alerts",           # 安规预警
    # P0-8 — DFM可制造性分析
    "dfm-checklist",           # DFM检查项模板
    "dfm-reports",             # DFM分析报告
    # P0-7 — 外协管理
    "outsource-partners",      # 外协厂商
    "outsource-orders",        # 外协订单
    "outsource-quality",       # 外协质检
    # S4 — 成本核算
    "cost-accounting",         # 成本核算
    # D1 — BI分析看板
    "bi-analytics",            # BI分析看板
    # D3 — 消息通知
    "notification-settings",   # 用户通知偏好设置
]

# 角色 → 菜单 映射表
ROLE_MENU_MAP: dict[str, list[str]] = {
    "admin": ALL_MENUS,
    "general_manager": ALL_MENUS,
    "rd_director": [
        "dashboard", "products", "bom", "projects", "tests",
        "certifications", "prototypes", "quality", "changes",
        'alerts', 'approvals', 'rd_dashboard', 'purchases',
        'pm-workspace', 'competitor_bench',
        'product-plans', 'verification-requirements', 'gate-rules',
        'risk-dashboard', 'event-timeline',
        'target-markets', 'test-executions',
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
 # S3 ECR/ECO
 'ecr', 'eco',
 # P0-6 安规管理
 'safety-standards', 'safety-inspection-items', 'safety-supplier-qual', 'safety-alerts',
 # S4 成本核算
 'cost-accounting',
 # D1 BI分析看板
 'bi-analytics',
 ],
 "product_manager": [
        "dashboard", "products", "bom", "projects",
        'certifications', 'alerts', 'approvals', 'pm-workspace',
        'competitor_bench', 'market_mgmt',
        'product-plans', 'target-markets', 'gate-rules',
        'verification-requirements', 'test-executions',
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S4 成本核算
        'cost-accounting',
        # D1 BI分析看板
        'bi-analytics',
    ],
    "systems_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "changes",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "structural_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "changes",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',

        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "electrical_control_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "changes", "certifications",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "electrical_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "changes", "certifications",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items', 'safety-supplier-qual',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "procurement": [
        "dashboard", "bom", "purchases", "alerts", "projects",
        "products", "certifications",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # P0-7 外协管理
        'outsource-partners', 'outsource-orders', 'outsource-quality',
    ],
    "quality_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "quality", "alerts", "certifications",
        "prototypes", "changes",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
        # P0-7 外协管理
        'outsource-partners', 'outsource-orders', 'outsource-quality',
    ],
    "process_engineer": [
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "certifications", "alerts",
        "verification-requirements", "test-executions",
        "target-markets",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
    ],
    "project_admin": [
        "dashboard", "projects", "alerts", "changes",
        "products", "bom", "tests", "prototypes", "approvals",
        "verification-requirements", "test-executions",
        # S3 ECR/ECO
        'ecr', 'eco',
        # D1 BI分析看板
        'bi-analytics',
    ],
    "production": [
        "dashboard", "bom", "quality", "alerts", "projects",
        "products", "prototypes",
    ],
    "module_manager": [  # 模块经理（通用）— BOM + 样机 + 质量 + 预警 + 审批
        "dashboard", "products", "bom", "projects",
        "prototypes", "quality", "alerts", "approvals",
        "tests", "certifications", "changes", "mm",
        "verification-requirements", "test-executions",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "module_manager_struct": [  # 结构模块经理 — 侧重结构
        "dashboard", "products", "bom", "projects",
        "prototypes", "quality", "alerts", "approvals",
        "tests", "certifications", "changes",
        "verification-requirements", "test-executions",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
    ],
    "module_manager_sys": [  # 系统模块经理 — 侧重系统性能
        "dashboard", "products", "bom", "projects", "tests",
        "prototypes", "quality", "alerts", "approvals",
        "certifications", "changes",
        "verification-requirements", "test-executions",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],
    "finance_manager": [  # 财务经理 — 成本核算
        "dashboard", "products", "bom",
        "projects", "purchases", "alerts", "approvals",
        # S4 成本核算
        "cost-accounting",
        # D1 BI分析看板
        "bi-analytics",
    ],
    "process_manager": [  # 工艺经理 — 管理工艺+审批
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "approvals",
        "verification-requirements", "test-executions",
    ],
    "procurement_director": [  # 采购总监 — 管理采购+审批
        "dashboard", "bom", "purchases", "alerts", "approvals", "projects",
        "products", "prototypes", "tests",
        "verification-requirements", "test-executions",
    ],
    "security_officer": [
        "dashboard", "alerts", "approvals",
        "products", "bom", "projects", "tests",
        "certifications", "prototypes", "quality", "changes",
        # S2 认证中心
        'cert-requirements', 'cert-projects', 'cert-samples',
        'cert-executions', 'cert-results', 'certificates', 'cert-gate-rules',
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
    ],  # IT安全员 — 裁剪权限（去掉 purchases, rd_dashboard, mm）
    "engineer": [  # 向后兼容：原系统默认角色，基础工程权限
        "dashboard", "products", "bom", "projects",
        "tests", "prototypes", "changes",
        "competitor_bench", "target-markets",
        "verification-requirements", "test-executions",
        # S3 ECR/ECO
        'ecr', 'eco',
        # P0-6 安规管理
        'safety-standards', 'safety-inspection-items',
        # P0-8 DFM
        'dfm-checklist', 'dfm-reports',
        # D3 用户通知偏好
        'notification-settings',
    ],
}


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


# 菜单名 → 前端路由路径映射（用于 /auth/me 返回 allowed_paths）
MENU_PATH_MAP: dict[str, str] = {
    "dashboard": "/dashboard",
    "products": "/products",
    "bom": "/bom",
    "projects": "/projects",
    "tests": "/tests",
    "alerts": "/alerts",
    "certifications": "/certifications",
    "prototypes": "/prototypes",
    "quality": "/quality",
    "changes": "/changes",
    "approvals": "/approvals",
    "purchases": "/purchases",
    "rd_dashboard": "/rd-dashboard",
    "mm": "/mm",
    "pm-workspace": "/pm-workspace",
    "competitor_bench": "/competitor-bench",
    "market_mgmt": "/market-mgmt",
    "product-plans": "/product-plans",
    "event-timeline": "/event-timeline",
    "saga-viewer": "/saga-viewer",
    "risk-dashboard": "/risk-dashboard",
    "admin-config": "/admin-config",
    "verification-requirements": "/tests/verification-requirements",
    "gate-rules": "/tests/gate-rules",
    "target-markets": "/tests/target-markets",
    # Phase 6 S2 — 认证中心
    "cert-requirements": "/s2/requirements",
    "cert-projects": "/s2/projects",
    "cert-samples": "/s2/samples",
    "cert-executions": "/s2/executions",
    "cert-results": "/s2/results",
    "certificates": "/s2/certificates",
    "cert-gate-rules": "/s2/gate-rules",
    # Phase 6 S3 — ECR/ECO
    "ecr": "/ecr",
    "eco": "/eco",
    # P0-6 安规管理
    "safety-standards": "/safety/standards",
    "safety-inspection-items": "/safety/inspection-items",
    "safety-supplier-qual": "/safety/supplier-qualifications",
    "safety-alerts": "/safety/alerts",
    # P0-8 DFM可制造性分析
    "dfm-checklist": "/dfm/checklist",
    "dfm-reports": "/dfm/reports",
    # P0-7 外协管理
    "outsource-partners": "/outsource/partners",
    "outsource-orders": "/outsource/orders",
    "outsource-quality": "/outsource/quality-records",
    # S4 成本核算
    "cost-accounting": "/cost-accounting",
}


def get_allowed_paths(role: str) -> list[str]:
    """根据角色返回允许访问的前端路由路径列表，用于动态下发权限"""
    menus = get_allowed_menus(role)
    return [MENU_PATH_MAP[m] for m in menus if m in MENU_PATH_MAP]


# API路径 → 菜单名映射（用于 require_menu 权限校验）
API_MENU_MAP: dict[str, str] = {
    "products": "products",
    "bom": "bom",
    "projects": "projects",
    "tests": "tests",
    "alerts": "alerts",
    "certifications": "certifications",
    "certifications/prototypes": "prototypes",
    "certifications/quality-issues": "quality",
    "certifications/ecrs": "changes",
    "certifications/ecns": "changes",
    "approval": "approvals",
    "purchases": "purchases",
    "dashboard": "dashboard",
    "prototypes": "prototypes",
    "verification-requirements": "verification-requirements",
    "gate-rules": "gate-rules",
    "target-markets": "target-markets",
    "test-executions": "test-executions",
    # Phase 6 S2 — 认证中心
    "s2/certification-requirements": "cert-requirements",
    "s2/certification-projects": "cert-projects",
    "s2/certification-samples": "cert-samples",
    "s2/certification-executions": "cert-executions",
    "s2/certification-results": "cert-results",
    "s2/certificates": "certificates",
    "s2/gate-rules": "cert-gate-rules",
    # Phase 6 S3 — ECR/ECO
    "ecr": "changes",
    "eco": "changes",
    # S4 成本核算
    "cost-accounting": "cost-accounting",
    # D1 BI分析看板
    "bi": "bi-analytics",
    # D3 消息通知
    "user": "notification-settings",
}

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
