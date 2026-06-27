"""驾驶舱仪表盘 API — 多层聚合 + 预警管理 + 角色化视图"""
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Any
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.product import Product, Platform, Version
from app.models.project import Project, ProjectGate
from app.models.bom import Part, BOM
from app.models.test import TestResult, QualityIssue
from app.models.alert import Alert, AlertRule
from app.models.approval import ApprovalRequest  # unified approval engine
from app.models.product_plan import ProductPlan, ProductPlanStage
from app.models.cost_accounting import CostAccountingSheet, SheetStatus
from app.models.competitor import CompetitorModel
from app.models.certification import CertificationProject, CertificationExecution
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])


# ═══════════════ 驾驶舱汇总（新版多层聚合） ═══════════════

@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_menu("dashboard")),
    role: Optional[str] = Query(None, description="角色视图: pm/rd/quality/management, 默认使用当前用户角色"),
) -> DashboardResponse:
    today = date.today()
    ninety_days = today + timedelta(days=90)

    # ─── 确定角色视图 ───
    raw_role = (role or current_user.role).lower()
    # 管理层映射: admin / general_manager → management
    MANAGEMENT_ROLES: set[str] = {"admin", "general_manager"}
    PM_ROLES: set[str] = {"product_manager"}
    RD_ROLES: set[str] = {"rd_director", "rd_engineer", "systems_engineer", "structural_engineer", "electrical_control_engineer", "electrical_engineer", "process_engineer", "project_admin"}
    QUALITY_ROLES: set[str] = {"quality_engineer"}

    if raw_role in PM_ROLES:
        role_view = "pm"
    elif raw_role in RD_ROLES:
        role_view = "rd"
    elif raw_role in QUALITY_ROLES:
        role_view = "quality"
    elif raw_role in MANAGEMENT_ROLES:
        role_view = "management"
    else:
        # 其他角色 fallback 到 management 视图
        role_view = "management"

    # ─────────────────── L1: 系统健康概览 ───────────────────
    total_platforms = db.query(func.count(Platform.id)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_versions = db.query(func.count(Version.id)).scalar() or 0
    active_projects = db.query(func.count(Project.id)).filter(
        Project.status == "running",
        Project.is_deleted == False,
    ).scalar() or 0

    # 产品状态分布
    product_status_rows = (
        db.query(Product.status, func.count(Product.id))
        .group_by(Product.status)
        .all()
    )
    product_status_distribution = {row[0] or "unknown": row[1] for row in product_status_rows}

    layer1 = Layer1SystemHealth(
        total_platforms=total_platforms,
        total_products=total_products,
        total_versions=total_versions,
        active_projects=active_projects,
        product_status_distribution=product_status_distribution,
    )

    # ─────────────────── L2: 项目运营概览 ───────────────────
    # 非删除项目总数
    project_count = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
    ).scalar() or 0

    # 活跃项目 (running + is_deleted=False)
    active_count = db.query(func.count(Project.id)).filter(
        Project.status == "running",
        Project.is_deleted == False,
    ).scalar() or 1  # 避免除以0

    # 按期完成: actual_end_date <= target_end_date（已完成且不超期）
    on_time_count = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.actual_end_date.isnot(None),
        Project.target_end_date.isnot(None),
        Project.actual_end_date <= Project.target_end_date,
    ).scalar() or 0

    on_time_rate = round((on_time_count / active_count) * 100, 1) if active_count > 0 else 0.0

    # 逾期项目: target_end_date < today 且 status != 'completed'
    overdue_count = db.query(func.count(Project.id)).filter(
        Project.is_deleted == False,
        Project.target_end_date.isnot(None),
        Project.target_end_date < today,
        Project.status != "completed",
    ).scalar() or 0

    # 最近5个项目 (按创建时间倒序, 排除已删除)
    recent_rows = (
        db.query(
            Project.id,
            Project.code,
            Project.name,
            Project.status,
            Project.project_class,
            Project.target_end_date,
            Project.owner,
        )
        .filter(Project.is_deleted == False)
        .order_by(Project.created_at.desc())
        .limit(5)
        .all()
    )
    recent_projects = [
        RecentProjectSummary(
            id=r[0],
            code=r[1],
            name=r[2],
            status=r[3],
            project_class=r[4],
            target_end_date=r[5],
            owner=r[6],
        )
        for r in recent_rows
    ]

    # 项目状态分布
    project_status_rows = (
        db.query(Project.status, func.count(Project.id))
        .filter(Project.is_deleted == False)
        .group_by(Project.status)
        .all()
    )
    project_status_distribution = {row[0] or "unknown": row[1] for row in project_status_rows}

    # 待审批项目数: 从统一 ApprovalRequest 统计
    pending_approvals_count = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == "pending",
        ApprovalRequest.request_type == "proposal",
    ).scalar() or 0

    layer2 = Layer2ProjectOps(
        project_count=project_count,
        on_time_rate=on_time_rate,
        overdue_count=overdue_count,
        pending_approvals_count=pending_approvals_count,
        recent_projects=recent_projects,
        project_status_distribution=project_status_distribution,
    )

    # ─────────────────── L3: 穿透链 ───────────────────
    # 选取一个活跃项目，构建穿透链: project → product → platform → versions → gates
    penetration_active = (
        db.query(Project)
        .filter(Project.status == "running", Project.is_deleted == False)
        .order_by(Project.created_at.desc())
        .first()
    )

    layer3 = None
    if penetration_active and penetration_active.product_code:
        product = (
            db.query(Product)
            .filter(Product.code == penetration_active.product_code)
            .first()
        )
        platform_obj = None
        versions_list = []
        gates_list = []

        if product:
            platform_obj = (
                db.query(Platform)
                .filter(Platform.id == product.platform_id)
                .first()
            )
            versions_list = (
                db.query(Version)
                .filter(Version.product_id == product.id)
                .order_by(Version.created_at.desc())
                .limit(5)
                .all()
            )

        gates_rows = (
            db.query(ProjectGate)
            .filter(ProjectGate.project_id == penetration_active.id)
            .order_by(ProjectGate.seq)
            .all()
        )
        gates_list = [
            {
                "gate_code": g.gate_code,
                "gate_name": g.gate_name,
                "status": g.status,
                "planned_date": g.planned_date.isoformat() if g.planned_date else None,
                "actual_date": g.actual_date.isoformat() if g.actual_date else None,
            }
            for g in gates_rows
        ]

        layer3 = {
            "project": {
                "id": penetration_active.id,
                "code": penetration_active.code,
                "name": penetration_active.name,
                "status": penetration_active.status,
                "project_class": penetration_active.project_class,
                "owner": penetration_active.owner,
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
                {"version_no": v.version_no, "status": v.status.value if hasattr(v.status, "value") else str(v.status)}
                for v in versions_list
            ],
            "gates": gates_list,
        }

    # ─────────────────── L4: 进度-测试-品质-成本综合指标 ───────────────────
    # phase_progress: 按Gate节点聚合 (总门数 vs 已通过)
    from sqlalchemy import case as sa_case
    gate_stats = (
        db.query(
            ProjectGate.gate_code,
            func.count(ProjectGate.id).label("total"),
            func.sum(
                sa_case(
                    (ProjectGate.status == "passed", 1),
                    else_=0,
                )
            ).label("passed"),
        )
        .join(Project, ProjectGate.project_id == Project.id)
        .filter(Project.is_deleted == False)
        .group_by(ProjectGate.gate_code)
        .order_by(ProjectGate.gate_code)
        .all()
    )

    phase_progress = {}
    phase_progress_array = []
    for row in gate_stats:
        code = row[0]
        total = row[1] or 1
        passed = row[2] or 0
        rate = round((passed / total) * 100, 1) if total > 0 else 0.0
        phase_progress[code] = rate
        phase_progress_array.append({
            "gate_code": code,
            "total": total,
            "passed": passed,
            "rate": rate,
        })

    # test_pass_rate: 从 TestResult 计算
    total_results = db.query(func.count(TestResult.id)).filter(
        TestResult.is_pass.isnot(None)
    ).scalar() or 0
    pass_results = db.query(func.count(TestResult.id)).filter(
        TestResult.is_pass == True
    ).scalar() or 0
    test_pass_rate = round((pass_results / total_results) * 100, 1) if total_results > 0 else 0.0

    # issue_close_rate: 品质问题关闭率
    total_issues = db.query(func.count(QualityIssue.id)).scalar() or 0
    closed_issues = db.query(func.count(QualityIssue.id)).filter(
        QualityIssue.status == "closed"
    ).scalar() or 0
    issue_close_rate = round((closed_issues / total_issues) * 100, 1) if total_issues > 0 else 0.0

    layer4 = Layer4ACMetrics(
        phase_progress=phase_progress,
        test_pass_rate=test_pass_rate,
        issue_close_rate=issue_close_rate,
        cost_execution_rate=0.0,
        generalization_rate=0.0,
        phase_progress_array=phase_progress_array,
        total_issues=total_issues,
        closed_issues=closed_issues,
    )

    # ─────────────────── 角色化视图: 竞品摘要 (PM)、BOM摘要 (RD)、认证摘要 (Quality) ───────────────────
    pm_competitor_summary: Optional[dict] = None
    rd_bom_summary: Optional[dict] = None
    quality_cert_summary: Optional[dict] = None

    if role_view == "pm":
        # 竞品动态摘要: 按市场统计竞品数量
        comp_rows = (
            db.query(CompetitorModel.market, func.count(CompetitorModel.id))
            .group_by(CompetitorModel.market)
            .all()
        )
        pm_competitor_summary = {
            "total": sum(r[1] for r in comp_rows),
            "by_market": {r[0] or "unknown": r[1] for r in comp_rows},
        }

    elif role_view == "rd":
        # BOM状态摘要: 物料总数、BOM总数
        total_parts = db.query(func.count(Part.id)).scalar() or 0
        total_boms = db.query(func.count(BOM.id)).scalar() or 0
        part_type_rows = (
            db.query(Part.part_type, func.count(Part.id))
            .filter(Part.part_type.isnot(None))
            .group_by(Part.part_type)
            .all()
        )
        rd_bom_summary = {
            "total_parts": total_parts,
            "total_boms": total_boms,
            "part_type_distribution": {r[0]: r[1] for r in part_type_rows},
        }

    elif role_view == "quality":
        # 认证进度摘要
        total_cert_projects = db.query(func.count(CertificationProject.id)).scalar() or 0
        cert_status_rows = (
            db.query(CertificationProject.status, func.count(CertificationProject.id))
            .group_by(CertificationProject.status)
            .all()
        )
        quality_cert_summary = {
            "total_projects": total_cert_projects,
            "status_distribution": {r[0] or "unknown": r[1] for r in cert_status_rows},
        }

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

