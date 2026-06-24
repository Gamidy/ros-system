"""JWT认证 + RBAC权限 + XSS/CSRF防护"""
import html
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import is_super_role, require_menu, MENU_PATH_MAP, ALL_ROLES
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Token 黑名单（登出失效） ─────────────────────────────────────
# dict: token → expiry_timestamp (UTC)
TOKEN_BLACKLIST: dict[str, float] = {}

# 清理阈值：每检查多少次 token 触发一次过期清理
_BLACKLIST_CLEANUP_COUNTER = 0
_BLACKLIST_CLEANUP_INTERVAL = 100


def invalidate_token(token: str) -> None:
    """将 token 加入黑名单，使其立即失效"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},  # 允许解析已过期 token
        )
        exp = payload.get("exp", 0)
    except JWTError:
        exp = 0
    TOKEN_BLACKLIST[token] = exp


def cleanup_blacklist() -> int:
    """清理黑名单中已过期的 token，返回清理数量"""
    now = datetime.now(timezone.utc).timestamp()
    expired = [t for t, exp in TOKEN_BLACKLIST.items() if exp > 0 and exp < now]
    for t in expired:
        TOKEN_BLACKLIST.pop(t, None)
    return len(expired)


# ── XSS 防护 ──────────────────────────────────────────────────────────

def sanitize_html(value: str) -> str:
    """转义 HTML 特殊字符，防御存储型 XSS（纵深防御）

    使用 Python 标准库 html.escape() 将 <>'"& 转为 HTML 实体。
    对不含特殊字符的普通文本是 idempotent 的。

    示例:
        sanitize_html('<img src=x onerror=alert(1)>')
        → '&lt;img src=x onerror=alert(1)&gt;'
    """
    return html.escape(value, quote=True)


def sanitize_dict(d: dict) -> dict:
    """递归清洗 dict 中所有字符串值的 HTML 特殊字符"""
    for k, v in d.items():
        if isinstance(v, str):
            d[k] = sanitize_html(v)
        elif isinstance(v, dict):
            sanitize_dict(v)
    return d


# ── CSRF 防护 ─────────────────────────────────────────────────────────

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """生成随机 CSRF token"""
    return secrets.token_hex(32)


def set_csrf_cookie(response: Response) -> str:
    """在响应中设置 SameSite=Strict 的 CSRF cookie

    JWT 使用 Bearer token（非 cookie 认证），天然免疫传统 CSRF。
    此 cookie 作为纵深防护，前端需在 state-changing 请求中将
    cookie 值写入 X-CSRF-Token 请求头（双提交模式）。
    """
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,        # 前端 JS 需要读取此 cookie
        samesite="strict",
        secure=True,            # 生产 HTTPS 时生效
        max_age=86400,          # 24 小时
    )
    return token


async def csrf_middleware(request: Request, call_next):
    """CSRF 检查中间件 — 对 state-changing 请求校验 X-CSRF-Token 头

    安全方法 (GET/HEAD/OPTIONS) 直接放行。
    POST/PUT/PATCH/DELETE 需要 X-CSRF-Token 头与 csrf_token cookie 一致。
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return await call_next(request)

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    # 如果没有设置 cookie，跳过检查（向后兼容 / 开发环境）
    if cookie_token is None:
        return await call_next(request)

    if not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token 校验失败")

    return await call_next(request)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token

    JWT payload 结构: {sub, role, org_id, user_id, exp}
    - sub: 用户ID（字符串）
    - role: 用户角色
    - org_id: 所属组织ID（可选）
    - user_id: 用户ID（数值）
    - exp: 过期时间
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    # 确保 user_id 写入 payload（数值形式）
    if "sub" in to_encode and "user_id" not in to_encode:
        to_encode["user_id"] = int(to_encode["sub"])
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    global _BLACKLIST_CLEANUP_COUNTER
    # 惰性清理：每 N 次检查触发一次过期 token 清理
    _BLACKLIST_CLEANUP_COUNTER += 1
    if _BLACKLIST_CLEANUP_COUNTER >= _BLACKLIST_CLEANUP_INTERVAL:
        _BLACKLIST_CLEANUP_COUNTER = 0
        cleanup_blacklist()

    # 检查 token 是否已被登出（黑名单）
    if token in TOKEN_BLACKLIST:
        raise HTTPException(status_code=401, detail="Token 已失效，请重新登录")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效凭证")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效凭证")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="无效凭证")
    return user


def require_role(*roles: str):
    """RBAC权限校验 — admin 和 general_manager 为超级角色，自动放行"""
    def checker(current_user: User = Depends(get_current_user)):
        # 超级角色（admin / general_manager）自动获得所有权限
        if is_super_role(current_user.role):
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return current_user
    return checker
