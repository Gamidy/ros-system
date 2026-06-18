"""审计日志中间件 — 记录所有 /api/ 的 CUD (POST/PUT/PATCH/DELETE) 操作"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt, JWTError
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.user import User

CUD_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    """审计中间件：对 /api/ 路径的写操作记录审计日志"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 只记录 /api/ 路径的 CUD 操作
        if not request.url.path.startswith("/api/"):
            return response
        if request.method not in CUD_METHODS:
            return response

        # 从 JWT token 提取 username 和 role
        username = "anonymous"
        role = "unknown"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                )
                role = payload.get("role", "unknown")
                user_id = payload.get("sub")
                # 查询用户名
                if user_id:
                    db = SessionLocal()
                    try:
                        user = db.query(User).filter(User.id == int(user_id)).first()
                        if user:
                            username = user.username
                    finally:
                        db.close()
            except (JWTError, ValueError):
                pass

        # 获取客户端 IP
        ip_address = request.client.host if request.client else None

        # 写入审计日志
        db = SessionLocal()
        try:
            audit = AuditLog(
                username=username,
                role=role,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip_address=ip_address,
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return response
