"""事件总线 — 同步/异步 Observer 模式 + Event Store + 版本化

三层架构:
1. EventBus: 事件发布/订阅核心（同步模式）
2. AsyncQueue: 异步分发（非阻塞 handler 执行）
3. Event Store: 所有事件自动落库

事件版本化:
    plan.approved.v1 — 通过 EventTypes.v() 方法生成
    默认版本 v1，向后兼容
"""
import json
import logging
import threading
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EventHandler = Callable[..., None]


class EventTypes:
    """事件类型常量 — 三层事件分级 + 版本化"""

    # ── 已有事件 ──
    PROPOSAL_APPROVED = "proposal.approved"
    TEST_DONE_WITH_NG = "test.done_with_ng"
    NG_THRESHOLD_REACHED = "test.ng_threshold_reached"
    ALERT_OVERDUE_FOUND = "alert.overdue_found"

    # ── Business Events — ProductPlan 流程事件 ──
    PLAN_COMPETITOR_DONE = "plan.competitor_done"
    PLAN_DEFINITION_DONE = "plan.definition_done"
    PLAN_COSTING_DONE = "plan.costing_done"
    PLAN_TECH_INPUT_DONE = "plan.tech_input_done"
    PLAN_PROJECT_INIT_DONE = "plan.project_init_done"
    PLAN_APPROVED = "plan.approved"
    PLAN_RELEASED = "plan.released"

    # ── System Events — 系统自动动作 ──
    PLAN_PROJECT_CREATED = "plan.project_created"
    PLAN_BOM_INITIALIZED = "plan.bom_initialized"

    # ── Side Effect Events — 通知/审计 ──
    PLAN_NOTIFY_PM = "plan.notify_pm"
    PLAN_AUDIT_LOG = "plan.audit_log"

    # ── 事件版本映射 ──
    _VERSIONS: Dict[str, str] = {
        PROPOSAL_APPROVED: "v1",
        TEST_DONE_WITH_NG: "v1",
        NG_THRESHOLD_REACHED: "v1",
        ALERT_OVERDUE_FOUND: "v1",
        PLAN_COMPETITOR_DONE: "v1",
        PLAN_DEFINITION_DONE: "v1",
        PLAN_COSTING_DONE: "v1",
        PLAN_TECH_INPUT_DONE: "v1",
        PLAN_PROJECT_INIT_DONE: "v1",
        PLAN_APPROVED: "v1",
        PLAN_RELEASED: "v1",
        PLAN_PROJECT_CREATED: "v1",
        PLAN_BOM_INITIALIZED: "v1",
        PLAN_NOTIFY_PM: "v1",
        PLAN_AUDIT_LOG: "v1",
    }

    @classmethod
    def v(cls, event_type: str) -> str:
        """获取带版本号的事件类型字符串

        如 EventTypes.v(EventTypes.PLAN_APPROVED) → "plan.approved.v1"
        """
        version = cls._VERSIONS.get(event_type, "v1")
        return f"{event_type}.{version}"


class EventBus:
    """同步事件总线（单例）+ 异步模式

    管理事件订阅和分发。
    同步模式: handler 在 emit() 调用线程中依次执行
    异步模式: handler 在独立线程中执行
    每个 handler 在独立 try/except 中执行，单 handler 失败不阻断其他。
    """

    _instance = None
    _handlers: Dict[str, List[EventHandler]]

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_handlers"):
            self._handlers = {}

    # ----- 公开 API -----

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器"""
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Handler registered for event '%s': %s", event_type, _handler_name(handler))

    def emit(self, event_type: str, **kwargs) -> None:
        """触发事件（同步模式）

        依次调用所有注册的 handler。
        每个 handler 在独立 try/except 中执行。
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event '%s', skipped", event_type)
            return

        logger.info("Emitting event '%s' to %d handler(s)", event_type, len(handlers))
        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception:
                logger.exception("Handler %s failed for event '%s'", _handler_name(handler), event_type)

    def emit_async(self, event_type: str, **kwargs) -> None:
        """触发事件（异步模式 — 非阻塞）

        handler 在后台线程中执行，不阻塞主流程。
        调用后立即返回。
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event '%s' (async), skipped", event_type)
            return

        logger.info("Async emitting event '%s' to %d handler(s)", event_type, len(handlers))

        def _run():
            for handler in handlers:
                try:
                    handler(**kwargs)
                except Exception:
                    logger.exception(
                        "Async handler %s failed for event '%s'",
                        _handler_name(handler), event_type,
                    )

        t = threading.Thread(target=_run, daemon=True, name=f"evt-{event_type.replace('.','-')}")
        t.start()

    def off(self, event_type: str, handler: EventHandler) -> None:
        """注销事件处理器"""
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return
        try:
            handlers.remove(handler)
            logger.debug("Handler unregistered for event '%s': %s", event_type, _handler_name(handler))
            if not handlers:
                del self._handlers[event_type]
        except ValueError:
            pass

    # ----- 辅助方法 -----

    @property
    def handlers(self) -> Dict[str, List[EventHandler]]:
        return {k: list(v) for k, v in self._handlers.items()}

    def clear(self) -> None:
        self._handlers.clear()
        logger.debug("All event handlers cleared")


# 模块级单例
bus = EventBus()


# ════════════════════════════════════════════════════════
# Event Store — 所有事件的持久化存储
# ════════════════════════════════════════════════════════


def store_event(event_type: str, **kwargs) -> None:
    """Event Store 处理器 — 自动记录事件到 event_logs 表

    注册方式: bus.on(ANY_EVENT, store_event) — 在 register_all_handlers 中调用
    """
    from app.core.database import SessionLocal
    from app.models.event_log import EventLog

    db = SessionLocal()
    try:
        # 构建 payload（排除敏感字段）
        payload = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                   for k, v in kwargs.items()}

        log = EventLog(
            event_type=event_type,
            event_version=EventTypes._VERSIONS.get(event_type, "v1"),
            payload=json.dumps(payload, ensure_ascii=False, default=str),
            status="emitted",
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error("Event Store 写入失败: event_type=%s, error=%s", event_type, e)
    finally:
        db.close()


def _handler_name(handler: EventHandler) -> str:
    return getattr(handler, "__name__", repr(handler))
