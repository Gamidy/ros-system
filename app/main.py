"""ROS 主应用入口 — Phase 4: Event Infrastructure"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.security import csrf_middleware
from app.middleware.audit import AuditMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.xss_protection import XSSProtectionMiddleware
from app.api import ai_key_api, admin_config, admin_cost_configs, admin_role_mappings, admin_role_templates, admin_tenant, ai_competitor_confirm, ai_competitor_import, ai_config_api, ai_plan_api, alerts, approvals, audit_logs, auth, bi_analytics, bi_cost_analytics, bom, certifications, ci_v2, competitor, competitor_crawl_admin, competitor_history, competitor_import_export, competitor_market_config, cost_accounting, cost_accounting_analysis, cost_accounting_export, cost_accounting_sheets, cost_alert_api, cost_recalculation, dashboard, dashboard_alerts, dashboard_business, dashboard_kpi, eco, eco_items, ecr, ecr_attachments, ecr_workflow, event_graph, event_logs, event_timeline, gate_rules, improvement_task_api, inventory, inventory_alert, inventory_bin, inventory_count, knowledge, knowledge_base, manufacturability, manufacturability_alias, market_param_config, markets, notification_grouping_api, notification_read_api, notification_test_api, outsource, password_reset_api, plan_templates, pm_accessory, pm_config, pm_proposal_api, pm_roadmap, pm_statistics, pm_workspace, pm_workspace_config, pm_workspace_drafts, pm_workspace_planning, process_sop, product_plan, product_plan_crud, product_plan_review, product_plan_subs, product_plan_versions, product_plan_workflow_api, product_requirements, products, project_reviews, project_templates, projects, projects_dashboard, projects_gates, projects_risks, projects_tasks, prototypes, purchase_return, purchase_rfq, purchase_supplier_eval, purchases, purchases_receipt, purchases_supplier, quality, quality_8d_report, quality_complaint, quality_iqc, rd_panel, review_dashboard, review_templates, risk_dashboard, s2_cert_executions, s2_cert_projects, s2_cert_requirements, s2_cert_results, s2_cert_samples, s2_certificates, s2_change_impact, s2_gate_rules, safety, standard_admin_api, standard_query_api, state_machine_api, target_markets, task_comments, task_deps, test_executions, tests, time_entries, upload, user_notification_api, verification_requirements, webhooks, ws

from app.models import system_config  # ensure table created
from app.services.event_handlers import register_all_handlers
import asyncio
import logging
from app.core.logging_config import setup_logging

setup_logging()
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
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


# ── 全局异常处理器 ──
from fastapi.responses import JSONResponse as _JSONResponse


@app.exception_handler(Exception)
async def _global_unhandled_exception_handler(request, exc):
    """捕获所有未处理异常，返回简洁 JSON 500（不泄漏栈）"""
    import logging as _lg
    _lg.getLogger(__name__).exception("Unhandled error: %s %s", request.method, request.url.path)
    return _JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "path": request.url.path},
    )


@app.exception_handler(ValueError)
async def _value_error_handler(request, exc):
    """ValueError 返回 400（如密码超长）"""
    import logging as _lg
    _lg.getLogger(__name__).warning("ValueError: %s %s → %s", request.method, request.url.path, str(exc)[:200])
    return _JSONResponse(
        status_code=400,
        content={"detail": str(exc)[:200] if "password" not in str(exc).lower() else "请求参数错误"},
    )


# SecurityHeadersMiddleware 已拆分到 middleware/security_headers.py
from app.middleware.security_headers import SecurityHeadersMiddleware


# CORS — 生产环境强制使用白名单，禁止 allow_origins=["*"]
_origins = settings.CORS_ORIGINS
if isinstance(_origins, str) and _origins != "*":
    _origins = [o.strip() for o in _origins.split(",") if o.strip()]
# 即使 _origins == "*" 也不使用通配符（与 allow_credentials=True 冲突且不安全）
_origins = _origins if isinstance(_origins, list) else [
    "http://139.196.15.52",
    "http://localhost:3000",
    "http://localhost:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Requested-With"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.middleware("http")(csrf_middleware)
app.add_middleware(XSSProtectionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(ai_key_api.router, prefix="/api")
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
app.include_router(manufacturability_alias.router)
app.include_router(outsource.router, prefix="/api")
app.include_router(cost_accounting.router, prefix="/api")
app.include_router(cost_accounting_export.router, prefix="/api")
app.include_router(cost_accounting_analysis.router, prefix="/api")
app.include_router(cost_accounting_sheets.router, prefix="/api")
# ── 冷量联动成本重算 ──
app.include_router(cost_recalculation.router, prefix="/api")
app.include_router(bi_analytics.router, prefix="/api")
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
app.include_router(quality.router, prefix="/api")
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
app.include_router(ai_config_api.logs_router, prefix="/api")

# ── 前后端路径兼容别名 ──
# 前端调用 /api/competitors，后端实际路由 /api/pm/competitors
# 前端调用 /api/dashboard（无后缀），重定向到 /api/dashboard/summary
from fastapi.responses import RedirectResponse as _RedirectResponse


@app.get("/api/dashboard", include_in_schema=False)
def _dashboard_alias():
    return _RedirectResponse(url="/api/dashboard/summary", status_code=307)


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
        r = redis.Redis(host="172.17.0.1", port=6379, socket_connect_timeout=1)
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


@app.on_event("startup")
def on_startup():
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
        r = redis.Redis(host="172.17.0.1", port=6379, socket_connect_timeout=2)
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


# ── 应用启动 ──────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """注册服务组件"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from app.services.change_impact_engine import ChangeImpactEngine
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            ChangeImpactEngine(db).register_events()
            logger.info("ChangeImpactEngine 注册到 EventBus ✅")
        finally:
            db.close()
    except Exception as e:
        logger.warning("ChangeImpactEngine 注册失败(非阻断): %s", e)
