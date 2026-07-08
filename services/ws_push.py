"""WebSocket 推送辅助 — 广播仪表盘刷新、通知等

当 BI 数据发生变更时（如新策划创建），广播 dashboard_refresh 事件
给所有在线用户，触发前端仪表盘自动刷新。
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


async def push_dashboard_refresh() -> int:
    """广播仪表盘刷新事件给所有在线用户

    前端 useWebSocket 监听 dashboard_refresh 类型消息，
    收到后自动重新请求 BI 图表数据。

    Returns:
        int: 成功推送的连接数
    """
    message = {
        "type": "dashboard_refresh",
        "action": "refresh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    sent = await ws_manager.broadcast(message)
    if sent > 0:
        logger.info("仪表盘刷新广播完成: 推送 %d 个连接", sent)
    else:
        logger.debug("仪表盘刷新广播: 无在线连接，消息已丢弃")
    return sent


def trigger_dashboard_refresh_sync() -> None:
    """同步上下文中触发仪表盘刷新广播（非阻塞）

    供同步 FastAPI 端点（如 create_plan）在事务提交后调用。
    自动适配有/无运行中事件循环的场景。

    用法:
        from app.services.ws_push import trigger_dashboard_refresh_sync
        trigger_dashboard_refresh_sync()
    """
    try:
        # 优先使用已有的运行中事件循环
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(push_dashboard_refresh())
            return
    except RuntimeError:
        pass

    # 无运行中事件循环 → 临时创建
    try:
        asyncio.run(push_dashboard_refresh())
    except RuntimeError as exc:
        logger.warning("仪表盘WS广播失败（无可用事件循环）: %s", exc)
