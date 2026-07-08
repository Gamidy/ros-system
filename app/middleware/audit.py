"""审计日志中间件 — 增强版：记录所有 /api/ 操作

记录字段:
- 基础: username, role, method, path, status_code, ip_address
- 增强: action_type, resource_type, resource_id, detail, request_body, user_agent, duration_ms
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt, JWTError
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

# 敏感字段过滤 — 请求体中包含这些key时自动脱敏
SENSITIVE_FIELDS = {"password", "secret", "token", "authorization", "api_key", "old_password", "new_password"}

# 要记录的HTTP方法（所有方法都记录，但GET只记录关键路径）
RECORD_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
GET_RECORD_PREFIXES = ("/api/auth/", "/api/admin/", "/api/approval/")

# 请求体截断上限(字节)
MAX_BODY_BYTES = 1024


def infer_action_type(method: str, status_code: int) -> str:
    """根据HTTP方法和状态码推断操作类型"""
    if method == "POST":
        return "create" if status_code < 300 else "create_failed"
    elif method in ("PUT", "PATCH"):
        return "update" if status_code < 300 else "update_failed"
    elif method == "DELETE":
        return "delete" if status_code < 300 else "delete_failed"
    return "other"


def infer_resource_type(path: str) -> str:
    """从路径提取资源类型"""
    parts = path.strip("/").split("/")
    # /api/projects/123 → projects
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1]
    return "unknown"


def infer_resource_id(path: str, method: str) -> int | None:
    """从路径提取资源ID（数字）"""
    parts = path.strip("/").split("/")
    # 查找路径中的数字段
    for part in parts:
        try:
            return int(part)
        except ValueError:
            continue
    return None


def sanitize_request_body(body_text: str, max_bytes: int = MAX_BODY_BYTES) -> str | None:
    """过滤敏感字段并截断请求体"""
    import json

    if not body_text:
        return None
    try:
        data = json.loads(body_text)
        if isinstance(data, dict):
            for key in list(data.keys()):
                if key.lower() in SENSITIVE_FIELDS:
                    data[key] = "***"
        sanitized = json.dumps(data, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        sanitized = body_text
    # 截断
    encoded = sanitized.encode("utf-8")
    if len(encoded) > max_bytes:
        sanitized = encoded[:max_bytes].decode("utf-8", errors="replace") + "..."
    return sanitized


class AuditMiddleware(BaseHTTPMiddleware):
    """审计中间件增强版"""

    async def dispatch(self, request: Request, call_next):
        # 记录开始时间
        start_time = time.time()

        # 判断是否需要记录
        path = request.url.path
        method = request.method
        should_record = method in RECORD_METHODS or any(
            path.startswith(p) for p in GET_RECORD_PREFIXES
        )
        if not path.startswith("/api/") or not should_record:
            return await call_next(request)

        # 读取请求体（可重复读取）
        body_bytes = b""
        if method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
            except Exception as e:
                logger.warning(f"读取请求体失败: {e}")
                pass

        response = await call_next(request)

        # 从 JWT 提取用户信息
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

        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)

        # 推断字段
        action_type = infer_action_type(method, response.status_code)
        resource_type = infer_resource_type(path)
        resource_id = infer_resource_id(path, method)

        # 请求体脱敏
        request_body_text = body_bytes.decode("utf-8", errors="replace") if body_bytes else ""
        request_body = sanitize_request_body(request_body_text)

        # 构建操作摘要
        detail = f"{method} {path} → {response.status_code}"

        # 写入审计日志（失败不阻塞请求）
        db = SessionLocal()
        try:
            audit = AuditLog(
                username=username,
                role=role,
                method=method,
                path=path,
                status_code=response.status_code,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                request_body=request_body,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent", "")[:255],
                duration_ms=duration_ms,
            )
            db.add(audit)
            db.commit()
        except Exception as exc:
            logger.exception(f"unexpected: {exc}")
            db.rollback()
            logger.warning("审计日志写入失败: %s %s — %s", method, path, exc)
        finally:
            db.close()

        return response
