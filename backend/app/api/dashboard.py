"""驾驶舱仪表盘 API — 多层聚合 + 预警管理 + 角色化视图"""
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Any
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case as sa_case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.product import Product, Platform, Version
from app.models.project import Project, ProjectGate
from app.models.test import TestResult, QualityIssue
from app.models.alert import Alert, AlertRule
from app.models.approval import ApprovalRequest  # unified approval engine
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.user import User
from app.schemas import (
    DashboardSummary,
    DashboardResponse,
    Layer1SystemHealth,
    Layer2ProjectOps,
    Layer4ACMetrics,
    RecentProjectSummary,
    AlertOut,
    AlertRuleCreate,
    AlertRuleOut,
    AlertItem,
    AlertsSummaryResponse,
    KpiDetailItem,
)
from app.services.dashboard_pm_service import get_pm_competitor_summary
from app.services.dashboard_rd_service import get_rd_bom_summary
from app.services.dashboard_quality_service import get_quality_cert_summary
from app.services.dashboard_alert_service import build_alerts_summary_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])

# ── 角色映射常量 ──

MANAGEMENT_ROLES: set[str] = {"admin", "general_manager"}
PM_ROLES: set[str] = {"product_manager"}
RD_ROLES: set[str] = {
    "rd_director", "rd_engineer", "systems_engineer", "structural_engineer",
    "electrical_control_engineer", "electrical_engineer", "process_engineer",
    "project_admin",
}
QUALITY_ROLES: set[str] = {"quality_engineer"}


# ═══════════════ 辅助函数: 角色视图 ═══════════════

def _get_role_view(raw_role: str) -> str:
    """将原始角色映射到视图类型: management|pm|rd|quality"""
    if raw_role in PM_ROLES:
        return "pm"
    if raw_role in RD_ROLES:
        return "rd"
    if raw_role in QUALITY_ROLES:
        return "quality"
    return "management"


# ═══════════════ L1: 系统健康概览 ═══════════════

