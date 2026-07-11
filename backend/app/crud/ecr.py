"""Phase 2 — ECR CRUD: 工程变更申请数据访问层（集成状态机 + 竞态安全编号）"""

import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ecr_eco import ECRRequest
from app.core.enums import ECRStatus
from app.services.state_machine import assert_transition, TransitionError

logger = logging.getLogger(__name__)


class ECRCrud:
    """ECR 数据访问"""

    def __init__(self):
        self.model = ECRRequest

    async def _gen_code(self, db: AsyncSession) -> str:
        """生成 ECR 编号: ECR-YYYYMMDD-HHMMSS-XXXX（随机后缀，消除竞态）"""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y%m%d-%H%M%S")
        suffix = secrets.token_hex(3)[:4].upper()
        return f"ECR-{ts}-{suffix}"

    async def create(self, db: AsyncSession, *, data: dict, submitter_id: int,
                     submitter_name: str = None) -> ECRRequest:
        """创建 ECR"""
        code = await self._gen_code(db)
        ecr = self.model(
            code=code,
            title=data["title"],
            ecr_type=data.get("ecr_type", "other"),
            reason=data["reason"],
            urgency=data.get("urgency", "medium"),
            affected_products=data.get("affected_products"),
            affected_documents=data.get("affected_documents"),
            description=data.get("description"),
            status=ECRStatus.DRAFT.value,
            submitter_id=submitter_id,
            submitter_name=submitter_name,
        )
        db.add(ecr)
        await db.flush()
        await db.refresh(ecr)
        logger.info("ECR 创建: %s (%s)", ecr.code, ecr.title)
        return ecr

    async def get(self, db: AsyncSession, ecr_id: int) -> Optional[ECRRequest]:
        """获取单个 ECR（含附件）"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.attachments))
            .where(self.model.id == ecr_id)
        )
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 20,
                   status: str = None, ecr_type: str = None) -> List[ECRRequest]:
        """分页列出 ECR"""
        stmt = select(self.model).order_by(self.model.created_at.desc())
        if status:
            stmt = stmt.where(self.model.status == status)
        if ecr_type:
            stmt = stmt.where(self.model.ecr_type == ecr_type)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, *, status: str = None,
                    ecr_type: str = None) -> int:
        """统计 ECR 数量"""
        stmt = select(func.count(self.model.id))
        if status:
            stmt = stmt.where(self.model.status == status)
        if ecr_type:
            stmt = stmt.where(self.model.ecr_type == ecr_type)
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def update(self, db: AsyncSession, ecr: ECRRequest, data: dict) -> ECRRequest:
        """更新 ECR（仅 draft 状态可编辑）"""
        if ecr.status != ECRStatus.DRAFT.value:
            raise ValueError(f"只有 draft 状态的 ECR 可以编辑，当前状态: {ecr.status}")

        allowed_fields = {
            "title", "ecr_type", "reason", "urgency",
            "affected_products", "affected_documents", "description"
        }
        for key, value in data.items():
            if key in allowed_fields and value is not None:
                setattr(ecr, key, value)
        await db.flush()
        await db.refresh(ecr)
        return ecr

    async def submit(self, db: AsyncSession, ecr: ECRRequest) -> ECRRequest:
        """提交 ECR: DRAFT → SUBMITTED（通过状态机校验）"""
        assert_transition("ECR", ecr.status, ECRStatus.SUBMITTED.value)
        ecr.status = ECRStatus.SUBMITTED.value
        await db.flush()
        await db.refresh(ecr)
        logger.info("ECR 已提交: %s", ecr.code)
        return ecr

    async def review(self, db: AsyncSession, ecr: ECRRequest, action: str,
                     reviewer_id: int, rejection_reason: str = None) -> ECRRequest:
        """审批 ECR: submitted → approved / submitted → rejected（通过状态机校验）"""
        target_status = (
            ECRStatus.APPROVED.value if action == "approve"
            else ECRStatus.REJECTED.value if action == "reject"
            else None
        )
        if target_status is None:
            raise ValueError(f"无效的审批操作: {action}")

        assert_transition("ECR", ecr.status, target_status)

        ecr.reviewer_id = reviewer_id
        ecr.reviewed_at = datetime.now(timezone.utc)
        ecr.status = target_status
        if action == "approve":
            ecr.rejection_reason = None
            logger.info("ECR 已通过: %s", ecr.code)
        else:
            ecr.rejection_reason = rejection_reason or "未提供驳回原因"
            logger.info("ECR 已驳回: %s, 原因: %s", ecr.code, ecr.rejection_reason)

        await db.flush()
        await db.refresh(ecr)
        return ecr


ecr_crud = ECRCrud()
