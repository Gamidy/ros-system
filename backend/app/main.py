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
from app.api import knowledge
from app.api import auth, products, bom, projects, tests, certifications, alerts, dashboard, purchases, approvals, pm_workspace, pm_statistics, pm_roadmap, product_plan, product_plan_subs, admin_config, pm_config, pm_accessory, competitor, competitor_bench, admin_role_templates, admin_role_mappings, admin_cost_configs, pm_proposal_api, rd_panel, state_machine_api, event_timeline, risk_dashboard, admin_tenant, webhooks
from app.api import product_plan_crud, product_plan_workflow_api, product_plan_versions
from app.api import markets
from app.api import verification_requirements, prototypes, test_executions, gate_rules, target_markets
from app.api import s2_cert_requirements, s2_cert_projects, s2_cert_samples, s2_cert_executions, s2_cert_results, s2_certificates, s2_gate_rules, s2_change_impact
from app.api import ecr, eco
from app.api import cost_alert_api
from app.api import audit_logs
from app.api import safety
from app.api import manufacturability
from app.api import outsource
from app.api import cost_accounting
from app.api import cost_accounting_export
from app.api import cost_accounting_analysis
from app.api import cost_accounting_sheets
from app.api import bi_analytics
from app.api import user_notification_api
from app.api import ai_plan_api
from app.api import password_reset_api
from app.api import event_logs
from app.api import product_plan_review
from app.api import improvement_task_api
from app.api import review_templates
from app.api import plan_templates
from app.api import notification_test_api
from app.api import notification_grouping_api
from app.api import notification_read_api
from app.api import competitor_import_export
from app.api import market_param_config
from app.api import competitor_crawl_admin
from app.api import ws
from app.api import standard_query_api, standard_admin_api
from app.api import ci_v2, event_graph, cost_recalculation
from app.api import inventory
from app.api import inventory_count
from app.api import inventory_alert
from app.api import inventory_bin
from app.api import purchase_return
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """添加安全响应头中间件"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# CORS
_cors_origins = settings.CORS_ORIGINS
if _cors_origins == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(SecurityHeadersMiddleware)
app.middleware("http")(csrf_middleware)
app.add_middleware(XSSProtectionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(bom.router, prefix="/api")
app.include_router(projects.program_router, prefix="/api")
app.include_router(projects.project_router, prefix="/api")
app.include_router(tests.router, prefix="/api")
app.include_router(certifications.router, prefix="/api")
app.include_router(verification_requirements.router)
app.include_router(prototypes.router)
app.include_router(test_executions.router)
app.include_router(gate_rules.router)
app.include_router(target_markets.router)
# ── Phase 6 S2 — 认证中心 API ──
app.include_router(s2_cert_requirements.router)
app.include_router(s2_cert_projects.router)
app.include_router(s2_cert_samples.router)
app.include_router(s2_cert_executions.router)
app.include_router(s2_cert_results.router)
app.include_router(s2_certificates.router)
app.include_router(s2_gate_rules.router)
app.include_router(s2_change_impact.router)
app.include_router(alerts.router, prefix="/api")
app.include_router(safety.router)
app.include_router(manufacturability.router)
app.include_router(outsource.router)
app.include_router(cost_accounting.router)
app.include_router(cost_accounting_export.router)
app.include_router(cost_accounting_analysis.router)
app.include_router(cost_accounting_sheets.router)
# ── 冷量联动成本重算 ──
app.include_router(cost_recalculation.router)
app.include_router(bi_analytics.router)
# ── 成本超标预警引擎 ──
app.include_router(cost_alert_api.router, prefix="/api")
# ── D3 用户通知偏好配置 ──
app.include_router(user_notification_api.router)
# ── D4 AI辅助策划 ──
app.include_router(ai_plan_api.router, prefix="/api")
# ── 密码重置 ──
app.include_router(password_reset_api.router, prefix="/api")
# ── P4 复盘 ──
app.include_router(product_plan_review.router, prefix="/api")
app.include_router(improvement_task_api.router)
app.include_router(review_templates.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(inventory_count.router, prefix="/api")
app.include_router(inventory_alert.router, prefix="/api")
app.include_router(inventory_bin.router, prefix="/api")
app.include_router(purchase_return.router, prefix="/api")
app.include_router(knowledge.router)
app.include_router(pm_workspace.router, prefix="/api")
app.include_router(pm_statistics.router, prefix="/api")
app.include_router(pm_roadmap.router, prefix="/api")
app.include_router(product_plan.router, prefix="/api")
app.include_router(product_plan_crud.router, prefix="/api/product-plans")
app.include_router(product_plan_workflow_api.router, prefix="/api/product-plans")
app.include_router(product_plan_versions.router, prefix="/api/product-plans")
app.include_router(product_plan_subs.router, prefix="/api")
app.include_router(pm_config.router, prefix="/api")
app.include_router(pm_accessory.router, prefix="/api")
app.include_router(competitor_bench.router, prefix="/api")
app.include_router(competitor.router, prefix="/api")
app.include_router(markets.router, prefix="/api")
app.include_router(competitor_crawl_admin.router)
app.include_router(market_param_config.router, prefix="/api")
app.include_router(admin_config.router)
app.include_router(admin_role_templates.router)
app.include_router(admin_role_mappings.router)
app.include_router(admin_role_mappings.pm_router)
app.include_router(admin_cost_configs.router)
app.include_router(admin_tenant.router)
app.include_router(admin_tenant.auth_router)
app.include_router(pm_proposal_api.router, prefix="/api")
app.include_router(rd_panel.router, prefix="/api")
app.include_router(state_machine_api.router, prefix="/api")
app.include_router(risk_dashboard.router)

# ── CI v2.0 变更智能评估系统 ──
app.include_router(ci_v2.router)

# ── Digital Thread: EventGraph ──
app.include_router(event_graph.router)

# ── Phase 6 S3 — ECR/ECO 工程变更控制 ──
app.include_router(ecr.router)
app.include_router(eco.router)

# ── 审计日志查询 ──
app.include_router(audit_logs.router, prefix="/api")

# ── Event Timeline 路由 ──
app.include_router(event_timeline.router)
# ── Event Log 管理 API ──
app.include_router(event_logs.router, prefix="/api")

# ── Webhook 路由 ──
app.include_router(webhooks.router)

# ── WebSocket 端点（实时推送通知）──
app.include_router(ws.router)

# ── D6-1 通知多渠道测试端点 ──
app.include_router(notification_test_api.router)

# ── D6-3 通知分组 & 免打扰 ──
app.include_router(notification_grouping_api.router)

# ── D6-4 通知已读/未读跨渠道同步 ──
app.include_router(notification_read_api.router)

# ── D2-1 策划模板 ──
app.include_router(plan_templates.router, prefix="/api")

# ── D1-2 竞品导入导出 ──
app.include_router(competitor_import_export.router)

# ── 标准监控 ──
app.include_router(standard_query_api.router)
app.include_router(standard_admin_api.router)

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
