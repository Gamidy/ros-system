"""系统配置API — 仅管理员可访问"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.system_config import SystemConfig
from app.core.permissions import require_role
from app.core.security import get_current_user

router = APIRouter(prefix="/admin/config", tags=["admin-config"])

# ── 配置分类 ──
SENSITIVE_KEYS = {"proto_unit_cost", "test_unit_price", "mfg_cost_threshold", "cert_cost"}
PUBLIC_KEYS = {"product_short_names", "accessory_defaults", "feature_defaults",
               "trial_qty_per_class", "indirect_cost", "capacity_unit_cost_map"}
DEFAULTS = {
    "proto_unit_cost": '{"7K":0.075,"9K":0.095,"12K":0.105,"18K":0.142,"24K":0.178}',
    "test_unit_price": "0.11",
    "mfg_cost_threshold": '[{"max_kw":12,"cost":50},{"max_kw":999,"cost":60}]',
    "cert_cost": '{"UL":20,"CE":3,"default":3}',
    "accessory_defaults": '[{"market":"通用","name":"除尘网","default_selection":"标配"},{"market":"通用","name":"WiFi模块","default_selection":"选配"},{"market":"通用","name":"蓝牙遥控","default_selection":"选配"},{"market":"通用","name":"离子发生器","default_selection":"不配"}]',
    "feature_defaults": '[{"market":"通用","name":"自清洁","default_selection":"标配"},{"market":"通用","name":"除霜","default_selection":"标配"},{"market":"通用","name":"快速制冷","default_selection":"标配"},{"market":"通用","name":"静音模式","default_selection":"选配"},{"market":"通用","name":"ECO模式","default_selection":"选配"}]',
    "indirect_cost": "5000",
    "trial_qty_per_class": '{"T":5,"A":3,"B":2,"C":1}',
    "capacity_unit_cost_map": '{"07K":{"btu":7000,"cost":0.075},"09K":{"btu":9000,"cost":0.095},"12K":{"btu":12000,"cost":0.105},"18K":{"btu":18000,"cost":0.142},"22K":{"btu":22000,"cost":0.178},"24K":{"btu":24000,"cost":0.178}}',
    "product_short_names": '{"分体式壁挂机":"挂机","分体式柜机":"柜机"}',
}


def _get_config_dict(db: Session) -> dict:
    """获取所有配置的字典"""
    rows = db.query(SystemConfig).all()
    config = dict(DEFAULTS)
    for r in rows:
        config[r.key] = r.value
    return config


@router.get("")
def get_config(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """获取完整系统配置（仅admin）"""
    return {"data": _get_config_dict(db)}


@router.get("/public")
def get_public_config(db: Session = Depends(get_db)) -> dict:
    """获取公开系统配置（无需登录即可访问，仅返回UI渲染和计算所需的非敏感配置）"""
    full = _get_config_dict(db)
    public = {k: v for k, v in full.items() if k in PUBLIC_KEYS}
    return {"data": public}


@router.put("")
def update_config(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """更新单个配置项（仅admin）"""
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
    _=Depends(require_role("admin")),
) -> dict:
    """批量更新配置（仅admin）"""
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
