"""项目/WBS/任务/Gate CRUD"""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.project import Project, WBSNode, Task, Gate, PhaseEnum


class CRUDProject(CRUDBase[Project]):
    def __init__(self):
        super().__init__(Project)


class CRUDWBS(CRUDBase[WBSNode]):
    def __init__(self):
        super().__init__(WBSNode)

    async def get_tree(self, db: AsyncSession, *, project_id: int) -> List[WBSNode]:
        result = await db.execute(
            select(WBSNode)
            .where(WBSNode.project_id == project_id, WBSNode.parent_id.is_(None))
            .options(selectinload(WBSNode.children), selectinload(WBSNode.tasks))
            .order_by(WBSNode.sequence)
        )
        return list(result.scalars().all())


class CRUDTask(CRUDBase[Task]):
    def __init__(self):
        super().__init__(Task)

    async def get_by_wbs(self, db: AsyncSession, *, wbs_id: int) -> List[Task]:
        result = await db.execute(
            select(Task).where(Task.wbs_id == wbs_id).order_by(Task.priority)
        )
        return list(result.scalars().all())


class CRUDGate(CRUDBase[Gate]):
    def __init__(self):
        super().__init__(Gate)

    async def get_by_project(self, db: AsyncSession, *, project_id: int) -> List[Gate]:
        result = await db.execute(
            select(Gate).where(Gate.project_id == project_id).order_by(Gate.id.desc())
        )
        return list(result.scalars().all())


# State machine for IPD phases
PHASE_TRANSITIONS = {
    PhaseEnum.NPR: [PhaseEnum.CONCEPT],
    PhaseEnum.CONCEPT: [PhaseEnum.PLAN, PhaseEnum.NPR],
    PhaseEnum.PLAN: [PhaseEnum.DEVELOPMENT, PhaseEnum.CONCEPT],
    PhaseEnum.DEVELOPMENT: [PhaseEnum.VALIDATION, PhaseEnum.PLAN],
    PhaseEnum.VALIDATION: [PhaseEnum.RELEASE, PhaseEnum.DEVELOPMENT],
    PhaseEnum.RELEASE: [PhaseEnum.LIFECYCLE, PhaseEnum.VALIDATION],
    PhaseEnum.LIFECYCLE: [],
}


def can_transition(current: str, target: str) -> bool:
    return target in PHASE_TRANSITIONS.get(PhaseEnum(current), [])


project_crud = CRUDProject()
wbs_crud = CRUDWBS()
task_crud = CRUDTask()
gate_crud = CRUDGate()
