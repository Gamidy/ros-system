"""事件总线 — Redis/Celery 异步 + 同步 Observer 模式 (Phase 4)

三层架构:
1. EventBus: 事件发布/订阅核心（同步模式）
2. Redis Queue (Celery): 异步任务分发（替换 Phase 3 threading）
3. Event Store: 所有事件自动落库

事件版本化:
    plan.approved.v1 — 通过 EventTypes.v() 方法生成
    默认版本 v1，向后兼容

迁移路径:
    Phase 3: threading.Thread → emit_async
    Phase 4: Redis/Celery → emit_async (无 threading 依赖)
    降级: 如果 Celery 不可用，自动 fallback 到 threading
"""
import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

EventHandler = Callable[..., None]

# ── Celery 可用性检测（惰性导入，避免没装 celery 时崩溃） ──
_has_celery = False
_celery_checked = False


def _check_celery() -> bool:
    """检测 Celery Redis 是否可用"""
    global _has_celery, _celery_checked
    if _celery_checked:
        return _has_celery
    _celery_checked = True
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=1)
        r.ping()
        _has_celery = True
        logger.info("Celery/Redis 连接成功，将使用 Redis 异步队列")
    except Exception as e:
        logger.warning(f"Redis 不可用: {e}")
        _has_celery = False
        logger.warning("Redis 不可用，emit_async 将使用 threading fallback")
    return _has_celery


# ════════════════════════════════════════════════════════
# 事件类型定义
# ════════════════════════════════════════════════════════


class EventTypes:
    """事件类型常量 — 三层事件分级 + 版本化"""

    # ── 已有事件 ──
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

    # ── Approval Events — 审批流事件 ──
    APPROVAL_COMPLETED = "approval.completed"
    APPROVAL_REJECTED = "approval.rejected"

    # ── 事件版本映射 ──
    _VERSIONS: Dict[str, str] = {
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
        APPROVAL_COMPLETED: "v1",
        APPROVAL_REJECTED: "v1",
    }

    @classmethod
    def v(cls, event_type: str) -> str:
        """获取带版本号的事件类型字符串"""
        version = cls._VERSIONS.get(event_type, "v1")
        return f"{event_type}.{version}"


# ════════════════════════════════════════════════════════
# Event Bus — 同步 + 异步（Redis/Threading）
# ════════════════════════════════════════════════════════


