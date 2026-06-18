"""ROS 主应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.core.security import csrf_middleware
from app.middleware.audit import AuditMiddleware
from app.api import knowledge
from app.api import auth, products, bom, projects, tests, certifications, alerts, dashboard, purchases, approvals, pm_workspace, admin_config, pm_config, pm_accessory, proposal_approval, admin_role_templates, admin_role_mappings, admin_cost_configs, pm_proposal_api
from app.models import system_config  # ensure table created

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


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
        response.headers["X-XSS-Protection"] = "0"  # 由 CSP 替代，禁用旧版浏览器 XSS filter
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers (CSP + other security headers)
app.add_middleware(SecurityHeadersMiddleware)

# CSRF 纵深防护中间件
app.middleware("http")(csrf_middleware)

# 审计日志中间件 — 记录所有 /api/ CUD 操作
app.add_middleware(AuditMiddleware)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(bom.router, prefix="/api")
app.include_router(projects.program_router, prefix="/api")
app.include_router(projects.project_router, prefix="/api")
app.include_router(tests.router, prefix="/api")
app.include_router(certifications.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(knowledge.router)
app.include_router(pm_workspace.router, prefix="/api")
app.include_router(pm_config.router, prefix="/api")
app.include_router(pm_accessory.router, prefix="/api")
app.include_router(admin_config.router)
app.include_router(admin_role_templates.router)
app.include_router(admin_role_mappings.router)
app.include_router(admin_cost_configs.router)
app.include_router(proposal_approval.router, prefix="/api")
app.include_router(pm_proposal_api.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
