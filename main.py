from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.security import csrf_middleware
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.xss_protection import XSSProtectionMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.api import proposal_approval, ci_v2, knowledge, ai_competitor_confirm, competitor_market_config, competitor_history, dashboard_alerts, dashboard_business, dashboard_kpi, projects_gates, projects_tasks, projects_risks, projects_dashboard
from app.api import proposal_approval, ci_v2, auth, products, bom, projects, tests, certifications, alerts, dashboard, purchases, approvals, pm_workspace, pm_workspace_drafts, pm_workspace_planning, pm_workspace_config, pm_statistics, pm_roadmap, product_plan, product_plan_subs, admin_config, pm_config, pm_accessory, competitor, admin_role_templates, admin_role_mappings, admin_cost_configs, pm_proposal_api, rd_panel, state_machine_api, event_timeline, risk_dashboard, admin_tenant, webhooks, task_deps, project_templates, time_entries, task_comments, project_reviews, knowledge_base, purchases_supplier, purchases_receipt
from app.api import proposal_approval, ci_v2, product_plan_crud, product_plan_workflow_api, product_plan_versions
from app.api import proposal_approval, ci_v2, markets
from app.api import proposal_approval, ci_v2, verification_requirements, prototypes, test_executions, gate_rules, target_markets
from app.api import proposal_approval, ci_v2, s2_cert_requirements, s2_cert_projects, s2_cert_samples, s2_cert_executions, s2_cert_results, s2_certificates, s2_gate_rules, s2_change_impact
from app.api import proposal_approval, ci_v2, ecr, eco, eco_items, ecr_workflow, ecr_attachments
from app.api import proposal_approval, ci_v2, cost_alert_api
from app.api import proposal_approval, ci_v2, audit_logs
from app.api import proposal_approval, ci_v2, safety
from app.api import proposal_approval, ci_v2, manufacturability
from app.api import proposal_approval, ci_v2, outsource
from app.api import proposal_approval, ci_v2, cost_accounting
from app.api import proposal_approval, ci_v2, cost_accounting_export
from app.api import proposal_approval, ci_v2, cost_accounting_analysis
from app.api import proposal_approval, ci_v2, cost_accounting_sheets
from app.api import proposal_approval, ci_v2, bi_analytics, bi_planning, bi_cost_analytics
from app.api import proposal_approval, ci_v2, user_notification_api
from app.api import proposal_approval, ci_v2, ai_plan_api
from app.api import proposal_approval, ci_v2, password_reset_api
from app.api import proposal_approval, ci_v2, event_logs
from app.api import proposal_approval, ci_v2, product_plan_review
from app.api import proposal_approval, ci_v2, improvement_task_api
from app.api import proposal_approval, ci_v2, review_templates
from app.api import proposal_approval, ci_v2, review_dashboard
from app.api import proposal_approval, ci_v2, plan_templates
from app.api import proposal_approval, ci_v2, notification_test_api
from app.api import proposal_approval, ci_v2, notification_grouping_api
from app.api import proposal_approval, ci_v2, notification_read_api
from app.api import proposal_approval, ci_v2, competitor_import_export
from app.api import proposal_approval, ci_v2, market_param_config
from app.api import proposal_approval, ci_v2, competitor_crawl_admin
from app.api import proposal_approval, ci_v2, ai_competitor_import
from app.api import proposal_approval, ci_v2, ws
from app.api import proposal_approval, ci_v2, standard_query_api, standard_admin_api
from app.api import proposal_approval, ci_v2, ci_v2, event_graph, cost_recalculation
from app.api import proposal_approval, ci_v2, quality_8d_report
from app.api import proposal_approval, ci_v2, quality_iqc, purchase_rfq, process_sop
from app.api import proposal_approval, ci_v2, quality_complaint, purchase_supplier_eval
from app.api import proposal_approval, ci_v2, inventory
from app.api import proposal_approval, ci_v2, inventory_count
from app.api import proposal_approval, ci_v2, inventory_alert
from app.api import proposal_approval, ci_v2, ai_config_api
from app.api import proposal_approval, ci_v2, upload
from app.api import proposal_approval, ci_v2, inventory_bin
from app.api import proposal_approval, ci_v2, purchase_return
from app.api import proposal_approval, ci_v2, product_requirements
from app.models import system_config  # ensure table created
from app.services.event_handlers import register_all_handlers
import asyncio
import logging

