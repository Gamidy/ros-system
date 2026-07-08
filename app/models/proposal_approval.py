"""项目立项审批模型 — ProposalApproval 表

审批流程:
  产品经理提交草稿 → 并行审批(4人) → 研发总监终审 → 项目自动创建
  任意环节驳回则整个审批结束，通知产品经理修改
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, func
from app.core.database import Base


class ProposalApproval(Base):
    __tablename__ = "proposal_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, nullable=False, index=True, comment="关联projects表ID(草稿)")
    proposer_id = Column(Integer, nullable=False, comment="提交人user_id")
    title = Column(String(200), nullable=False, comment="项目名称")
    status = Column(
        String(30),
        default="pending_parallel",
        comment="pending_parallel/pending_director/approved/rejected",
    )
    # 并行审批人JSON:
    # [{"user_id":1,"username":"xxx","role":"结构模块经理","status":"pending/approved/rejected","reason":"","reviewed_at":null}, ...]
    parallel_reviewers = Column(JSON, nullable=True)
    # 研发总监
    director_reviewer_id = Column(Integer, nullable=True, comment="研发总监 user_id")
    director_status = Column(String(20), default="pending", comment="pending/approved/rejected")
    director_reason = Column(Text, nullable=True, comment="研发总监审批意见")
    director_reviewed_at = Column(DateTime, nullable=True)
    # 对比快照 JSON — 提交时的完整立项数据
    snapshot = Column(JSON, nullable=True, comment="提交时的立项数据快照")
    # 上一次被驳回前的快照 (用于修改对比视图)
    previous_snapshot = Column(JSON, nullable=True, comment="上一次驳回前的立项快照(修改对比用)")
    # 重新提交次数
    resubmit_count = Column(Integer, default=0, comment="驳回后重新提交次数")
    # 催办标记
    reminded = Column(Boolean, default=False, comment="是否已发24h催办通知")
    escalated = Column(Boolean, default=False, comment="是否已升级通知(>48h)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
