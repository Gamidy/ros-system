"""事件处理器 — 注册系统内各类事件的处理逻辑

每个 handler 使用独立 DB session，独立 try/except，
失败只打 log 不抛异常，保证不影响主流程。

在 main.py 启动时调用 register_all_handlers() 注册。
"""
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.alert import Alert, Notification
from app.models.test import QualityIssue
from .events import bus, EventTypes, store_event
from app.services.notification.consumer import register_handlers as register_notification_handlers
from app.services.ws_bridge import register_handlers as register_ws_handlers

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Handler: 测试完成且有不合格项
# ─────────────────────────────────────────────────────────


def on_test_done_with_ng(test_id: int, request_no: str, ng_count: int, **kwargs):
    """测试完成且存在不合格项

    1. 检查是否已有同源未解决预警 (alert_type='test_ng', target_id=test_id)
       — 没有则创建新的 Alert(level=2)
    2. 如果 ng_count >= 3:
       - 创建 QualityIssue（来源=测试NG）
       - 将 Alert 升级到 level=1
       - emit('test.ng_threshold_reached', ...)
    """
    db: Session = SessionLocal()
    try:
        # ── 查询已有同源预警 ──
        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.alert_type == "test_ng",
                Alert.target_id == test_id,
                Alert.is_resolved == False,
            )
            .first()
        )

        if existing_alert is None:
            alert = Alert(
                target_type="test",
                target_id=test_id,
                alert_type="test_ng",
                level=2,
                title=f"测试不合格: {request_no}",
                message=f"测试申请 {request_no} 存在 {ng_count} 项不合格",
            )
            db.add(alert)
            db.flush()
            alert_id = alert.id
        else:
            alert_id = existing_alert.id

        # ── NG 阈值触达 (>=3) ──
        if ng_count >= 3:
            # 创建品质整改单
            now_str = datetime.now().strftime("%Y%m%d%H%M%S")
            quality_issue = QualityIssue(
                issue_no=f"QI-TEST-{test_id}-{now_str}",
                title=f"测试NG阈值触达: {request_no}（{ng_count}项不合格）",
                project_code=kwargs.get("project_code"),
                issue_source="测试NG",
                severity="A",
                status="open",
            )
            db.add(quality_issue)
            db.flush()

            # 升级预警到 level=1
            target_alert = existing_alert or (
                db.query(Alert).filter(Alert.id == alert_id).first()
            )
            if target_alert is not None:
                target_alert.level = 1

            db.commit()

            # 发射阈值触达事件（独立 try/except，不影响本次事务）
            try:
                bus.emit(
                    "test.ng_threshold_reached",
                    test_id=test_id,
                    request_no=request_no,
                    ng_count=ng_count,
                    quality_issue_id=quality_issue.id,
                )
            except Exception as emit_err:
                logger.error("emit test.ng_threshold_reached 失败: %s", emit_err)

            logger.info(
                "测试NG阈值触达: test_id=%s, request_no=%s, "
                "ng_count=%s, quality_issue_id=%s",
                test_id, request_no, ng_count, quality_issue.id,
            )
        else:
            db.commit()
            logger.info(
                "测试NG预警已创建（未达阈值）: "
                "test_id=%s, request_no=%s, ng_count=%s",
                test_id, request_no, ng_count,
            )

    except Exception as e:
        db.rollback()
        logger.error("on_test_done_with_ng 处理失败: %s", e)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────
# Handler: 预警逾期未处理
# ─────────────────────────────────────────────────────────


def on_alert_overdue_found(alert_id: int, target_type: str, target_id: int, **kwargs):
    """预警逾期发现

    1. 将预警等级升级 (level-1, 数字越小越紧急)
    2. 创建通知提醒审批人
    """
    db: Session = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert is None:
            logger.warning("预警记录不存在: alert_id=%s", alert_id)
            return

        # 升级预警等级（降低数字 = 更紧急）
        if alert.level > 1:
            old_level = alert.level
            alert.level = alert.level - 1
            level_change = f"{old_level}→{alert.level}"
        else:
            level_change = "已是最高级(1)"
            logger.info("预警等级已最高: alert_id=%s", alert_id)

        # 创建通知给审批人
        approver = kwargs.get("approver", "系统管理员")
        notification = Notification(
            alert_id=alert_id,
            target_user=approver,
            channel="system",
            title=f"【预警升级】{alert.title}",
            content=(
                f"预警「{alert.title}」(目标: {target_type}#{target_id}) "
                f"已逾期未处理，等级已升级({level_change})，请及时处理。"
            ),
        )
        db.add(notification)

        db.commit()
        logger.info(
            "逾期预警已升级: alert_id=%s, level_change=%s, approver=%s",
            alert_id, level_change, approver,
        )

    except Exception as e:
        db.rollback()
        logger.error("on_alert_overdue_found 处理失败: %s", e)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────
# 注册入口
# ─────────────────────────────────────────────────────────


