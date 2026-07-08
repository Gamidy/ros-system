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
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.database import SessionLocal
from app.services.events import bus

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
    event_type: 可选事件类型（非 None 时用于事件驱动模式），默认 None=同步
    """
    name: str
    action: Callable[..., Tuple[bool, dict]]
    compensate: Callable[..., Tuple[bool, dict]]
    timeout_seconds: int = 30
    event_type: Optional[str] = None


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
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def to_dict(self) -> dict:
        """转换为字典，自动计算 duration（秒）"""
        d = {
            "saga_id": self.saga_id,
            "status": self.status.value,
            "steps": {k: v.value for k, v in self.steps.items()},
            "error": self.error,
            "failed_step": self.failed_step,
            "compensation_results": self.compensation_results,
            "step_results": self.step_results,
        }
        if self.start_time is not None:
            d["start_time"] = datetime.fromtimestamp(self.start_time).isoformat()
            if self.end_time is not None:
                d["end_time"] = datetime.fromtimestamp(self.end_time).isoformat()
                d["duration"] = round(self.end_time - self.start_time, 4)
            else:
                d["duration"] = round(time.time() - self.start_time, 4)  # 仍在执行中
        else:
            d["duration"] = None
        return d


# ════════════════════════════════════════════════════════
# Saga Coordinator
# ════════════════════════════════════════════════════════


class SagaCoordinator:
    """Saga 事务协调器 — 执行 + 补偿

    支持双模式:
    - sync (默认): 同步逐步骤执行，失败补偿
    - event_driven: 通过 EventBus 发射事件驱动步骤执行
    """

    def __init__(self, mode: str = "sync") -> None:
        self.mode = mode
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
        """执行 Saga 步骤（根据 mode 自动选择模式）

        mode='sync' (默认): 同步逐步骤执行，失败补偿
        mode='event_driven': 通过 EventBus 事件驱动执行

        Returns: SagaResult
        """
        if self.mode == "event_driven":
            return self.event_driven_execute(saga_id, steps, context)
        return self.sync_execute(saga_id, steps, context)

    def sync_execute(
        self,
        saga_id: str,
        steps: List[SagaStep],
        context: Optional[dict] = None,
    ) -> SagaResult:
        """按序同步执行 Saga 步骤（模式1：默认）

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

        result.start_time = time.time()
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
                    logger.exception(f"unexpected: {e}")
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
                    result.end_time = time.time()
                    return result

            # 全部成功
            result.status = SagaStatus.COMPLETED
            result.end_time = time.time()
            logger.info("Saga COMPLETED: %s (%d steps)", saga_id, len(steps))
            return result

        except Exception as e:
            logger.exception(f"unexpected: {e}")
            result.status = SagaStatus.FAILED
            result.error = str(e)
            result.end_time = time.time()
            logger.exception("Saga unexpected error: %s", saga_id)
            self._compensate(result, executed, steps, ctx)
            return result

    def event_driven_execute(
        self,
        saga_id: str,
        steps: List[SagaStep],
        context: Optional[dict] = None,
    ) -> SagaResult:
        """通过 EventBus 事件驱动执行 Saga 步骤（模式2）

        流程:
        1. 每个 step 通过 EventBus 发射 event_type 事件（含 step_id + ctx）
        2. 事件处理器执行 action，完成→发射链上下一事件，失败→发射补偿事件
        3. 无 event_type 的 step 回退到同步执行

        Returns: SagaResult
        """
        from app.services.events import bus

        result = self._active_sagas.get(saga_id)
        if result is None:
            result = SagaResult(saga_id=saga_id, status=SagaStatus.PENDING)
            self._active_sagas[saga_id] = result

        result.start_time = time.time()
        result.status = SagaStatus.IN_PROGRESS
        ctx = dict(context or {})
        executed: List[str] = []

        step_map = {s.name: s for s in steps}
        registered_handlers: List[tuple] = []  # (event_type, handler)

        def _handle_step(step_name: str) -> None:
            """内部：执行单个 step 并链式触发下一步或补偿"""
            step = step_map[step_name]
            result.steps[step_name] = StepStatus.PENDING
            logger.info("Saga event step: %s → %s", saga_id, step_name)

            try:
                success, step_result = step.action(**ctx)
            except Exception as e:
                logger.exception(f"unexpected: {e}")
                success, step_result = False, {"error": str(e)}

            if success:
                result.steps[step_name] = StepStatus.SUCCESS
                result.step_results[step_name] = step_result
                executed.append(step_name)
                if isinstance(step_result, dict):
                    ctx.update(step_result)
                logger.info("Saga event step OK: %s → %s", saga_id, step_name)

                # 查找下一步骤并触发
                next_idx = next(
                    (i for i, s in enumerate(steps) if s.name == step_name), -1
                ) + 1
                if next_idx < len(steps):
                    next_step = steps[next_idx]
                    if next_step.event_type:
                        bus.emit(
                            next_step.event_type,
                            step_id=next_step.name,
                            saga_id=saga_id,
                            **ctx,
                        )
                    else:
                        # 无 event_type 的 step 同步执行
                        _handle_step(next_step.name)
                else:
                    # 所有步骤完成
                    result.status = SagaStatus.COMPLETED
                    result.end_time = time.time()
                    logger.info(
                        "Saga event COMPLETED: %s (%d steps)", saga_id, len(steps)
                    )
            else:
                result.steps[step_name] = StepStatus.FAILED
                result.failed_step = step_name
                result.error = step_result.get("error", "Unknown error")
                logger.error(
                    "Saga event step FAILED: %s → %s: %s",
                    saga_id, step_name, result.error,
                )
                # 启动补偿
                self._compensate(result, executed, steps, ctx)
                result.end_time = time.time()

        def _make_handler(step_name: str):
            """工厂：为每个 step 创建闭包处理器"""
            def _handler(step_id: str = None, _saga_id: str = None, **kw) -> None:
                # 验证 saga_id 匹配（防止串扰）
                if _saga_id is not None and _saga_id != saga_id:
                    return
                _handle_step(step_name)
            return _handler

        # 注册临时事件处理器
        for step in steps:
            if step.event_type:
                handler = _make_handler(step.name)
                registered_handlers.append((step.event_type, handler))
                bus.on(step.event_type, handler)

        try:
            # 触发第一个步骤
            first_step = steps[0]
            if first_step.event_type:
                bus.emit(
                    first_step.event_type,
                    step_id=first_step.name,
                    saga_id=saga_id,
                    **ctx,
                )
            else:
                _handle_step(first_step.name)
        except Exception as e:
            logger.exception(f"unexpected: {e}")
            result.status = SagaStatus.FAILED
            result.error = str(e)
            result.end_time = time.time()
            logger.exception("Saga event unexpected error: %s", saga_id)
            self._compensate(result, executed, steps, ctx)
        finally:
            # 清理临时事件处理器
            for event_type, handler in registered_handlers:
                bus.off(event_type, handler)

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
                logger.exception(f"unexpected: {e}")
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


