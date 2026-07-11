"""Phase 2 — ECO CRUD: 工程变更指令数据访问层（集成状态机 + 竞态安全编号）"""

import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ecr_eco import ECO, ECOItem, ECRRequest
from app.core.enums import ECOStatus, ECRStatus
from app.services.state_machine import assert_transition, TransitionError

logger = logging.getLogger(__name__)


class ECOCrud:
    """ECO 数据访问"""

    def __init__(self):
        self.model = ECO

    async def _gen_code(self, db: AsyncSession) -> str:
        """生成 ECO 编号: ECO-YYYYMMDD-HHMMSS-XXXX（随机后缀，消除竞态）"""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d-%H%M%S")
        suffix = secrets.token_hex(3)[:4].upper()
        return f"ECO-{ts}-{suffix}"

    async def create(self, db: AsyncSession, *, data: dict, created_by: int,
                     ecr: ECRRequest = None) -> ECO:
        """创建 ECO"""
        code = await self._gen_code(db)
        eco = self.model(
            code=code,
            ecr_id=ecr.id if ecr else data.get("ecr_id"),
            title=data["title"],
            change_summary=data["change_summary"],
            implementation_plan=data.get("implementation_plan"),
            effective_date=data.get("effective_date"),
            status=ECOStatus.DRAFT.value,
            created_by=created_by,
        )

        # 创建明细项
        items_data = data.get("items") or []
        for item_data in items_data:
            eco_item = ECOItem(
                seq=item_data.get("seq", 0),
                change_type=item_data["change_type"],
                object_type=item_data["object_type"],
                object_id=item_data.get("object_id"),
                object_code=item_data.get("object_code"),
                object_name=item_data.get("object_name"),
                old_value=item_data.get("old_value"),
                new_value=item_data.get("new_value"),
                description=item_data.get("description"),
            )
            eco.items.append(eco_item)

        db.add(eco)

        # 如果关联 ECR，标记为 CONVERTED
        if ecr and ecr.status == ECRStatus.APPROVED.value:
            ecr.status = ECRStatus.CONVERTED.value
            db.add(ecr)

        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 创建: %s (%s)", eco.code, eco.title)
        return eco

    async def get(self, db: AsyncSession, eco_id: int) -> Optional[ECO]:
        """获取单个 ECO（含明细项）"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.items))
            .where(self.model.id == eco_id)
        )
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 20,
                   status: str = None) -> List[ECO]:
        """分页列出 ECO"""
        stmt = select(self.model).order_by(self.model.created_at.desc())
        if status:
            stmt = stmt.where(self.model.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, *, status: str = None) -> int:
        """统计 ECO 数量"""
        stmt = select(func.count(self.model.id))
        if status:
            stmt = stmt.where(self.model.status == status)
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def update(self, db: AsyncSession, eco: ECO, data: dict) -> ECO:
        """更新 ECO（仅 draft 状态）"""
        if eco.status != ECOStatus.DRAFT.value:
            raise ValueError(f"只有 draft 状态的 ECO 可以编辑，当前状态: {eco.status}")

        allowed_fields = {
            "title", "change_summary", "implementation_plan", "effective_date"
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(eco, key, value)
        await db.flush()
        await db.refresh(eco)
        return eco

    async def start_implementing(self, db: AsyncSession, eco: ECO) -> ECO:
        """开始实施: DRAFT → IMPLEMENTING（通过状态机校验）"""
        assert_transition("ECO", eco.status, ECOStatus.IMPLEMENTING.value)
        eco.status = ECOStatus.IMPLEMENTING.value
        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 开始实施: %s", eco.code)
        return eco

    async def verify(self, db: AsyncSession, eco: ECO,
                     verified_by: int) -> ECO:
        """验证: IMPLEMENTING → VERIFIED（通过状态机校验）"""
        assert_transition("ECO", eco.status, ECOStatus.VERIFIED.value)
        eco.status = ECOStatus.VERIFIED.value
        eco.verified_by = verified_by
        eco.verified_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 已验证: %s", eco.code)
        return eco

    async def make_effective(self, db: AsyncSession, eco: ECO) -> ECO:
        """生效: VERIFIED → EFFECTIVE（通过状态机校验）"""
        assert_transition("ECO", eco.status, ECOStatus.EFFECTIVE.value)
        eco.status = ECOStatus.EFFECTIVE.value
        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 已生效: %s", eco.code)
        return eco

    async def close(self, db: AsyncSession, eco: ECO,
                    closed_by: int) -> ECO:
        """关闭: EFFECTIVE → CLOSED（通过状态机校验）"""
        assert_transition("ECO", eco.status, ECOStatus.CLOSED.value)
        eco.status = ECOStatus.CLOSED.value
        eco.closed_by = closed_by
        eco.closed_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 已关闭: %s", eco.code)
        return eco

    async def cancel(self, db: AsyncSession, eco: ECO) -> ECO:
        """取消 ECO（通过状态机校验，任意非终态可取消）"""
        assert_transition("ECO", eco.status, ECOStatus.CANCELLED.value)
        eco.status = ECOStatus.CANCELLED.value
        await db.flush()
        await db.refresh(eco)
        logger.info("ECO 已取消: %s", eco.code)
        return eco


eco_crud = ECOCrud()
