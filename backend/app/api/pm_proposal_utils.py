"""产品立项书工具函数 — 跨Tab自动计算 & 模板加载

纯函数优先，无副作用，方便测试。
提供：制冷量BTU→W转换、认证费用生成、人月计算、人员负载查询、按市场/项目类型加载模板。
"""
from __future__ import annotations

import json
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.pm_config import CertStandard
from app.models.team_role_template import TeamRoleTemplate
from app.models.user import User


# ══════════════════════════════════════════════════════════════
# 1. 制冷量 BTU → 瓦特 转换
# ══════════════════════════════════════════════════════════════

def calc_cooling_capacity_btu_to_w(capacity_range: str) -> int:
    """从 capacity_range 解析 BTU，转换为瓦特（÷3.4128 取整）。

    支持格式：
      - "12000BTU" / "12KBTU" / "12k"
      - "12K"    → 按 1K = 1000 BTU 处理
      - "07K-12K" → 取最后一个（最大值）
      - 纯数字 "12000" → 直接当 BTU

    返回 int 瓦特数；解析失败返回 0。
    """
    if not capacity_range or not isinstance(capacity_range, str):
        return 0

    s = capacity_range.strip().upper()

    # 优先处理区间格式 "07K-12K" → 取最后一个
    parts = re.split(r"[-~–—]", s)
    if len(parts) > 1:
        s = parts[-1].strip()

    # 尝试匹配明确的 BTU 标注（如 "12000BTU" 或 "12KBTU"）
    m = re.search(r"(\d+(?:\.\d+)?)\s*(K?)\s*BTU", s)
    if m:
        btu = float(m.group(1))
        if m.group(2):  # "12KBTU" — K 表示 ×1000
            btu *= 1000
        return max(0, round(btu / 3.4128))

    # "12K" 格式（无 BTU 后缀，K 表示 ×1000）
    m = re.search(r"(\d+(?:\.\d+)?)\s*K$", s)
    if m:
        btu = float(m.group(1)) * 1000
        return max(0, round(btu / 3.4128))

    # 纯数字，直接当 BTU（最后手段）
    m = re.search(r"(\d+)", s)
    if m:
        return max(0, round(float(m.group(1)) / 3.4128))

    return 0


# ══════════════════════════════════════════════════════════════
# 2. 按市场加载认证标准模板
# ══════════════════════════════════════════════════════════════

def get_cert_standards_by_market(market: str, db: Session) -> list[dict]:
    """查询 cert_standards 表，按目标市场返回安全合规标准列表。

    返回格式:
        [{standard, key_requirement, verification_method, cert_cycle, sort_order}]
    """
    items = (
        db.query(CertStandard)
        .filter(CertStandard.market == market)
        .order_by(CertStandard.sort_order, CertStandard.id)
        .all()
    )
    return [
        {
            "standard": item.standard,
            "key_requirement": item.key_requirement or "",
            "verification_method": item.verification_method or "",
            "cert_cycle": item.cert_cycle or "",
            "sort_order": item.sort_order or 0,
        }
        for item in items
    ]


# ══════════════════════════════════════════════════════════════
# 3. 从 Tab3 safety_compliance JSON 生成认证费用行
# ══════════════════════════════════════════════════════════════

# 默认认证机构-费用映射（万元）
_DEFAULT_CERT_COST_CONFIG: dict[str, float] = {
    "UL": 20.0,
    "CE": 3.0,
    "CB": 4.0,
    "CCC": 5.0,
    "TUV": 15.0,
    "ETL": 12.0,
    "CSA": 10.0,
    "SAA": 6.0,
    "PSE": 8.0,
    "KC": 7.0,
    "BSMI": 5.0,
    "NOM": 4.0,
    "INMETRO": 6.0,
    "SASO": 5.0,
    "ISO": 3.0,
    "IEC": 3.0,
    "EN": 3.0,
    "default": 3.0,
}


