"""测试实验 + MQ验证 API"""
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.core.permissions import require_menu
from app.models.user import User
from app.models.test import TestRequest, TestResult, MQVerification, _VALID_TRANSITIONS
from app.models.alert import Alert
from app.schemas import (
    TestRequestCreate, TestRequestOut,
    TestResultCreate, TestResultOut,
    MQVerificationCreate, MQVerificationOut,
)

router = APIRouter(prefix="/tests", tags=["测试实验"])


# ═══════════════ helpers ═══════════════

def _gen_request_no() -> str:
    return f"TR-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def _gen_mq_no() -> str:
    return f"MQ-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


def validate_transition(current: str, target: str) -> None:
    """校验状态转换是否合法，非法则抛出 HTTPException"""
    valid_targets = _VALID_TRANSITIONS.get(current)
    if valid_targets is None:
        raise HTTPException(status_code=400, detail=f"未知当前状态: {current}")
    if target not in valid_targets:
        raise HTTPException(
            status_code=400,
            detail=f"非法状态转换: {current} → {target}，允许的目标状态: {'、'.join(valid_targets) if valid_targets else '无'}"
        )


def _create_test_ng_alert(test: TestRequest, db: Session) -> None:
    """当测试完成且不合格项>0时，自动创建test_ng预警记录"""
    alert = Alert(
        target_type="test",
        target_id=test.id,
        title=f"测试不合格: {test.title}",
        level=2,
        alert_type="test_ng",
        message=f"测试 [{test.request_no}] {test.title} 已完成，不合格项数: {test.ng_count}",
    )
    db.add(alert)


# ═══════════════ 测试申请 ═══════════════

@router.get("", response_model=list[TestRequestOut])
def list_tests(
    product_code: str = Query("", description="产品编码"),
    project_code: str = Query("", description="项目编号"),
    test_type: str = Query("", description="测试类型"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    q = db.query(TestRequest)
    if product_code:
        q = q.filter(TestRequest.product_code == product_code)
    if project_code:
        q = q.filter(TestRequest.project_code == project_code)
    if test_type:
        q = q.filter(TestRequest.test_type == test_type)
    if status:
        q = q.filter(TestRequest.status == status)
    return q.order_by(TestRequest.created_at.desc()).all()


@router.post("", response_model=TestRequestOut)
def create_test(
    data: TestRequestCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "systems_engineer", "quality_engineer")),
):
    req = TestRequest(**data.model_dump(), request_no=_gen_request_no())
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/{rid}", response_model=TestRequestOut)
def get_test(rid: int, db: Session = Depends(get_db), _=Depends(require_menu("tests"))):
    r = db.query(TestRequest).filter(TestRequest.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="测试申请不存在")
    return r


@router.patch("/{rid}")
def update_test(
    rid: int,
    status: str = Query("", description="目标状态"),
    result_summary: str = Query("", description="结果摘要"),
    ng_count: int = Query(None, description="不合格项数"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "systems_engineer", "quality_engineer")),
):
    r = db.query(TestRequest).filter(TestRequest.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="测试申请不存在")
    old_status = r.status
    if status:
        validate_transition(old_status, status)
        r.status = status
        if status == "done":
            r.completed_date = date.today()
        elif status == "testing":
            r.updated_at = datetime.now(timezone.utc)
    if result_summary:
        r.result_summary = result_summary
    if ng_count is not None:
        r.ng_count = ng_count
    # 当状态变为done且ng_count>0时，自动创建test_ng预警记录
    if status == "done" and old_status != "done" and r.ng_count > 0:
        _create_test_ng_alert(r, db)
    r.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    return {"ok": True, "status": r.status, "ng_count": r.ng_count}


@router.post("/{rid}/results", response_model=TestResultOut)
def add_test_result(
    rid: int,
    data: TestResultCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "systems_engineer", "quality_engineer")),
):
    tr = db.query(TestRequest).filter(TestRequest.id == rid).first()
    if not tr:
        raise HTTPException(status_code=404, detail="测试申请不存在")

    result = TestResult(
        test_request_id=rid,
        **data.model_dump(),
        tested_at=datetime.now(timezone.utc),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


# ═══════════════ MQ验证 ═══════════════

@router.get("/mq", response_model=list[MQVerificationOut])
def list_mq(
    product_code: str = Query("", description="产品编码"),
    status: str = Query("", description="状态"),
    db: Session = Depends(get_db),
    _=Depends(require_menu("tests")),
):
    q = db.query(MQVerification)
    if product_code:
        q = q.filter(MQVerification.product_code == product_code)
    if status:
        q = q.filter(MQVerification.status == status)
    return q.order_by(MQVerification.created_at.desc()).all()


@router.post("/mq", response_model=MQVerificationOut)
def create_mq(
    data: MQVerificationCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "systems_engineer", "quality_engineer")),
):
    mq = MQVerification(**data.model_dump())
    db.add(mq)
    db.commit()
    db.refresh(mq)
    return mq


@router.patch("/mq/{mid}")
def update_mq(
    mid: int,
    status: str = Query("", description="目标状态"),
    pass_items: int = Query(None, description="通过项数"),
    fail_items: int = Query(None, description="失败项数"),
    result_report: str = Query("", description="结果报告"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "general_manager", "rd_director", "systems_engineer", "quality_engineer")),
):
    mq = db.query(MQVerification).filter(MQVerification.id == mid).first()
    if not mq:
        raise HTTPException(status_code=404, detail="MQ验证记录不存在")
    if status:
        mq.status = status
        if status in ("pass", "fail"):
            mq.verified_at = date.today()
    if pass_items is not None:
        mq.pass_items = pass_items
    if fail_items is not None:
        mq.fail_items = fail_items
    if result_report:
        mq.result_report = result_report
    db.commit()
    db.refresh(mq)
    return {"ok": True, "status": mq.status, "pass_items": mq.pass_items, "fail_items": mq.fail_items}
