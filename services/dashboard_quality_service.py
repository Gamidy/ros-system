"""质量角色相关查询逻辑 — 认证进度摘要"""
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.certification import CertificationProject


def get_quality_cert_summary(db: Session) -> Optional[dict]:
    """获取质量角色认证进度摘要

    Args:
        db: 数据库会话

    Returns:
        dict: 包含 total_projects 和 status_distribution
    """
    total_cert_projects = db.query(func.count(CertificationProject.id)).scalar() or 0
    cert_status_rows = (
        db.query(CertificationProject.status, func.count(CertificationProject.id))
        .group_by(CertificationProject.status)
        .all()
    )
    return {
        "total_projects": total_cert_projects,
        "status_distribution": {row[0] or "unknown": row[1] for row in cert_status_rows},
    }
