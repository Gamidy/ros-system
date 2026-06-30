"""市场管理 API — Market CRUD + 能效等级管理"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pm", tags=["市场管理"])


# ── Pydantic Schemas ──────────────────────────────────────────────

class MarketCreate(BaseModel):
    """新增市场请求"""
    code: str = Field(..., min_length=1, max_length=20, description="市场代码")
    name: str = Field("", max_length=100, description="市场名称")
    region: str = Field(..., max_length=50, description="区域")
    energy_standard: str = Field("eer", max_length=20, description="能效标准代码")
    energy_label: str = Field("EER", max_length=20, description="能效显示名")
    energy_unit: str = Field("", max_length=20, description="能效单位")
    energy_standard_detail: Optional[str] = Field(None, max_length=100, description="能效标准细分")
    national_standard: Optional[str] = Field(None, max_length=100, description="国家标准编号")
    voltage_freq: str = Field(..., max_length=50, description="电压/频率")
    cooling_max_temp: float = Field(..., description="制冷最高环境温度")
    heating_min_temp: float = Field(..., description="制热最低环境温度")
    structure_type: str = Field(..., max_length=100, description="机型结构")
    main_selling_model: Optional[str] = Field(None, max_length=200, description="主销机型")
    refrigerant: str = Field(..., max_length=50, description="主要制冷剂")
    refrigerant_charge: Optional[float] = Field(None, description="制冷剂灌注量")
    min_voltage: int = Field(..., description="最低电压要求")
    is_active: str = Field("true", max_length=5, description="是否激活")


class MarketUpdate(BaseModel):
    """更新市场请求（全部可选）"""
    name: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=50)
    energy_standard: Optional[str] = Field(None, max_length=20)
    energy_label: Optional[str] = Field(None, max_length=20)
    energy_unit: Optional[str] = Field(None, max_length=20)
    energy_standard_detail: Optional[str] = Field(None, max_length=100)
    national_standard: Optional[str] = Field(None, max_length=100)
    voltage_freq: Optional[str] = Field(None, max_length=50)
    cooling_max_temp: Optional[float] = Field(None)
    heating_min_temp: Optional[float] = Field(None)
    structure_type: Optional[str] = Field(None, max_length=100)
    main_selling_model: Optional[str] = Field(None, max_length=200)
    refrigerant: Optional[str] = Field(None, max_length=50)
    refrigerant_charge: Optional[float] = Field(None)
    min_voltage: Optional[int] = Field(None)
    is_active: Optional[str] = Field(None, max_length=5)


class EnergyLevelCreate(BaseModel):
    """新增能效等级请求"""
    level_name: str = Field(..., max_length=50, description="等级名称")
    sort_order: int = Field(0, description="排序")
    seer_min: Optional[float] = Field(None, description="最低SEER")
    eer_min: Optional[float] = Field(None, description="最低EER")
    cspf_min: Optional[float] = Field(None, description="最低CSPF")
    is_primary: str = Field("false", max_length=5, description="是否主销等级")


class EnergyLevelUpdate(BaseModel):
    """更新能效等级请求（全部可选）"""
    level_name: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = Field(None)
    seer_min: Optional[float] = Field(None)
    eer_min: Optional[float] = Field(None)
    cspf_min: Optional[float] = Field(None)
    is_primary: Optional[str] = Field(None, max_length=5)


# ── 辅助函数 ──────────────────────────────────────────────────────

def _get_market_code(market_name: str, db: Session) -> str:
    """市场名称 → 市场代码（用于 market_param_configs 查询）"""
    from app.models.product import Market
    try:
        m = db.query(Market).filter(Market.name == market_name).first()
        if m:
            return m.code
    except Exception:
        pass
    NAME_TO_CODE = {
        "欧盟": "EU", "越南": "VN", "印度尼西亚": "ID", "马来西亚": "MY",
        "巴基斯坦": "PK", "乌兹别克斯坦": "UZ", "吉尔吉斯斯坦": "KG",
        "塔吉克斯坦": "TJ", "沙特": "SA", "阿联酋": "AE", "科威特": "KW",
        "巴林": "BH", "以色列": "IL", "伊朗": "IR", "伊拉克": "IQ",
        "美国": "US", "加拿大": "CA", "墨西哥": "MX", "哥伦比亚": "CO",
        "巴西": "BR", "阿根廷": "AR", "俄罗斯": "RU", "白俄罗斯": "BY",
        "乌克兰": "UA", "英国": "GB", "意大利": "IT", "阿塞拜疆": "AZ",
        "南非": "ZA", "阿尔及利亚": "DZ", "尼日利亚": "NG",
        "加纳": "GH", "澳大利亚": "AU",
    }
    return NAME_TO_CODE.get(market_name, "")


# ── 市场列表查询 ──────────────────────────────────────────────────

@router.get("/markets")
def list_markets_with_standards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """返回所有激活的市场列表（含能效标准），用于前端下拉"""
    from app.models.product import Market
    items = db.query(Market).filter(
        Market.is_active == 'true',
        Market.energy_standard.isnot(None),
        Market.energy_standard != '',
    ).order_by(Market.region, Market.code).all()
    return [
        {
            "code": m.code,
            "name": m.name,
            "region": m.region,
            "energy_standard": m.energy_standard or "eer",
            "energy_label": m.energy_label or "EER",
            "energy_unit": m.energy_unit or "",
            "energy_standard_detail": m.energy_standard_detail,
            "national_standard": m.national_standard,
            "voltage_freq": m.voltage_freq,
            "cooling_max_temp": m.cooling_max_temp,
            "heating_min_temp": m.heating_min_temp,
            "structure_type": m.structure_type,
            "main_selling_model": m.main_selling_model,
            "refrigerant": m.refrigerant,
            "refrigerant_charge": m.refrigerant_charge,
            "min_voltage": m.min_voltage,
        }
        for m in items
    ]


@router.get("/markets/all")
def list_all_markets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """返回全部市场（含激活和停用的），PM管理用"""
    from app.models.product import Market
    items = db.query(Market).order_by(Market.region, Market.code).all()
    return [
        {
            "code": m.code,
            "name": m.name,
            "region": m.region or "",
            "energy_standard": m.energy_standard or "",
            "energy_label": m.energy_label or "",
            "energy_unit": m.energy_unit or "",
            "energy_standard_detail": m.energy_standard_detail,
            "national_standard": m.national_standard,
            "voltage_freq": m.voltage_freq,
            "cooling_max_temp": m.cooling_max_temp,
            "heating_min_temp": m.heating_min_temp,
            "structure_type": m.structure_type,
            "main_selling_model": m.main_selling_model,
            "refrigerant": m.refrigerant,
            "refrigerant_charge": m.refrigerant_charge,
            "min_voltage": m.min_voltage,
            "is_active": m.is_active or "true",
        }
        for m in items
    ]


# ── Market CRUD ───────────────────────────────────────────────────

@router.post("/markets")
def create_market(
    data: MarketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增市场"""
    from app.models.product import Market

    # ── 必填字段校验 ──
    errors = []
    if not data.code or not data.code.strip():
        errors.append("市场代码不能为空")
    if not data.name or not data.name.strip():
        errors.append("国家/市场名称不能为空")
    if not data.region or not data.region.strip():
        errors.append("区域不能为空")
    if not data.energy_standard or not data.energy_standard.strip():
        errors.append("能效标准代码不能为空")
    if not data.energy_label or not data.energy_label.strip():
        errors.append("能效显示名称不能为空")
    if not data.energy_unit or not data.energy_unit.strip():
        errors.append("能效单位不能为空")
    if not data.structure_type or not data.structure_type.strip():
        errors.append("机型结构不能为空")
    if not data.refrigerant or not data.refrigerant.strip():
        errors.append("主要制冷剂不能为空")
    if not data.voltage_freq or not data.voltage_freq.strip():
        errors.append("电压/频率不能为空")
    if data.min_voltage is None:
        errors.append("最低电压要求不能为空")
    if data.cooling_max_temp is None:
        errors.append("制冷最高环境温度不能为空")
    if data.heating_min_temp is None:
        errors.append("制热最低环境温度不能为空")
    if errors:
        raise HTTPException(status_code=422, detail="；".join(errors))

    code = data.code.strip().upper()
    existing = db.query(Market).filter(Market.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"市场代码 {code} 已存在")
    m = Market(
        code=code,
        name=data.name or code,
        region=data.region,
        energy_standard=data.energy_standard or "eer",
        energy_label=data.energy_label or "EER",
        energy_unit=data.energy_unit,
        energy_standard_detail=data.energy_standard_detail,
        national_standard=data.national_standard,
        voltage_freq=data.voltage_freq,
        cooling_max_temp=data.cooling_max_temp,
        heating_min_temp=data.heating_min_temp,
        structure_type=data.structure_type,
        main_selling_model=data.main_selling_model,
        refrigerant=data.refrigerant,
        refrigerant_charge=data.refrigerant_charge,
        min_voltage=data.min_voltage,
        is_active=data.is_active or "true",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"message": "新增成功", "code": m.code, "name": m.name}


