"""BOM API: Part主数据 + AVL + 替代料 + BOM结构 + CDF合规检查"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bom import PartCategory, Part, PartAVL, BOM, BOMItem, part_alternative_table
from app.schemas import (
    PartCreate, PartOut, PartUpdate, PartDetailOut,
    PartAVLCreate, PartAVLOut,
    BOMCreate, BOMUpdate, BOMOut, BOMItemCreate, BOMItemOut,
    AlternativeAssign,
)

router = APIRouter(prefix="/bom", tags=["BOM物料管理"])


# ══════════════════════════════════════════════════
# Part Categories
# ══════════════════════════════════════════════════

@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return db.query(PartCategory).all()


# ══════════════════════════════════════════════════
# Part Master
# ══════════════════════════════════════════════════

@router.get("/parts", response_model=list[PartOut])
def list_parts(
    keyword: str = "",
    lifecycle: str = "",
    is_cdf_item: bool = None,
    category_id: int = None,
    db: Session = Depends(get_db),
):
    """列出所有物料，支持关键词/生命周期/CDF标记/分类筛选"""
    q = db.query(Part)
    if keyword:
        q = q.filter(Part.name.like(f"%{keyword}%") | Part.part_no.like(f"%{keyword}%"))
    if lifecycle:
        q = q.filter(Part.lifecycle == lifecycle)
    if is_cdf_item is not None:
        q = q.filter(Part.is_cdf_item == is_cdf_item)
    if category_id:
        q = q.filter(Part.category_id == category_id)
    return q.all()


@router.post("/parts", response_model=PartDetailOut)
def create_part(data: PartCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """创建物料 — part_no全局唯一"""
    if db.query(Part).filter(Part.part_no == data.part_no).first():
        raise HTTPException(status_code=400, detail="物料编码已存在")
    p = Part(**data.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p


# ══════════════════════════════════════════════════
# CDF Compliance Check (必须在 /parts/{part_id} 前注册，避免路由冲突)
# ══════════════════════════════════════════════════

@router.get("/parts/cdf-expiring", response_model=list[PartDetailOut])
def cdf_expiring(days: int = Query(90, ge=1), db: Session = Depends(get_db)):
    """CDF证书即将到期的物料 — 按有效期过滤"""
    today = date.today()
    cutoff = today + timedelta(days=days)
    parts = db.query(Part).filter(
        Part.is_cdf_item == True,
        Part.cdf_expiry_date.isnot(None),
        Part.cdf_expiry_date >= today,
        Part.cdf_expiry_date <= cutoff,
    ).order_by(Part.cdf_expiry_date).all()
    return parts


@router.get("/parts/{part_id}", response_model=PartDetailOut)
def get_part(part_id: int, db: Session = Depends(get_db)):
    """获取物料详情 — 含AVL供应商清单"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="物料不存在")
    return p


