"""SOP标准作业指导书 + 工艺路线 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.process_sop import SOP, ProcessRoute
import json

router = APIRouter(prefix="/process", tags=["工艺管理"])


# ═══ SOP ═══

def _sop_out(s: SOP) -> dict:
    return {
        "id": s.id, "code": s.code, "name": s.name,
        "product_model": s.product_model, "process_name": s.process_name,
        "step_no": s.step_no, "description": s.description,
        "standard_time": s.standard_time, "tools": s.tools,
        "quality_standard": s.quality_standard, "image_url": s.image_url,
        "version": s.version, "status": s.status,
        "author": s.author, "reviewer": s.reviewer,
        "review_date": str(s.review_date) if s.review_date else None,
        "created_at": str(s.created_at) if s.created_at else None,
    }


@router.get("/sops")
def list_sop(
    product_model: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SOP)
    if product_model: q = q.filter(SOP.product_model == product_model)
    if status: q = q.filter(SOP.status == status)
    if keyword: q = q.filter(SOP.name.ilike(f"%{keyword}%") | SOP.code.ilike(f"%{keyword}%"))
    return [_sop_out(s) for s in q.order_by(SOP.id.desc()).limit(100).all()]


@router.get("/sops/{sid}")
def get_sop(sid: int, db: Session = Depends(get_db)):
    s = db.query(SOP).filter(SOP.id == sid).first()
    if not s: raise HTTPException(404, "SOP不存在")
    return _sop_out(s)


@router.post("/sops")
def create_sop(data: dict, db: Session = Depends(get_db)):
    valid_fields = {c.name for c in SOP.__table__.columns}
    s = SOP(**{k: v for k, v in data.items() if k in valid_fields})
    if not s.code: s.code = f"SOP-{s.id or 0}"
    db.add(s); db.commit(); db.refresh(s)
    return _sop_out(s)


@router.put("/sops/{sid}")
def update_sop(sid: int, data: dict, db: Session = Depends(get_db)):
    s = db.query(SOP).filter(SOP.id == sid).first()
    if not s: raise HTTPException(404, "SOP不存在")
    for k, v in data.items():
        if hasattr(s, k): setattr(s, k, v)
    db.commit(); db.refresh(s)
    return _sop_out(s)


@router.delete("/sops/{sid}")
def delete_sop(sid: int, db: Session = Depends(get_db)):
    s = db.query(SOP).filter(SOP.id == sid).first()
    if not s: raise HTTPException(404, "SOP不存在")
    db.delete(s); db.commit()
    return {"message": "已删除"}


# ═══ 工艺路线 ═══

def _route_out(r: ProcessRoute) -> dict:
    return {
        "id": r.id, "code": r.code, "name": r.name,
        "product_model": r.product_model, "version": r.version,
        "steps": r.steps, "total_time": r.total_time,
        "status": r.status, "author": r.author,
        "created_at": str(r.created_at) if r.created_at else None,
    }


@router.get("/routes")
def list_routes(product_model: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ProcessRoute)
    if product_model: q = q.filter(ProcessRoute.product_model == product_model)
    return [_route_out(r) for r in q.order_by(ProcessRoute.id.desc()).limit(50).all()]


@router.get("/routes/{rid}")
def get_route(rid: int, db: Session = Depends(get_db)):
    r = db.query(ProcessRoute).filter(ProcessRoute.id == rid).first()
    if not r: raise HTTPException(404, "工艺路线不存在")
    return _route_out(r)


@router.post("/routes")
def create_route(data: dict, db: Session = Depends(get_db)):
    valid_fields = {c.name for c in ProcessRoute.__table__.columns}
    r = ProcessRoute(**{k: v for k, v in data.items() if k in valid_fields})
    if not r.code: r.code = f"ROUTE-{r.id or 0}"
    # 计算总工时
    try:
        steps = json.loads(r.steps) if r.steps else []
        r.total_time = sum(s.get("std_time", 0) for s in steps)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    db.add(r); db.commit(); db.refresh(r)
    return _route_out(r)


@router.put("/routes/{rid}")
def update_route(rid: int, data: dict, db: Session = Depends(get_db)):
    r = db.query(ProcessRoute).filter(ProcessRoute.id == rid).first()
    if not r: raise HTTPException(404, "工艺路线不存在")
    for k, v in data.items():
        if hasattr(r, k): setattr(r, k, v)
    try:
        steps = json.loads(r.steps) if r.steps else []
        r.total_time = sum(s.get("std_time", 0) for s in steps)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    db.commit(); db.refresh(r)
    return _route_out(r)


@router.delete("/routes/{rid}")
def delete_route(rid: int, db: Session = Depends(get_db)):
    r = db.query(ProcessRoute).filter(ProcessRoute.id == rid).first()
    if not r: raise HTTPException(404, "工艺路线不存在")
    db.delete(r); db.commit()
    return {"message": "已删除"}
