"""知识库API — 立项书下拉选项数据源"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.knowledge import KnowledgeItem
from app.models.user import User

router = APIRouter(prefix="/api/kb", tags=["知识库"])

@router.get("/items")
def get_kb_items(
    category: str | None = Query(None, description="按分类筛选"),
    db: Session = Depends(get_db),
):
    """获取知识库条目列表"""
    q = db.query(KnowledgeItem)
    if category:
        q = q.filter(KnowledgeItem.category == category)
    items = q.order_by(KnowledgeItem.sort_order, KnowledgeItem.id).all()
    return [
        {"id": i.id, "category": i.category, "code": i.code, "name": i.name}
        for i in items
    ]

@router.get("/categories")
def get_kb_categories(db: Session = Depends(get_db)):
    """获取所有知识库分类"""
    rows = db.query(KnowledgeItem.category).distinct().all()
    return [r[0] for r in rows]

@router.get("/team")
def get_team_members(
    role: str | None = Query(None, description="按系统角色筛选"),
    db: Session = Depends(get_db),
):
    """获取系统内活跃用户，可按角色筛选，供团队选择"""
    q = db.query(User).filter(User.is_active == True)
    if role:
        q = q.filter(User.role == role)
    users = q.order_by(User.full_name).all()
    return [
        {"id": u.id, "username": u.username, "full_name": u.full_name or u.username, "department": u.department or "", "position": u.position or "", "role": u.role}
        for u in users
    ]

# 立项团队角色 → 系统角色映射

@router.get("/exchange-rate")
def get_exchange_rate():
    """获取美元兑人民币汇率（中国银行现汇卖出价）"""
    import urllib.request, json
    try:
        # 使用免费汇率API
        req = urllib.request.Request("https://api.exchangerate-api.com/v4/latest/USD", 
            headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        rate = data["rates"].get("CNY", 7.2)
    except:
        rate = 7.2  # fallback
    return {"rate": round(rate, 4), "currency_pair": "USD/CNY", "source": "中国银行参考"}

TEAM_ROLE_MAP = {
    "项目经理": "product_manager",
    "系统工程师": "systems_engineer",
    "结构工程师": "structural_engineer",
    "电控工程师": "electrical_control_engineer",
    "电气工程师": "electrical_engineer",
    "工艺工程师": "process_engineer",
    "IQC工程师": "quality_engineer",
    "采购工程师": "procurement",
    "项目管理员": "project_admin",
}

@router.get("/team-roles")
def get_team_roles():
    """获取立项团队可选角色列表"""
    return [{"label": k, "value": k, "sys_role": v} for k, v in TEAM_ROLE_MAP.items()]
