"""知识库模型 — 立项书下拉选项 + 富文本内容 + 全文搜索"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.database import Base


class KnowledgeItem(Base):
    """知识库条目"""
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True, comment="分类")
    code = Column(String(50), nullable=False, comment="编码")
    name = Column(String(200), nullable=False, comment="显示名称")
    content = Column(Text, nullable=True, comment="富文本内容(HTML/Markdown)")
    content_type = Column(String(10), default="text", comment="内容类型: text/html/markdown")
    tags = Column(String(500), nullable=True, comment="标签(逗号分隔)")
    version = Column(Integer, default=1, comment="版本号")
    status = Column(String(20), default="active", comment="状态: active/archived/draft")
    created_by = Column(String(50), nullable=True, comment="创建人")
    updated_by = Column(String(50), nullable=True, comment="更新人")
    sort_order = Column(Integer, default=0, comment="排序")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