def _action_create_project(plan_id: str, plan_name: str, project_id=None, **kwargs) -> Tuple[bool, dict]:
    """创建项目（正向操作）"""
    # ── 守卫：如果 project_id 已存在，跳过创建 ──
    if project_id is not None:
        logger.info("Saga: 项目已存在, 跳过创建: project_id=%s", project_id)
        return True, {"project_id": project_id, "skipped": True}

    from app.models.project import Project
    from app.models.product_plan import ProductPlan
    from datetime import datetime
    import random

    db = SessionLocal()
    try:
        # 生成项目编号
        code = f"PLAN-{datetime.now().strftime('%y%m%d')}-{random.randint(100,999)}"

        # 读取 ProductPlan 信息
        plan = db.query(ProductPlan).filter(ProductPlan.id == plan_id).first()
        plan_name_clean = plan_name or (plan.name if plan else "未命名策划")

        project = Project(
            code=code,
            name=plan_name_clean,
            project_class="B",  # 默认 B 级
            status="planning",
            is_draft=False,
        )
        db.add(project)
        db.flush()
        project_id = project.id

        # 关联 plan 到 project
        from app.models.product_plan import ProductPlanProjectLink
        if plan:
            link = ProductPlanProjectLink(product_plan_id=plan.id, project_id=project_id, link_type='primary')
            db.add(link)
        db.commit()
        logger.info("Saga: 项目已创建: id=%s, code=%s, name=%s", project_id, code, plan_name_clean)
        return True, {"project_id": project_id, "project_code": code}
    except Exception as e:
        logger.exception(f"unexpected: {e}")
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
        logger.exception(f"unexpected: {e}")
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
        logger.exception(f"unexpected: {e}")
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
        logger.exception(f"unexpected: {e}")
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
        logger.exception(f"unexpected: {e}")
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
        SagaStep(name="create_project", action=_action_create_project, compensate=_compensate_create_project, event_type="saga.create_project"),
        SagaStep(name="create_gate", action=_action_create_gate, compensate=_compensate_create_gate, event_type="saga.create_gate"),
        SagaStep(name="notify_pm", action=_action_notify_pm, compensate=_compensate_notify_pm, event_type="saga.notify_pm"),
    ]


# 模块级单例
saga_coordinator = SagaCoordinator()
