"""产品立项书专用API端点 — 模板加载 & 跨Tab自动计算

提供：
  - GET /api/pm/cert-standards/by-market   → 按市场查询认证标准
  - GET /api/pm/team-role-template         → 按项目类型加载团队角色模板
  - GET /api/pm/user-workloads             → 全部用户当前项目负载
  - GET /api/pm/proposal-calc              → 制冷量/人月等计算服务
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.api.pm_proposal_utils import (
    calc_cooling_capacity_btu_to_w,
    calc_person_months,
    get_cert_standards_by_market,
    get_cert_costs_from_compliance,
    get_team_role_template_by_project_type,
    get_user_workload,
)

router = APIRouter(prefix="/pm", tags=["产品立项书工具"])


def _require_auth(current_user: User = Depends(get_current_user)) -> User:
    """认证校验 — 需要登录用户"""
    return current_user


# ══════════════════════════════════════════════════════════════
# GET /api/pm/cert-standards/by-market
# ══════════════════════════════════════════════════════════════

@router.get("/cert-standards/by-market")
def api_cert_standards_by_market(
    market: str = Query(..., description="目标市场，如'越南'、'通用'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
) -> dict:
    """按目标市场查询认证标准模板。

    返回该市场所有认证标准行，含标准名、关键要求、验证方式、认证周期。
    """
    items = get_cert_standards_by_market(market, db)
    return {
        "market": market,
        "items": items,
        "count": len(items),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/pm/team-role-template
# ══════════════════════════════════════════════════════════════

@router.get("/team-role-template")
def api_team_role_template(
    project_type: str = Query(..., description="项目类型，如'全新开发'、'改型'、'引用'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
) -> dict:
    """按项目类型加载预设团队角色模板。

    返回该类型下的角色清单，含角色名、默认人数、职责描述、排序。
    """
    items = get_team_role_template_by_project_type(project_type, db)
    return {
        "project_type": project_type,
        "items": items,
        "count": len(items),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/pm/user-workloads
# ══════════════════════════════════════════════════════════════

@router.get("/user-workloads")
def api_user_workloads(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
) -> dict:
    """查询所有活跃用户的当前项目负载。

    返回每个用户的项目参与数、负载率百分比。
    负载率 = min(项目数 × 10%, 100%)，每人最多10个项目即满负载。
    """
    workloads = get_user_workload(db)
    users_list = [
        {
            "user_id": uid,
            "username": info["username"],
            "full_name": info["full_name"],
            "role": info["role"],
            "project_count": info["project_count"],
            "load_rate": info["load_rate"],
        }
        for uid, info in workloads.items()
    ]
    # 按负载率降序排列
    users_list.sort(key=lambda x: x["load_rate"], reverse=True)
    return {"users": users_list, "total": len(users_list)}


# ══════════════════════════════════════════════════════════════
# GET /api/pm/proposal-calc — 通用计算端点
# ══════════════════════════════════════════════════════════════

@router.get("/proposal-calc")
def api_proposal_calc(
    action: str = Query(..., description="计算类型: btu_to_w | person_months | cert_costs"),
    capacity_range: Optional[str] = Query(None, description="冷量段字符串（action=btu_to_w 时必填）"),
    duration_months: Optional[int] = Query(None, description="项目周期月数（action=person_months 时必填）"),
    occupancy_rate: Optional[float] = Query(None, description="人员投入占比 0~1（action=person_months 时必填）"),
    safety_compliance: Optional[str] = Query(None, description="安全合规 JSON（action=cert_costs 时必填）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_auth),
) -> dict:
    """通用自动计算端点。

    action 可选值:
      - btu_to_w: 制冷量 BTU → 瓦特转换
          必填: capacity_range (如 "12K" 或 "12000BTU")
          返回: {btu, watts}
      - person_months: 人月计算
          必填: duration_months, occupancy_rate
          返回: {duration_months, occupancy_rate, person_months}
      - cert_costs: 认证费用生成
          必填: safety_compliance (JSON 字符串)
          返回: {cert_costs: [{cert_name, cert_body, cost_wan, remark}]}

    前端也可本地使用工具函数，此端点提供无 DB 依赖的纯计算能力。
    """
    if action == "btu_to_w":
        if not capacity_range:
            raise HTTPException(status_code=400, detail="action=btu_to_w 需要 capacity_range 参数")
        watts = calc_cooling_capacity_btu_to_w(capacity_range)
        return {
            "action": "btu_to_w",
            "capacity_range": capacity_range,
            "watts": watts,
        }

    elif action == "person_months":
        if duration_months is None or occupancy_rate is None:
            raise HTTPException(
                status_code=400,
                detail="action=person_months 需要 duration_months 和 occupancy_rate 参数",
            )
        pm_val = calc_person_months(duration_months, occupancy_rate)
        return {
            "action": "person_months",
            "duration_months": duration_months,
            "occupancy_rate": occupancy_rate,
            "person_months": pm_val,
        }

    elif action == "cert_costs":
        if not safety_compliance:
            raise HTTPException(status_code=400, detail="action=cert_costs 需要 safety_compliance 参数")
        costs = get_cert_costs_from_compliance(safety_compliance)
        return {
            "action": "cert_costs",
            "cert_costs": costs,
            "count": len(costs),
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"未知 action: {action}，支持 btu_to_w / person_months / cert_costs",
        )
