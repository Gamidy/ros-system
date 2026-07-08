"""驾驶舱仪表盘 — 经营分析看板（四维聚合）"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case as sa_case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_menu
from app.schemas.business import (
    BusinessAnalysisResponse,
    ProductionSalesPillar,
    FinancialControlPillar,
    GrowthEnginePillar,
    EfficiencyMetricsPillar,
)
from app.models.project import Project, ProjectGate
from app.models.product import Product, Platform, Version, Market
from app.models.bom import BOM, BOMItem
from app.models.purchase import PurchaseOrder, Supplier
from app.models.competitor import CompetitorModel as Competitor
from app.models.certification import CertificationProject
from app.models.product_plan import ProductPlan, ProductPlanStage, ProductPlanProjectLink
from app.models.delivery_record import DeliveryRecord
from app.models.financial_snapshot import FinancialSnapshot
from app.models.revenue_channel import RevenueByChannel
from app.models.inventory_snapshot import InventorySnapshot
from app.models.ai_agent import AIAgent
from app.models.cost_saving import CostSaving as CostSavingRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["驾驶舱-经营分析"])


def _build_production_sales(db: Session) -> ProductionSalesPillar:
    """产销协同维度"""
    try:
        total_projects = db.query(func.count(Project.id)).filter(Project.is_deleted == False).scalar() or 0
        running_projects = db.query(func.count(Project.id)).filter(Project.status == "running", Project.is_deleted == False).scalar() or 0
        completed_projects = db.query(func.count(Project.id)).filter(Project.status == "completed", Project.is_deleted == False).scalar() or 0
        today = date.today()
        overdue_projects = (
            db.query(func.count(Project.id))
            .filter(Project.is_deleted == False, Project.target_end_date.isnot(None),
                    Project.target_end_date < today, Project.status != "completed")
            .scalar() or 0
        )
        total_plans = db.query(func.count(ProductPlan.id)).scalar() or 0
        draft_plans = db.query(func.count(ProductPlan.id)).filter(ProductPlan.status == ProductPlanStage.DRAFT).scalar() or 0
        costing_plans = db.query(func.count(ProductPlan.id)).filter(ProductPlan.status == ProductPlanStage.COSTING).scalar() or 0
        released_plans = db.query(func.count(ProductPlan.id)).filter(ProductPlan.status == ProductPlanStage.RELEASED).scalar() or 0
        total_boms = db.query(func.count(BOM.id)).scalar() or 0
        total_parts = db.query(func.count(BOMItem.id)).scalar() or 0
        linked_plans = db.query(func.count(ProductPlanProjectLink.product_plan_id.distinct())).scalar() or 0
        plan_to_project_rate = round((linked_plans / max(total_plans, 1)) * 100, 1)
        try:
            avg_days = db.query(func.avg(DeliveryRecord.cycle_days)).scalar()
            avg_delivery_cycle_days = round(avg_days, 1) if avg_days else None
        except Exception:
            logger.exception("unexpected error")
            avg_delivery_cycle_days = None
        try:
            inv = db.query(func.avg(InventorySnapshot.turnover_rate)).scalar()
            inventory_turnover_rate = round(inv, 1) if inv else None
        except Exception:
            logger.exception("unexpected error")
            inventory_turnover_rate = None
        try:
            total_deliveries = db.query(func.count(DeliveryRecord.id)).scalar() or 0
            on_time_deliveries = db.query(func.count(DeliveryRecord.id)).filter(DeliveryRecord.on_time == True).scalar() or 0
            otd_rate = round((on_time_deliveries / max(total_deliveries, 1)) * 100, 1) if total_deliveries > 0 else None
        except Exception:
            logger.exception("unexpected error")
            otd_rate = None
        return ProductionSalesPillar(
            total_projects=total_projects, running_projects=running_projects,
            completed_projects=completed_projects, overdue_projects=overdue_projects,
            total_plans=total_plans, draft_plans=draft_plans,
            costing_plans=costing_plans, released_plans=released_plans,
            total_boms=total_boms, total_parts=total_parts,
            plan_to_project_rate=plan_to_project_rate,
            avg_delivery_cycle_days=avg_delivery_cycle_days,
            inventory_turnover_rate=inventory_turnover_rate,
            on_time_delivery_rate=otd_rate,
        )
    except Exception:
        logger.exception("unexpected error")
        return ProductionSalesPillar()


def _build_financial_control(db: Session) -> FinancialControlPillar:
    """财务管控维度"""
    try:
        total_purchase_orders = db.query(func.count(PurchaseOrder.id)).scalar() or 0
        pending_purchase_orders = db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.status == "pending_approval").scalar() or 0
        total_amount = db.query(func.sum(PurchaseOrder.total_amount)).scalar() or 0.0
        total_suppliers = db.query(func.count(Supplier.id)).filter(Supplier.is_deleted == 0).scalar() or 0
        active_suppliers = db.query(func.count(Supplier.id)).filter(Supplier.status == "active", Supplier.is_deleted == 0).scalar() or 0
        try:
            from app.models.product_plan_subs import ProjectCostItem
            cost_orders = db.query(func.count(ProjectCostItem.id)).scalar() or 0
        except Exception:
            logger.exception("unexpected error")
            cost_orders = 0
        try:
            from app.models.certification import CostAccountingPeriod
            cost_periods = db.query(func.count(CostAccountingPeriod.id)).scalar() or 0
        except Exception:
            logger.exception("unexpected error")
            cost_periods = 0
        return FinancialControlPillar(
            total_purchase_orders=total_purchase_orders,
            pending_purchase_orders=pending_purchase_orders,
            total_purchase_amount=round(total_amount, 2),
            total_suppliers=total_suppliers, active_suppliers=active_suppliers,
            cost_accounting_periods=cost_periods, cost_orders_count=cost_orders,
            cost_execution_rate=0.0, cost_overrun_alerts=0,
        )
    except Exception:
        logger.exception("unexpected error")
        return FinancialControlPillar()


def _add_financial_metrics(db: Session, pillar: FinancialControlPillar) -> FinancialControlPillar:
    """补充财务指标（来自 financial_snapshots 表）"""
    try:
        fs = db.query(FinancialSnapshot).order_by(FinancialSnapshot.period.desc()).first()
        if fs:
            pillar.revenue = fs.revenue
            pillar.gross_profit_rate = fs.gross_profit_rate
            pillar.net_profit_rate = fs.net_profit_rate
            pillar.r_and_d_budget = fs.r_and_d_budget
            pillar.r_and_d_spent = fs.r_and_d_spent
    except Exception:
        logger.debug(f"ignored: {{e}}")
        pass
    return pillar


def _build_growth_engine(db: Session) -> GrowthEnginePillar:
    """增长引擎维度"""
    try:
        total_markets = db.query(func.count(Market.code)).filter(Market.is_active == "true").scalar() or 0
        r32_markets = db.query(func.count(Market.code)).filter(Market.is_active == "true", Market.refrigerant == "R32").scalar() or 0
        r410a_markets = db.query(func.count(Market.code)).filter(Market.is_active == "true", Market.refrigerant == "R410A").scalar() or 0
        total_competitors = db.query(func.count(Competitor.id)).scalar() or 0
        from sqlalchemy import text as sa_text
        competitor_markets = db.execute(sa_text("SELECT COUNT(DISTINCT market) FROM competitor_models")).scalar() or 0
        total_cert_projects = db.query(func.count(CertificationProject.id)).scalar() or 0
        cert_in_progress = db.query(func.count(CertificationProject.id)).filter(CertificationProject.status == "in_progress").scalar() or 0
        total_products = db.query(func.count(Product.id)).scalar() or 0
        total_versions = db.query(func.count(Version.id)).scalar() or 0
        return GrowthEnginePillar(
            total_markets=total_markets, r32_markets=r32_markets,
            r410a_markets=r410a_markets, total_competitors=total_competitors,
            competitor_markets_count=competitor_markets,
            total_cert_projects=total_cert_projects,
            cert_projects_in_progress=cert_in_progress,
            total_products=total_products, total_versions=total_versions,
        )
    except Exception:
        logger.exception("unexpected error")
        return GrowthEnginePillar()


def _add_revenue_metrics(db: Session, pillar: GrowthEnginePillar) -> GrowthEnginePillar:
    """补充收入渠道数据"""
    try:
        rows = db.query(RevenueByChannel).order_by(RevenueByChannel.period.desc()).all()
        if rows:
            period_rows = [r for r in rows if r.period == rows[0].period]
            total = 0.0
            for r in period_rows:
                if r.channel_type == "overseas":
                    pillar.overseas_revenue = r.amount
                elif r.channel_type == "tob":
                    pillar.tob_revenue = r.amount
                elif r.channel_type == "domestic_retail":
                    pillar.domestic_revenue = r.amount
                total += r.amount or 0
            pillar.total_revenue = round(total, 2)
    except Exception:
        logger.debug(f"ignored: {{e}}")
        pass
    return pillar


def _build_efficiency(db: Session) -> EfficiencyMetricsPillar:
    """效率指标维度"""
    try:
        active_count = db.query(func.count(Project.id)).filter(Project.status == "running", Project.is_deleted == False).scalar() or 1
        on_time_count = (
            db.query(func.count(Project.id))
            .filter(Project.is_deleted == False, Project.actual_end_date.isnot(None),
                    Project.target_end_date.isnot(None), Project.actual_end_date <= Project.target_end_date)
            .scalar() or 0
        )
        on_time_rate = round((on_time_count / active_count) * 100, 1) if active_count > 0 else 0.0
        from app.models.test import TestResult, QualityIssue
        total_results = db.query(func.count(TestResult.id)).filter(TestResult.is_pass.isnot(None)).scalar() or 0
        pass_results = db.query(func.count(TestResult.id)).filter(TestResult.is_pass == True).scalar() or 0
        test_pass_rate = round((pass_results / max(total_results, 1)) * 100, 1) if total_results > 0 else 0.0
        total_issues = db.query(func.count(QualityIssue.id)).scalar() or 0
        closed_issues = db.query(func.count(QualityIssue.id)).filter(QualityIssue.status == "closed").scalar() or 0
        issue_close_rate = round((closed_issues / max(total_issues, 1)) * 100, 1) if total_issues > 0 else 0.0
        gate_total = db.query(func.count(ProjectGate.id)).scalar() or 1
        gate_passed = db.query(func.count(ProjectGate.id)).filter(ProjectGate.status == "passed").scalar() or 0
        phase_gate_pass_rate = round((gate_passed / max(gate_total, 1)) * 100, 1)
        from app.models.alert import Alert
        total_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0
        overdue_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False, Alert.level == 1).scalar() or 0
        return EfficiencyMetricsPillar(
            on_time_rate=on_time_rate, avg_project_duration_days=0.0,
            test_pass_rate=test_pass_rate, issue_close_rate=issue_close_rate,
            phase_gate_pass_rate=phase_gate_pass_rate,
            alert_count=total_alerts, overdue_alert_count=overdue_alerts,
        )
    except Exception:
        logger.exception("unexpected error")
        return EfficiencyMetricsPillar()


def _add_ai_metrics(db: Session, pillar: EfficiencyMetricsPillar) -> EfficiencyMetricsPillar:
    """补充AI数字化指标"""
    try:
        pillar.ai_agent_count = db.query(func.count(AIAgent.id)).filter(AIAgent.status == "active").scalar() or 0
    except Exception:
        logger.debug(f"ignored: {{e}}")
        pass
    try:
        savings = db.query(func.sum(CostSavingRecord.amount)).filter(CostSavingRecord.verified == True).scalar()
        pillar.monthly_cost_savings = round(savings, 2) if savings else None
    except Exception:
        logger.debug(f"ignored: {{e}}")
        pass
    return pillar


@router.get("/business-analysis", response_model=BusinessAnalysisResponse)
def get_business_analysis(
    db: Session = Depends(get_db),
    _=Depends(require_menu("dashboard")),
) -> BusinessAnalysisResponse:
    """经营分析看板 — 四维聚合（产销协同/财务管控/增长引擎/效率指标）"""
    try:
        ps = _build_production_sales(db)
        fc = _build_financial_control(db)
        ge = _build_growth_engine(db)
        ef = _build_efficiency(db)
        fc = _add_financial_metrics(db, fc)
        ge = _add_revenue_metrics(db, ge)
        ef = _add_ai_metrics(db, ef)
        return BusinessAnalysisResponse(
            production_sales=ps, financial_control=fc,
            growth_engine=ge, efficiency=ef,
        )
    except Exception as exc:
        logger.exception("经营分析看板构建失败: %s", exc)
        return BusinessAnalysisResponse()