class EventBus:
    """事件总线（单例）

    同步模式: emit() — 当前线程直接调用 handler
    异步模式: emit_async() — Redis/Celery 优先，threading fallback

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

    # ----- 同步模式 -----

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器"""
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("Handler registered for event '%s': %s", event_type, _handler_name(handler))

    def emit(self, event_type: str, **kwargs) -> None:
        """触发事件（同步模式）

        当前线程直接调用所有 handler。
        适合需要立即生效的场景（如状态更新）。
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event '%s', skipped", event_type)
            return

        logger.info("Emitting event '%s' to %d handler(s)", event_type, len(handlers))
        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.exception("Handler %s failed for event '%s': %s", _handler_name(handler), event_type, e)

    # ----- 异步模式（Phase 4: Redis/Celery + Threading fallback） -----

    def emit_async(self, event_type: str, **kwargs) -> None:
        """触发事件（异步模式 — 非阻塞）

        Phase 4 升级:
        1. 尝试 Redis/Celery 队列（生产级）
        2. 如果不可用 → threading fallback（开发兼容）

        Phase 5 (P5-10):
        事件发出后自动触发 Webhook 推送。
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("No handlers for event '%s' (async), skipped", event_type)
            return

        logger.info("Async emit: '%s' to %d handler(s)", event_type, len(handlers))

        if _check_celery():
            self._emit_via_celery(event_type, handlers, kwargs)
        else:
            self._emit_via_threading(event_type, handlers, kwargs)

        # ── P5-10: 事件发出后触发 Webhook 推送 ──
        self._trigger_webhooks(event_type, kwargs)

    def _trigger_webhooks(self, event_type: str, kwargs: dict) -> None:
        """触发 Webhook 推送（非阻塞）

        在异步事件分发后调用，确保不阻塞主流程。
        使用 asyncio.create_task 在事件循环中调度，
        若当前线程无事件循环则使用 threading fallback。
        """
        try:
            from app.services.webhook_service import webhook_dispatcher

            payload = {
                k: str(v) if not isinstance(v, (str, int, float, bool, type(None), list, dict))
                else v
                for k, v in kwargs.items()
            }

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(webhook_dispatcher.dispatch(event_type, payload))
                    logger.debug("Webhook dispatch scheduled via event loop: %s", event_type)
                    return
            except RuntimeError:
                pass

            # Fallback: threading
            import threading
            t = threading.Thread(
                target=lambda: asyncio.run(
                    webhook_dispatcher.dispatch(event_type, payload)
                ),
                daemon=True,
                name=f"wh-{event_type.replace('.','-')}",
            )
            t.start()
            logger.debug("Webhook dispatch scheduled via threading: %s", event_type)

        except Exception as e:
            logger.error("Webhook dispatch 失败: event_type=%s, error=%s", event_type, e)

    def _emit_via_celery(self, event_type: str, handlers: List[EventHandler], kwargs: dict) -> None:
        """通过 Celery 任务异步分发（生产级）"""
        try:
            from app.workers.plan_worker import (
                process_plan_approved,
                process_plan_side_effect,
                process_store_event,
            )

            # 根据事件类型选择对应 Celery 任务
            event_base = event_type.split(".")[0] + "." + event_type.split(".")[1] if "." in event_type else event_type

            if event_type == "plan.approved" or event_type.startswith("plan.approved"):
                # critical 队列 — 需要 Saga 保证
                process_plan_approved.delay(**kwargs)
            elif event_type in ("plan.audit_log", "plan.notify_pm"):
                # side_effect 队列 — 可延迟
                process_store_event.delay(
                    event_type=event_type,
                    payload=kwargs,
                    plan_id=kwargs.get("plan_id"),
                )
                process_plan_side_effect.delay(**kwargs)
            elif event_type.startswith("plan."):
                # default 队列 — 普通业务事件
                process_store_event.delay(
                    event_type=event_type,
                    payload=kwargs,
                    plan_id=kwargs.get("plan_id"),
                )
                process_plan_side_effect.delay(**kwargs)
            else:
                # 通用 fallback — 直接调 threading
                self._emit_via_threading(event_type, handlers, kwargs)

            logger.debug("Celery task dispatched: %s", event_type)

        except Exception as e:
            logger.warning("Celery 分发失败 (%s)，fallback 到 threading: %s", event_type, e)
            self._emit_via_threading(event_type, handlers, kwargs)

    def _emit_via_threading(self, event_type: str, handlers: List[EventHandler], kwargs: dict) -> None:
        """通过 threading 异步分发（开发兼容 / fallback）"""
        import threading

        def _run():
            for handler in handlers:
                try:
                    handler(**kwargs)
                except Exception as e:
                    logger.exception(
                        "Async handler %s failed for event '%s': %s",
                        _handler_name(handler), event_type, e,
                    )

        t = threading.Thread(
            target=_run, daemon=True,
            name=f"evt-{event_type.replace('.','-')}",
        )
        t.start()
        logger.debug("Threading fallback used: %s", event_type)

    # ----- 生命周期管理 -----

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
    """Event Store 处理器 — 自动记录事件到 event_logs 表"""
    from app.core.database import SessionLocal
    from app.core.event_store import event_store

    db = SessionLocal()
    try:
        payload = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                   for k, v in kwargs.items()}

        event_store.store(
            db=db,
            event_type=event_type,
            event_version=EventTypes._VERSIONS.get(event_type, "v1"),
            payload=payload,
            plan_id=kwargs.get("plan_id"),
            saga_id=kwargs.get("saga_id"),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Event Store 写入失败: event_type=%s, error=%s", event_type, e)
    finally:
        db.close()


def _handler_name(handler: EventHandler) -> str:
    return getattr(handler, "__name__", repr(handler))
