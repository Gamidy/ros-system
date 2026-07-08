"""DFM可制造性分析模块 API — 检查项模板+分析报告+评分引擎"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.services import event_bus
from app.models.user import User
from app.models.manufacturability import (
    DFMChecklist, DFMReport, DFMReportItem, DFMScoreWeight,
)
from app.schemas.manufacturability import (
    DFMChecklistCreate, DFMChecklistUpdate, DFMChecklistOut, DFMChecklistListOut,
    DFMReportCreate, DFMReportUpdate, DFMReportOut, DFMReportListOut,
    DFMReportItemCreate, DFMReportItemUpdate, DFMReportItemOut,
    DFMScoreWeightCreate, DFMScoreWeightUpdate, DFMScoreWeightOut, DFMScoreWeightListOut,
    DFMScoreResult,
)

router = APIRouter(prefix="/dfm", tags=["DFM可制造性分析"])


# ═══════════════ 评分引擎 ═══════════════

def calculate_dfm_score(db: Session, report_id: int) -> DFMScoreResult:
    """计算DFM报告总分"""
    items = db.query(DFMReportItem).filter(DFMReportItem.report_id == report_id).all()
    report = db.query(DFMReport).filter(DFMReport.id == report_id).first()

    if not items:
        return DFMScoreResult(total_score=0, category_scores={},
                              item_count=0, critical_count=0, major_count=0, minor_count=0)

    product_type = report.product_type if report else None
    cat_items: dict[str, list] = {}
    critical = major = minor = 0

    for item in items:
        cat = item.dfm_category or "other"
        if cat not in cat_items:
            cat_items[cat] = []
        cat_items[cat].append(item)
        if item.severity == "critical":
            critical += 1
        elif item.severity == "major":
            major += 1
        elif item.severity == "minor":
            minor += 1

    # 获取权重配置
    weights: dict[str, float] = {}
    if product_type:
        weight_rows = db.query(DFMScoreWeight).filter(
            DFMScoreWeight.product_type == product_type).all()
        for w in weight_rows:
            weights[w.dfm_category] = w.weight

    # 按分类计算得分
    category_scores = {}
    total_weighted = 0.0
    total_weight = 0.0

    for cat, cat_items_list in cat_items.items():
        resolved = [i for i in cat_items_list if i.status == "verified"]
        cat_score = (len(resolved) / len(cat_items_list)) * 100 if cat_items_list else 100
        cat_weight = weights.get(cat, 1.0 / max(len(cat_items), 1))
        category_scores[cat] = {
            "score": round(cat_score, 1),
            "max": 100,
            "weight": cat_weight,
            "total": len(cat_items_list),
            "resolved": len(resolved),
        }
        total_weighted += cat_score * cat_weight
        total_weight += cat_weight

    total_score = round(total_weighted / total_weight, 1) if total_weight > 0 else 0

    return DFMScoreResult(
        total_score=min(total_score, 100),
        category_scores=category_scores,
        item_count=len(items),
        critical_count=critical,
        major_count=major,
        minor_count=minor,
    )


def auto_generate_report_no(db: Session) -> str:
    """自动生成报告编号 DFM-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(DFMReport).filter(
        DFMReport.report_no.like(f"DFM-{today}-%")
    ).count()
    return f"DFM-{today}-{count + 1:04d}"


# ═══════════════ DFM检查项模板 CRUD ═══════════════

@router.get("/checklist", response_model=DFMChecklistListOut)
def list_checklist(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, alias="dfm_category"),
    severity: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DFMChecklistListOut:
    """获取DFM检查项模板列表"""
    query = db.query(DFMChecklist)
    if category:
        query = query.filter(DFMChecklist.dfm_category == category)
    if severity:
        query = query.filter(DFMChecklist.severity == severity)
    if status:
        query = query.filter(DFMChecklist.status == status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(DFMChecklist.item_code.ilike(kw),
                DFMChecklist.item_name.ilike(kw))
        )
    total = query.count()
    items = query.order_by(DFMChecklist.dfm_category, DFMChecklist.sort_order,
                           DFMChecklist.id).offset(
        (page - 1) * page_size).limit(page_size).all()
    return {"items": [DFMChecklistOut.model_validate(i) for i in items], "total": total}


@router.get("/checklist/{cid}", response_model=DFMChecklistOut)
def get_checklist_item(cid: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)) -> DFMChecklistOut:
    item = db.query(DFMChecklist).filter(DFMChecklist.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="检查项不存在")
    return DFMChecklistOut.model_validate(item)


