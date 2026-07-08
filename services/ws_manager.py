"""WebSocket 连接管理器 — 管理认证 + 用户消息推送

架构:
  ws_manager (单例)
    ├── connect(ws, user_id)     — 注册新连接
    ├── disconnect(ws, user_id)  — 移除断开的连接
    ├── send_to_user(user_id, msg) — 推送给指定用户
    └── broadcast(msg)           — 推送给所有在线用户

认证方式:
  - WebSocket URL 参数 ?token=xxx
  - 使用 jwt.decode 解析用户身份 (sub=user_id)
  - 从数据库查找 username 用于消息推送
"""
import json
import logging
from typing import Optional

from fastapi import WebSocket
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


_WSMessage = dict  # type alias for JSON-serializable dict


class WSConnectionManager:
    """WebSocket 连接管理器（单例）"""

    _instance = None

    def __new__(cls) -> "WSConnectionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        # username -> list[WebSocket]
        self._connections: dict[str, list[WebSocket]] = {}
        # WebSocket id -> username 反向查找
        self._ws_to_user: dict[int, str] = {}

    # ── 认证 ────────────────────────────────────────────

    async def _decode_token(self, token: str) -> Optional[dict]:
        """解码 JWT token，返回 payload dict"""
        try:
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": True},
            )
        except JWTError as e:
            logger.warning("WebSocket JWT 解码失败: %s", e)
            return None

    async def _lookup_username(self, user_id: int) -> Optional[str]:
        """从数据库查询 username"""
        db = SessionLocal()
        try:
            user: User = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active and user.username:
                return str(user.username)
            logger.warning("WebSocket 认证: 用户不存在或已禁用: id=%s", user_id)
            return None
        except Exception as e:
            logger.error("WebSocket 数据库查询失败: %s", e)
            return None
        finally:
            db.close()

    async def authenticate(self, websocket: WebSocket) -> Optional[str]:
        """从 WebSocket 查询参数解析 JWT token 并返回 username

        Returns:
            username (str) 或 None（认证失败）
        """
        token = websocket.query_params.get("token")
        if not token:
            logger.warning("WebSocket 连接缺少 token 参数")
            return None

        payload = await self._decode_token(token)
        if not payload:
            return None

        sub = payload.get("sub")
        if not sub:
            logger.warning("JWT payload 缺少 sub")
            return None

        return await self._lookup_username(int(sub))

    # ── 连接管理 ────────────────────────────────────────

    async def connect(self, websocket: WebSocket, username: str) -> None:
        """接受 WebSocket 连接并注册"""
        await websocket.accept()
        if username not in self._connections:
            self._connections[username] = []
        self._connections[username].append(websocket)
        self._ws_to_user[id(websocket)] = username
        logger.info(
            "WebSocket 已连接: user=%s, total_connections=%d",
            username, self._total_count(),
        )

    def disconnect(self, websocket: WebSocket, username: str) -> None:
        """断开连接并清理"""
        conns = self._connections.get(username, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(username, None)
        self._ws_to_user.pop(id(websocket), None)
        logger.info(
            "WebSocket 已断开: user=%s, total_connections=%d",
            username, self._total_count(),
        )

    # ── 消息推送 ────────────────────────────────────────

    async def send_to_user(self, username: str, message: dict) -> int:
        """向指定用户的所有连接推送消息

        Args:
            username: 目标用户名
            message: JSON 可序列化的 dict

        Returns:
            int: 成功推送的连接数
        """
        conns = self._connections.get(username, [])
        if not conns:
            logger.debug("用户 '%s' 无在线连接，消息丢弃: type=%s", username, message.get("type"))
            return 0

        data = json.dumps(message, ensure_ascii=False)
        sent = 0
        dead = []
        for ws in conns:
            try:
                await ws.send_text(data)
                sent += 1
            except Exception as e:
                logger.warning("向用户 '%s' 推送失败: %s", username, e)
                dead.append(ws)

        # 清理失效连接
        for ws in dead:
            self.disconnect(ws, username)

        return sent

    async def broadcast(self, message: dict) -> int:
        """向所有在线用户广播消息"""
        data = json.dumps(message, ensure_ascii=False)
        sent = 0
        dead = []
        for username, conns in list(self._connections.items()):
            for ws in conns:
                try:
                    await ws.send_text(data)
                    sent += 1
                except Exception as e:
                    logger.warning("广播失败 user=%s: %s", username, e)
                    dead.append(ws)
        for ws in dead:
            uid = self._ws_to_user.get(id(ws))
            if uid:
                self.disconnect(ws, uid)
        return sent

    # ── 在线状态查询 ────────────────────────────────────

    def is_online(self, username: str) -> bool:
        return username in self._connections and bool(self._connections[username])

    def online_users(self) -> list[str]:
        return list(self._connections.keys())

    def _total_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


# 模块级单例
ws_manager = WSConnectionManager()
