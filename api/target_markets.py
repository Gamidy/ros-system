"""目标市场 API — Phase 6 S1"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.target_market import (
    TargetMarket, RequiredTest, RequiredCertification, RequiredStandard,
)
from app.schemas import (
    TargetMarketCreate, TargetMarketOut,
    RequiredTestCreate, RequiredTestOut,
    RequiredCertificationCreate, RequiredCertificationOut,
    RequiredStandardCreate, RequiredStandardOut,
)

router = APIRouter(prefix="/target-markets", tags=["目标市场"])


@router.get("", response_model=list[TargetMarketOut])
def list_target_markets(
    market_code: str = Query("", description="市场代码"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> list[TargetMarketOut]:
    q = db.query(TargetMarket)
    if market_code:
        q = q.filter(TargetMarket.market_code == market_code)
    return q.order_by(TargetMarket.market_code).all()


@router.post("", response_model=TargetMarketOut)
def create_target_market(
    data: TargetMarketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_menu("market_mgmt")),
) -> TargetMarketOut:
    tm = TargetMarket(
        **data.model_dump(),
        org_id=getattr(current_user, "org_id", None),
    )
    db.add(tm)
    db.commit()
    db.refresh(tm)
    return tm


@router.get("/{tid}", response_model=TargetMarketOut)
def get_target_market(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> TargetMarketOut:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    return tm


@router.put("/{tid}", response_model=TargetMarketOut)
def update_target_market(
    tid: int,
    data: TargetMarketCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> TargetMarketOut:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    for key, val in data.model_dump().items():
        setattr(tm, key, val)
    tm.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tm)
    return tm


@router.delete("/{tid}")
def delete_target_market(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> dict:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    db.delete(tm)
    db.commit()
    return {"ok": True, "message": "目标市场已删除"}


# ── RequiredTest ──

@router.get("/{tid}/tests", response_model=list[RequiredTestOut])
def list_required_tests(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> list[RequiredTestOut]:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    return db.query(RequiredTest).filter(RequiredTest.target_market_id == tid).order_by(RequiredTest.sort_order).all()


@router.post("/{tid}/tests", response_model=RequiredTestOut)
def add_required_test(
    tid: int,
    data: RequiredTestCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredTestOut:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    rt = RequiredTest(target_market_id=tid, **data.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.delete("/{tid}/tests/{rtid}")
def delete_required_test(
    tid: int,
    rtid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> dict:
    rt = db.query(RequiredTest).filter(
        RequiredTest.id == rtid,
        RequiredTest.target_market_id == tid,
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="RequiredTest不存在")
    db.delete(rt)
    db.commit()
    return {"ok": True, "message": "RequiredTest已删除"}


@router.put("/{tid}/tests/{rtid}", response_model=RequiredTestOut)
def update_required_test(
    tid: int,
    rtid: int,
    data: RequiredTestCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredTestOut:
    rt = db.query(RequiredTest).filter(
        RequiredTest.id == rtid,
        RequiredTest.target_market_id == tid,
    ).first()
    if not rt:
        raise HTTPException(status_code=404, detail="RequiredTest不存在")
    for key, val in data.model_dump().items():
        setattr(rt, key, val)
    db.commit()
    db.refresh(rt)
    return rt


# ── RequiredCertification ──

@router.get("/{tid}/certifications", response_model=list[RequiredCertificationOut])
def list_required_certifications(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> list[RequiredCertificationOut]:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    return db.query(RequiredCertification).filter(RequiredCertification.target_market_id == tid).order_by(RequiredCertification.sort_order).all()


@router.post("/{tid}/certifications", response_model=RequiredCertificationOut)
def add_required_certification(
    tid: int,
    data: RequiredCertificationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredCertificationOut:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    rc = RequiredCertification(target_market_id=tid, **data.model_dump())
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


@router.put("/{tid}/certifications/{rcid}", response_model=RequiredCertificationOut)
def update_required_certification(
    tid: int,
    rcid: int,
    data: RequiredCertificationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredCertificationOut:
    rc = db.query(RequiredCertification).filter(
        RequiredCertification.id == rcid,
        RequiredCertification.target_market_id == tid,
    ).first()
    if not rc:
        raise HTTPException(status_code=404, detail="RequiredCertification不存在")
    for key, val in data.model_dump().items():
        setattr(rc, key, val)
    db.commit()
    db.refresh(rc)
    return rc


@router.delete("/{tid}/certifications/{rcid}")
def delete_required_certification(
    tid: int,
    rcid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> dict:
    rc = db.query(RequiredCertification).filter(
        RequiredCertification.id == rcid,
        RequiredCertification.target_market_id == tid,
    ).first()
    if not rc:
        raise HTTPException(status_code=404, detail="RequiredCertification不存在")
    db.delete(rc)
    db.commit()
    return {"ok": True, "message": "RequiredCertification已删除"}


# ── RequiredStandard ──

@router.get("/{tid}/standards", response_model=list[RequiredStandardOut])
def list_required_standards(
    tid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> list[RequiredStandardOut]:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    return db.query(RequiredStandard).filter(RequiredStandard.target_market_id == tid).order_by(RequiredStandard.sort_order).all()


@router.post("/{tid}/standards", response_model=RequiredStandardOut)
def add_required_standard(
    tid: int,
    data: RequiredStandardCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredStandardOut:
    tm = db.query(TargetMarket).filter(TargetMarket.id == tid).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    rs = RequiredStandard(target_market_id=tid, **data.model_dump())
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return rs


@router.delete("/{tid}/standards/{rsid}")
def delete_required_standard(
    tid: int,
    rsid: int,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> dict:
    rs = db.query(RequiredStandard).filter(
        RequiredStandard.id == rsid,
        RequiredStandard.target_market_id == tid,
    ).first()
    if not rs:
        raise HTTPException(status_code=404, detail="RequiredStandard不存在")
    db.delete(rs)
    db.commit()
    return {"ok": True, "message": "RequiredStandard已删除"}


@router.put("/{tid}/standards/{rsid}", response_model=RequiredStandardOut)
def update_required_standard(
    tid: int,
    rsid: int,
    data: RequiredStandardCreate,
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> RequiredStandardOut:
    rs = db.query(RequiredStandard).filter(
        RequiredStandard.id == rsid,
        RequiredStandard.target_market_id == tid,
    ).first()
    if not rs:
        raise HTTPException(status_code=404, detail="RequiredStandard不存在")
    for key, val in data.model_dump().items():
        setattr(rs, key, val)
    db.commit()
    db.refresh(rs)
    return rs


# ── 按市场代码查询 ──

@router.get("/by-market", response_model=TargetMarketOut)
def get_target_market_by_code(
    market_code: str = Query(..., description="市场代码"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("market_mgmt")),
) -> TargetMarketOut:
    tm = db.query(TargetMarket).filter(
        TargetMarket.market_code == market_code
    ).first()
    if not tm:
        raise HTTPException(status_code=404, detail="目标市场不存在")
    return tm
