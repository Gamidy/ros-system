"""项目复盘 — Lessons Learned"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Boolean
from app.core.database import Base


class ProjectReview(Base):
    """项目复盘记录"""
    __tablename__ = "project_reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,  # project_id)
    # 复盘类型
    review_type = Column(String(20), default="final", comment="final: 结项复盘 / phase: 阶段复盘 / milestone: 里程碑复盘")
    phase_name = Column(String(100), nullable=True, comment="阶段名称(阶段复盘时填写)")
    # 复盘内容
    what_went_well = Column(Text, nullable=True, comment="做得好(亮点)")
    what_could_improve = Column(Text, nullable=True, comment="待改进(不足)")
    key_lessons = Column(Text, nullable=True, comment="关键经验教训")
    action_items = Column(Text, nullable=True, comment="改进措施JSON")
    # 评分
    overall_rating = Column(Integer, nullable=True, comment="总体评分 1-5")
    # 元信息
    reviewer = Column(String(50), nullable=True, comment="复盘人")
    review_date = Column(Date, nullable=True, comment="复盘日期")
    is_shared = Column(Boolean, default=True, comment="是否共享到知识库")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)
