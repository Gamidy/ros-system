"""8D报告管理 API — CRUD + 状态流转"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.quality_8d_report import EightDReport
from app.schemas.quality_8d_report import (
    EightDReportCreate, EightDReportUpdate, EightDReportOut,
    EightDReportListOut, EightDReportStatusUpdate,
)

router = APIRouter(prefix="/api/quality/8d-reports", tags=["8D报告管理"])

# 可允许的状态流转
STATUS_TRANSITIONS = {
    "open": ["analysis"],
    "analysis": ["containment", "open"],
    "containment": ["corrective", "analysis"],
    "corrective": ["verify", "containment"],
    "verify": ["closed", "corrective"],
    "closed": [],
}


def _auto_report_no(db: Session) -> str:
    """自动生成8D报告编号"""
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(EightDReport).filter(
        EightDReport.report_no.like(f"8D-{today}-%")).count()
    return f"8D-{today}-{count + 1:04d}"


@router.get("", response_model=EightDReportListOut)
def list_8d_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    responsible_person: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EightDReportListOut:
    """获取8D报告列表，支持多维度筛选"""
    try:
        query = db.query(EightDReport)
        if status:
            query = query.filter(EightDReport.status == status)
        if severity:
            query = query.filter(EightDReport.severity == severity)
        if responsible_person:
            query = query.filter(EightDReport.responsible_person == responsible_person)
        if keyword:
            kw = f"%{keyword}%"
            query = query.filter(
                or_(
                    EightDReport.report_no.ilike(kw),
                    EightDReport.issue_title.ilike(kw),
                    EightDReport.issue_desc.ilike(kw),
                    EightDReport.product_info.ilike(kw),
                )
            )
        total = query.count()
        items = query.order_by(EightDReport.id.desc()).offset(
            (page - 1) * page_size).limit(page_size).all()
        return EightDReportListOut(items=[EightDReportOut.model_validate(r) for r in items], total=total)
    except Exception:
        return EightDReportListOut(items=[], total=0)


@router.get("/{rid}", response_model=EightDReportOut)
def get_8d_report(
    rid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EightDReportOut:
    """获取单个8D报告详情"""
    report = db.query(EightDReport).filter(EightDReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="8D报告不存在")
    return EightDReportOut.model_validate(report)


@router.post("", response_model=EightDReportOut)
def create_8d_report(
    data: EightDReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EightDReportOut:
    """创建8D报告"""
    report = EightDReport(**data.model_dump())
    if not report.report_no:
        report.report_no = _auto_report_no(db)
    report.status = "open"
    db.add(report)
    db.commit()
    db.refresh(report)
    return EightDReportOut.model_validate(report)


@router.put("/{rid}", response_model=EightDReportOut)
def update_8d_report(
    rid: int,
    data: EightDReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EightDReportOut:
    """更新8D报告（非状态字段）"""
    report = db.query(EightDReport).filter(EightDReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="8D报告不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)
    db.commit()
    db.refresh(report)
    return EightDReportOut.model_validate(report)


@router.put("/{rid}/status", response_model=EightDReportOut)
def update_8d_report_status(
    rid: int,
    data: EightDReportStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EightDReportOut:
    """状态流转: open→analysis→containment→corrective→verify→closed"""
    report = db.query(EightDReport).filter(EightDReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="8D报告不存在")

    current = report.status
    target = data.status

    if current == target:
        raise HTTPException(status_code=400, detail="状态未变化")

    allowed = STATUS_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不允许的状态流转: {current} → {target}，允许目标: {allowed}"
        )

    report.status = target
    if target == "closed":
        report.closed_date = datetime.now()
    db.commit()
    db.refresh(report)
    return EightDReportOut.model_validate(report)


@router.delete("/{rid}")
def delete_8d_report(
    rid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """删除8D报告"""
    report = db.query(EightDReport).filter(EightDReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="8D报告不存在")
    db.delete(report)
    db.commit()
    return {"message": "删除成功"}
