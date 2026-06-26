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
from app.api import verification_requirements, prototypes, test_executions, gate_rules, target_markets
from app.api import s2_cert_requirements, s2_cert_projects, s2_cert_samples, s2_cert_executions, s2_cert_results, s2_certificates, s2_gate_rules, s2_change_impact
from app.api import ecr, eco
from app.api import cost_alert_api
from app.api import audit_logs
from app.api import safety
from app.api import manufacturability
from app.api import outsource
from app.api import cost_accounting
from app.api import bi_analytics
from app.api import user_notification_api
from app.api import ai_plan_api
from app.api import password_reset_api
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
app.include_router(bi_analytics.router)
# ── 成本超标预警引擎 ──
app.include_router(cost_alert_api.router, prefix="/api")
# ── D3 用户通知偏好配置 ──
app.include_router(user_notification_api.router)
# ── D4 AI辅助策划 ──
app.include_router(ai_plan_api.router, prefix="/api")
# ── 密码重置 ──
app.include_router(password_reset_api.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(knowledge.router)
app.include_router(pm_workspace.router, prefix="/api")
app.include_router(pm_statistics.router, prefix="/api")
app.include_router(pm_roadmap.router, prefix="/api")
app.include_router(product_plan.router, prefix="/api")
app.include_router(product_plan_subs.router, prefix="/api")
app.include_router(pm_config.router, prefix="/api")
app.include_router(pm_accessory.router, prefix="/api")
app.include_router(competitor_bench.router, prefix="/api")
app.include_router(competitor.router, prefix="/api")
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

# ── Phase 6 S3 — ECR/ECO 工程变更控制 ──
app.include_router(ecr.router)
app.include_router(eco.router)

# ── 审计日志查询 ──
app.include_router(audit_logs.router, prefix="/api")

# ── Event Timeline 路由 ──
app.include_router(event_timeline.router)

# ── Webhook 路由 ──
app.include_router(webhooks.router)

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

    # ── Phase 4 初始化 ──
    _init_phase4()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ── Phase 4: 基础设施健康检查 ──


@app.get("/api/v2/infra/health")
def infra_health():
    """Phase 4 基础设施健康检查"""
    checks = {"redis": False, "celery": False, "event_store": False}

    # Redis
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = True
    except Exception:
        pass

    # Event Store
    try:
        from app.core.event_store import EventStore
        from app.core.database import SessionLocal
        db = SessionLocal()
        EventStore._ensure_columns(db)
        checks["event_store"] = True
        db.close()
    except Exception:
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
    except Exception:
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
