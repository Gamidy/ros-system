"""标准监控 — 管理员配置与爬取控制 API

提供管理员对标准库的 CRUD 操作、地区配置管理、手动触发爬取、爬取日志查看。
路由前缀: /api/admin/standards
"""
import logging
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.user import User
from app.models.standard import (
    Standard, StandardRegion, StandardCategory,
    StandardCrawl, STANDARD_STATUSES, IMPACT_LEVELS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/standards", tags=["标准监控管理"])


# ════════════════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ════════════════════════════════════════════════════════════════════════════


class StandardCreate(BaseModel):
    """标准条目创建"""
    region_id: int = Field(..., description="地区 ID")
    category_id: Optional[int] = Field(None, description="分类 ID")
    std_number: str = Field(..., max_length=100, description="标准编号")
    title: str = Field(..., max_length=500, description="标准标题")
    title_en: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, max_length=50)
    amendment: Optional[str] = Field(None, max_length=200)
    status: str = Field("active", description=f"状态: {STANDARD_STATUSES}")
    effective_date: Optional[date] = None
    repeal_date: Optional[date] = None
    source_url: Optional[str] = Field(None, max_length=1024)
    impact_level: Optional[str] = Field(None, description=f"影响等级: {IMPACT_LEVELS}")
    impact_scope: Optional[str] = None


class StandardUpdate(BaseModel):
    """标准条目更新"""
    category_id: Optional[int] = None
    title: Optional[str] = Field(None, max_length=500)
    title_en: Optional[str] = Field(None, max_length=500)
    version: Optional[str] = Field(None, max_length=50)
    amendment: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(None, description=f"状态: {STANDARD_STATUSES}")
    effective_date: Optional[date] = None
    repeal_date: Optional[date] = None
    source_url: Optional[str] = Field(None, max_length=1024)
    impact_level: Optional[str] = Field(None, description=f"影响等级: {IMPACT_LEVELS}")
    impact_scope: Optional[str] = None


class RegionCreate(BaseModel):
    """地区配置创建"""
    code: str = Field(..., max_length=20, description="地区代码")
    name: str = Field(..., max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=512)
    scan_method: str = Field("rss", description="爬取方式: rss|html|api")
    is_active: bool = True
    sort_order: int = 0


class RegionUpdate(BaseModel):
    """地区配置更新"""
    name: Optional[str] = Field(None, max_length=100)
    name_en: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=512)
    scan_method: Optional[str] = Field(None, description="爬取方式: rss|html|api")
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CrawlLogOut(BaseModel):
    """爬取日志输出"""
    id: int
    region_id: int
    region_name: str = ""
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    total_fetched: int
    new_added: int
    updated: int
    skipped: int
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlLogPage(BaseModel):
    """爬取日志分页"""
    items: list[CrawlLogOut]
    total: int
    page: int
    page_size: int


# ════════════════════════════════════════════════════════════════════════════
# 权限验证
# ════════════════════════════════════════════════════════════════════════════

_admin_dep = Depends(require_role("admin"))


# ════════════════════════════════════════════════════════════════════════════
# 地区配置 CRUD
# ════════════════════════════════════════════════════════════════════════════


@router.get("/regions")
def list_regions(
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> list[dict]:
    """地区配置列表（含爬取配置）"""
    regions = db.query(StandardRegion).order_by(StandardRegion.sort_order).all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "name_en": r.name_en,
            "base_url": r.base_url,
            "scan_method": r.scan_method,
            "is_active": r.is_active,
            "sort_order": r.sort_order,
        }
        for r in regions
    ]