@router.get("/kpi-detail")
def get_kpi_detail(
    type: str = Query(..., description="KPI类型: in_progress / pending / completed / overdue"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """返回KPI卡片对应的明细数据，用于右侧抽屉表格展示"""
    today = date.today()

    if type == "in_progress":
        # 进行中策划: status in draft~project_init
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
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                "series": p.series,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "type": "plan",
            }
            for p in plans
        ]

    elif type == "pending":
        # 待审批: ApprovalRequest (proposal type)
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
        result = []
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

    elif type == "completed":
        # 本月完成的策划
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
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                "series": p.series,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "type": "plan",
            }
            for p in plans
        ]

    elif type == "overdue":
        # 超期项目
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

    else:
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
    _=Depends(require_role("admin", "general_manager", "rd_director", "project_admin", "product_manager", "quality_engineer")),
) -> dict:
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
    # check duplicate name
    existing = db.query(AlertRule).filter(AlertRule.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"规则[{data.name}]已存在")
    rule = AlertRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/trends")  # BUGFIX: added missing endpoint for dashboard trends chart
def get_dashboard_trends(
    days: int = Query(30, description="统计天数"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
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
    result = []
    for i in range(days, -1, -1):
        d = (dt_date.today() - timedelta(days=i)).isoformat()
        result.append({"date": d, "value": data_map.get(d, 0)})
    return result


# ═══════════════ D3-3: 仪表盘预警摘要 ═══════════════

TERMINAL_STAGES = {ProductPlanStage.APPROVED, ProductPlanStage.RELEASED}
OVERDUE_DAYS = 30          # 逾期阈值：超过30天未完成
STUCK_DAYS = 7              # 滞留阈值：同一阶段停留超过7天
COST_OVERRUN_RATIO = 1.1    # 成本超标阈值：实际 > 目标 * 1.1


@router.get("/alerts-summary", response_model=AlertsSummaryResponse)
def get_alerts_summary(
    db: Session = Depends(get_db),
    _=Depends(require_menu("dashboard")),
) -> AlertsSummaryResponse:
    """预警摘要 — 扫描 product_plans 表检测逾期/滞留/超标"""
    now = datetime.now(timezone.utc)
    today = now.date()
    alerts: list[AlertItem] = []

    # ── 1. 全部未终态策划（非 approved / released）──
    active_plans = (
        db.query(
            ProductPlan.id,
            ProductPlan.name,
            ProductPlan.status,
            ProductPlan.created_at,
            ProductPlan.updated_at,
        )
        .filter(~ProductPlan.status.in_(TERMINAL_STAGES))
        .all()
    )

    plan_ids = [r.id for r in active_plans]
    sheet_map: dict[str, tuple[float, float]] = {}
    if plan_ids:
        sheet_rows = (
            db.query(
                CostAccountingSheet.product_plan_id,
                CostAccountingSheet.total_cost_actual,
                CostAccountingSheet.total_cost_target,
            )
            .filter(
                CostAccountingSheet.product_plan_id.in_(plan_ids),
                CostAccountingSheet.status == SheetStatus.FINALIZED,
            )
            .all()
        )
        for r in sheet_rows:
            if r.product_plan_id not in sheet_map:
                sheet_map[r.product_plan_id] = (r.total_cost_actual or 0, r.total_cost_target or 0)

    for row in active_plans:
        plan_id: str = row.id
        plan_name: str = row.name
        status_val: str = row.status.value if hasattr(row.status, 'value') else str(row.status)
        created_at: datetime = row.created_at or now
        updated_at: datetime = row.updated_at or created_at

        days_since_created = (today - created_at.date()).days
        days_since_updated = (today - updated_at.date()).days

        # ── 逾期检测：创建超过 OVERDUE_DAYS 天且未完成 ──
        if days_since_created >= OVERDUE_DAYS:
            alerts.append(AlertItem(
                type="overdue",
                plan_id=plan_id,
                plan_name=plan_name,
                message=f"策划创建 {days_since_created} 天仍在「{status_val}」阶段，请尽快推进",
                severity=3,
                status=status_val,
                created_at=created_at,
            ))

        # ── 滞留检测：同一阶段停留超过 STUCK_DAYS 天 ──
        if days_since_updated >= STUCK_DAYS:
            is_already_overdue = any(
                a.plan_id == plan_id and a.type == "overdue" for a in alerts
            )
            if not is_already_overdue:
                alerts.append(AlertItem(
                    type="stuck",
                    plan_id=plan_id,
                    plan_name=plan_name,
                    message=f"在「{status_val}」阶段停留 {days_since_updated} 天，请关注推动",
                    severity=1,
                    status=status_val,
                    created_at=created_at,
                ))

    # ── 2. 成本超标检测 ──
    cost_overrun_rows = (
        db.query(
            CostAccountingSheet.product_plan_id,
            CostAccountingSheet.total_cost_actual,
            CostAccountingSheet.total_cost_target,
            CostAccountingSheet.variance_pct,
            ProductPlan.name,
            ProductPlan.status,
            ProductPlan.created_at,
        )
        .join(ProductPlan, ProductPlan.id == CostAccountingSheet.product_plan_id)
        .filter(
            CostAccountingSheet.status == SheetStatus.FINALIZED,
            CostAccountingSheet.total_cost_target > 0,
            CostAccountingSheet.total_cost_actual > CostAccountingSheet.total_cost_target * COST_OVERRUN_RATIO,
        )
        .all()
    )

    for row in cost_overrun_rows:
        plan_id: str = row.product_plan_id
        plan_name: str = row.name or "(未命名)"
        actual = row.total_cost_actual or 0
        target = row.total_cost_target or 0
        variance_pct = row.variance_pct or 0
        status_val: str = row.status.value if hasattr(row.status, 'value') else str(row.status)

        alerts.append(AlertItem(
            type="cost_overrun",
            plan_id=plan_id,
            plan_name=plan_name,
            message=f"成本超支 {variance_pct:.1f}%（实际 ¥{actual:,.0f} / 目标 ¥{target:,.0f}）",
            severity=2,
            status=status_val,
            created_at=row.created_at,
        ))

    # ── 3. 去重 + 排序 ──
    seen: set[tuple[str, str]] = set()
    deduped: list[AlertItem] = []
    for a in alerts:
        key = (a.plan_id, a.type)
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    deduped.sort(key=lambda a: (-a.severity, a.plan_name or ""))

    overdue_count = sum(1 for a in deduped if a.type == "overdue")
    stuck_count = sum(1 for a in deduped if a.type == "stuck")
    cost_overrun_count = sum(1 for a in deduped if a.type == "cost_overrun")

    return AlertsSummaryResponse(
        overdue_count=overdue_count,
        stuck_count=stuck_count,
        cost_overrun_count=cost_overrun_count,
        alerts=deduped,
    )
