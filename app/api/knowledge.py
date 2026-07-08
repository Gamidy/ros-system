"""知识库API — CRUD + 全文搜索 + 富文本内容"""
from __future__ import annotations
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.knowledge import KnowledgeItem
from app.models.user import User
from pydantic import BaseModel
from typing import Optional

from app.services import event_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kb", tags=["知识库"])


# ── Schema ──

class KnowledgeCreate(BaseModel):
    category: str
    code: str
    name: str
    content: Optional[str] = None
    content_type: Optional[str] = "text"
    tags: Optional[str] = None
    sort_order: int = 0
    remark: Optional[str] = None


class KnowledgeUpdate(BaseModel):
    category: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    tags: Optional[str] = None
    sort_order: Optional[int] = None
    remark: Optional[str] = None


class KnowledgeOut(BaseModel):
    id: int
    category: str
    code: str
    name: str
    content: Optional[str] = None
    content_type: Optional[str] = None
    tags: Optional[str] = None
    version: Optional[int] = 1
    status: Optional[str] = "active"
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    sort_order: Optional[int] = 0
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Endpoints ──

@router.get("")
def list_knowledge_root(
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    db: Session = Depends(get_db),
) -> list[KnowledgeOut]:
    """知识库列表（根路径别名）"""
    return list_knowledge(category, keyword, status, db)


@router.get("/items", response_model=list[KnowledgeOut])
def list_knowledge(
    category: Optional[str] = Query(None, description="按分类筛选"),
    keyword: Optional[str] = Query(None, description="全文搜索关键词"),
    status: Optional[str] = Query("active", description="按状态筛选"),
    db: Session = Depends(get_db),
) -> list[KnowledgeOut]:
    """知识库列表 — 支持分类筛选、全文搜索、状态筛选"""
    q = db.query(KnowledgeItem)

    if category:
        q = q.filter(KnowledgeItem.category == category)
    if status:
        q = q.filter(KnowledgeItem.status == status)
    if keyword:
        # 全文搜索：匹配 name, content, tags, code
        like = f"%{keyword}%"
        q = q.filter(
            or_(
                KnowledgeItem.name.ilike(like),
                KnowledgeItem.content.ilike(like),
                KnowledgeItem.tags.ilike(like),
                KnowledgeItem.code.ilike(like),
            )
        )
    return q.order_by(KnowledgeItem.sort_order, KnowledgeItem.id).all()


@router.get("/items/{item_id}", response_model=KnowledgeOut)
def get_knowledge_item(item_id: int, db: Session = Depends(get_db)) -> KnowledgeOut:
    """知识库条目详情"""
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    return item


@router.post("/items", response_model=KnowledgeOut, status_code=201)
def create_knowledge(
    data: KnowledgeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeOut:
    """创建知识库条目（需登录）"""
    # 检查同分类同编码是否已存在
    existing = db.query(KnowledgeItem).filter(
        KnowledgeItem.category == data.category,
        KnowledgeItem.code == data.code,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="该分类下编码已存在")

    item = KnowledgeItem(
        category=data.category,
        code=data.code,
        name=data.name,
        content=data.content,
        content_type=data.content_type or "text",
        tags=data.tags,
        sort_order=data.sort_order,
        remark=data.remark,
        created_by=current_user.username,
        updated_by=current_user.username,
        version=1,
        status="active",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    event_bus.emit(
        "knowledge.created",
        {"item_id": item.id, "category": item.category, "code": item.code, "name": item.name},
        source="knowledge",
        producer="knowledge.service",
        user_id=current_user.username,
    )
    return item


@router.put("/items/{item_id}", response_model=KnowledgeOut)
def update_knowledge(
    item_id: int,
    data: KnowledgeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeOut:
    """更新知识库条目（需登录，自动版本+1）"""
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(item, field, value)
    item.version = (item.version or 1) + 1
    item.updated_by = current_user.username
    item.updated_at = datetime.now()
    db.commit()
    db.refresh(item)
    event_bus.emit(
        "knowledge.updated",
        {"item_id": item.id, "category": item.category, "code": item.code, "name": item.name},
        source="knowledge",
        producer="knowledge.service",
        user_id=current_user.username,
    )
    event_bus.emit(
        "knowledge.linked",
        {"item_id": item.id, "category": item.category, "code": item.code, "name": item.name},
        source="knowledge",
        producer="knowledge.service",
        user_id=current_user.username,
    )
    return item


@router.delete("/items/{item_id}")
def delete_knowledge(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """删除知识库条目（需登录）"""
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    db.delete(item)
    db.commit()
    event_bus.emit(
        "knowledge.archived",
        {"item_id": item_id},
        source="knowledge",
        producer="knowledge.service",
        user_id=current_user.username,
    )
    return {"ok": True, "id": item_id}


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)) -> list[str]:
    """获取所有分类"""
    rows = db.query(KnowledgeItem.category).distinct().all()
    return sorted(set(r[0] for r in rows if r[0]))


@router.get("/team")
def get_team_members(
    role: Optional[str] = Query(None, description="按系统角色筛选"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """获取活跃用户列表（供团队选择）"""
    q = db.query(User).filter(User.is_active == True)
    if role:
        q = q.filter(User.role == role)
    users = q.order_by(User.full_name).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name or u.username,
            "department": u.department or "",
            "position": u.position or "",
            "role": u.role,
        }
        for u in users
    ]


# ── 全文搜索 Schema ──

class KnowledgeSearchResult(BaseModel):
    """搜索结果分页"""
    total: int
    page: int
    size: int
    items: list[KnowledgeOut]


# ── 全文搜索端点 ──

@router.get("/items/search", response_model=KnowledgeSearchResult)
def search_knowledge(
    q: str = Query(..., description="搜索关键词"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
) -> KnowledgeSearchResult:
    """全文搜索知识条目（基于 ILIKE 模糊匹配）"""
    query = db.query(KnowledgeItem)

    if category:
        query = query.filter(KnowledgeItem.category == category)

    like = f"%{q}%"
    query = query.filter(
        or_(
            KnowledgeItem.name.ilike(like),
            KnowledgeItem.content.ilike(like),
            KnowledgeItem.tags.ilike(like),
            KnowledgeItem.code.ilike(like),
        )
    )

    total = query.count()
    items = (
        query.order_by(KnowledgeItem.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    return KnowledgeSearchResult(total=total, page=page, size=size, items=items)


# ── 分类树接口 ──

@router.get("/categories/tree")
def get_category_tree(db: Session = Depends(get_db)) -> list[dict]:
    """返回分类树（支持 / 层级分隔嵌套）"""
    rows = db.query(KnowledgeItem.category).distinct().all()
    categories = sorted(set(r[0] for r in rows if r[0]))

    # 以 / 为分隔符构建嵌套树
    tree: dict[str, dict] = {}

    for cat in categories:
        parts = [p.strip() for p in cat.split("/")]
        current_level = tree
        parent_id: str | None = None
        for i, part in enumerate(parts):
            if not part:
                continue
            if part not in current_level:
                node_id = "/".join(parts[: i + 1])
                current_level[part] = {
                    "id": node_id,
                    "name": part,
                    "parent_id": parent_id,
                    "children": {},
                }
            parent_id = current_level[part]["id"]
            current_level = current_level[part]["children"]

    def _flatten(node: dict) -> dict:
        children = [_flatten(v) for v in node["children"].values()]
        return {
            "id": node["id"],
            "name": node["name"],
            "parent_id": node["parent_id"],
            "children": children,
        }

    return [_flatten(v) for v in tree.values()]
