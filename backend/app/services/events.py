"""事件总线 — 同步 Observer 模式

提供解耦的事件发布/订阅能力，用于模块间通信。
当前为同步实现，不引入异步/消息队列。

事件列表:
    - PROPOSAL_APPROVED     提案审批通过
    - TEST_DONE_WITH_NG     测试完成且存在 NG 项
    - NG_THRESHOLD_REACHED  NG 数量达到阈值 (>= 3)
    - ALERT_OVERDUE_FOUND   发现超时未处理的预警

用法:
    bus = EventBus()
    bus.on(EventTypes.PROPOSAL_APPROVED, my_handler)
    bus.emit(EventTypes.PROPOSAL_APPROVED, proposal_id=42)
    bus.off(EventTypes.PROPOSAL_APPROVED, my_handler)
"""

import logging
from typing import Callable, Dict, List

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[..., None]


class EventTypes:
    """事件类型常量"""

    PROPOSAL_APPROVED = "proposal.approved"
    TEST_DONE_WITH_NG = "test.done_with_ng"
    NG_THRESHOLD_REACHED = "test.ng_threshold_reached"
    ALERT_OVERDUE_FOUND = "alert.overdue_found"


class EventBus:
    """同步事件总线（单例）

    管理事件订阅和分发，每个 handler 在独立 try/except 中执行，
    单个 handler 失败不会阻断其他 handler。
    """

    _instance = None
    _handlers: Dict[str, List[EventHandler]]

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # 仅在首次创建时初始化，避免 __init__ 重复覆盖
        if not hasattr(self, "_handlers"):
            self._handlers = {}

    # ----- 公开 API -----

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器

        Args:
            event_type: 事件类型，使用 EventTypes 常量或自定义字符串
            handler:     回调函数，签名 handler(**kwargs) -> None

        Raises:
            TypeError: handler 不可调用时抛出
        """
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Handler registered for event '%s': %s", event_type, _handler_name(handler))

    def emit(self, event_type: str, **kwargs) -> None:
        """触发事件，依次调用所有注册的 handler

        每个 handler 在独立的 try/except 中执行，一个 handler 抛异常
        不影响后续 handler 的执行。

        Args:
            event_type: 事件类型
            **kwargs:   传递给 handler 的关键字参数
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event '%s', skipped", event_type)
            return

        logger.info(
            "Emitting event '%s' to %d handler(s)",
            event_type,
            len(handlers),
        )

        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception:
                logger.exception(
                    "Handler %s failed for event '%s'",
                    _handler_name(handler),
                    event_type,
                )

    def off(self, event_type: str, handler: EventHandler) -> None:
        """注销事件处理器

        如果 handler 未注册过，静默忽略。

        Args:
            event_type: 事件类型
            handler:     此前注册的回调函数
        """
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return

        try:
            handlers.remove(handler)
            logger.debug("Handler unregistered for event '%s': %s", event_type, _handler_name(handler))
            # 清理空列表
            if not handlers:
                del self._handlers[event_type]
        except ValueError:
            pass

    # ----- 辅助方法（调试/管理） -----

    @property
    def handlers(self) -> Dict[str, List[EventHandler]]:
        """返回当前所有事件及其处理器数量的只读快照"""
        return {k: list(v) for k, v in self._handlers.items()}

    def clear(self) -> None:
        """清除所有事件处理器（主要用于测试）"""
        self._handlers.clear()
        logger.debug("All event handlers cleared")


# 模块级单例 —— 整个应用共享同一事件总线实例
bus = EventBus()


def _handler_name(handler: EventHandler) -> str:
    """获取 handler 的可读名称"""
    return getattr(handler, "__name__", repr(handler))
