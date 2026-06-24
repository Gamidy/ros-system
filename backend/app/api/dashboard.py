"""驾驶舱仪表盘 API — 多层聚合 + 预警管理"""
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_menu, require_role
from app.models.product import Product, Platform, Version
from app.models.project import Project, ProjectGate
from app.models.bom import Part
from app.models.test import TestRequest, TestResult, Certification, QualityIssue
from app.models.alert import Alert, AlertRule
from app.models.proposal_approval import ProposalApproval  # BUGFIX: for pending approvals count
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
)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱"])


# ═══════════════ 驾驶舱汇总（新版多层聚合） ═══════════════

@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(db: Session = Depends(get_db), _=Depends(require_menu("dashboard"))):
    today = date.today()
    ninety_days = today + timedelta(days=90)

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

    # 待审批项目数: 从 proposal_approvals 表统计 pending 状态的记录 (BUGFIX: was querying Project.approval_status which is never written)
    pending_approvals_count = db.query(func.count(ProposalApproval.id)).filter(
        ProposalApproval.status.in_(["pending_parallel", "pending_director"]),
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
        cost_execution_rate=0.0,       # 暂无预算执行数据，占位
        generalization_rate=0.0,        # 暂无通用化率数据，占位
        phase_progress_array=phase_progress_array,
    )

    return DashboardResponse(
        layer1_system_health=layer1,
        layer2_project_ops=layer2,
        layer3_penetration=layer3,
        layer4_ac_metrics=layer4,
    )


# ═══════════════ 预警管理 ═══════════════

@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    level: int = Query(None, description="预警级别: 1紧急/2警告/3提示"),
    is_resolved: bool = Query(None, description="是否已解决"),
    alert_type: str = Query("", description="预警类型"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("alerts")),
):
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
):
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
):
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
):
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
):
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
