"""安规管理模块 API — 安全标准库 + 安规检测项 + 供应商安规资质 + 预警"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.safety import (
    SafetyStandard, SafetyInspectionItem,
    SupplierSafetyQualification, SupplierSafetyAuditRecord,
)
from app.models.user import User
from app.schemas.safety import (
    SafetyStandardCreate, SafetyStandardUpdate, SafetyStandardOut, SafetyStandardListOut,
    SafetyInspectionItemCreate, SafetyInspectionItemUpdate, SafetyInspectionItemOut, SafetyInspectionItemListOut,
    SupplierSafetyQualificationCreate, SupplierSafetyQualificationUpdate, SupplierSafetyQualificationOut,
    SupplierSafetyQualificationListOut,
    SafetyAuditRecordCreate, SafetyAuditRecordUpdate, SafetyAuditRecordOut,
    SafetyAlertItem, SafetyAlertListOut,
)
from app.models.purchase import Supplier

router = APIRouter(prefix="/api/safety", tags=["安规管理"])

ALLOWED_ROLES = ["admin", "general_manager", "quality_engineer", "certification_engineer",
                  "procurement", "rd_director", "product_manager", "systems_engineer",
                  "electrical_control_engineer", "electrical_engineer", "structural_engineer",
                  "process_engineer", "project_admin", "security_officer",
                  "module_manager", "module_manager_struct", "module_manager_sys"]


def _get_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ═══════════════ 安全标准库 CRUD ═══════════════

@router.get("/standards", response_model=SafetyStandardListOut)
def list_standards(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    standard_type: Optional[str] = Query(None, description="标准类型"),
    status: Optional[str] = Query(None, description="状态: active/draft/obsolete"),
    applicable_market: Optional[str] = Query(None, description="适用市场"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """获取安全标准库分页列表"""
    query = db.query(SafetyStandard)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(SafetyStandard.standard_code.ilike(kw),
                SafetyStandard.standard_name_cn.ilike(kw),
                SafetyStandard.standard_name_en.ilike(kw))
        )
    if standard_type:
        query = query.filter(SafetyStandard.standard_type == standard_type)
    if status:
        query = query.filter(SafetyStandard.status == status)
    if applicable_market:
        query = query.filter(SafetyStandard.applicable_market.ilike(f"%{applicable_market}%"))

    total = query.count()
    items = query.order_by(SafetyStandard.standard_code).offset(
        (page - 1) * page_size).limit(page_size).all()

    result = []
    for item in items:
        out = SafetyStandardOut.model_validate(item)
        out.inspection_items_count = len(item.inspection_items) if item.inspection_items else 0
        result.append(out)
    return {"items": result, "total": total}


@router.get("/standards/{sid}", response_model=SafetyStandardOut)
def get_standard(sid: int, db: Session = Depends(get_db),
                 current_user: User = Depends(_get_current_user)):
    """获取安全标准详情"""
    item = db.query(SafetyStandard).options(
        joinedload(SafetyStandard.inspection_items)
    ).filter(SafetyStandard.id == sid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安全标准不存在")
    out = SafetyStandardOut.model_validate(item)
    out.inspection_items_count = len(item.inspection_items) if item.inspection_items else 0
    return out


@router.post("/standards", response_model=SafetyStandardOut,
             dependencies=[Depends(require_role("admin", "quality_engineer", "certification_engineer"))])
def create_standard(data: SafetyStandardCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(_get_current_user)):
    """创建安全标准"""
    item = SafetyStandard(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return SafetyStandardOut.model_validate(item)


@router.put("/standards/{sid}", response_model=SafetyStandardOut,
            dependencies=[Depends(require_role("admin", "quality_engineer", "certification_engineer"))])
def update_standard(sid: int, data: SafetyStandardUpdate, db: Session = Depends(get_db),
                     current_user: User = Depends(_get_current_user)):
    """更新安全标准"""
    item = db.query(SafetyStandard).filter(SafetyStandard.id == sid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安全标准不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return SafetyStandardOut.model_validate(item)


@router.delete("/standards/{sid}", dependencies=[Depends(require_role("admin"))])
def delete_standard(sid: int, db: Session = Depends(get_db),
                     current_user: User = Depends(_get_current_user)):
    """删除安全标准（物理删除，仅admin）"""
    item = db.query(SafetyStandard).filter(SafetyStandard.id == sid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安全标准不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.put("/standards/{sid}/archive", response_model=SafetyStandardOut,
            dependencies=[Depends(require_role("admin", "quality_engineer", "certification_engineer"))])
def archive_standard(sid: int, db: Session = Depends(get_db),
                      current_user: User = Depends(_get_current_user)):
    """归档安全标准（软删除：状态设为obsolete）"""
    item = db.query(SafetyStandard).filter(SafetyStandard.id == sid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安全标准不存在")
    item.status = "obsolete"
    db.commit()
    db.refresh(item)
    return SafetyStandardOut.model_validate(item)


# ═══════════════ 安规检测项 CRUD ═══════════════

@router.get("/inspection-items", response_model=SafetyInspectionItemListOut)
def list_inspection_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    standard_id: Optional[int] = Query(None, description="所属标准ID"),
    inspection_category: Optional[str] = Query(None, description="检测类别"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="状态"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """获取安规检测项分页列表"""
    query = db.query(SafetyInspectionItem).options(
        joinedload(SafetyInspectionItem.standard))
    if standard_id:
        query = query.filter(SafetyInspectionItem.standard_id == standard_id)
    if inspection_category:
        query = query.filter(SafetyInspectionItem.inspection_category == inspection_category)
    if status:
        query = query.filter(SafetyInspectionItem.status == status)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(SafetyInspectionItem.item_code.ilike(kw),
                SafetyInspectionItem.item_name.ilike(kw))
        )
    total = query.count()
    items = query.order_by(SafetyInspectionItem.sort_order,
                           SafetyInspectionItem.id).offset(
        (page - 1) * page_size).limit(page_size).all()

    result = []
    for item in items:
        out = SafetyInspectionItemOut.model_validate(item)
        if item.standard:
            out.standard_code = item.standard.standard_code
        result.append(out)
    return {"items": result, "total": total}


@router.get("/inspection-items/{iid}", response_model=SafetyInspectionItemOut)
def get_inspection_item(iid: int, db: Session = Depends(get_db),
                         current_user: User = Depends(_get_current_user)):
    """获取安规检测项详情"""
    item = db.query(SafetyInspectionItem).options(
        joinedload(SafetyInspectionItem.standard)
    ).filter(SafetyInspectionItem.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安规检测项不存在")
    out = SafetyInspectionItemOut.model_validate(item)
    if item.standard:
        out.standard_code = item.standard.standard_code
    return out


@router.post("/inspection-items", response_model=SafetyInspectionItemOut,
             dependencies=[Depends(require_role("admin", "quality_engineer", "certification_engineer"))])
def create_inspection_item(data: SafetyInspectionItemCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(_get_current_user)):
    """创建安规检测项"""
    # 验证标准存在
    std = db.query(SafetyStandard).filter(SafetyStandard.id == data.standard_id).first()
    if not std:
        raise HTTPException(status_code=404, detail="关联安全标准不存在")
    item = SafetyInspectionItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    out = SafetyInspectionItemOut.model_validate(item)
    out.standard_code = std.standard_code
    return out


@router.put("/inspection-items/{iid}", response_model=SafetyInspectionItemOut,
            dependencies=[Depends(require_role("admin", "quality_engineer", "certification_engineer"))])
def update_inspection_item(iid: int, data: SafetyInspectionItemUpdate, db: Session = Depends(get_db),
                            current_user: User = Depends(_get_current_user)):
    """更新安规检测项"""
    item = db.query(SafetyInspectionItem).options(
        joinedload(SafetyInspectionItem.standard)
    ).filter(SafetyInspectionItem.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安规检测项不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "standard_id" in update_data and update_data["standard_id"] != item.standard_id:
        std = db.query(SafetyStandard).filter(SafetyStandard.id == update_data["standard_id"]).first()
        if not std:
            raise HTTPException(status_code=404, detail="关联安全标准不存在")
    for k, v in update_data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    out = SafetyInspectionItemOut.model_validate(item)
    if item.standard:
        out.standard_code = item.standard.standard_code
    return out


@router.delete("/inspection-items/{iid}", dependencies=[Depends(require_role("admin"))])
def delete_inspection_item(iid: int, db: Session = Depends(get_db),
                            current_user: User = Depends(_get_current_user)):
    """删除安规检测项（仅admin）"""
    item = db.query(SafetyInspectionItem).filter(SafetyInspectionItem.id == iid).first()
    if not item:
        raise HTTPException(status_code=404, detail="安规检测项不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/inspection-items/batch", dependencies=[Depends(require_role("admin", "quality_engineer"))])
def batch_import_inspection_items(
    items: list[SafetyInspectionItemCreate] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """批量导入安规检测项"""
    created = 0
    for data in items:
        std = db.query(SafetyStandard).filter(SafetyStandard.id == data.standard_id).first()
        if not std:
            continue
        existing = db.query(SafetyInspectionItem).filter(
            SafetyInspectionItem.standard_id == data.standard_id,
            SafetyInspectionItem.item_code == data.item_code
        ).first()
        if existing:
            continue
        db.add(SafetyInspectionItem(**data.model_dump()))
        created += 1
    db.commit()
    return {"ok": True, "created": created}


# ═══════════════ 供应商安规资质 CRUD ═══════════════

@router.get("/supplier-qualifications", response_model=SupplierSafetyQualificationListOut)
def list_supplier_qualifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    supplier_id: Optional[int] = Query(None),
    qualification_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="status: active/expired/revoked"),
    audit_status: Optional[str] = Query(None, description="审核状态: pending/approved/rejected"),
    expiry_soon: Optional[int] = Query(None, description="N天内到期预警"),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """获取供应商安规资质列表"""
    query = db.query(SupplierSafetyQualification).options(
        joinedload(SupplierSafetyQualification.audit_records))
    if supplier_id:
        query = query.filter(SupplierSafetyQualification.supplier_id == supplier_id)
    if qualification_type:
        query = query.filter(SupplierSafetyQualification.qualification_type == qualification_type)
    if status:
        query = query.filter(SupplierSafetyQualification.status == status)
    if audit_status:
        query = query.filter(SupplierSafetyQualification.audit_status == audit_status)
    if expiry_soon:
        cutoff = date.today() + timedelta(days=expiry_soon)
        query = query.filter(SupplierSafetyQualification.expiry_date <= cutoff,
                             SupplierSafetyQualification.expiry_date >= date.today())
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(SupplierSafetyQualification.cert_no.ilike(kw),
                SupplierSafetyQualification.qualification_type.ilike(kw))
        )
    total = query.count()
    items = query.order_by(SupplierSafetyQualification.expiry_date.asc().nullslast(),
                           SupplierSafetyQualification.id).offset(
        (page - 1) * page_size).limit(page_size).all()

    result = []
    for item in items:
        out = SupplierSafetyQualificationOut.model_validate(item)
        # 获取供应商名称
        supplier = db.query(Supplier).filter(Supplier.id == item.supplier_id).first()
        if supplier:
            out.supplier_name = supplier.name
        result.append(out)
    return {"items": result, "total": total}


@router.get("/supplier-qualifications/{qid}", response_model=SupplierSafetyQualificationOut)
def get_supplier_qualification(qid: int, db: Session = Depends(get_db),
                                current_user: User = Depends(_get_current_user)):
    """获取供应商安规资质详情"""
    item = db.query(SupplierSafetyQualification).options(
        joinedload(SupplierSafetyQualification.audit_records)
    ).filter(SupplierSafetyQualification.id == qid).first()
    if not item:
        raise HTTPException(status_code=404, detail="供应商安规资质不存在")
    out = SupplierSafetyQualificationOut.model_validate(item)
    supplier = db.query(Supplier).filter(Supplier.id == item.supplier_id).first()
    if supplier:
        out.supplier_name = supplier.name
    return out


@router.post("/supplier-qualifications", response_model=SupplierSafetyQualificationOut,
             dependencies=[Depends(require_role("admin", "procurement", "quality_engineer"))])
def create_supplier_qualification(data: SupplierSafetyQualificationCreate,
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(_get_current_user)):
    """创建供应商安规资质"""
    # 验证供应商存在
    supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    # 检查重复
    existing = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.supplier_id == data.supplier_id,
        SupplierSafetyQualification.qualification_type == data.qualification_type,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"该供应商已存在相同类型的安规资质: {data.qualification_type}")
    item = SupplierSafetyQualification(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    out = SupplierSafetyQualificationOut.model_validate(item)
    out.supplier_name = supplier.name
    return out


@router.put("/supplier-qualifications/{qid}", response_model=SupplierSafetyQualificationOut,
            dependencies=[Depends(require_role("admin", "procurement", "quality_engineer"))])
def update_supplier_qualification(qid: int, data: SupplierSafetyQualificationUpdate,
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(_get_current_user)):
    """更新供应商安规资质"""
    item = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.id == qid).first()
    if not item:
        raise HTTPException(status_code=404, detail="供应商安规资质不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    out = SupplierSafetyQualificationOut.model_validate(item)
    supplier = db.query(Supplier).filter(Supplier.id == item.supplier_id).first()
    if supplier:
        out.supplier_name = supplier.name
    return out


@router.delete("/supplier-qualifications/{qid}",
               dependencies=[Depends(require_role("admin"))])
def delete_supplier_qualification(qid: int, db: Session = Depends(get_db),
                                   current_user: User = Depends(_get_current_user)):
    """删除供应商安规资质（仅admin）"""
    item = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.id == qid).first()
    if not item:
        raise HTTPException(status_code=404, detail="供应商安规资质不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ═══════════════ 供应商安规审核记录 ═══════════════

@router.get("/supplier-qualifications/{qid}/audit-records", response_model=list[SafetyAuditRecordOut])
def list_audit_records(qid: int, db: Session = Depends(get_db),
                        current_user: User = Depends(_get_current_user)):
    """获取供应商安规审核记录列表"""
    records = db.query(SupplierSafetyAuditRecord).filter(
        SupplierSafetyAuditRecord.qualification_id == qid
    ).order_by(SupplierSafetyAuditRecord.audit_date.desc()).all()
    return [SafetyAuditRecordOut.model_validate(r) for r in records]


@router.post("/audit-records", response_model=SafetyAuditRecordOut,
             dependencies=[Depends(require_role("admin", "quality_engineer"))])
def create_audit_record(data: SafetyAuditRecordCreate, db: Session = Depends(get_db),
                         current_user: User = Depends(_get_current_user)):
    """创建安规审核记录"""
    qual = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.id == data.qualification_id).first()
    if not qual:
        raise HTTPException(status_code=404, detail="供应商安规资质不存在")
    record = SupplierSafetyAuditRecord(**data.model_dump())
    db.add(record)
    # 更新资质审核状态
    if data.result == "pass":
        qual.audit_status = "approved"
    elif data.result == "fail":
        qual.audit_status = "rejected"
    else:
        qual.audit_status = "pending"
    db.commit()
    db.refresh(record)
    return SafetyAuditRecordOut.model_validate(record)


# ═══════════════ 安规预警信息 ═══════════════

@router.get("/alerts", response_model=SafetyAlertListOut)
def get_safety_alerts(
    days: int = Query(30, ge=1, le=365, description="预警提前天数"),
    severity: Optional[str] = Query(None, description="筛选严重等级: critical/warning/info"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """获取安规预警信息（证书到期、资质到期、标准变更）"""
    today = date.today()
    items: list[SafetyAlertItem] = []

    # 1. 标准废止预警
    obsolete_standards = db.query(SafetyStandard).filter(
        SafetyStandard.status == "obsolete"
    ).all()
    for s in obsolete_standards:
        items.append(SafetyAlertItem(
            alert_type="standard_change",
            title=f"标准已废止: {s.standard_code}",
            description=f"{s.standard_name_cn} 已被废止",
            severity="warning",
            target_type="standard",
            target_id=s.id,
        ))

    # 2. 供应商资质到期预警
    cutoff = today + timedelta(days=days)
    qual_query = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.expiry_date <= cutoff,
        SupplierSafetyQualification.expiry_date >= today,
        SupplierSafetyQualification.status == "active",
    )
    if severity:
        if severity == "critical":
            qual_query = qual_query.filter(
                SupplierSafetyQualification.expiry_date <= today + timedelta(days=7))
        elif severity == "warning":
            qual_query = qual_query.filter(
                SupplierSafetyQualification.expiry_date > today + timedelta(days=7),
                SupplierSafetyQualification.expiry_date <= today + timedelta(days=30))
    qualifications = qual_query.all()
    for q in qualifications:
        days_left = (q.expiry_date - today).days if q.expiry_date else 0
        sev = "critical" if days_left <= 7 else "warning"
        items.append(SafetyAlertItem(
            alert_type="qual_expiry",
            title=f"供应商资质即将到期: {q.qualification_type}",
            description=f"供应商ID={q.supplier_id}, 证书编号={q.cert_no or '-'}",
            severity=sev,
            target_type="supplier_qualification",
            target_id=q.id,
            expiry_date=q.expiry_date,
            days_remaining=days_left,
        ))

    # 3. 已过期的资质
    expired = db.query(SupplierSafetyQualification).filter(
        SupplierSafetyQualification.expiry_date < today,
        SupplierSafetyQualification.status == "active",
    ).all()
    for q in expired:
        items.append(SafetyAlertItem(
            alert_type="qual_expiry",
            title=f"资质已过期: {q.qualification_type}",
            description=f"供应商ID={q.supplier_id}, 证书={q.cert_no or '-'}, 过期日={q.expiry_date}",
            severity="critical",
            target_type="supplier_qualification",
            target_id=q.id,
            expiry_date=q.expiry_date,
            days_remaining=-1,
        ))

    # 按严重等级排序: critical → warning → info
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    items.sort(key=lambda x: (sev_order.get(x.severity, 3), x.expiry_date or date.max))

    if severity:
        items = [i for i in items if i.severity == severity]

    return {"items": items, "total": len(items)}
