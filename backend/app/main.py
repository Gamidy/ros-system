"""PLM 系统入口 — FastAPI 应用工厂"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import setup_logging
from app.api.v1.router import v1_router
from app.middleware.security import (
    SecurityHeadersMiddleware,
    XSSProtectionMiddleware,
    csrf_middleware,
)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建表，关闭时清理"""
    from app.database import async_engine, Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="吉德家用变频空调PLM系统 — 基于IPD结构化流程",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

# Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# CSRF Protection (纵深防护)
app.middleware("http")(csrf_middleware)

# XSS Protection (仅 state-changing 请求)
app.add_middleware(XSSProtectionMiddleware)

# 全局异常处理器


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "path": request.url.path},
    )

# 路由
app.include_router(v1_router)

# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