logger = logging.getLogger(__name__)

# ── OpenAPI 中文分组描述 ──
tags_metadata = [
    {"name": "auth",       "description": "认证与用户管理"},
    {"name": "products",   "description": "产品管理"},
    {"name": "bom",        "description": "BOM物料"},
    {"name": "projects",   "description": "项目管理"},
    {"name": "events",     "description": "事件时间线"},
    {"name": "dashboard",  "description": "决策看板"},
    {"name": "admin",      "description": "系统管理"},
    {"name": "tenant",     "description": "多租户"},
]

app = FastAPI(
from app.api import ai_key_api
app.include_router(ai_key_api.router, prefix="/api")
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ROS (R&D Operations System) API - 空调产品研发运营系统",
    contact={
        "name": "ROS Team",
        "email": "ros@nousresearch.com",
        "url": "https://ros-system.dev",
    },
    license_info={
        "name": "Proprietary",
        "url": "https://ros-system.dev/license",
    },
    openapi_tags=tags_metadata,
    openapi_url="/api/v2/openapi.json",
    docs_url="/api/v2/docs",
    redoc_url="/api/v2/redoc",
)


# ── 全局异常处理器（原则25: Fail Safety） ──
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "status_code": exc.status_code})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未捕获异常: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试", "status_code": 500})



# CORS
_cors_origins = settings.CORS_ORIGINS
if _cors_origins == "*":
    app.add_middleware(SecurityHeadersMiddleware)
