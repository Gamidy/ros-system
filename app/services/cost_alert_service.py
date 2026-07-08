"""成本超标预警引擎 — 服务层

check_cost_alerts(): 遍历规则 → 对比预算vs实际 → 超标时写入 alert_events 表
"""
from datetime import datetime
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.cost_alert_rule import CostAlertRule, AlertEvent
from app.models.cost_accounting import CostAccountingSheet, SheetStatus
from app.models.product_plan import ProductPlan


def check_cost_alerts(db: Session) -> List[AlertEvent]:
    """遍历所有启用的成本超标预警规则，检查核算单是否超标。

    超标判断逻辑:
      1. 获取所有 FINALIZED 状态的核算单
      2. 对每条规则，找到符合条件的核算单（按 project_type 过滤）
      3. 对比 variance_pct >= threshold_pct 或 variance_amount >= threshold_amount
      4. 超标则创建 AlertEvent（不重复写入同一 sheet+rule）

    返回: 本次新创建的 AlertEvent 列表
    """
    new_events: List[AlertEvent] = []

    # 1. 获取所有启用的规则
    rules = db.query(CostAlertRule).filter(CostAlertRule.enabled == True).all()
    if not rules:
        return new_events

    # 2. 获取所有已终稿的核算单（含关联的 ProductPlan 名称）
    sheets = (
        db.query(CostAccountingSheet)
        .options(joinedload(CostAccountingSheet.product_plan))
        .filter(CostAccountingSheet.status == SheetStatus.FINALIZED)
        .all()
    )
    if not sheets:
        return new_events

    # 3. 逐规则检查
    for rule in rules:
        # 按 project_type 过滤核算单
        for sheet in sheets:
            # 获取 plan_name（从关联对象）
            pp = sheet.product_plan
            plan_name = pp.name if pp is not None else None
            plan_product_type = pp.product_type if pp is not None else None

            # project_type 过滤：如果规则指定了类型，跳过不匹配的
            rule_type = rule.project_type
            if rule_type is not None and plan_product_type != rule_type:
                continue

            # 获取指标
            target_amount = sheet.total_cost_target or 0
            actual_amount = sheet.total_cost_actual or 0
            variance_amount = sheet.variance_amount or 0
            variance_pct = sheet.variance_pct or 0

            # 判断是否超标
            is_over_pct = rule.threshold_pct > 0 and variance_pct >= rule.threshold_pct
            is_over_amount = rule.threshold_amount > 0 and variance_amount >= rule.threshold_amount

            if not (is_over_pct or is_over_amount):
                continue

            # 检查是否已存在同 sheet+rule 的事件（避免重复写入）
            existing = (
                db.query(AlertEvent)
                .filter(
                    AlertEvent.rule_id == rule.id,
                    AlertEvent.sheet_id == sheet.id,
                )
                .first()
            )
            if existing is not None:
                continue

            # 确定预警等级
            critical_pct = rule.threshold_pct > 0 and variance_pct >= rule.threshold_pct * 1.5
            critical_amount = rule.threshold_amount > 0 and variance_amount >= rule.threshold_amount * 1.5
            alert_level = "critical" if (critical_pct or critical_amount) else "warning"

            # 构造消息
            msg_plan = plan_name or sheet.sheet_no
            message = (
                f"成本超标预警：{msg_plan} "
                f"目标{target_amount:.2f}元，实际{actual_amount:.2f}元，"
                f"差异{variance_amount:+.2f}元（{variance_pct:+.2f}%）"
            )

            event = AlertEvent(
                rule_id=rule.id,
                rule_name=rule.name,
                sheet_id=sheet.id,
                product_plan_id=sheet.product_plan_id,
                plan_name=plan_name,
                target_amount=target_amount,
                actual_amount=actual_amount,
                variance_amount=variance_amount,
                variance_pct=variance_pct,
                threshold_pct=rule.threshold_pct,
                threshold_amount=rule.threshold_amount,
                alert_level=alert_level,
                message=message,
                org_id=rule.org_id if rule.org_id else sheet.org_id,
            )
            db.add(event)
            new_events.append(event)

    if new_events:
        db.commit()

    return new_events
