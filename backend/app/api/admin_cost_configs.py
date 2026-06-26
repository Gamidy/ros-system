"""成本配置管理API — 能力段单价/间接成本/试制数量 — 仅admin可操作"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.capacity_unit_cost import CapacityUnitCost
from app.models.indirect_cost_config import IndirectCostConfig
from app.models.trial_qty_config import TrialQtyConfig

router = APIRouter(prefix="/api/admin", tags=["admin-cost-configs"])


# ── Request/Response Schemas ──────────────────────────────────────────

class CapacityUnitCostItem(BaseModel):
    """能力段单价条目"""
    capacity_key: str = Field(..., description="冷量段标识, 如'22K'")
    btu: int = Field(..., description="BTU值, 如22000")
    unit_cost_w: float = Field(..., description="单价(万元), 如0.178")


class CapacityUnitCostOut(BaseModel):
    id: int
    capacity_key: str
    btu: int
    unit_cost_w: float

    class Config:
        from_attributes = True


class IndirectCostUpdate(BaseModel):
    """间接成本更新请求"""
    key: str = Field("default", description="配置键, 如'default'")
    amount: float = Field(..., description="金额(元)")
    description: Optional[str] = Field(None, description="说明")


class IndirectCostOut(BaseModel):
    id: int
    key: str
    amount: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class TrialQtyConfigItem(BaseModel):
    """试制数量配置条目"""
    project_class: str = Field(..., description="项目等级: T/A/B/C")
    trial_qty: int = Field(..., description="试制数量")
    remark: Optional[str] = Field(None, description="备注说明")


class TrialQtyConfigOut(BaseModel):
    id: int
    project_class: str
    trial_qty: int
    remark: Optional[str] = None

    class Config:
        from_attributes = True


# ── Capacity Unit Cost Routes ────────────────────────────────────────

@router.get("/capacity-unit-costs", response_model=List[CapacityUnitCostOut])
def list_capacity_unit_costs(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> list:
    """查询所有能力段单价"""
    return db.query(CapacityUnitCost).order_by(CapacityUnitCost.btu).all()


@router.put("/capacity-unit-costs")
def batch_update_capacity_unit_costs(
    data: List[CapacityUnitCostItem],
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """批量更新能力段单价 — 先清空再全量插入"""
    # 清空旧数据
    db.query(CapacityUnitCost).delete()
    # 批量插入
    created = []
    for item in data:
        cost = CapacityUnitCost(
            capacity_key=item.capacity_key,
            btu=item.btu,
            unit_cost_w=item.unit_cost_w,
        )
        db.add(cost)
        created.append(cost)
    db.commit()
    return {"ok": True, "count": len(created)}


# ── Indirect Cost Route ──────────────────────────────────────────────

@router.get("/indirect-cost/current", response_model=IndirectCostOut)
def get_current_indirect_cost(
    db: Session = Depends(get_db),
) -> dict:
    """查询当前间接成本配置（默认key='default'）"""
    cost = db.query(IndirectCostConfig).filter(
        IndirectCostConfig.key == "default"
    ).first()
    if not cost:
        return IndirectCostOut(id=0, key="default", amount=0, description=None)
    return cost


@router.post("/indirect-cost")
def update_indirect_cost(
    data: IndirectCostUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """创建或更新间接成本配置（upsert by key）"""
    existing = db.query(IndirectCostConfig).filter(
        IndirectCostConfig.key == data.key
    ).first()
    if existing:
        existing.amount = data.amount
        if data.description is not None:
            existing.description = data.description
    else:
        existing = IndirectCostConfig(
            key=data.key,
            amount=data.amount,
            description=data.description,
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return {"ok": True, "key": existing.key, "amount": existing.amount}


# ── Trial Qty Config Route ───────────────────────────────────────────

@router.put("/trial-qty-configs")
def batch_update_trial_qty_configs(
    data: List[TrialQtyConfigItem],
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """批量更新试制数量配置 — 先清空再全量插入"""
    # 清空旧数据
    db.query(TrialQtyConfig).delete()
    # 批量插入
    created = []
    for item in data:
        config = TrialQtyConfig(
            project_class=item.project_class,
            trial_qty=item.trial_qty,
            remark=item.remark,
        )
        db.add(config)
        created.append(config)
    db.commit()
    return {"ok": True, "count": len(created)}