def _build_layer1(db: Session) -> Layer1SystemHealth:
    """构建L1系统健康概览 — 平台/产品/版本/项目统计"""
    total_platforms = db.query(func.count(Platform.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_versions = db.query(func.count(Version.id)).scalar() or 0
    active_projects = (
        db.query(func.count(Project.id))
        .filter(Project.status == "running", Project.is_deleted == False)
        .scalar() or 0
    )
    product_status_rows = (
        db.query(Product.status, func.count(Product.id))
        .group_by(Product.status)
        .all()
    )
    product_status_distribution = {row[0] or "unknown": row[1] for row in product_status_rows}
    return Layer1SystemHealth(
        total_platforms=total_platforms,
        total_products=total_products,
        total_versions=total_versions,
        active_projects=active_projects,
        product_status_distribution=product_status_distribution,
    )


# ═══════════════ L2: 项目运营概览 ═══════════════

def _build_layer2_stats(db: Session, today: date) -> tuple[int, float, int]:
    """构建L2基础统计 — 项目总数/按时率/逾期数"""
    project_count = (
        db.query(func.count(Project.id))
        .filter(Project.is_deleted == False)
        .scalar() or 0
    )
    active_count = (
        db.query(func.count(Project.id))
        .filter(Project.status == "running", Project.is_deleted == False)
        .scalar() or 1
    )
    on_time_count = (
        db.query(func.count(Project.id))
        .filter(
            Project.is_deleted == False,
            Project.actual_end_date.isnot(None),
            Project.target_end_date.isnot(None),
            Project.actual_end_date <= Project.target_end_date,
        )
        .scalar() or 0
    )
    on_time_rate = round((on_time_count / active_count) * 100, 1) if active_count > 0 else 0.0
    overdue_count = (
        db.query(func.count(Project.id))
        .filter(
            Project.is_deleted == False,
            Project.target_end_date.isnot(None),
            Project.target_end_date < today,
            Project.status != "completed",
        )
        .scalar() or 0
    )
    return project_count, on_time_rate, overdue_count


def _build_recent_projects(db: Session) -> list[RecentProjectSummary]:
    """构建L2最近项目列表（最近5个）"""
    rows = (
        db.query(
            Project.id, Project.code, Project.name, Project.status,
            Project.project_class, Project.target_end_date, Project.owner,
        )
        .filter(Project.is_deleted == False)
        .order_by(Project.created_at.desc())
        .limit(5)
        .all()
    )
    return [
        RecentProjectSummary(
            id=r[0], code=r[1], name=r[2], status=r[3],
            project_class=r[4], target_end_date=r[5], owner=r[6],
        )
        for r in rows
    ]


def _build_layer2_extra(db: Session) -> tuple[dict[str, int], int]:
    """构建L2项目状态分布及待审批数"""
    project_status_rows = (
        db.query(Project.status, func.count(Project.id))
        .filter(Project.is_deleted == False)
        .group_by(Project.status)
        .all()
    )
    project_status_distribution = {row[0] or "unknown": row[1] for row in project_status_rows}
    pending_approvals_count = (
        db.query(func.count(ApprovalRequest.id))
        .filter(
            ApprovalRequest.status == "pending",
            ApprovalRequest.request_type == "proposal",
        )
        .scalar() or 0
    )
    return project_status_distribution, pending_approvals_count


def _build_layer2(db: Session, today: date) -> Layer2ProjectOps:
    """组装L2项目运营概览"""
    project_count, on_time_rate, overdue_count = _build_layer2_stats(db, today)
    recent_projects = _build_recent_projects(db)
    project_status_distribution, pending_approvals_count = _build_layer2_extra(db)
    return Layer2ProjectOps(
        project_count=project_count,
        on_time_rate=on_time_rate,
        overdue_count=overdue_count,
        pending_approvals_count=pending_approvals_count,
        recent_projects=recent_projects,
        project_status_distribution=project_status_distribution,
    )


# ═══════════════ L3: 穿透链 ═══════════════

def _get_penetration_project(db: Session) -> Optional[Project]:
    """获取用于穿透链展示的活跃项目"""
    return (
        db.query(Project)
        .filter(Project.status == "running", Project.is_deleted == False)
        .order_by(Project.created_at.desc())
        .first()
    )


def _build_penetration_product(
    db: Session, product_code: str,
) -> tuple[Optional[Product], Optional[Platform], list]:
    """构建穿透链中的产品/平台/版本数据"""
    product = db.query(Product).filter(Product.code == product_code).first()
    platform_obj = None
    versions_list: list = []
    if product:
        platform_obj = db.query(Platform).filter(Platform.id == product.platform_id).first()
        versions_list = (
            db.query(Version)
            .filter(Version.product_id == product.id)
            .order_by(Version.created_at.desc())
            .limit(5)
            .all()
        )
    return product, platform_obj, versions_list


def _build_penetration_gates(db: Session, project_id: int) -> list[dict]:
    """构建穿透链中的门控节点列表"""
    gates_rows = (
        db.query(ProjectGate)
        .filter(ProjectGate.project_id == project_id)
        .order_by(ProjectGate.seq)
        .all()
    )
    return [
        {
            "gate_code": g.gate_code,
            "gate_name": g.gate_name,
            "status": g.status,
            "planned_date": g.planned_date.isoformat() if g.planned_date else None,
            "actual_date": g.actual_date.isoformat() if g.actual_date else None,
        }
        for g in gates_rows
    ]


def _assemble_layer3(
    project: Project,
    product: Optional[Product],
    platform_obj: Optional[Platform],
    versions_list: list,
    gates_list: list[dict],
) -> dict:
    """组装L3穿透链响应字典"""
    return {
        "project": {
            "id": project.id,
            "code": project.code,
            "name": project.name,
            "status": project.status,
            "project_class": project.project_class,
            "owner": project.owner,
        },
        "product": {
            "code": product.code,
            "name": product.name,
            "status": product.status,
        } if product else None,
        "platform": {
            "code": platform_obj.code,
            "name": platform_obj.name,
            "platform_type": platform_obj.platform_type,
        } if platform_obj else None,
        "versions": [
            {
                "version_no": v.version_no,
                "status": v.status.value if hasattr(v.status, "value") else str(v.status),
            }
            for v in versions_list
        ],
        "gates": gates_list,
    }


def _build_layer3(db: Session) -> Optional[dict]:
    """构建L3穿透链"""
    project = _get_penetration_project(db)
    if not project or not project.product_code:
        return None
    product, platform_obj, versions_list = _build_penetration_product(
        db, project.product_code,
    )
    gates_list = _build_penetration_gates(db, project.id)
    return _assemble_layer3(project, product, platform_obj, versions_list, gates_list)


# ═══════════════ L4: 指标聚合 ═══════════════

def _build_phase_progress(db: Session) -> tuple[dict[str, float], list[dict]]:
    """构建阶段进度 — 按Gate节点聚合通过率"""
    gate_stats = (
        db.query(
            ProjectGate.gate_code,
            func.count(ProjectGate.id).label("total"),
            func.sum(
                sa_case((ProjectGate.status == "passed", 1), else_=0),
            ).label("passed"),
        )
        .join(Project, ProjectGate.project_id == Project.id)
        .filter(Project.is_deleted == False)
        .group_by(ProjectGate.gate_code)
        .order_by(ProjectGate.gate_code)
        .all()
    )
    phase_progress: dict[str, float] = {}
    phase_progress_array: list[dict] = []
    for row in gate_stats:
        code = row[0]
        total = row[1] or 1
        passed = row[2] or 0
        rate = round((passed / total) * 100, 1) if total > 0 else 0.0
        phase_progress[code] = rate
        phase_progress_array.append({
            "gate_code": code, "total": total, "passed": passed, "rate": rate,
        })
    return phase_progress, phase_progress_array


def _build_layer4(db: Session) -> Layer4ACMetrics:
    """构建L4进度-测试-品质-成本综合指标"""
    phase_progress, phase_progress_array = _build_phase_progress(db)

    total_results = (
        db.query(func.count(TestResult.id))
        .filter(TestResult.is_pass.isnot(None))
        .scalar() or 0
    )
    pass_results = (
        db.query(func.count(TestResult.id))
        .filter(TestResult.is_pass == True)
        .scalar() or 0
    )
    test_pass_rate = round((pass_results / total_results) * 100, 1) if total_results > 0 else 0.0

    total_issues = db.query(func.count(QualityIssue.id)).scalar() or 0
    closed_issues = (
        db.query(func.count(QualityIssue.id))
        .filter(QualityIssue.status == "closed")
        .scalar() or 0
    )
    issue_close_rate = round((closed_issues / total_issues) * 100, 1) if total_issues > 0 else 0.0

    return Layer4ACMetrics(
        phase_progress=phase_progress,
        test_pass_rate=test_pass_rate,
        issue_close_rate=issue_close_rate,
        cost_execution_rate=0.0,
        generalization_rate=0.0,
        phase_progress_array=phase_progress_array,
        total_issues=total_issues,
        closed_issues=closed_issues,
    )


# ═══════════════ 角色化视图数据 ═══════════════

def _get_role_specific_data(
    db: Session, role_view: str,
) -> tuple[Optional[dict], Optional[dict], Optional[dict]]:
    """根据角色视图获取对应摘要数据

    Returns:
        (pm_competitor_summary, rd_bom_summary, quality_cert_summary)
    """
    pm_competitor_summary: Optional[dict] = None
    rd_bom_summary: Optional[dict] = None
    quality_cert_summary: Optional[dict] = None

    if role_view == "pm":
        pm_competitor_summary = get_pm_competitor_summary(db)
    elif role_view == "rd":
        rd_bom_summary = get_rd_bom_summary(db)
    elif role_view == "quality":
        quality_cert_summary = get_quality_cert_summary(db)

    return pm_competitor_summary, rd_bom_summary, quality_cert_summary


# ═══════════════ 驾驶舱汇总（新版多层聚合） ═══════════════

@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_menu("dashboard")),
    role: Optional[str] = Query(None, description="角色视图: pm/rd/quality/management, 默认使用当前用户角色"),
) -> DashboardResponse:
    """驾驶舱多层聚合仪表盘 — 按角色视图展示"""
    today = date.today()

    # 确定角色视图
    raw_role = (role or current_user.role).lower()
    role_view = _get_role_view(raw_role)

    # 构建各层数据
    layer1 = _build_layer1(db)
    layer2 = _build_layer2(db, today)
    layer3 = _build_layer3(db)
    layer4 = _build_layer4(db)

    # 角色化视图数据
    pm_competitor_summary, rd_bom_summary, quality_cert_summary = _get_role_specific_data(
        db, role_view,
    )

    return DashboardResponse(
        layer1_system_health=layer1,
        layer2_project_ops=layer2,
        layer3_penetration=layer3,
        layer4_ac_metrics=layer4,
        role_view=role_view,
        pm_competitor_summary=pm_competitor_summary,
        rd_bom_summary=rd_bom_summary,
        quality_cert_summary=quality_cert_summary,
    )


