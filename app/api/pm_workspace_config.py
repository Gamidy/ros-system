"""PM工作台 — 配置端点（冷量成本/安全合规/认证费用/团队模板/人员负载/摘要）"""
from __future__ import annotations
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.models.project import Project
from app.models.system_config import SystemConfig
from app.api.pm_workspace import _require_pm
from app.api.pm_proposal_utils import get_cert_costs_from_compliance, get_cert_standards_by_market, get_team_role_template_by_project_type, get_user_workload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pm", tags=["产品经理工作台"])


def _normalize_capacity_key(capacity_range: str) -> str:
    """Normalize capacity range key: '7K' → '07K', '12K' → '12K'"""
    cap = capacity_range.strip().upper()
    if len(cap) == 2 and cap[0].isdigit() and cap[1] == 'K':
        return '0' + cap
    return cap


def _extract_capacity_number(capacity_range: str) -> int:
    """Extract numeric part from capacity range: '12K' → 12, '07K' → 7"""
    cap = capacity_range.strip().upper().rstrip('K')
    try:
        return int(cap)
    except ValueError:
        return 0


@router.get("/capacity-cost-config")
def get_capacity_cost_config(
    capacity_range: str = Query(..., description="冷量段，如 12K, 07K, 18K"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_pm),
) -> dict:
    """返回该冷量段对应的完整成本配置"""
    config_keys = ["mfg_cost_threshold", "capacity_unit_cost_map", "test_unit_price", "indirect_cost"]
    rows = db.query(SystemConfig).filter(SystemConfig.key.in_(config_keys)).all()
    config = {row.key: row.value for row in rows}

    manufacturing_cost = 0
    cap_num = _extract_capacity_number(capacity_range)
    if "mfg_cost_threshold" in config:
        try:
            thresholds = json.loads(config["mfg_cost_threshold"])
            for t in thresholds:
                if cap_num <= t.get("max_kw", 0):
                    manufacturing_cost = t.get("cost", 0)
                    break
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"mfg_cost_threshold JSON解析失败: {e}")

    proto_unit_cost = 0.0
    if "capacity_unit_cost_map" in config:
        try:
            cost_map = json.loads(config["capacity_unit_cost_map"])
            normalized_key = _normalize_capacity_key(capacity_range)
            entry = cost_map.get(normalized_key)
            if entry and isinstance(entry, dict):
                proto_unit_cost = entry.get("cost", 0.0)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"capacity_unit_cost_map JSON解析失败: {e}")

    try:
        test_unit_price = float(config.get("test_unit_price", "0"))
    except (ValueError, TypeError):
        test_unit_price = 0.0

    try:
        indirect_cost = int(float(config.get("indirect_cost", "0")))
    except (ValueError, TypeError):
        indirect_cost = 0

    return {
        "manufacturing_cost": manufacturing_cost, "proto_unit_cost": proto_unit_cost,
        "test_unit_price": test_unit_price, "indirect_cost": indirect_cost,
    }


@router.get("/safety-compliance-standards")
def get_safety_compliance_standards(
    target_market: str = Query(..., description="目标市场名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """按 target_market 从 cert_standards 表加载安全合规标准"""
    if not target_market or not target_market.strip():
        raise HTTPException(status_code=400, detail="target_market 不能为空")
    standards = get_cert_standards_by_market(target_market.strip(), db)
    return {"data": standards, "total": len(standards)}


@router.post("/cert-costs-from-compliance")
def get_cert_costs_endpoint(
    safety_compliance_json: str = Body(..., description="Tab3 安全合规 JSON 字符串"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """从 Tab3 safety_compliance JSON 解析标准名，匹配 cert_cost 配置生成费用行"""
    cert_cost_row = db.query(SystemConfig).filter(SystemConfig.key == "cert_cost").first()
    cert_cost_config = None
    if cert_cost_row:
        try:
            cert_cost_config = json.loads(cert_cost_row.value)
        except (json.JSONDecodeError, TypeError):
            cert_cost_config = None
    costs = get_cert_costs_from_compliance(safety_compliance_json=safety_compliance_json, cert_cost_config=cert_cost_config)
    return {"data": costs, "total": len(costs)}


@router.get("/team-role-templates")
def get_team_role_templates_endpoint(
    project_type: str = Query(..., description="项目类型: 全新开发/改型/引用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """按 project_type 返回预设团队角色模板"""
    if not project_type or not project_type.strip():
        raise HTTPException(status_code=400, detail="project_type 不能为空")
    templates = get_team_role_template_by_project_type(project_type.strip(), db)
    return {"data": templates, "total": len(templates)}


@router.get("/user-workload")
def get_user_workload_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """返回所有用户当前参与的项目数及负载率"""
    workload = get_user_workload(db)
    return {"data": workload, "total": len(workload)}


@router.get("/team-summary")
def get_team_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("product_manager")),
) -> dict:
    """团队摘要统计: 总人数/已分配/未分配/各角色人数"""
    users = db.query(User).filter(User.is_active == True).all()
    active_projects = db.query(Project).filter(Project.status.notin_(["completed", "cancelled"])).all()

    assigned_usernames: set[str] = set()
    for proj in active_projects:
        if proj.owner:
            assigned_usernames.add(proj.owner)
        if proj.leader_id:
            for u in users:
                if u.id == proj.leader_id:
                    assigned_usernames.add(u.username)
                    break

    total_count = len(users)
    assigned_count = sum(1 for u in users if u.username in assigned_usernames)
    unassigned_count = total_count - assigned_count
    role_counts: dict[str, int] = {}
    for u in users:
        role = u.role or "unknown"
        role_counts[role] = role_counts.get(role, 0) + 1

    return {
        "total_users": total_count, "assigned_users": assigned_count,
        "unassigned_users": unassigned_count, "role_distribution": role_counts,
    }
