"""项目角色→系统岗位映射 — 一个项目角色可映射多个系统岗位"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class RolePositionMapping(Base):
    """角色岗位映射表 — 项目角色名 → 系统岗位名"""

    __tablename__ = "role_position_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    project_role = Column(
        String(50),
        nullable=False,
        index=True,
        comment="项目角色名, 如'结构工程师'",
    )
    system_role = Column(
        String(100),
        nullable=False,
        comment="系统岗位名, 如'主任结构工程师'",
    )
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