app.middleware("http")(csrf_middleware)
app.add_middleware(XSSProtectionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(proposal_approval.router, prefix="/api")
app.include_router(ci_v2.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(bom.router, prefix="/api")
app.include_router(projects.program_router, prefix="/api")
app.include_router(projects.project_router, prefix="/api")
app.include_router(task_deps.router, prefix="/api")
app.include_router(project_templates.router, prefix="/api")
app.include_router(time_entries.router, prefix="/api")
app.include_router(task_comments.router, prefix="/api")
app.include_router(project_reviews.router, prefix="/api")
app.include_router(projects_gates.router, prefix="/api")
app.include_router(projects_tasks.router, prefix="/api")
app.include_router(projects_risks.router, prefix="/api")
app.include_router(projects_dashboard.router, prefix="/api")
app.include_router(tests.router, prefix="/api")
app.include_router(certifications.router, prefix="/api")
app.include_router(verification_requirements.router, prefix="/api")
app.include_router(prototypes.router, prefix="/api")
app.include_router(test_executions.router, prefix="/api")
app.include_router(gate_rules.router, prefix="/api")
app.include_router(target_markets.router, prefix="/api")
# ── Phase 6 S2 — 认证中心 API ──
app.include_router(s2_cert_requirements.router, prefix="/api")
app.include_router(s2_cert_projects.router, prefix="/api")
app.include_router(s2_cert_samples.router, prefix="/api")
app.include_router(s2_cert_executions.router, prefix="/api")
app.include_router(s2_cert_results.router, prefix="/api")
app.include_router(s2_certificates.router, prefix="/api")
app.include_router(s2_gate_rules.router, prefix="/api")
app.include_router(s2_change_impact.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(safety.router, prefix="/api")
app.include_router(manufacturability.router, prefix="/api")
app.include_router(outsource.router, prefix="/api")
app.include_router(cost_accounting.router, prefix="/api")
app.include_router(cost_accounting_export.router, prefix="/api")
app.include_router(cost_accounting_analysis.router, prefix="/api")
app.include_router(cost_accounting_sheets.router, prefix="/api")
# ── 冷量联动成本重算 ──
app.include_router(cost_recalculation.router, prefix="/api")
app.include_router(bi_analytics.router, prefix="/api")
app.include_router(bi_planning.router, prefix="/api")
app.include_router(bi_cost_analytics.router, prefix="/api")
# ── 成本超标预警引擎 ──
app.include_router(cost_alert_api.router, prefix="/api")
# ── D3 用户通知偏好配置 ──
app.include_router(user_notification_api.router, prefix="/api")
# ── D4 AI辅助策划 ──
app.include_router(ai_plan_api.router, prefix="/api")
# ── 密码重置 ──
app.include_router(password_reset_api.router, prefix="/api")
# ── P4 复盘 ──
app.include_router(product_plan_review.router, prefix="/api")
app.include_router(improvement_task_api.router, prefix="/api")
app.include_router(review_templates.router, prefix="/api")
app.include_router(review_dashboard.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(dashboard_alerts.router, prefix="/api")
app.include_router(dashboard_business.router, prefix="/api")
app.include_router(dashboard_kpi.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(purchases_supplier.router, prefix="/api")
app.include_router(purchases_receipt.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(inventory_count.router, prefix="/api")
app.include_router(inventory_alert.router, prefix="/api")
app.include_router(inventory_bin.router, prefix="/api")
app.include_router(purchase_return.router, prefix="/api")

# ── 8D报告管理 (质量工程师P0) ──
app.include_router(quality_8d_report.router, prefix="/api")
app.include_router(quality_iqc.router, prefix="/api")
app.include_router(purchase_rfq.router, prefix="/api")
app.include_router(process_sop.router, prefix="/api")
app.include_router(quality_complaint.router, prefix="/api")
app.include_router(purchase_supplier_eval.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(knowledge_base.router, prefix="/api")
app.include_router(pm_workspace.router, prefix="/api")
app.include_router(pm_workspace_drafts.router, prefix="/api")
app.include_router(pm_workspace_planning.router, prefix="/api")
app.include_router(pm_workspace_config.router, prefix="/api")
app.include_router(pm_statistics.router, prefix="/api")
app.include_router(pm_roadmap.router, prefix="/api")
app.include_router(product_plan.router, prefix="/api")
app.include_router(product_plan_crud.router, prefix="/api")
app.include_router(product_plan_workflow_api.router, prefix="/api")
app.include_router(product_plan_versions.router, prefix="/api")
app.include_router(product_plan_subs.router, prefix="/api")
app.include_router(product_requirements.router, prefix="/api")
app.include_router(pm_config.router, prefix="/api")
app.include_router(pm_accessory.router, prefix="/api")
app.include_router(competitor.router, prefix="/api")
app.include_router(markets.router, prefix="/api")
app.include_router(competitor_crawl_admin.router, prefix="/api")
# ── 竞品AI导入 ──
app.include_router(ai_competitor_import.router, prefix="/api")
app.include_router(ai_competitor_confirm.router, prefix="/api")
app.include_router(competitor_market_config.router, prefix="/api")
app.include_router(competitor_history.router, prefix="/api")
app.include_router(market_param_config.router, prefix="/api")
app.include_router(admin_config.router, prefix="/api")
app.include_router(admin_role_templates.router, prefix="/api")
app.include_router(admin_role_mappings.router, prefix="/api")
app.include_router(admin_role_mappings.pm_router, prefix="/api")
app.include_router(admin_cost_configs.router, prefix="/api")
app.include_router(admin_tenant.router, prefix="/api")
app.include_router(admin_tenant.auth_router, prefix="/api")
app.include_router(pm_proposal_api.router, prefix="/api")
app.include_router(rd_panel.router, prefix="/api")
app.include_router(state_machine_api.router, prefix="/api")
app.include_router(risk_dashboard.router, prefix="/api")

# ── CI v2.0 变更智能评估系统 ──
app.include_router(ci_v2.router, prefix="/api")

# ── Digital Thread: EventGraph ──
app.include_router(event_graph.router, prefix="/api")

# ── Phase 6 S3 — ECR/ECO 工程变更控制 ──
app.include_router(ecr.router, prefix="/api")
app.include_router(eco.router, prefix="/api")
app.include_router(eco_items.router, prefix="/api")
app.include_router(ecr_workflow.router, prefix="/api")
app.include_router(ecr_attachments.router, prefix="/api")

# ── 审计日志查询 ──
app.include_router(audit_logs.router, prefix="/api")

# ── Event Timeline 路由 ──
app.include_router(event_timeline.router, prefix="/api")
# ── Event Log 管理 API ──
app.include_router(event_logs.router, prefix="/api")

# ── Webhook 路由 ──
app.include_router(webhooks.router, prefix="/api")

# ── WebSocket 端点（实时推送通知）──
app.include_router(ws.router, prefix="/api")

# ── D6-1 通知多渠道测试端点 ──
app.include_router(notification_test_api.router, prefix="/api")

# ── D6-3 通知分组 & 免打扰 ──
app.include_router(notification_grouping_api.router, prefix="/api")

# ── D6-4 通知已读/未读跨渠道同步 ──
app.include_router(notification_read_api.router, prefix="/api")

# ── D2-1 策划模板 ──
app.include_router(plan_templates.router, prefix="/api")

# ── D1-2 竞品导入导出 ──
app.include_router(competitor_import_export.router, prefix="/api")

# ── 标准监控 ──
app.include_router(standard_query_api.router, prefix="/api")
app.include_router(standard_admin_api.router, prefix="/api")

# ── AI 供应商配置管理 ──
app.include_router(ai_config_api.router, prefix="/api")
app.include_router(ai_competitor_confirm.router, prefix="/api")
app.include_router(competitor_market_config.router, prefix="/api")
app.include_router(competitor_history.router, prefix="/api")
app.include_router(dashboard_alerts.router, prefix="/api")
app.include_router(dashboard_business.router, prefix="/api")
app.include_router(dashboard_kpi.router, prefix="/api")
app.include_router(projects_gates.router, prefix="/api")
app.include_router(projects_tasks.router, prefix="/api")
app.include_router(projects_risks.router, prefix="/api")
app.include_router(projects_dashboard.router, prefix="/api")
app.include_router(ai_config_api.logs_router, prefix="/api")

# ── 图片上传 ──
app.include_router(upload.router, prefix="/api")

# ── 上传文件静态服务 ──
from fastapi.staticfiles import StaticFiles
import os
uploads_dir = "/app/static/uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=uploads_dir), name="uploads")

_celery_thread = None


def _start_celery_worker():
    """在后台线程启动 Celery Worker

    使用 subprocess 运行 `celery -A app.workers.celery_app worker`，
    独立进程不阻塞 API server。
    """
    global _celery_thread
    import subprocess
    import sys
    import os

    try:
        # 先验证 Redis 可用
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=1)
        r.ping()
        logger.info("Redis 连接确认: OK")
    except Exception as e:
        logger.warning("Redis 不可用，Celery worker 不启动: %s", e)
        return

    # 启动 Celery worker（后台子进程）
    try:
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "celery",
                "-A", "app.workers.celery_app",
                "worker",
                "--loglevel=info",
                "--concurrency=2",
                "--pool=solo",  # solo 模式，兼容 asyncio
                "-Q", "critical,default,side_effect",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        logger.info("Celery worker 已启动 (PID=%s)", proc.pid)
    except Exception as e:
        logger.warning("Celery worker 启动失败（不影响API）: %s", e)


def _init_phase4():
    """Phase 4 初始化：Event Store + Celery + MQ/MRC/CDF"""
    # 1. Event Store 表结构检查（自动建列）
    from app.core.event_store import EventStore
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        EventStore._ensure_columns(db)
        logger.info("Event Store 初始化: OK")
    except Exception as e:
        logger.warning("Event Store 初始化异常: %s", e)
    finally:
        db.close()

    # 2. 启动 Celery worker
    _start_celery_worker()

    # 3. 注册 Phase 4 健康检查
    logger.info("Phase 4 Infrastructure 初始化完成")


# ── 启动：合并所有初始化逻辑 ──
@app.on_event("startup")
def unified_startup():
    """建表 + 调度器 + ChangeImpactEngine 注册"""
    Base.metadata.create_all(bind=engine)
    # ── 启动审批催办定时任务 ──
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.services.approval_reminder import scan_and_remind

        scheduler = BackgroundScheduler()
        scheduler.add_job(scan_and_remind, "interval", minutes=30, id="approval_reminder")
        scheduler.start()
        logger.info("审批催办定时任务已启动 (每30分钟)")
    except ImportError:
        pass

    # ── 注册事件总线处理器 ──
    register_all_handlers()

    # ── 初始化默认校验规则 ──
    try:
        from app.core.database import SessionLocal
        from app.services.plan_validator import seed_default_rules
        seed_db = SessionLocal()
        seed_default_rules(seed_db)
        seed_db.close()
    except Exception as exc:
        logger.warning("初始化默认校验规则失败: %s", exc)

    # ── 初始化默认策划模板 ──
    try:
        from app.core.database import SessionLocal
        from app.services.plan_template_seeder import seed_default_templates
        seed_db = SessionLocal()
        seed_default_templates(seed_db)
        seed_db.close()
    except Exception as exc:
        logger.warning("初始化默认策划模板失败: %s", exc)

    # ── 初始化标准监控预置数据 ──
    try:
        from app.core.database import SessionLocal
        from app.services.standard_seeder import seed_standard_data
        seed_db = SessionLocal()
        seed_standard_data(seed_db)
        seed_db.close()
    except Exception as exc:
        logger.warning("初始化标准监控预置数据失败: %s", exc)

    # ── Phase 4 初始化 ──
    _init_phase4()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ── Phase 4: 基础设施健康检查 ──


@app.get("/api/v2/infra/health")
def infra_health() -> dict:
    """Phase 4 基础设施健康检查"""
    checks = {"redis": False, "celery": False, "event_store": False}

    # Redis
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.warning(f"Redis健康检查失败: {e}")
        pass

    # Event Store
    try:
        from app.core.event_store import EventStore
        from app.core.database import SessionLocal
        db = SessionLocal()
        EventStore._ensure_columns(db)
        checks["event_store"] = True
        db.close()
    except Exception as e:
        logger.warning(f"EventStore健康检查失败: {e}")
        pass

    # Celery ping（重试一次）
    try:
        from app.workers.celery_app import celery_app
        r = celery_app.control.ping(timeout=2)
        checks["celery"] = len(r) > 0 if r else False
        if not checks["celery"]:
            # 再试一次
            import time
            time.sleep(0.5)
            r = celery_app.control.ping(timeout=1)
            checks["celery"] = len(r) > 0 if r else False
    except Exception as e:
        logger.warning(f"Celery健康检查失败: {e}")
        pass

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_ok else "degraded",
            "phase": 4,
            "checks": checks,
        },
    )


    # ── ChangeImpactEngine 注册 ──
    try:
        from app.services.change_impact_engine import ChangeImpactEngine
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            ChangeImpactEngine(db).register_events()
            logger.info("ChangeImpactEngine 注册到 EventBus")
        finally:
            db.close()
    except Exception as e:
        logger.warning("ChangeImpactEngine 注册失败(非阻断): %s", e)
