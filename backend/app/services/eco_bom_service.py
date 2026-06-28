"""
ECO BOM 联动服务 — BOM更新/重试/回滚
Board 裁决: EFFECTIVE → BOM Update → Retry(3次) → ROLLBACK_REQUIRED
"""
import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import ECOStatus
from app.models.ecr_eco import ECO

logger = logging.getLogger(__name__)


def apply_bom_update(eco_id: int) -> bool:
    """
    执行 BOM 更新操作（由 ECO EFFECTIVE 触发）

    当前实现: 模拟BOM更新，生产环境对接实际BOM服务。
    返回 True=成功, False=失败。

    Saga 步骤:
    1. Update BOM (当前实现)
    2. Update Prototype (预留)
    3. Update Certification Impact (预留)
    4. Emit Event (预留)
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        eco = db.query(ECO).filter(ECO.id == eco_id).first()
        if not eco:
            logger.error("apply_bom_update: ECO %s 不存在", eco_id)
            return False

        # ── BOM 更新主逻辑（生产环境替换为实际BOM Patch）──
        logger.info("正在执行 ECO %s (%s) 的 BOM 更新...", eco_id, eco.code)

        # TODO: 实际 BOM Patch 调用
        # from app.services.bom_service import apply_eco_bom_changes
        # apply_eco_bom_changes(eco_id, eco.items)

        logger.info("ECO %s BOM 更新成功 (模拟)", eco_id)
        return True

    except Exception as e:
        logger.error("apply_bom_update: ECO %s 失败: %s", eco_id, str(e))
        return False
    finally:
        if db:
            db.close()


def rollback_bom_update(eco_id: int) -> bool:
    """
    Saga 补偿: 回滚 BOM 更新
    当 BOM 更新失败且重试耗尽时调用。
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        eco = db.query(ECO).filter(ECO.id == eco_id).first()
        if not eco:
            return False

        logger.warning("Saga 补偿: 回滚 ECO %s (%s) 的 BOM 变更", eco_id, eco.code)

        # TODO: 实际 BOM Rollback 调用
        # from app.services.bom_service import rollback_eco_bom_changes
        # rollback_eco_bom_changes(eco_id)

        logger.info("ECO %s BOM 回滚完成 (模拟)", eco_id)
        return True

    except Exception as e:
        logger.error("rollback_bom_update: ECO %s 回滚失败: %s", eco_id, str(e))
        return False
    finally:
        if db:
            db.close()