def _extract_cert_names(standard_text: str) -> list[str]:
    """从标准文本中提取认证机构/标准名。

    示例输入: "UL 60335-2-40 / CE LVD / CB IEC 60335"
    返回: ["UL", "CE", "CB"]
    """
    if not standard_text:
        return []
    # 按常见分隔符拆分
    tokens = re.split(r"[/,;，；、\s]+", standard_text)
    # 已知认证机构关键词（大写2-8字母）
    cert_names = []
    for token in tokens:
        token = token.strip().upper()
        # 匹配纯大写字母的认证机构缩写
        if re.match(r"^[A-Z]{2,8}$", token):
            cert_names.append(token)
    return cert_names


def get_cert_costs_from_compliance(
    safety_compliance_json: str,
    cert_cost_config: Optional[dict] = None,
) -> list[dict]:
    """从 Tab3 safety_compliance JSON 解析标准名，匹配费用。

    Args:
        safety_compliance_json: Tab3 安全合规 JSON 字符串
        cert_cost_config: 认证费用映射，如 {"UL":20, "CE":3, "default":3}
                         不传则使用内置默认映射

    返回:
        [{cert_name, cert_body, cost_wan, remark}]
        - cert_name: 标准名（如 "UL"）
        - cert_body: 认证机构（同标准名）
        - cost_wan: 费用（万元）
        - remark: 备注说明
    """
    config = cert_cost_config or _DEFAULT_CERT_COST_CONFIG
    default_cost = config.get("default", 3.0)

    # 尝试解析 JSON
    standards_list: list[str] = []
    try:
        data = json.loads(safety_compliance_json) if safety_compliance_json else {}
    except (json.JSONDecodeError, TypeError):
        data = {}

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                std = item.get("standard") or item.get("name") or item.get("cert_name", "")
                if std:
                    standards_list.append(str(std))
            elif isinstance(item, str):
                standards_list.append(item)
    elif isinstance(data, dict):
        # 可能 key 是标准名
        for key in data:
            standards_list.append(str(key))
        std_val = data.get("standard") or data.get("standards") or data.get("cert_standards")
        if isinstance(std_val, str):
            standards_list.append(std_val)
        elif isinstance(std_val, list):
            standards_list.extend(str(s) for s in std_val)

    # 去重提取认证机构名
    found_certs: list[str] = []
    for text in standards_list:
        found_certs.extend(_extract_cert_names(text))

    # 如果没有解析出，尝试直接从原始文本提取
    if not found_certs:
        found_certs = _extract_cert_names(safety_compliance_json or "")

    # 去重并保留顺序
    seen: set[str] = set()
    unique_certs: list[str] = []
    for c in found_certs:
        if c not in seen:
            seen.add(c)
            unique_certs.append(c)

    # 生成费用行
    result: list[dict] = []
    for cert_name in unique_certs:
        cost = config.get(cert_name, default_cost)
        result.append({
            "cert_name": cert_name,
            "cert_body": cert_name,
            "cost_wan": float(cost),
            "remark": "自动生成" if cert_name not in config else "",
        })

    return result


# ══════════════════════════════════════════════════════════════
# 4. 按项目类型加载团队角色模板
# ══════════════════════════════════════════════════════════════

def get_team_role_template_by_project_type(project_type: str, db: Session) -> list[dict]:
    """按 project_type 查询 team_role_templates 表，返回预设团队角色。

    返回:
        [{role_name, headcount, responsibility_default, seq}]
    """
    items = (
        db.query(TeamRoleTemplate)
        .filter(TeamRoleTemplate.project_type == project_type)
        .order_by(TeamRoleTemplate.seq, TeamRoleTemplate.id)
        .all()
    )
    return [
        {
            "role_name": item.role_name,
            "headcount": item.headcount or 1,
            "responsibility_default": item.responsibility_default or "",
            "seq": item.seq or 0,
        }
        for item in items
    ]


# ══════════════════════════════════════════════════════════════
# 5. 查询所有用户当前项目负载
# ══════════════════════════════════════════════════════════════

