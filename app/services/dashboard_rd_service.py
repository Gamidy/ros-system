"""RD角色相关查询逻辑 — BOM状态摘要"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.bom import Part, BOM


def get_rd_bom_summary(db: Session) -> Optional[dict]:
    """获取RD角色BOM状态摘要: 物料总数、BOM总数、物料类型分布

    Args:
        db: 数据库会话

    Returns:
        dict: 包含 total_parts, total_boms, part_type_distribution
    """
    total_parts = db.query(func.count(Part.id)).scalar() or 0
    total_boms = db.query(func.count(BOM.id)).scalar() or 0
    part_type_rows = (
        db.query(Part.part_type, func.count(Part.id))
        .filter(Part.part_type.isnot(None))
        .group_by(Part.part_type)
        .all()
    )
    return {
        "total_parts": total_parts,
        "total_boms": total_boms,
        "part_type_distribution": {row[0]: row[1] for row in part_type_rows},
    }