@router.put("/markets/{code}")
def update_market(
    code: str,
    data: MarketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新市场信息"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    update_data = data.model_dump(exclude_unset=True)
    # ── 必填字段校验（当传入空值时拒绝） ──
    errors = []
    if "structure_type" in update_data and (not update_data["structure_type"] or not str(update_data["structure_type"]).strip()):
        errors.append("机型结构不能为空")
    if "refrigerant" in update_data and (not update_data["refrigerant"] or not str(update_data["refrigerant"]).strip()):
        errors.append("主要制冷剂不能为空")
    if errors:
        raise HTTPException(status_code=422, detail="；".join(errors))
    for key, val in update_data.items():
        setattr(m, key, val)
    db.commit()
    return {"message": "更新成功", "code": m.code, "name": m.name}


@router.delete("/markets/{code}")
def delete_market(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除市场"""
    from app.models.product import Market
    m = db.query(Market).filter(Market.code == code).first()
    if not m:
        raise HTTPException(status_code=404, detail="市场不存在")
    from app.models.pm_config import MarketCertification, MarketCompressor
    from app.models.competitor import CompetitorModel
    cert_count = db.query(MarketCertification).filter(MarketCertification.market_code == code).count()
    comp_count = db.query(MarketCompressor).filter(MarketCompressor.market_code == code).count()
    comp_model_count = db.query(CompetitorModel).filter(CompetitorModel.market == m.name).count()
    if cert_count > 0 or comp_count > 0 or comp_model_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该市场有 {cert_count} 条认证要求、{comp_count} 条压缩机信息、{comp_model_count} 条竞品数据，请先删除子记录"
        )
    db.delete(m)
    db.commit()
    return {"message": "已删除"}


# ── 能效等级 CRUD ────────────────────────────────────────────────

@router.get("/markets/{code}/energy-levels")
def list_energy_levels(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> list:
    """获取市场能效等级列表"""
    from app.models.product import MarketEnergyLevel
    items = db.query(MarketEnergyLevel).filter(
        MarketEnergyLevel.market_code == code
    ).order_by(MarketEnergyLevel.sort_order).all()
    return [
        {
            "id": e.id,
            "market_code": e.market_code,
            "level_name": e.level_name,
            "sort_order": e.sort_order,
            "seer_min": e.seer_min,
            "eer_min": e.eer_min,
            "cspf_min": e.cspf_min,
            "is_primary": e.is_primary,
        }
        for e in items
    ]


@router.post("/markets/{code}/energy-levels")
def create_energy_level(
    code: str,
    data: EnergyLevelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """新增能效等级"""
    from app.models.product import Market, MarketEnergyLevel
    market = db.query(Market).filter(Market.code == code).first()
    if not market:
        raise HTTPException(status_code=404, detail="市场不存在")
    e = MarketEnergyLevel(
        market_code=code,
        level_name=data.level_name,
        sort_order=data.sort_order,
        seer_min=data.seer_min,
        eer_min=data.eer_min,
        cspf_min=data.cspf_min,
        is_primary=data.is_primary or "false",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"message": "新增成功", "id": e.id}


@router.put("/markets/{code}/energy-levels/{level_id}")
def update_energy_level(
    code: str,
    level_id: int,
    data: EnergyLevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """更新能效等级"""
    from app.models.product import MarketEnergyLevel
    e = db.query(MarketEnergyLevel).filter(
        MarketEnergyLevel.id == level_id,
        MarketEnergyLevel.market_code == code,
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="能效等级不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(e, key, val)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/markets/{code}/energy-levels/{level_id}")
def delete_energy_level(
    code: str,
    level_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_role("admin", "product_manager")),
) -> dict:
    """删除能效等级"""
    from app.models.product import MarketEnergyLevel
    e = db.query(MarketEnergyLevel).filter(
        MarketEnergyLevel.id == level_id,
        MarketEnergyLevel.market_code == code,
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="能效等级不存在")
    db.delete(e)
    db.commit()
    return {"message": "删除成功"}
