"""团队角色模板管理API — 仅admin可操作"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.team_role_template import TeamRoleTemplate

router = APIRouter(prefix="/admin", tags=["admin-role-templates"])


# ── Request/Response Schemas ──────────────────────────────────────────

class RoleTemplateItem(BaseModel):
    """单条角色模板"""
    role_name: str = Field(..., description="角色名称")
    headcount: int = Field(1, description="默认人数")
    responsibility_default: Optional[str] = Field(None, description="默认职责描述")
    seq: int = Field(0, description="排序")


class RoleTemplateBatch(BaseModel):
    """批量创建/更新请求"""
    project_type: str = Field(..., description="项目类型: 全新开发/改型/引用")
    roles: List[RoleTemplateItem] = Field(..., description="角色列表")


class RoleTemplateOut(BaseModel):
    id: int
    project_type: str
    role_name: str
    headcount: int
    responsibility_default: Optional[str] = None
    seq: int

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/team-role-templates", response_model=List[RoleTemplateOut])
def list_team_role_templates(
    project_type: str = Query("", description="按项目类型筛选，留空返回全部"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> list:
    """查询团队角色模板，可按project_type筛选"""
    q = db.query(TeamRoleTemplate)
    if project_type:
        q = q.filter(TeamRoleTemplate.project_type == project_type)
    return q.order_by(TeamRoleTemplate.seq, TeamRoleTemplate.id).all()


@router.post("/team-role-templates")
def batch_upsert_team_role_templates(
    data: RoleTemplateBatch,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """批量创建/更新团队角色模板 — 对指定project_type先删除旧数据再批量插入"""
    # 删除该 project_type 下的所有旧记录
    db.query(TeamRoleTemplate).filter(
        TeamRoleTemplate.project_type == data.project_type
    ).delete()
    # 批量插入
    created = []
    for item in data.roles:
        tpl = TeamRoleTemplate(
            project_type=data.project_type,
            role_name=item.role_name,
            headcount=item.headcount,
            responsibility_default=item.responsibility_default,
            seq=item.seq,
        )
        db.add(tpl)
        created.append(tpl)
    db.commit()
    return {"ok": True, "project_type": data.project_type, "count": len(created)}


@router.delete("/team-role-templates/{template_id}")
def delete_team_role_template(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """删除单条团队角色模板"""
    tpl = db.query(TeamRoleTemplate).filter(TeamRoleTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "模板不存在")
    db.delete(tpl)
    db.commit()
    return {"ok": True, "id": template_id}
