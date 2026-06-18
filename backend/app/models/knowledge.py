"""知识库模型 — 立项书下拉选项"""
from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True, comment="分类")
    code = Column(String(50), nullable=False, comment="编码")
    name = Column(String(100), nullable=False, comment="显示名称")
    sort_order = Column(Integer, default=0, comment="排序")
    remark = Column(Text, nullable=True, comment="备注")
