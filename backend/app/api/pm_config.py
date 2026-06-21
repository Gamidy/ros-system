"""PM 配置查询API — 安规标准 & 性能默认参数"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.pm_config import CertStandard, PerfDefault
from app.models.pm_accessory import FeatureDefault

router = APIRouter(prefix="/pm", tags=["PM配置查询"])


def _require_auth(current_user: User = Depends(get_current_user)) -> User:
    """认证校验 — 需要登录用户"""
    return current_user


@router.get("/cert-standards")
def get_cert_standards(
    market: str = Query(..., description="目标市场，如越南、通用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
):
    """获取指定市场的安规标准列表"""
    items = (
        db.query(CertStandard)
        .filter(CertStandard.market == market)
        .order_by(CertStandard.sort_order, CertStandard.id)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "market": item.market,
                "standard": item.standard,
                "key_requirement": item.key_requirement,
                "verification_method": item.verification_method,
                "cert_cycle": item.cert_cycle,
                "sort_order": item.sort_order,
            }
            for item in items
        ]
    }


@router.get("/perf-defaults")
def get_perf_defaults(
    market: str = Query(..., description="目标市场，如越南、通用"),
    capacity: str = Query(None, description="冷量段，如07K、09K、12K、18K、24K"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
):
    """获取指定市场+冷量段的性能默认参数（capacity可选）"""
    query = db.query(PerfDefault).filter(PerfDefault.market == market)
    if capacity:
        query = query.filter(PerfDefault.capacity_range == capacity)
    items = query.order_by(PerfDefault.sort_order, PerfDefault.id).all()
    return {
        "items": [
            {
                "id": item.id,
                "capacity_range": item.capacity_range,
                "market": item.market,
                "param_name": item.param_name,
                "target_value": item.target_value,
                "aux_competitor": item.aux_competitor,
                "tcl_competitor": item.tcl_competitor,
                "sort_order": item.sort_order,
            }
            for item in items
        ]
    }


@router.get("/feature-defaults")
def get_feature_defaults(
    market: str = Query(..., description="目标市场，如越南、泰国、印尼、中东"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
):
    """获取指定市场的功能默认配置"""
    items = (
        db.query(FeatureDefault)
        .filter(FeatureDefault.market == market)
        .order_by(FeatureDefault.sort_order, FeatureDefault.id)
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "market": item.market,
                "name": item.name,
                "default_selection": item.default_selection,
                "sort_order": item.sort_order,
            }
            for item in items
        ]
    }
