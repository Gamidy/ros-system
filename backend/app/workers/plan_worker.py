"""Celery Worker 任务 — ProductPlan 事件处理

每个任务对应一个事件类型，Celery 负责队列、重试、失败处理。

迁移路径:
- Phase 3: threading.Thread (emit_async) — 直接调用 handler
- Phase 4: Celery task (emit_async) — 通过 Redis 队列调用 handler
- 兼容层: events.py 中的 emit_async 会先尝试 Celery，fallback 到 threading
"""
import json
import logging
from typing import Optional

from app.workers.celery_app import celery_app
from app.core.event_store import event_store
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# Celery 任务：Plan 事件处理
# ════════════════════════════════════════════════════════


@celery_app.task(
    bind=True,
    queue="critical",
    max_retries=3,
    default_retry_delay=5,
    name="process_plan_approved",
)
def process_plan_approved(self, plan_id: str, plan_name: str, project_id: int, **kwargs):
    """处理 PLAN_APPROVED 事件

    使用 Saga 事务确保:
    1. 创建 G0 Gate
    2. 通知 PM
    3. 如果失败 → Saga 自动补偿
    """
    from app.core.saga_engine import saga_coordinator, create_product_plan_saga
    from app.services.events import bus, EventTypes

    try:
        # ── 1. 创建 Saga 事务 ──
        saga_id = saga_coordinator.create_saga(plan_id=plan_id, context={
            "plan_id": plan_id,
            "plan_name": plan_name,
            "project_id": project_id,
            "created_by": kwargs.get("created_by", "system"),
        })

        # ── 2. 执行 Saga ──
        steps = create_product_plan_saga()
        result = saga_coordinator.execute(saga_id, steps, context={
            "plan_id": plan_id,
            "plan_name": plan_name,
            "project_id": project_id,
            "created_by": kwargs.get("created_by", "system"),
        })

        if result.status == "completed":
            logger.info("PlanApproved saga OK: plan=%s, project=%s", plan_id, project_id)
        else:
            logger.error("PlanApproved saga FAILED: plan=%s, error=%s",
                         plan_id, result.error)

        # ── 3. 记录 Event Store ──
        db = SessionLocal()
        try:
            event_store.store(
                db=db,
                event_type=EventTypes.v(EventTypes.PLAN_PROJECT_CREATED),
                payload={"plan_id": plan_id, "project_id": project_id, "saga_status": result.status.value},
                plan_id=plan_id,
                saga_id=saga_id,
                status="processed" if result.status == "completed" else "failed",
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        # ── 4. 发射系统事件 ──
        bus.emit_async(
            EventTypes.PLAN_PROJECT_CREATED,
            plan_id=plan_id,
            project_id=project_id,
            plan_name=plan_name,
        )

    except Exception as e:
        logger.exception("process_plan_approved 崩溃: plan=%s", plan_id)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=3,
    name="process_plan_side_effect",
)
def process_plan_side_effect(self, plan_id: str, plan_name: str, new_stage: str,
                              username: str = "system", **kwargs):
    """处理 Plan 副作用事件（审计日志 + 通知）

    这个任务可容忍延迟，放在 default 队列。
    """
    from app.models.audit import AuditLog
    from app.models.alert import Notification

    db = SessionLocal()
    try:
        # 审计日志
        audit = AuditLog(
            action=f"plan.advance:{new_stage}",
            target_type="product_plan",
            target_id=plan_id,
            operator=username,
            detail=f"产品策划「{plan_name}」推进到阶段: {new_stage}",
        )
        db.add(audit)

        # 通知 PM
        notif = Notification(
            target_user=username,
            channel="system",
            title=f"🔄 策划阶段更新: {plan_name}",
            content=f"产品策划「{plan_name}」已推进到「{new_stage}」阶段",
        )
        db.add(notif)
        db.commit()
        logger.info("SideEffect done: plan=%s, stage=%s", plan_id, new_stage)

    except Exception as e:
        db.rollback()
        logger.exception("process_plan_side_effect 失败: plan=%s", plan_id)
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    queue="side_effect",
    max_retries=1,
    name="process_store_event",
)
def process_store_event(self, event_type: str, event_version: str = "v1",
                         payload: Optional[dict] = None,
                         plan_id: Optional[str] = None,
                         saga_id: Optional[str] = None,
                         **kwargs):
    """记录事件到 Event Store（异步版）

    放在 side_effect 队列，不影响主流程。
    """
    db = SessionLocal()
    try:
        event_store.store(
            db=db,
            event_type=event_type,
            event_version=event_version,
            payload=payload,
            plan_id=plan_id,
            saga_id=saga_id,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Async store_event 失败: %s", e)
    finally:
        db.close()