# ═══════════════ KPI卡片明细数据钻取 [D3-2] ═══════════════

def _get_kpi_in_progress(db: Session) -> list[dict[str, Any]]:
    """获取进行中策划明细"""
    in_progress_stages = [
        ProductPlanStage.DRAFT,
        ProductPlanStage.COMPETITOR,
        ProductPlanStage.DEFINITION,
        ProductPlanStage.COSTING,
        ProductPlanStage.TECH_INPUT,
        ProductPlanStage.PROJECT_INIT,
    ]
    plans = (
        db.query(ProductPlan)
        .filter(ProductPlan.status.in_(in_progress_stages))
        .order_by(ProductPlan.updated_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "market": p.market,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "series": p.series,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "plan",
        }
        for p in plans
    ]


def _get_kpi_pending(db: Session) -> list[dict[str, Any]]:
    """获取待审批明细"""
    approvals = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.status == "pending",
            ApprovalRequest.request_type == "proposal",
        )
        .order_by(ApprovalRequest.created_at.desc())
        .limit(200)
        .all()
    )
    result: list[dict[str, Any]] = []
    for a in approvals:
        name = f"审批#{a.id}"
        if a.request_data:
            try:
                data = json.loads(a.request_data) if isinstance(a.request_data, str) else a.request_data
                name = data.get("title") or data.get("name") or name
            except (json.JSONDecodeError, TypeError):
                pass
        result.append({
            "id": a.id,
            "name": name,
            "market": None,
            "status": a.status,
            "series": None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": None,
            "type": "approval",
        })
    return result


