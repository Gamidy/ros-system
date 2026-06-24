"""PM 配置查询API — 配件默认 & 功能默认"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.pm_accessory import AccessoryDefault  # BUGFIX: removed FeatureDefault import (route moved to pm_config.py)

router = APIRouter(prefix="/pm", tags=["PM配置查询"])


def _require_auth(current_user: User = Depends(get_current_user)) -> User:
    """认证校验 — 需要登录用户"""
    return current_user


@router.get("/accessory-defaults")
def get_accessory_defaults(
    market: str = Query(..., description="目标市场，如'通用'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
):
    """获取指定市场的配件默认列表"""
    items = (
        db.query(AccessoryDefault)
        .filter(AccessoryDefault.market == market)
        .order_by(AccessoryDefault.sort_order, AccessoryDefault.id)
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


# ══════════════════════════════════════════════════════════════
# /feature-defaults 路由已移入 pm_config.py 以避免路由冲突
# BUGFIX: 删除本文件的重复注册，由 pm_config.py 统一提供
# ══════════════════════════════════════════════════════════════
