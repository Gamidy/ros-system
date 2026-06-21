"""项目立项审批模型 — ProposalApproval 表

审批流程:
  产品经理提交草稿 → 并行审批(4人) → 研发总监终审 → 项目自动创建
  任意环节驳回则整个审批结束，通知产品经理修改

并行审批人独立表 proposal_parallel_reviewers:
  替代旧的 JSON 列 parallel_reviewers，解决并发读写竞态条件。
  旧 JSON 列保留（仅做兼容读取，不做写入）。
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
        comment="pending_parallel/pending_director/approved/rejected/withdrawn",
    )
    # 并行审批人JSON (deprecated — 仅做旧数据兼容读取，新数据写入 proposal_parallel_reviewers 表)
    # 新代码读取并行审批人统一走 ProposalParallelReviewer 表
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


class ProposalParallelReviewer(Base):
    """并行审批人独立表 — 替代 JSON 列存储

    每行对应一个并行审批人对某条审批记录的审批状态。
    使用 UPDATE ... WHERE status='pending' 原子更新避免竞态条件。
    """
    __tablename__ = "proposal_parallel_reviewers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    approval_id = Column(Integer, nullable=False, index=True, comment="关联 proposal_approvals.id")
    user_id = Column(Integer, nullable=False, comment="审批人 user_id")
    username = Column(String(100), nullable=True, comment="审批人用户名")
    role = Column(String(50), nullable=True, comment="审批角色（中文）")
    status = Column(String(20), nullable=False, default="pending", comment="pending/approved/rejected")
    reason = Column(Text, nullable=True, comment="审批意见")
    reviewed_at = Column(DateTime, nullable=True, comment="审批时间")
