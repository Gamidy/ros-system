"""团队角色模板 — 按项目类型预设团队角色与人数"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class TeamRoleTemplate(Base):
    """团队角色模板表 — 按 project_type 预设角色清单"""

    __tablename__ = "team_role_templates"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    project_type = Column(
        String(30),
        nullable=False,
        index=True,
        comment="项目类型: 全新开发/改型/引用",
    )
    role_name = Column(String(50), nullable=False, comment="角色名称")
    headcount = Column(Integer, default=1, comment="默认人数")
    responsibility_default = Column(Text, nullable=True, comment="默认职责描述")
    seq = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
