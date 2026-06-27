"""标准知识库 — PM 查询接口

提供供 PM 查询标准库的只读端点，支持分类筛选、全文搜索、最近更新概览。
路由前缀: /api/standards
"""
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.standard import (
    Standard, StandardRegion, StandardCategory,
    IMPACT_LEVELS, STANDARD_STATUSES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/standards", tags=["标准知识库"])


# ════════════════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ════════════════════════════════════════════════════════════════════════════


class StandardOut(BaseModel):
    """标准条目输出"""
    id: int
    region_id: int
    category_id: Optional[int] = None
    std_number: str
    title: str
    title_en: Optional[str] = None
    version: Optional[str] = None
    amendment: Optional[str] = None
    status: str
    effective_date: Optional[date] = None
    repeal_date: Optional[date] = None
    source_url: Optional[str] = None
    impact_level: Optional[str] = None
    impact_scope: Optional[str] = None
    region_name: str = ""
    region_code: str = ""
    category_name: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    class Config:
        from_attributes = True


class StandardPage(BaseModel):
    """标准条目分页"""
    items: list[StandardOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class RegionOut(BaseModel):
    """地区输出"""
    id: int
    code: str
    name: str
    name_en: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    """分类输出"""
    id: int
    code: str
    name: str

    class Config:
        from_attributes = True


class RecentStats(BaseModel):
    """最近更新概览统计"""
    total_active: int = 0
    new_last_7d: int = 0
    new_last_30d: int = 0
    upcoming_effective: int = 0
    by_region: list[dict] = []


# ════════════════════════════════════════════════════════════════════════════
# 端点
# ════════════════════════════════════════════════════════════════════════════


@router.get("", response_model=StandardPage)
def list_standards(
    region: Optional[str] = Query(None, description="地区代码: EU/US/SA/IEC"),
    category: Optional[str] = Query(None, description="分类代码"),
    status: Optional[str] = Query(None, description="状态: active/superseded/draft/repealed"),
    impact: Optional[str] = Query(None, description="影响等级: critical/high/medium/low"),
    search: Optional[str] = Query(None, description="全文搜索（标准编号+标题）"),
    date_from: Optional[date] = Query(None, description="生效日期起"),
    date_to: Optional[date] = Query(None, description="生效日期止"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StandardPage:
    """标准列表查询（多条件筛选 + 全文搜索 + 分页）"""
    # ── 参数校验 ──
    if status and status not in STANDARD_STATUSES:
        from fastapi import HTTPException as _HE
        raise _HE(400, detail=f"无效状态: {status}，可选: {STANDARD_STATUSES}")

    # ── 构建筛选条件 ──
    from sqlalchemy import select, func as _func
    base_query = select(Standard)

    if region:
        base_query = base_query.join(StandardRegion).where(StandardRegion.code == region.upper())
    if category:
        base_query = base_query.join(StandardCategory).where(StandardCategory.code == category)

    filters = []
    if status:
        filters.append(Standard.status == status)
    if impact and impact in IMPACT_LEVELS:
        filters.append(Standard.impact_level == impact)
    if search:
        kw = f"%{search}%"
        filters.append(
            Standard.std_number.ilike(kw)
            | Standard.title.ilike(kw)
            | Standard.title_en.ilike(kw)
        )
    if date_from:
        filters.append(Standard.effective_date >= date_from)
    if date_to:
        filters.append(Standard.effective_date <= date_to)

    if filters:
        base_query = base_query.where(*filters)

    # ── 计数（独立查询避免 joinedload 干扰） ──
    count_query = select(_func.count()).select_from(base_query.subquery())
    total = db.execute(count_query).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    # ── 分页主查询（使用 select + joinedload 避免冲突） ──
    main_query = (
        base_query.add_columns(
            StandardRegion, StandardCategory,
        )
        .outerjoin(StandardRegion, Standard.region_id == StandardRegion.id)
        .outerjoin(StandardCategory, Standard.category_id == StandardCategory.id)
        .order_by(Standard.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(main_query).unique().all()
    items = [_row_to_out(r) for r in rows]

    return StandardPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{standard_id}", response_model=StandardOut)
def get_standard(
    standard_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StandardOut:
    """标准详情"""
    std = (
        db.query(Standard)
        .options(joinedload(Standard.region), joinedload(Standard.category))
        .filter(Standard.id == standard_id)
        .first()
    )
    if not std:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="标准条目不存在")
    return _to_out(std)


@router.get("/recent")
def get_recent_standards(
    days: int = Query(7, ge=1, le=90, description="最近 N 天"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """最近 N 天新增/更新的标准列表（用于首页快速查看）"""
    since = date.today() - timedelta(days=days)
    items = (
        db.query(Standard)
        .options(joinedload(Standard.region), joinedload(Standard.category))
        .filter(Standard.updated_at >= since)
        .order_by(Standard.updated_at.desc())
        .limit(20)
        .all()
    )
    return {"items": [_to_out(s) for s in items], "days": days}


@router.get("/stats", response_model=RecentStats)
def get_standard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecentStats:
    """标准库概览统计"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    total_active = db.query(Standard).filter(Standard.status == "active").count()
    new_last_7d = db.query(Standard).filter(Standard.created_at >= week_ago).count()
    new_last_30d = db.query(Standard).filter(Standard.created_at >= month_ago).count()
    upcoming = (
        db.query(Standard)
        .filter(Standard.status == "active", Standard.effective_date >= today)
        .count()
    )

    # 按地区统计
    region_counts = (
        db.query(
            StandardRegion.code,
            StandardRegion.name,
            func.count(Standard.id).label("count"),
        )
        .join(Standard, Standard.region_id == StandardRegion.id)
        .group_by(StandardRegion.id)
        .all()
    )

    return RecentStats(
        total_active=total_active,
        new_last_7d=new_last_7d,
        new_last_30d=new_last_30d,
        upcoming_effective=upcoming,
        by_region=[
            {"code": r.code, "name": r.name, "count": r.count}
            for r in region_counts
        ],
    )


@router.get("/regions", response_model=list[RegionOut])
def list_regions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StandardRegion]:
    """地区/机构列表（用于前端筛选下拉）"""
    return db.query(StandardRegion).order_by(StandardRegion.sort_order).all()


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StandardCategory]:
    """分类列表（用于前端筛选下拉）"""
    return db.query(StandardCategory).order_by(StandardCategory.sort_order).all()


# ════════════════════════════════════════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════════════════════════════════════════


def _row_to_out(row) -> StandardOut:
    """select 查询结果行 → Pydantic Out Schema"""
    std: Standard = row[0] if isinstance(row, (list, tuple)) else row
    region = getattr(row, 'StandardRegion', None) if not isinstance(row, (list, tuple)) else \
        row[1] if len(row) > 1 else None
    category = getattr(row, 'StandardCategory', None) if not isinstance(row, (list, tuple)) else \
        row[2] if len(row) > 2 else None

    return StandardOut(
        id=std.id,
        region_id=std.region_id,
        category_id=std.category_id,
        std_number=std.std_number,
        title=std.title,
        title_en=std.title_en,
        version=std.version,
        amendment=std.amendment,
        status=std.status,
        effective_date=std.effective_date,
        repeal_date=std.repeal_date,
        source_url=std.source_url,
        impact_level=std.impact_level,
        impact_scope=std.impact_scope,
        region_name=region.name if region else "",
        region_code=region.code if region else "",
        category_name=category.name if category else None,
        created_at=std.created_at.date() if std.created_at else None,
        updated_at=std.updated_at.date() if std.updated_at else None,
    )


def _to_out(std: Standard) -> StandardOut:
    """ORM → Pydantic Out Schema"""
    return StandardOut(
        id=std.id,
        region_id=std.region_id,
        category_id=std.category_id,
        std_number=std.std_number,
        title=std.title,
        title_en=std.title_en,
        version=std.version,
        amendment=std.amendment,
        status=std.status,
        effective_date=std.effective_date,
        repeal_date=std.repeal_date,
        source_url=std.source_url,
        impact_level=std.impact_level,
        impact_scope=std.impact_scope,
        region_name=std.region.name if std.region else "",
        region_code=std.region.code if std.region else "",
        category_name=std.category.name if std.category else None,
        created_at=std.created_at.date() if std.created_at else None,
        updated_at=std.updated_at.date() if std.updated_at else None,
    )
