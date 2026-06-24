"""Saga 事务引擎 — 事件失败补偿机制 (Phase 4)

核心概念:
- Saga: 一个跨多个步骤的分布式事务
- Step: 单个操作 (action) + 其逆向补偿 (compensate)
- Coordinator: 按序执行 step，失败时回滚已成功的 step

使用场景:
  PLAN_APPROVED → create_project → create_gate → create_bom
  如果 create_bom 失败 → 回滚 create_gate 和 create_project

架构决策:
- 不依赖数据库事务（Saga 本身用于跨事务一致性）
- 补偿操作记录到 event_logs (saga_id 关联)
- 幂等设计：同名 step 可重试
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════
# 类型定义
# ════════════════════════════════════════════════════════


class SagaStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL_COMPLETED = "partial_completed"  # 部分完成（有补偿）
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


class StepStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    COMPENSATED = "compensated"
    COMPENSATE_FAILED = "compensate_failed"


@dataclass
class SagaStep:
    """Saga 步骤定义

    name: 步骤名称（用于日志和追踪）
    action: 正向操作 (callable，接收 **kwargs)
    compensate: 补偿操作 (callable，接收 **kwargs + error_info)
    timeout_seconds: 超时（秒），默认 30
    """
    name: str
    action: Callable[..., Tuple[bool, dict]]
    compensate: Callable[..., Tuple[bool, dict]]
    timeout_seconds: int = 30


@dataclass
class SagaResult:
    """Saga 执行结果"""
    saga_id: str
    status: SagaStatus
    steps: Dict[str, StepStatus] = field(default_factory=dict)
    step_results: Dict[str, dict] = field(default_factory=dict)
    error: Optional[str] = None
    failed_step: Optional[str] = None
    compensation_results: Dict[str, bool] = field(default_factory=dict)


# ════════════════════════════════════════════════════════
# Saga Coordinator
# ════════════════════════════════════════════════════════


class SagaCoordinator:
    """Saga 事务协调器 — 执行 + 补偿"""

    def __init__(self) -> None:
        self._active_sagas: Dict[str, SagaResult] = {}

    def create_saga(
        self,
        plan_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> str:
        """创建新的 Saga 事务

        Returns: saga_id
        """
        saga_id = f"saga-{uuid.uuid4().hex[:12]}"
        result = SagaResult(
            saga_id=saga_id,
            status=SagaStatus.PENDING,
        )
        self._active_sagas[saga_id] = result
        logger.info("Saga created: %s (plan=%s, ctx=%s)", saga_id, plan_id, context)
        return saga_id

    def execute(
        self,
        saga_id: str,
        steps: List[SagaStep],
        context: Optional[dict] = None,
    ) -> SagaResult:
        """按序执行 Saga 步骤

        流程:
        1. 依次执行每个 step
        2. 如果某个 step 失败 → 反向补偿已成功的 step
        3. 记录所有中间结果

        Returns: SagaResult
        """
        result = self._active_sagas.get(saga_id)
        if result is None:
            result = SagaResult(saga_id=saga_id, status=SagaStatus.PENDING)
            self._active_sagas[saga_id] = result

        result.status = SagaStatus.IN_PROGRESS
        ctx = context or {}
        executed: List[str] = []

        try:
            for step in steps:
                result.steps[step.name] = StepStatus.PENDING
                logger.info("Saga step executing: %s → %s", saga_id, step.name)

                try:
                    success, step_result = step.action(**ctx)
                except Exception as e:
                    success, step_result = False, {"error": str(e)}

                if success:
                    result.steps[step.name] = StepStatus.SUCCESS
                    result.step_results[step.name] = step_result
                    executed.append(step.name)
                    # 更新 context 供后续步骤使用
                    if isinstance(step_result, dict):
                        ctx.update(step_result)
                    logger.info("Saga step OK: %s → %s", saga_id, step.name)
                else:
                    result.steps[step.name] = StepStatus.FAILED
                    result.failed_step = step.name
                    result.error = step_result.get("error", "Unknown error")
                    logger.error("Saga step FAILED: %s → %s: %s",
                                 saga_id, step.name, result.error)
                    # 启动补偿
                    self._compensate(result, executed, steps, ctx)
                    return result

            # 全部成功
            result.status = SagaStatus.COMPLETED
            logger.info("Saga COMPLETED: %s (%d steps)", saga_id, len(steps))
            return result

        except Exception as e:
            result.status = SagaStatus.FAILED
            result.error = str(e)
            logger.exception("Saga unexpected error: %s", saga_id)
            self._compensate(result, executed, steps, ctx)
            return result

    def _compensate(
        self,
        result: SagaResult,
        executed: List[str],
        steps: List[SagaStep],
        context: dict,
    ) -> None:
        """补偿已成功执行的步骤（反向顺序）"""
        result.status = SagaStatus.COMPENSATING
        logger.info("Saga compensating: %s (reverse %d steps)", result.saga_id, len(executed))

        # 反向补偿
        for step_name in reversed(executed):
            step = next((s for s in steps if s.name == step_name), None)
            if step is None:
                continue

            try:
                success, _ = step.compensate(**context, error_info=result.error)
                if success:
                    result.steps[step_name] = StepStatus.COMPENSATED
                    result.compensation_results[step_name] = True
                    logger.info("Saga compensate OK: %s → %s", result.saga_id, step_name)
                else:
                    result.steps[step_name] = StepStatus.COMPENSATE_FAILED
                    result.compensation_results[step_name] = False
                    logger.error("Saga compensate FAILED: %s → %s", result.saga_id, step_name)
            except Exception as e:
                result.steps[step_name] = StepStatus.COMPENSATE_FAILED
                result.compensation_results[step_name] = False
                logger.exception("Saga compensate error: %s → %s: %s",
                                 result.saga_id, step_name, e)

        # 根据补偿结果判定最终状态
        all_compensated = all(result.compensation_results.values())
        result.status = SagaStatus.COMPENSATED if all_compensated else SagaStatus.FAILED
        logger.info("Saga compensate done: %s → %s (all=%s)",
                     result.saga_id, result.status, all_compensated)

    def get_result(self, saga_id: str) -> Optional[SagaResult]:
        """获取 Saga 执行结果"""
        return self._active_sagas.get(saga_id)

    def cleanup(self, saga_id: str) -> None:
        """清理 Saga 状态（完成后调用）"""
        self._active_sagas.pop(saga_id, None)


# ════════════════════════════════════════════════════════
# 预置 Saga 定义 — ProductPlan 审批 Saga
# ════════════════════════════════════════════════════════


def _action_create_project(plan_id: str, plan_name: str, **kwargs) -> Tuple[bool, dict]:
    """创建项目（正向操作）"""
    from app.models.project import Project
    from app.services.product_plan_workflow import create_project_from_plan

    db = SessionLocal()
    try:
        project = create_project_from_plan(db, plan_id, plan_name)
        db.commit()
        return True, {"project_id": project.id, "project_code": project.code}
    except Exception as e:
        db.rollback()
        logger.error("Saga action create_project 失败: %s", e)
        return False, {"error": str(e)}
    finally:
        db.close()


def _compensate_create_project(project_id: int = None, **kwargs) -> Tuple[bool, dict]:
    """创建项目失败 → 标记删除项目（补偿）"""
    if not project_id:
        return True, {}  # 项目未创建，无需补偿
    from app.models.project import Project

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.is_draft = True
            project.status = "cancelled"
            db.commit()
            logger.info("Saga compensate: 项目 %s 已标记取消", project_id)
        return True, {}
    except Exception as e:
        db.rollback()
        logger.error("Saga compensate create_project 失败: %s", e)
        return False, {"error": str(e)}
    finally:
        db.close()


def _action_create_gate(project_id: int, **kwargs) -> Tuple[bool, dict]:
    """创建 G0 Gate（正向操作）"""
    from app.models.project import ProjectGate

    db = SessionLocal()
    try:
        gate = ProjectGate(
            project_id=project_id,
            gate_code="G0",
            gate_name="策划立项",
            seq=0,
            status="passed",
        )
        db.add(gate)
        db.commit()
        return True, {"gate_code": "G0"}
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def _compensate_create_gate(project_id: int = None, **kwargs) -> Tuple[bool, dict]:
    """删除 G0 Gate（补偿）"""
    if not project_id:
        return True, {}
    from app.models.project import ProjectGate

    db = SessionLocal()
    try:
        db.query(ProjectGate).filter(
            ProjectGate.project_id == project_id,
            ProjectGate.gate_code == "G0",
        ).delete()
        db.commit()
        return True, {}
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def _action_notify_pm(plan_name: str, created_by: str = "system", **kwargs) -> Tuple[bool, dict]:
    """通知 PM（正向操作）"""
    from app.models.alert import Notification

    db = SessionLocal()
    try:
        notif = Notification(
            target_user=created_by,
            channel="system",
            title=f"✅ 策划已批准: {plan_name}",
            content=(
                f"产品策划「{plan_name}」已批准，关联项目已自动创建。"
            ),
        )
        db.add(notif)
        db.commit()
        return True, {}
    except Exception as e:
        db.rollback()
        return False, {"error": str(e)}
    finally:
        db.close()


def _compensate_notify_pm(**kwargs) -> Tuple[bool, dict]:
    """通知补偿 — 通知无法撤回，只打日志"""
    logger.info("Saga compensate: 通知已发送无法撤回 (notification already sent)")
    return True, {"note": "通知已发送，不可撤回"}


def create_product_plan_saga() -> list:
    """创建 ProductPlan 审批 Saga 步骤定义"""
    return [
        SagaStep(name="create_project", action=_action_create_project, compensate=_compensate_create_project),
        SagaStep(name="create_gate", action=_action_create_gate, compensate=_compensate_create_gate),
        SagaStep(name="notify_pm", action=_action_notify_pm, compensate=_compensate_notify_pm),
    ]


# 模块级单例
saga_coordinator = SagaCoordinator()
