"""
存量审批数据迁移脚本 P3 — 将旧 ProposalApproval 记录迁移到 ApprovalRequest

策略：
  - 只迁移已终态（approved/rejected/withdrawn）的记录
  - 审批中（pending_parallel/pending_director）的保持旧表驱动，不迁移
  - DRY RUN 模式预览变更，不加 --apply 参数只读不写
  - 支持断点续传（按ID分批）

用法：
  python3 -m app.migrate_proposal_approvals          # DRY RUN
  python3 -m app.migrate_proposal_approvals --apply   # 实际执行
  python3 -m app.migrate_proposal_approvals --apply --batch 100  # 每批100条
"""
import sys
import argparse
from datetime import datetime

from app.core.database import SessionLocal
from app.models.proposal_approval import (
    ProposalApproval, ProposalParallelReviewer,
    ProposalStatus, ReviewStatus,
)
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord


_TERMINAL_STATUSES = {
    ProposalStatus.APPROVED,
    ProposalStatus.REJECTED,
    ProposalStatus.WITHDRAWN,
}

_STATUS_MAP = {
    ProposalStatus.PENDING_PARALLEL: "pending",
    ProposalStatus.PENDING_DIRECTOR: "pending",
    ProposalStatus.APPROVED: "approved",
    ProposalStatus.REJECTED: "rejected",
    ProposalStatus.WITHDRAWN: "withdrawn",
}


def migrate_batch(db, batch_size=50, dry_run=True):
    """迁移一批已终态的 ProposalApproval 记录"""
    # 查找已终态且没有对应 ApprovalRequest 的记录
    records = (
        db.query(ProposalApproval)
        .filter(
            ProposalApproval.status.in_(list(_TERMINAL_STATUSES)),
            ~db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.request_type == "proposal",
                ApprovalRequest.request_id == ProposalApproval.id,
            )
            .exists(),
        )
        .order_by(ProposalApproval.id)
        .limit(batch_size)
        .all()
    )

    if not records:
        print("没有需要迁移的记录")
        return 0

    # 获取 proposal 审批链
    chain = db.query(ApprovalChain).filter(ApprovalChain.code == "proposal").first()
    if not chain:
        print("ERROR: proposal 审批链不存在，请先确保系统已初始化")
        return 0

    migrated = 0
    for pa in records:
        req = ApprovalRequest(
            chain_id=chain.id,
            request_type="proposal",
            request_id=pa.id,
            title=pa.title,
            requester=str(pa.proposer_id),
            status=_STATUS_MAP.get(pa.status, "pending"),
            current_step=(
                3 if pa.status == ProposalStatus.APPROVED else
                1
            ),
            step_meta={},
        )
        if dry_run:
            print(f"  [DRY-RUN] pa.id={pa.id}, status={pa.status}, title={pa.title}")
            migrated += 1
            continue

        db.add(req)
        db.flush()

        # 迁移并行审批人记录为 ApprovalRecord
        reviewer_rows = (
            db.query(ProposalParallelReviewer)
            .filter(ProposalParallelReviewer.approval_id == pa.id)
            .all()
        )
        for row in reviewer_rows:
            if row.status != ReviewStatus.PENDING:
                record = ApprovalRecord(
                    request_id=req.id,
                    step_id=None,
                    approver=row.username,
                    decision=row.status,
                    comment=row.reason or "",
                    decided_at=row.reviewed_at or datetime.now(),
                )
                db.add(record)

        # 迁移总监审批记录
        if pa.director_status and pa.director_status != ReviewStatus.PENDING:
            record = ApprovalRecord(
                request_id=req.id,
                step_id=None,
                approver=f"director:{pa.director_reviewer_id}",
                decision=pa.director_status,
                comment=pa.director_reason or "",
                decided_at=pa.director_reviewed_at or datetime.now(),
            )
            db.add(record)

        db.flush()
        migrated += 1
        print(f"  ✓ pa.id={pa.id} → ApprovalRequest.id={req.id}")

    if not dry_run:
        db.commit()
        print(f"已提交 {migrated} 条")

    return migrated


def main():
    parser = argparse.ArgumentParser(description="存量审批数据迁移到 ApprovalRequest")
    parser.add_argument("--apply", action="store_true", help="实际执行（默认DRY RUN）")
    parser.add_argument("--batch", type=int, default=50, help="每批处理条数")
    args = parser.parse_args()

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"=== 审批数据迁移 ({mode}) ===")
    print(f"批次大小: {args.batch}")
    print()

    db = SessionLocal()
    try:
        total = 0
        while True:
            count = migrate_batch(db, batch_size=args.batch, dry_run=dry_run)
            total += count
            if count == 0:
                break
            print(f"  累计: {total} 条\n")
        print(f"\n=== 迁移完成 ({mode}), 共 {total} 条 ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