def _register_all_events():
    """注册所有事件处理器 + Event Store"""
    # ── 注册通知事件处理器（事件驱动推送引擎）──
    register_notification_handlers()

    # ── 注册 WebSocket 事件桥接 ──
    register_ws_handlers()

    # ── 已有事件 ──
    for evt in [
        "test.done_with_ng",
        "alert.overdue_found",
    ]:
        bus.on(evt, store_event)

    # NOTE: on_proposal_approved 已移除 — 这是 proposal审批(立项审批)处理器，
    # 错误地注册到了 plan.approved (产品策划审批)。Saga 统一处理 plan.approved 的后续流程。
    bus.on("test.done_with_ng", on_test_done_with_ng)
    bus.on("alert.overdue_found", on_alert_overdue_found)

    # ── ProductPlan 事件 ──
    for evt in [
        "plan.approved",
        "plan.competitor_done",
        "plan.definition_done",
        "plan.costing_done",
        "plan.tech_input_done",
        "plan.project_init_done",
        "plan.released",
    ]:
        bus.on(evt, store_event)

    bus.on("plan.approved", on_plan_approved)
    bus.on("plan.competitor_done", on_plan_side_effect)
    bus.on("plan.definition_done", on_plan_side_effect)
    bus.on("plan.costing_done", on_plan_side_effect)
    bus.on("plan.tech_input_done", on_plan_side_effect)
    bus.on("plan.project_init_done", on_plan_side_effect)
    bus.on("plan.released", on_plan_side_effect)

    # ── System Events（预留） ──
    bus.on("plan.project_created", store_event)
    bus.on("plan.bom_initialized", store_event)

    # ── Side Effect Events（预留） ──
    bus.on("plan.audit_log", store_event)
    bus.on("plan.notify_pm", store_event)

    # ── Approval Events — ProductPlan 审批集成 ──
    from app.services.product_plan_approval import (
        on_approval_completed,
        on_proposal_rejected,
    )
    bus.on("approval.completed", on_approval_completed)
    bus.on("approval.rejected", on_proposal_rejected)
    bus.on("approval.completed", store_event)
    bus.on("approval.rejected", store_event)

    logger.info(
        "事件系统初始化完成: %d 事件类型, Event Store 已激活",
        len(bus.handlers),
    )


register_all_handlers = _register_all_events


# ════════════════════════════════════════════════════════
# ProductPlan 事件处理器
# ════════════════════════════════════════════════════════


def on_plan_approved(plan_id: str, plan_name: str, project_id: int, **kwargs):
    """ProductPlan 批准事件处理器 (Phase 4: Saga 事务封装)

    这是一个兼容层:
    - 如果 Celery/Redis 在线 → 事件已通过 Celery 任务处理
    - 如果 Celery 不可用 → 用 Saga 直接同步执行
    """
    from app.core.saga_engine import saga_coordinator, create_product_plan_saga

    # 检查是否已通过 Celery 处理（避免重复）
    if kwargs.get("_from_celery"):
        logger.debug("Saga already handled by Celery, skipping sync handler")
        return

    # threading/同步模式 — 用 Saga 保证事务一致性
    saga_id = saga_coordinator.create_saga(plan_id=plan_id, context={
        "plan_id": plan_id,
        "plan_name": plan_name,
        "project_id": project_id,
        "created_by": kwargs.get("created_by", "system"),
    })

    steps = create_product_plan_saga()
    result = saga_coordinator.execute(saga_id, steps, context={
        "plan_id": plan_id,
        "plan_name": plan_name,
        "project_id": project_id,
        "created_by": kwargs.get("created_by", "system"),
    })

    if result.status == "completed":
        logger.info("Saga 完成: plan=%s, project=%s, saga=%s", plan_id, project_id, saga_id)
        # 发射系统事件
        bus.emit_async(
            EventTypes.PLAN_PROJECT_CREATED,
            plan_id=plan_id,
            project_id=project_id,
            plan_name=plan_name,
        )
    else:
        logger.error("Saga 失败: plan=%s, error=%s", plan_id, result.error)

    saga_coordinator.cleanup(saga_id)


def on_plan_side_effect(**kwargs):
    """通用 ProductPlan 副作用处理器

    每个阶段推进时执行:
    1. 写入审计日志
    2. 通知PM
    """
    db: Session = SessionLocal()
    try:
        plan_id = kwargs.get("plan_id", "")
        plan_name = kwargs.get("plan_name", "")
        new_stage = kwargs.get("new_stage", "")
        username = kwargs.get("username", "system")

        from app.models.audit import AuditLog
        from app.models.alert import Notification

        # 审计日志
        audit = AuditLog(
            action=f"plan.advance:{new_stage}",
            target_type="product_plan",
            target_id=plan_id,
            operator=username,
            detail=f"产品策划「{plan_name}」推进到阶段: {new_stage}",
        )
        db.add(audit)

        # 通知PM
        notif = Notification(
            target_user=username,
            channel="system",
            title=f"🔄 策划阶段更新: {plan_name}",
            content=f"产品策划「{plan_name}」已推进到「{new_stage}」阶段",
        )
        db.add(notif)
        db.commit()

        logger.info("plan side_effect 完成: plan_id=%s, stage=%s", plan_id, new_stage)

    except Exception as e:
        db.rollback()
        logger.error("on_plan_side_effect 处理失败: %s", e)
    finally:
        db.close()
