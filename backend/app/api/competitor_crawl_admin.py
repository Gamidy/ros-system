"""竞品爬取管理 API — 触发爬取、查询日志、管理搜索词

Endpoints:
  POST   /api/pm/crawls/run               — 触发指定市场+品牌的批量爬取
  GET    /api/pm/crawls/logs               — 分页查询爬取日志
  GET    /api/pm/crawls/search-terms       — 分页查询搜索词
  POST   /api/pm/crawls/search-terms       — 新增搜索词
  DELETE /api/pm/crawls/search-terms/{id}  — 删除搜索词
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.competitor_crawl import CompetitorCrawl
from app.models.competitor_search_term import CompetitorSearchTerm
from app.services.competitor_crawl_runner import (
    run_batch_crawl,
    send_crawl_notification,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pm/crawls", tags=["竞品爬取管理"])


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════════════════════════════════════════


class RunCrawlRequest(BaseModel):
    """触发爬取请求体"""
    market_code: str = Field(
        ..., min_length=1, max_length=20, description="目标市场代码: VN, US, SA…",
    )
    brand: str = Field(
        ..., min_length=1, max_length=80, description="品牌: AUX / TCL / Midea",
    )


class SearchTermCreate(BaseModel):
    """新增搜索词请求体"""
    market_code: str = Field(..., min_length=1, max_length=20)
    brand: str = Field(..., min_length=1, max_length=80)
    search_query: str = Field(..., min_length=1, max_length=500)
    language: Optional[str] = Field(None, max_length=20)
    product_type_hint: Optional[str] = Field(None, max_length=60)
    priority: int = Field(0, ge=0)
    notes: Optional[str] = None


class CrawlLogOut(BaseModel):
    """爬取日志输出"""
    id: int
    market_code: str
    brand: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    query_count: int
    pages_fetched: int
    total_found: int
    new_added: int
    updated: int
    skipped: int
    draft_count: int
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class SearchTermOut(BaseModel):
    """搜索词输出"""
    id: int
    market_code: str
    brand: str
    search_query: str
    language: Optional[str]
    product_type_hint: Optional[str]
    priority: int
    is_active: bool
    last_used_at: Optional[datetime]
    use_count: int
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════


@router.post("/run", response_model=dict)
async def trigger_crawl(
    req: RunCrawlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """触发指定市场+品牌的批量爬取

    对当前市场下所有活跃搜索词依次执行爬取管道，
    每个搜索词完成后自动创建一条系统通知。
    """
    logs = await run_batch_crawl(
        market_code=req.market_code,
        brand=req.brand,
        db=db,
    )

    # 每条日志发送通知
    for log in logs:
        send_crawl_notification(log, db)
    db.commit()

    logger.info(
        "批量爬取完成: market=%s brand=%s terms=%d",
        req.market_code, req.brand, len(logs),
    )

    return {
        "message": f"爬取完成，共执行 {len(logs)} 个搜索词",
        "market_code": req.market_code,
        "brand": req.brand,
        "log_count": len(logs),
        "log_ids": [log.id for log in logs],
    }


@router.get("/logs", response_model=dict)
def list_crawl_logs(
    market_code: Optional[str] = Query(None, description="按市场筛选"),
    brand: Optional[str] = Query(None, description="按品牌筛选"),
    status: Optional[str] = Query(None, description="按状态筛选: running/success/partial/failed"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询爬取日志"""
    q = db.query(CompetitorCrawl)

    if market_code:
        q = q.filter(CompetitorCrawl.market_code == market_code)
    if brand:
        q = q.filter(CompetitorCrawl.brand == brand)
    if status:
        q = q.filter(CompetitorCrawl.status == status)

    total = q.count()
    items = (
        q.order_by(CompetitorCrawl.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [CrawlLogOut.model_validate(c) for c in items],
    }


@router.get("/search-terms", response_model=dict)
def list_search_terms(
    market_code: Optional[str] = Query(None, description="按市场筛选"),
    brand: Optional[str] = Query(None, description="按品牌筛选"),
    is_active: Optional[bool] = Query(None, description="按启用状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询搜索词配置"""
    q = db.query(CompetitorSearchTerm)

    if market_code:
        q = q.filter(CompetitorSearchTerm.market_code == market_code)
    if brand:
        q = q.filter(CompetitorSearchTerm.brand == brand)
    if is_active is not None:
        q = q.filter(CompetitorSearchTerm.is_active.is_(is_active))

    total = q.count()
    items = (
        q.order_by(CompetitorSearchTerm.priority.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [SearchTermOut.model_validate(s) for s in items],
    }


@router.post("/search-terms", response_model=SearchTermOut, status_code=201)
def add_search_term(
    data: SearchTermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新增搜索词配置"""
    # 重复检查
    existing = (
        db.query(CompetitorSearchTerm)
        .filter(
            CompetitorSearchTerm.market_code == data.market_code,
            CompetitorSearchTerm.brand == data.brand,
            CompetitorSearchTerm.search_query == data.search_query,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"该搜索词已存在 (id={existing.id})",
        )

    term = CompetitorSearchTerm(
        market_code=data.market_code,
        brand=data.brand,
        search_query=data.search_query,
        language=data.language,
        product_type_hint=data.product_type_hint,
        priority=data.priority,
        notes=data.notes,
        is_active=True,
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    logger.info("新增搜索词: id=%d query=%s", term.id, term.search_query)

    return SearchTermOut.model_validate(term)


@router.delete("/search-terms/{term_id}", status_code=204)
def delete_search_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除搜索词配置"""
    term = (
        db.query(CompetitorSearchTerm)
        .filter(CompetitorSearchTerm.id == term_id)
        .first()
    )
    if not term:
        raise HTTPException(status_code=404, detail="搜索词不存在")

    db.delete(term)
    db.commit()
    logger.info("删除搜索词: id=%d query=%s", term_id, term.search_query)