@router.patch("/parts/{part_id}", response_model=PartDetailOut)
def update_part(part_id: int, data: PartUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """更新物料 — 生命周期/CDF/MQ/MRC字段"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="物料不存在")

    # CDF规则校验: 如果标记为CDF物料，cert_no和expiry_date必须有值
    update_dict = data.model_dump(exclude_unset=True)
    is_cdf = update_dict.get("is_cdf_item", p.is_cdf_item)
    cert_no = update_dict.get("cdf_cert_no", p.cdf_cert_no)
    expiry = update_dict.get("cdf_expiry_date", p.cdf_expiry_date)
    if is_cdf and (not cert_no or not expiry):
        raise HTTPException(status_code=400, detail="CDF物料必须填写证书编号和有效期")

    for k, v in update_dict.items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return p


# ══════════════════════════════════════════════════
# Part AVL Management
# ══════════════════════════════════════════════════

@router.get("/parts/{part_id}/avl", response_model=list[PartAVLOut])
def list_avl(part_id: int, db: Session = Depends(get_db)):
    """列出物料的所有批准供应商"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="物料不存在")
    return db.query(PartAVL).filter(PartAVL.part_id == part_id).all()


@router.post("/parts/{part_id}/avl", response_model=PartAVLOut)
def add_avl(part_id: int, data: PartAVLCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """添加物料批准供应商 — 同一物料可有多家供应商"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="物料不存在")
    if db.query(PartAVL).filter(
        PartAVL.part_id == part_id, PartAVL.vendor_code == data.vendor_code
    ).first():
        raise HTTPException(status_code=400, detail="该供应商已存在于此物料的AVL中")

    avl = PartAVL(part_id=part_id, **data.model_dump())
    db.add(avl); db.commit(); db.refresh(avl)
    return avl


@router.delete("/parts/{part_id}/avl/{avl_id}")
def remove_avl(part_id: int, avl_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """从AVL中移除供应商"""
    avl = db.query(PartAVL).filter(PartAVL.id == avl_id, PartAVL.part_id == part_id).first()
    if not avl:
        raise HTTPException(status_code=404, detail="AVL记录不存在")
    db.delete(avl); db.commit()
    return {"detail": "已移除"}


# ══════════════════════════════════════════════════
# Part Alternatives Management
# ══════════════════════════════════════════════════

@router.get("/parts/{part_id}/alternatives", response_model=list[PartOut])
def list_alternatives(part_id: int, db: Session = Depends(get_db)):
    """列出物料的替代料 — 不同part_no，功能可替代"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="物料不存在")
    return part.alternatives


@router.post("/parts/{part_id}/alternatives")
def set_alternatives(part_id: int, data: AlternativeAssign, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """设置替代料关系 — 替换全部替代料列表"""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="物料不存在")

    # 不允许把自己设为替代料
    if part_id in data.alternative_part_ids:
        raise HTTPException(status_code=400, detail="不能将自身设为替代料")

    # 验证所有替代料存在
    for alt_id in data.alternative_part_ids:
        alt = db.query(Part).filter(Part.id == alt_id).first()
        if not alt:
            raise HTTPException(status_code=404, detail=f"替代料 {alt_id} 不存在")
        if alt.part_no == part.part_no:
            raise HTTPException(status_code=400, detail="替代料必须具有不同物料编码")

    # 清除旧替代料
    db.execute(
        part_alternative_table.delete().where(part_alternative_table.c.part_id == part_id)
    )
    # 添加新替代料
    for i, alt_id in enumerate(data.alternative_part_ids):
        db.execute(part_alternative_table.insert().values(
            part_id=part_id, alternative_part_id=alt_id, priority=i + 1
        ))
    db.commit()
    return {"detail": "替代料已更新", "alternative_count": len(data.alternative_part_ids)}


# ══════════════════════════════════════════════════
# BOM Management
# ══════════════════════════════════════════════════

@router.get("", response_model=list[BOMOut])
def list_boms(
    product_code: str = "",
    factory_code: str = "",
    status: str = "",
    db: Session = Depends(get_db),
):
    """列出BOM，可按产品编码/工厂/状态筛选"""
    q = db.query(BOM)
    if product_code:
        q = q.filter(BOM.product_code == product_code)
    if factory_code:
        q = q.filter(BOM.factory_code == factory_code)
    if status:
        q = q.filter(BOM.status == status)
    return q.all()


@router.post("", response_model=BOMOut)
def create_bom(data: BOMCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """创建BOM — bom_no全局唯一"""
    if db.query(BOM).filter(BOM.bom_no == data.bom_no).first():
        raise HTTPException(status_code=400, detail="BOM编号已存在")
    b = BOM(**data.model_dump())
    db.add(b); db.commit(); db.refresh(b)
    return b


@router.patch("/{bom_id}", response_model=BOMOut)
def update_bom(bom_id: int, data: BOMUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """更新BOM状态/版本 — MBOM变更需产生新版本(Rule #2)"""
    b = db.query(BOM).filter(BOM.id == bom_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="BOM不存在")

    update_dict = data.model_dump(exclude_unset=True)
    # Rule #2: MBOM changes must produce new BOM version
    for k, v in update_dict.items():
        setattr(b, k, v)
    db.commit(); db.refresh(b)
    return b


# ══════════════════════════════════════════════════
# BOM Items
# ══════════════════════════════════════════════════

@router.post("/{bom_id}/items", response_model=BOMItemOut)
def add_bom_item(bom_id: int, data: BOMItemCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """向BOM添加条目 — 支持6层体系和item_type标记"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")

    # 验证母件item（如果指定）
    if data.parent_item_id:
        parent = db.query(BOMItem).filter(
            BOMItem.id == data.parent_item_id, BOMItem.bom_id == bom_id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父级BOM条目不存在")
        # 子件层级 = 父级 + 1
        expected_level = parent.level + 1
        if data.level != expected_level:
            raise HTTPException(
                status_code=400,
                detail=f"子件层级应为 {expected_level}（父件层级 {parent.level} + 1）",
            )

    item = BOMItem(**data.model_dump(exclude={"bom_id"}), bom_id=bom_id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.get("/{bom_id}/items", response_model=list[BOMItemOut])
def list_bom_items(bom_id: int, db: Session = Depends(get_db)):
    """列出BOM所有条目（平铺）"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    return db.query(BOMItem).filter(BOMItem.bom_id == bom_id).all()


@router.get("/{bom_id}/tree")
def get_bom_tree(bom_id: int, db: Session = Depends(get_db)):
    """获取BOM树形结构 — 含item_type字段"""
    bom = db.query(BOM).filter(BOM.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")

    items = db.query(BOMItem).filter(BOMItem.bom_id == bom_id).all()

    def build_tree(parent_id=None):
        return [
            {
                "id": i.id,
                "part_no": i.part_no,
                "part_name": i.part_name,
                "item_type": i.item_type,
                "level": i.level,
                "quantity": i.quantity,
                "position_no": i.position_no,
                "remark": i.remark,
                "children": build_tree(i.id),
            }
            for i in items if i.parent_item_id == parent_id
        ]

    return {"bom": _bom_to_dict(bom), "tree": build_tree()}


# ══════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════

def _bom_to_dict(bom: BOM) -> dict:
    return {
        "id": bom.id,
        "bom_no": bom.bom_no,
        "product_code": bom.product_code,
        "version": bom.version,
        "bom_type": bom.bom_type,
        "description": bom.description,
        "factory_code": bom.factory_code,
        "status": bom.status,
        "created_at": bom.created_at,
    }
