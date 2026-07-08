"""物料与部件清单模板 — 按目标市场预设物料/部件"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class MaterialComponentTemplate(Base):
    """物料部件模板表 — 按市场预设物料和部件清单"""

    __tablename__ = "material_component_templates"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    market = Column(String(50), nullable=False, index=True, comment="目标市场")
    type = Column(
        String(20),
        nullable=False,
        comment="类型: 物料/部件",
    )
    name = Column(String(100), nullable=False, comment="名称")
    spec = Column(String(200), nullable=True, comment="规格/型号")
    unit = Column(String(20), nullable=True, comment="单位")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