def _get_kpi_completed(db: Session) -> list[dict[str, Any]]:
    """获取本月已完成策划明细"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    plans = (
        db.query(ProductPlan)
        .filter(
            ProductPlan.status == ProductPlanStage.RELEASED,
            ProductPlan.updated_at >= month_start,
        )
        .order_by(ProductPlan.updated_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "market": p.market,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "series": p.series,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "plan",
        }
        for p in plans
    ]


def _get_kpi_overdue(db: Session, today: date) -> list[dict[str, Any]]:
    """获取超期项目明细"""
    projects = (
        db.query(Project)
        .filter(
            Project.is_deleted == False,
            Project.target_end_date.isnot(None),
            Project.target_end_date < today,
            Project.status != "completed",
        )
        .order_by(Project.target_end_date)
        .limit(200)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "market": None,
            "status": p.status,
            "series": None,
            "code": p.code,
            "target_end_date": p.target_end_date.isoformat() if p.target_end_date else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "type": "project",
        }
        for p in projects
    ]


@router.get("/kpi-detail")
def get_kpi_detail(
    type: str = Query(..., description="KPI类型: in_progress / pending / completed / overdue"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """返回KPI卡片对应的明细数据，用于右侧抽屉表格展示"""
    today = date.today()
    if type == "in_progress":
        return _get_kpi_in_progress(db)
    if type == "pending":
        return _get_kpi_pending(db)
    if type == "completed":
        return _get_kpi_completed(db)
    if type == "overdue":
        return _get_kpi_overdue(db, today)
    raise HTTPException(status_code=400, detail=f"未知的KPI类型: {type}")


# ═══════════════ 预警管理 ═══════════════

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    is_resolved: bool = Query(None, description="是否已解决"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
) -> list[AlertOut]:
    """列出预警记录，支持级别/状态/类型筛选"""
    q = db.query(Alert)
    if level is not None:
        q = q.filter(Alert.level == level)
    if is_resolved is not None:
        q = q.filter(Alert.is_resolved == is_resolved)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    return q.order_by(Alert.level.desc(), Alert.created_at.desc()).all()


@router.patch("/alerts/{aid}")
def resolve_alert(
    aid: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(
        "admin", "general_manager", "rd_director", "project_admin",
        "product_manager", "quality_engineer",
    )),
) -> dict:
    """标记预警为已解决"""
    alert = db.query(Alert).filter(Alert.id == aid).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ═══════════════ 预警规则 ═══════════════

@router.get("/alerts/rules", response_model=list[AlertRuleOut])
def list_alert_rules(
    target_type: str = Query("", description="监控对象类型"),
    is_enabled: bool = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
) -> list[AlertRuleOut]:
    """列出预警规则，支持类型/启用状态筛选"""
    q = db.query(AlertRule)
    if target_type:
        q = q.filter(AlertRule.target_type == target_type)
    if is_enabled is not None:
        q = q.filter(AlertRule.is_enabled == is_enabled)
    return q.order_by(AlertRule.created_at.desc()).all()


@router.post("/alerts/rules", response_model=AlertRuleOut)
def create_alert_rule(
    data: AlertRuleCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> AlertRuleOut:
    """创建预警规则"""
    existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"规则[{data.name}]已存在")
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/trends")
def get_dashboard_trends(
    days: int = Query(30, description="统计天数"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[dict]:
    """返回最近N天每日项目创建数量，用于趋势图"""
    from datetime import date as dt_date
    start = dt_date.today() - timedelta(days=days)
    rows = (
        db.query(
            func.date(Project.created_at).label("d"),
            func.count(Project.id).label("c"),
        )
        .filter(Project.created_at >= start)
        .group_by(func.date(Project.created_at))
        .order_by(func.date(Project.created_at))
        .all()
    )
    data_map = {str(r.d): r.c for r in rows}
    result: list[dict] = []
    for i in range(days, -1, -1):
        d = (dt_date.today() - timedelta(days=i)).isoformat()
        result.append({"date": d, "value": data_map.get(d, 0)})
    return result


# ═══════════════ D3-3: 仪表盘预警摘要 ═══════════════

@router.get("/alerts-summary", response_model=AlertsSummaryResponse)
def get_alerts_summary(
    db: Session = Depends(get_db),
    _=Depends(require_menu("dashboard")),
) -> AlertsSummaryResponse:
    """预警摘要 — 委托 dashboard_alert_service 扫描检测"""
    return build_alerts_summary_response(db)


# ═══════════════ WS实时推送角色化视图 ═══════════════

_ROLE_WIDGETS: dict[str, list[dict]] = {
    "admin": [
        {"id": "sys-health", "type": "overview", "title": "系统健康概览"},
        {"id": "project-ops", "type": "overview", "title": "项目运营概览"},
        {"id": "penetration", "type": "detail", "title": "穿透分析"},
        {"id": "ac-metrics", "type": "metrics", "title": "AC指标"},
        {"id": "alerts", "type": "alert", "title": "预警管理"},
    ],
    "product_manager": [
        {"id": "competitor", "type": "insight", "title": "竞品动态"},
        {"id": "project-ops", "type": "overview", "title": "项目运营概览"},
        {"id": "kpi-detail", "type": "metrics", "title": "KPI明细"},
    ],
    "rd_director": [
        {"id": "bom-summary", "type": "detail", "title": "BOM汇总"},
        {"id": "project-ops", "type": "overview", "title": "项目运营概览"},
        {"id": "penetration", "type": "detail", "title": "穿透分析"},
    ],
    "quality_engineer": [
        {"id": "cert-summary", "type": "insight", "title": "认证汇总"},
        {"id": "test-pass-rate", "type": "metrics", "title": "测试通过率"},
        {"id": "issue-tracking", "type": "detail", "title": "问题追踪"},
    ],
    "procurement": [
        {"id": "order-stats", "type": "metrics", "title": "采购统计"},
        {"id": "pending-approval", "type": "alert", "title": "待审批订单"},
        {"id": "supplier-summary", "type": "overview", "title": "供应商概览"},
    ],
}


@router.get("/role-view")
def get_role_view(
    role: str = Query(..., description="角色: product_manager|rd_director|quality_engineer|procurement|admin"),
) -> dict:
    """根据角色返回对应仪表盘配置"""
    role = role.lower()
    if role not in _ROLE_WIDGETS:
        raise HTTPException(status_code=400, detail=f"未知角色: {role}")
    return {"role": role, "widgets": _ROLE_WIDGETS[role]}
