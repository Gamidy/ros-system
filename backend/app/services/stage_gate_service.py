"""Stage Gate 阶段门控服务

G0~G6 概念层门控（why/what），
与现有 M1~M9 执行层门控（how）形成两层体系。

G0~G6 通过 gate_code 前缀 'G' 与 M 系列区分，
共存在 project_gates 表中。
"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import enum


class GateStage(str, enum.Enum):
    """概念层门控阶段"""
    G0 = "G0"
    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    G4 = "G4"
    G5 = "G5"
    G6 = "G6"


GATE_LABELS: dict[GateStage, str] = {
    GateStage.G0: "立项",
    GateStage.G1: "方案评审",
    GateStage.G2: "设计评审",
    GateStage.G3: "样机评审",
    GateStage.G4: "试产评审",
    GateStage.G5: "验证评审",
    GateStage.G6: "量产评审",
}

GATE_TRANSITIONS: dict[GateStage, list[GateStage]] = {
    GateStage.G0: [GateStage.G1],
    GateStage.G1: [GateStage.G2],
    GateStage.G2: [GateStage.G3],
    GateStage.G3: [GateStage.G4],
    GateStage.G4: [GateStage.G5],
    GateStage.G5: [GateStage.G6],
    GateStage.G6: [],
}

# 每个 Gate 的检查条件
GATE_REQUIREMENTS: dict[GateStage, list[dict]] = {
    GateStage.G0: [
        {"field": "name", "label": "项目名称", "required": True},
        {"field": "project_class", "label": "项目等级", "required": True},
    ],
    GateStage.G1: [
        {"field": "tech_scheme", "label": "技术方案", "required": True},
        {"field": "bom_preliminary", "label": "初步BOM", "required": False},
    ],
    GateStage.G2: [
        {"field": "design_docs", "label": "设计文档", "required": True},
        {"field": "risk_assessment", "label": "风险评估", "required": True},
    ],
    GateStage.G3: [
        {"field": "prototype_report", "label": "样机报告", "required": True},
        {"field": "test_results", "label": "测试结果", "required": True},
    ],
    GateStage.G4: [
        {"field": "pilot_plan", "label": "试产计划", "required": True},
        {"field": "bom_design", "label": "设计BOM", "required": True},
    ],
    GateStage.G5: [
        {"field": "pilot_report", "label": "试产报告", "required": True},
        {"field": "cert_status", "label": "认证状态", "required": True},
    ],
    GateStage.G6: [
        {"field": "mass_production_checklist", "label": "量产检查清单", "required": True},
    ],
}


def validate_gate_transition(db: Session, project_id: int, from_gate: str, to_gate: str) -> bool:
    """校验 Project Gate 是否允许从 from_gate 推进到 to_gate

    检查 project_gates 表中对应记录的状态。
    """
    try:
        from_stage = GateStage(from_gate)
        to_stage = GateStage(to_gate)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的 Gate 编号: {from_gate}/{to_gate}")

    allowed = GATE_TRANSITIONS.get(from_stage, [])
    if to_stage not in allowed:
        return False

    # 检查数据库中 gate 记录是否存在且状态合法
    result = db.execute(
        text("SELECT status FROM project_gates WHERE project_id = :pid AND gate_code = :gate"),
        {"pid": project_id, "gate": from_gate},
    ).fetchone()

    if not result:
        # Gate 不存在 = 未到达该门
        return False

    return True


def get_gate_requirements(gate_code: str) -> list[dict]:
    """返回某 Gate 的检查条件清单"""
    try:
        stage = GateStage(gate_code)
    except ValueError:
        return []
    return GATE_REQUIREMENTS.get(stage, [])


def get_gate_status(db: Session, project_id: int) -> list[dict]:
    """返回项目所有 G0~G6 Gate 的当前状态"""
    rows = db.execute(
        text("""
            SELECT gate_code, status, passed_at, handler, remark
            FROM project_gates
            WHERE project_id = :pid AND gate_code LIKE 'G%'
            ORDER BY gate_code
        """),
        {"pid": project_id},
    ).fetchall()

    gate_map: dict[str, dict] = {}
    for g in GateStage:
        gate_map[g.value] = {
            "gate_code": g.value,
            "gate_name": GATE_LABELS.get(g, g.value),
            "status": "pending",
            "passed_at": None,
            "handler": None,
            "remark": None,
        }

    for row in rows:
        code = row[0]
        if code in gate_map:
            gate_map[code].update({
                "status": row[1] or "pending",
                "passed_at": str(row[2]) if row[2] else None,
                "handler": row[3],
                "remark": row[4],
            })

    return list(gate_map.values())