@router.post("/checklist", response_model=DFMChecklistOut,
             dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer"))])
def create_checklist_item(data: DFMChecklistCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> DFMChecklistOut:
    item = DFMChecklist(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return DFMChecklistOut.model_validate(item)


@router.put("/checklist/{cid}", response_model=DFMChecklistOut,
            dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer"))])
def update_checklist_item(cid: int, data: DFMChecklistUpdate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> DFMChecklistOut:
    item = db.query(DFMChecklist).filter(DFMChecklist.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="检查项不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return DFMChecklistOut.model_validate(item)


@router.delete("/checklist/{cid}", dependencies=[Depends(require_role("admin"))])
def delete_checklist_item(cid: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)) -> dict:
    item = db.query(DFMChecklist).filter(DFMChecklist.id == cid).first()
    if not item:
        raise HTTPException(status_code=404, detail="检查项不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ═══════════════ DFM评分权重配置 CRUD ═══════════════

@router.get("/score-weights", response_model=DFMScoreWeightListOut)
def list_score_weights(
    product_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DFMScoreWeightListOut:
    query = db.query(DFMScoreWeight)
    if product_type:
        query = query.filter(DFMScoreWeight.product_type == product_type)
    items = query.order_by(DFMScoreWeight.product_type, DFMScoreWeight.dfm_category).all()
    return {"items": [DFMScoreWeightOut.model_validate(i) for i in items], "total": len(items)}


@router.post("/score-weights", response_model=DFMScoreWeightOut,
             dependencies=[Depends(require_role("admin", "rd_director"))])
def create_score_weight(data: DFMScoreWeightCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)) -> DFMScoreWeightOut:
    item = DFMScoreWeight(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return DFMScoreWeightOut.model_validate(item)


@router.put("/score-weights/{wid}", response_model=DFMScoreWeightOut,
            dependencies=[Depends(require_role("admin", "rd_director"))])
def update_score_weight(wid: int, data: DFMScoreWeightUpdate, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)) -> DFMScoreWeightOut:
    item = db.query(DFMScoreWeight).filter(DFMScoreWeight.id == wid).first()
    if not item:
        raise HTTPException(status_code=404, detail="权重配置不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return DFMScoreWeightOut.model_validate(item)


@router.delete("/score-weights/{wid}", dependencies=[Depends(require_role("admin"))])
def delete_score_weight(wid: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)) -> dict:
    item = db.query(DFMScoreWeight).filter(DFMScoreWeight.id == wid).first()
    if not item:
        raise HTTPException(status_code=404, detail="权重配置不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ═══════════════ DFM报告 CRUD ═══════════════

@router.get("/reports", response_model=DFMReportListOut)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    prototype_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DFMReportListOut:
    query = db.query(DFMReport)
    if project_id:
        query = query.filter(DFMReport.project_id == project_id)
    if prototype_id:
        query = query.filter(DFMReport.prototype_id == prototype_id)
    if status:
        query = query.filter(DFMReport.status == status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(DFMReport.report_no.ilike(kw), DFMReport.title.ilike(kw))
        )
    total = query.count()
    items = query.order_by(DFMReport.id.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    result = []
    for r in items:
        out = DFMReportOut.model_validate(r)
        out.items = [DFMReportItemOut.model_validate(i) for i in r.items] if r.items else []
        result.append(out)
    return {"items": result, "total": total}


@router.get("/reports/{rid}", response_model=DFMReportOut)
def get_report(rid: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)) -> DFMReportOut:
    report = db.query(DFMReport).options(
        joinedload(DFMReport.items)
    ).filter(DFMReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="DFM报告不存在")
    out = DFMReportOut.model_validate(report)
    out.items = [DFMReportItemOut.model_validate(i) for i in report.items] if report.items else []
    return out


@router.post("/reports", response_model=DFMReportOut,
             dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer", "quality_engineer"))])
def create_report(data: DFMReportCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)) -> DFMReportOut:
    report = DFMReport(**data.model_dump())
    report.report_no = auto_generate_report_no(db)
    db.add(report)
    db.commit()
    db.refresh(report)

    # ── event bus: dfm.report.created ──
    user_id = str(current_user.id) if hasattr(current_user, "id") else None
    event_bus.emit(
        event_type="dfm.report.created",
        payload={
            "id": report.id,
            "report_no": report.report_no,
            "project_id": report.project_id,
            "title": report.title,
        },
        source="manufacturability",
        producer="manufacturability.service",
        user_id=user_id,
    )

    return DFMReportOut.model_validate(report)


@router.put("/reports/{rid}", response_model=DFMReportOut,
            dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer"))])
def update_report(rid: int, data: DFMReportUpdate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)) -> DFMReportOut:
    report = db.query(DFMReport).options(
        joinedload(DFMReport.items)
    ).filter(DFMReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="DFM报告不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(report, k, v)
    # 完成时自动计算总分
    if data.status == "completed":
        score = calculate_dfm_score(db, rid)
        report.total_score = score.total_score

        # ── event bus: dfm.score.calculated ──
        user_id = str(current_user.id) if hasattr(current_user, "id") else None
        event_bus.emit(
            event_type="dfm.score.calculated",
            payload={
                "id": rid,
                "total_score": score.total_score,
                "critical_count": score.critical_count,
                "major_count": score.major_count,
                "minor_count": score.minor_count,
            },
            source="manufacturability",
            producer="manufacturability.service",
            user_id=user_id,
        )

        # ── event bus: dfm.issue.identified (if serious issues found) ──
        if score.total_score < 60 or score.critical_count > 0:
            event_bus.emit(
                event_type="dfm.issue.identified",
                payload={
                    "id": rid,
                    "total_score": score.total_score,
                    "critical_count": score.critical_count,
                    "major_count": score.major_count,
                    "minor_count": score.minor_count,
                    "threshold": 60,
                },
                source="manufacturability",
                producer="manufacturability.service",
                user_id=user_id,
            )
    db.commit()
    db.refresh(report)
    out = DFMReportOut.model_validate(report)
    out.items = [DFMReportItemOut.model_validate(i) for i in report.items] if report.items else []
    return out


@router.delete("/reports/{rid}", dependencies=[Depends(require_role("admin"))])
def delete_report(rid: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)) -> dict:
    report = db.query(DFMReport).filter(DFMReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="DFM报告不存在")
    db.delete(report)
    db.commit()
    return {"ok": True}


@router.get("/reports/{rid}/score", response_model=DFMScoreResult)
def get_report_score(rid: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)) -> DFMScoreResult:
    report = db.query(DFMReport).filter(DFMReport.id == rid).first()
    if not report:
        raise HTTPException(status_code=404, detail="DFM报告不存在")
    return calculate_dfm_score(db, rid)


# ═══════════════ DFM评分统计 ═══════════════

@router.get("/stats")
def get_dfm_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    """返回DFM统计: 总报告数/平均分/通过数/失败数/未关闭问题数"""
    total_reports = db.query(DFMReport).count()
    avg_result = db.query(func.avg(DFMReport.total_score)).filter(DFMReport.total_score.isnot(None)).scalar()
    avg_score = round(float(avg_result), 1) if avg_result else 0.0
    pass_count = db.query(DFMReport).filter(DFMReport.total_score >= 60).count() if avg_result else 0
    fail_count = db.query(DFMReport).filter(DFMReport.total_score < 60, DFMReport.total_score.isnot(None)).count()
    open_issues = db.query(DFMReportItem).filter(DFMReportItem.status != "verified").count()
    return {
        "total_reports": total_reports,
        "avg_score": avg_score,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "open_issues": open_issues,
    }


# ═══════════════ DFM报告问题项 CRUD ═══════════════

@router.get("/reports/{rid}/items", response_model=list[DFMReportItemOut])
def list_report_items(rid: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)) -> list[DFMReportItemOut]:
    items = db.query(DFMReportItem).filter(
        DFMReportItem.report_id == rid
    ).order_by(DFMReportItem.sort_order, DFMReportItem.id).all()
    return [DFMReportItemOut.model_validate(i) for i in items]


@router.post("/report-items", response_model=DFMReportItemOut,
             dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer", "quality_engineer"))])
def create_report_item(data: DFMReportItemCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)) -> DFMReportItemOut:
    report = db.query(DFMReport).filter(DFMReport.id == data.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="DFM报告不存在")
    # 自动更新报告状态
    if report.status == "draft":
        report.status = "in_progress"
    item = DFMReportItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return DFMReportItemOut.model_validate(item)


@router.put("/report-items/{iid}", response_model=DFMReportItemOut,
            dependencies=[Depends(require_role("admin", "rd_director", "structural_engineer", "process_engineer", "quality_engineer"))])
def update_report_item(iid: int, data: DFMReportItemUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)) -> DFMReportItemOut:
    item = db.query(DFMReportItem).filter(DFMReportItem.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="问题项不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return DFMReportItemOut.model_validate(item)


@router.delete("/report-items/{iid}", dependencies=[Depends(require_role("admin"))])
def delete_report_item(iid: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)) -> dict:
    item = db.query(DFMReportItem).filter(DFMReportItem.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="问题项不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}
