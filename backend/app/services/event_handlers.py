"""事件处理器 — 注册系统内各类事件的处理逻辑

每个 handler 使用独立 DB session，独立 try/except，
失败只打 log 不抛异常，保证不影响主流程。

在 main.py 启动时调用 register_all_handlers() 注册。
"""
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.project import ProjectGate
from app.models.test import TestRequest, QualityIssue
from app.models.alert import Alert, Notification
from .events import bus, EventTypes, store_event

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Handler: 立项审批通过
# ─────────────────────────────────────────────────────────


def on_proposal_approved(project_id: int, project_name: str, **kwargs):
    """立项审批通过后处理

    1. 更新项目状态（核准 → planning）
    2. 生成项目编号（如空）
    3. 通知团队成员
    4. 创建默认 M1~M9 Gate 计划
    5. 创建占位 TestRequest
    """
    db: Session = SessionLocal()
    try:
        from app.models.project import Project
        from app.models.user import User

        project_code = kwargs.get("project_code", "")
        proposer_id = kwargs.get("proposer_id")
        team_members = kwargs.get("team_members", "")

        # ── 1. 更新项目状态 ──
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            if not project.code and not project_code:
                import random
                project.code = f"P-{datetime.now().strftime('%y%m%d')}-{random.randint(1000,9999)}"
            project.is_draft = False
            project.status = "planning"
            project.approval_status = "approved"
            db.flush()

        # ── 2. 通知团队成员 ──
        if proposer_id:
            proposer = db.query(User).filter(User.id == proposer_id).first()
            if proposer:
                from app.models.alert import Notification
                notification = Notification(
                    target_user=proposer.username,
                    channel="system",
                    title=f"立项审批通过: {project_name}",
                    content=(
                        f"您的项目「{project_name}」({project_code or project.code}) "
                        f"审批已通过，项目已自动创建。"
                    ),
                )
                db.add(notification)

        # ── 3. M1~M9 默认 Gate ──
        base_date = datetime.now().date() + timedelta(days=30)
        default_gates = [
            ("M1", "项目启动", 1), ("M2", "需求确认", 2),
            ("M3", "方案设计评审", 3), ("M4", "详细设计评审", 4),
            ("M5", "样机评审", 5), ("M6", "试产评审", 6),
            ("M7", "认证评审", 7), ("M8", "试产验证", 8),
            ("M9", "量产放行", 9),
        ]
        for code, name, seq in default_gates:
            gate = ProjectGate(
                project_id=project_id,
                gate_code=code, gate_name=name, seq=seq,
                planned_date=base_date + timedelta(days=(seq - 1) * 14),
                status="pending",
            )
            db.add(gate)

        # ── 4. 占位 TestRequest ──
        now_str = datetime.now().strftime("%Y%m%d%H%M%S")
        test_req = TestRequest(
            request_no=f"TR-AUTO-{project_id}-{now_str}",
            title=f"{project_name} — 常规测试申请（自动创建）",
            project_code=project_code or (project.code if project else ""),
            test_type="常规", trigger_mode="auto",
            requester="system", status="draft",
        )
        db.add(test_req)

        db.commit()
        logger.info(
            "on_proposal_approved 完成: project_id=%s, status=planning, "
            "gates=9, draft_test=1, notified=%s",
            project_id, proposer_id,
        )

    except Exception as e:
        db.rollback()
        logger.error("on_proposal_approved 处理失败: %s", e)
    finally:
        db.close()


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
    # ── 已有事件 ──
    for evt in [
        "proposal.approved",
        "test.done_with_ng",
        "alert.overdue_found",
    ]:
        bus.on(evt, store_event)

    bus.on("proposal.approved", on_proposal_approved)
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

    logger.info(
        "事件系统初始化完成: %d 事件类型, Event Store 已激活",
        len(bus.handlers),
    )


register_all_handlers = _register_all_events


# ════════════════════════════════════════════════════════
# ProductPlan 事件处理器
# ════════════════════════════════════════════════════════


def on_plan_approved(plan_id: str, plan_name: str, project_id: int, **kwargs):
    """ProductPlan 批准事件处理器

    1. 在 project_gates 表中创建 G0 Gate 记录
    2. 通知PM：「项目已自动创建」
    3. emit PLAN_PROJECT_CREATED 系统事件
    """
    db: Session = SessionLocal()
    try:
        # ── 1. 创建 G0 Gate 记录 ──
        gate = ProjectGate(
            project_id=project_id,
            gate_code="G0",
            gate_name="策划立项",
            seq=0,
            status="passed",  # 策划批准即 G0 通过
            passed_at=datetime.now(),
        )
        db.add(gate)

        # ── 2. 通知 PM ──
        from app.models.alert import Notification
        notif = Notification(
            target_user=kwargs.get("created_by", "system"),
            channel="system",
            title=f"✅ 策划已批准: {plan_name}",
            content=(
                f"产品策划「{plan_name}」已批准，"
                f"关联项目(ID={project_id})已自动创建，"
                f"请进入项目管理推进后续 Gate 评审。"
            ),
        )
        db.add(notif)
        db.commit()

        logger.info(
            "on_plan_approved 完成: plan_id=%s, project_id=%s, G0 created",
            plan_id, project_id,
        )

        # ── 3. 发射系统事件：Project 已创建 ──
        bus.emit(
            EventTypes.PLAN_PROJECT_CREATED,
            plan_id=plan_id,
            project_id=project_id,
            plan_name=plan_name,
        )

    except Exception as e:
        db.rollback()
        logger.error("on_plan_approved 处理失败: %s", e)
    finally:
        db.close()


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
