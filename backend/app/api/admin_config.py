"""系统配置API — 仅管理员可访问"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.system_config import SystemConfig
from app.core.security import get_current_user

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])

# 默认配置
DEFAULTS = {
    "proto_unit_cost": '{"7K":0.075,"9K":0.095,"12K":0.105,"18K":0.142,"24K":0.178}',
    "test_unit_price": "0.11",
    "mfg_cost_threshold": '[{"max_kw":12,"cost":50},{"max_kw":999,"cost":60}]',
    "cert_cost": '{"UL":20,"CE":3,"default":3}',
}


def _require_admin(user):
    if user.get("role") != "admin":
        raise HTTPException(403, "仅管理员可操作")


def _get_config_dict(db: Session) -> dict:
    """获取所有配置的字典"""
    rows = db.query(SystemConfig).all()
    config = dict(DEFAULTS)
    for r in rows:
        config[r.key] = r.value
    return config


@router.get("")
def get_config(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取系统配置（所有登录用户可读，修改需admin）"""
    return {"data": _get_config_dict(db)}


@router.put("")
def update_config(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新单个配置项（仅admin）"""
    _require_admin(user)
    if key not in DEFAULTS:
        raise HTTPException(400, f"未知配置项: {key}")

    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
    else:
        row = SystemConfig(key=key, value=value)
        db.add(row)
    db.commit()
    return {"ok": True, "key": key}


@router.put("/batch")
def update_config_batch(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """批量更新配置（仅admin）"""
    _require_admin(user)
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            row.value = str(value)
        else:
            row = SystemConfig(key=key, value=str(value))
            db.add(row)
    db.commit()
    return {"ok": True}