@router.post("/regions")
def create_region(
    body: RegionCreate,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """新增地区"""
    existing = db.query(StandardRegion).filter(StandardRegion.code == body.code.upper()).first()
    if existing:
        raise HTTPException(400, detail=f"地区代码 {body.code} 已存在")
    region = StandardRegion(
        code=body.code.upper(),
        name=body.name,
        name_en=body.name_en,
        base_url=body.base_url,
        scan_method=body.scan_method,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    return {"ok": True, "id": region.id}


@router.put("/regions/{region_id}")
def update_region(
    region_id: int,
    body: RegionUpdate,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """更新地区配置"""
    region = db.query(StandardRegion).filter(StandardRegion.id == region_id).first()
    if not region:
        raise HTTPException(404, detail="地区不存在")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(region, key, value)
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# 标准条目 CRUD
# ════════════════════════════════════════════════════════════════════════════


@router.post("")
def create_standard(
    body: StandardCreate,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """手动录入标准"""
    if body.status not in STANDARD_STATUSES:
        raise HTTPException(400, detail=f"无效状态: {body.status}")
    if body.impact_level and body.impact_level not in IMPACT_LEVELS:
        raise HTTPException(400, detail=f"无效影响等级: {body.impact_level}")

    std = Standard(
        region_id=body.region_id,
        category_id=body.category_id,
        std_number=body.std_number,
        title=body.title,
        title_en=body.title_en,
        version=body.version,
        amendment=body.amendment,
        status=body.status,
        effective_date=body.effective_date,
        repeal_date=body.repeal_date,
        source_url=body.source_url,
        impact_level=body.impact_level,
        impact_scope=body.impact_scope,
        created_by=current_user.username,
    )
    db.add(std)
    db.commit()
    db.refresh(std)
    return {"ok": True, "id": std.id}


@router.put("/{standard_id}")
def update_standard(
    standard_id: int,
    body: StandardUpdate,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """编辑标准条目"""
    std = db.query(Standard).filter(Standard.id == standard_id).first()
    if not std:
        raise HTTPException(404, detail="标准条目不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] not in STANDARD_STATUSES:
        raise HTTPException(400, detail=f"无效状态: {update_data['status']}")
    if "impact_level" in update_data and update_data["impact_level"] and \
       update_data["impact_level"] not in IMPACT_LEVELS:
        raise HTTPException(400, detail=f"无效影响等级: {update_data['impact_level']}")

    for key, value in update_data.items():
        setattr(std, key, value)
    db.commit()
    return {"ok": True}


@router.delete("/{standard_id}")
def delete_standard(
    standard_id: int,
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """删除标准（软删除 → status=repealed）"""
    std = db.query(Standard).filter(Standard.id == standard_id).first()
    if not std:
        raise HTTPException(404, detail="标准条目不存在")
    std.status = "repealed"
    db.commit()
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# 爬取控制
# ════════════════════════════════════════════════════════════════════════════


@router.post("/trigger-crawl")
def trigger_crawl(
    region_id: Optional[int] = Query(None, description="仅爬取指定地区（不传则爬全部活跃地区）"),
    current_user: User = _admin_dep,
    db: Session = Depends(get_db),
) -> dict:
    """手动触发标准爬取（异步执行）"""
    if region_id:
        region = db.query(StandardRegion).filter(
            StandardRegion.id == region_id, StandardRegion.is_active.is_(True)
        ).first()
        if not region:
            raise HTTPException(404, detail="地区不存在或未启用")
        targets = [region]
    else:
        targets = db.query(StandardRegion).filter(
            StandardRegion.is_active.is_(True)
        ).all()
        if not targets:
            raise HTTPException(400, detail="没有已启用的爬取地区")

    # 创建爬取日志记录
    crawl_ids: list[int] = []
    for region in targets:
        crawl_log = StandardCrawl(
            region_id=region.id,
            started_at=datetime.now(),
            status="running",
        )
        db.add(crawl_log)
        db.flush()
        crawl_ids.append(crawl_log.id)

    db.commit()

    # 爬取任务将在 Phase 3 实现真正的异步执行
    # 当前仅记录日志条目，标记为 running 状态等待爬虫接入
    return {
        "ok": True,
        "crawl_ids": crawl_ids,
        "message": "爬取任务已排队，Phase 3 实现后自动执行",
        "simulated": True,
    }


@router.get("/crawl-logs", response_model=CrawlLogPage)
def list_crawl_logs(
    region_id: Optional[int] = Query(None, description="地区 ID"),
    status: Optional[str] = Query(None, description="状态: running|success|failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> CrawlLogPage:
    """爬取日志列表"""
    from sqlalchemy.orm import joinedload as _jl
    query = db.query(StandardCrawl).options(_jl(StandardCrawl.region))
    if region_id:
        query = query.filter(StandardCrawl.region_id == region_id)
    if status:
        query = query.filter(StandardCrawl.status == status)

    total = query.count()
    items = (
        query.order_by(StandardCrawl.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CrawlLogPage(
        items=[
            CrawlLogOut(
                id=log.id,
                region_id=log.region_id,
                region_name=log.region.name if log.region else "",
                started_at=log.started_at,
                finished_at=log.finished_at,
                status=log.status,
                total_fetched=log.total_fetched,
                new_added=log.new_added,
                updated=log.updated,
                skipped=log.skipped,
                error_message=log.error_message,
                created_at=log.created_at,
            )
            for log in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