def get_user_workload(db: Session) -> dict[int, dict]:
    """查询所有用户当前参与的项目数及负载率。

    统计规则：
      - 作为项目 owner 或 leader_id 计入 1 个项目
      - 负载率 = min(项目数 × 10%, 100%)（每人最多10个项目即满负载）

    返回:
        {user_id: {project_count: N, load_rate: percent}}
    """
    from app.models.project import Project

    users = db.query(User).filter(User.is_active == True).all()
    active_projects = (
        db.query(Project)
        .filter(Project.status.notin_(["completed", "cancelled"]))
        .all()
    )

    # 统计每个用户参与的项目数
    user_project_count: dict[int, int] = {u.id: 0 for u in users}

    for proj in active_projects:
        # owner 匹配（owner 字段存的是 username）
        if proj.owner:
            for u in users:
                if u.username == proj.owner:
                    user_project_count[u.id] += 1
                    break
        # leader_id 匹配
        if proj.leader_id and proj.leader_id in user_project_count:
            user_project_count[proj.leader_id] += 1

    result: dict[int, dict] = {}
    for u in users:
        count = user_project_count.get(u.id, 0)
        load_rate = min(count * 10, 100)  # 每项目10%负载，上限100%
        result[u.id] = {
            "username": u.username,
            "full_name": u.full_name or "",
            "role": u.role,
            "project_count": count,
            "load_rate": load_rate,
        }
    return result


# ══════════════════════════════════════════════════════════════
# 6. 人月计算
# ══════════════════════════════════════════════════════════════

def calc_person_months(project_duration_months: int, occupancy_rate: float) -> float:
    """计算人月数。

    Args:
        project_duration_months: 项目周期（月）
        occupancy_rate: 人员投入占比（0.0 ~ 1.0）

    Returns:
        人月 = 项目周期(月) × 占比%
    """
    if project_duration_months <= 0 or occupancy_rate <= 0:
        return 0.0
    return round(project_duration_months * occupancy_rate, 2)


# ══════════════════════════════════════════════════════════════
# 辅助: 将制冷量计算值注入 core_performance JSON
# ══════════════════════════════════════════════════════════════

def inject_cooling_capacity_to_core_performance(
    core_performance: Optional[str],
    capacity_range: str,
) -> str:
    """在 core_performance JSON 中追加/更新 cooling_power_w 字段。

    保留原有 JSON 内容，仅添加/更新 cooling_power_w 键。
    如果原文本不是合法 JSON，则创建新的 JSON 对象。
    """
    watts = calc_cooling_capacity_btu_to_w(capacity_range)

    existing: dict = {}
    if core_performance:
        try:
            existing = json.loads(core_performance)
        except (json.JSONDecodeError, TypeError):
            existing = {}

    if not isinstance(existing, dict):
        existing = {}

    existing["cooling_power_w"] = watts
    existing["cooling_capacity_btu_raw"] = capacity_range

    return json.dumps(existing, ensure_ascii=False, separators=(",", ":"))


# ══════════════════════════════════════════════════════════════
# 辅助: 生成人月费用 JSON 写入 labor_costs
# ══════════════════════════════════════════════════════════════

def generate_labor_costs_json(
    project_duration_str: Optional[str],
    team_members_json: Optional[str],
    db: Optional[Session] = None,
) -> str:
    """根据项目周期和团队成员生成人月费用 JSON。

    解析 project_duration 获取月数，遍历 team_members 计算每人月。
    返回 JSON 字符串可直接写入 labor_costs 字段。
    """
    # 解析周期月数
    months = 0
    if project_duration_str:
        m = re.search(r"(\d+)", str(project_duration_str))
        if m:
            months = int(m.group(1))

    # 解析团队
    members: list[dict] = []
    if team_members_json:
        try:
            members = json.loads(team_members_json)
        except (json.JSONDecodeError, TypeError):
            members = []

    if not isinstance(members, list):
        members = []

    labor_items: list[dict] = []
    total_person_months = 0.0

    for member in members:
        if not isinstance(member, dict):
            continue
        role_name = member.get("role_name") or member.get("role") or "未指定"
        headcount = member.get("headcount", 1)
        occupancy = member.get("occupancy", 1.0)
        if isinstance(occupancy, str):
            try:
                occupancy = float(occupancy.rstrip("%")) / 100
            except (ValueError, TypeError):
                occupancy = 1.0

        person_months = calc_person_months(months, occupancy)
        total_person_months += person_months * headcount

        labor_items.append({
            "role": role_name,
            "headcount": headcount,
            "occupancy": round(occupancy, 2),
            "person_months": person_months,
        })

    result = {
        "project_duration_months": months,
        "total_person_months": round(total_person_months, 2),
        "items": labor_items,
    }
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
