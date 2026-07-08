#!/usr/bin/env python3
"""
ROS 系统 — 30天沙盒商业模拟数据生成脚本

使用 Faker 生成逼真的 30 天测试数据，覆盖
  ProductPlan(8阶段) → ApprovalRequest(并行审批) → Project(28列+M1-M9 Gate)
完整流程，含正常和异常场景。

用法:
  cd /Users/gamidy/ros-source/ros-system
  python tests/sandbox/generate_sandbox_data.py
  python tests/sandbox/generate_sandbox_data.py --seed 42          # 固定随机种子
  python tests/sandbox/generate_sandbox_data.py --db-url mysql+pymysql://root:pass@localhost/ros_db
  python tests/sandbox/generate_sandbox_data.py --dry-run           # 只打印不写入
  python tests/sandbox/generate_sandbox_data.py --clean             # 先清理旧数据再生成
"""

import sys
import os
import random
import json
import uuid
import argparse
from datetime import datetime, date, timedelta
from typing import Optional

# ── 确保能找到 app 包 ──────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
sys.path.insert(0, PROJECT_ROOT)

# ── Faker ──────────────────────────────────────────────────────────
try:
    from faker import Faker
except ImportError:
    print("正在安装 Faker...")
    os.system(f"{sys.executable} -m pip install faker -q")
    from faker import Faker

fake = Faker("zh_CN")
Faker.seed(0)

# ── 数据库 / 模型 ─────────────────────────────────────────────────
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.database import Base
from app.core.enums import (
    TargetMarketCode,
    CertType,
)
from app.models.product_plan import ProductPlan, Cost, CostType, BOMType, ProductPlanStage
from app.models.user import User, UserRole
from app.models.product_plan_subs import (
    ProductPlanInitiation,
    ProductPlanMarket,
    ProductPlanTechSpec,
    ProductPlanTeam,
)
from app.models.approval import ApprovalChain, ApprovalStep, ApprovalRequest, ApprovalRecord
from app.models.project import Project, ProjectGate, Task, Milestone, Risk, Program
from app.models.organization import Organization
from app.models.competitor import CompetitorModel
from app.core.database import SessionLocal


# ══════════════════════════════════════════════════════════════════
#  常量定义
# ══════════════════════════════════════════════════════════════════

# ── 审批链配置 ──
PLAN_APPROVAL_CHAIN_CODE = "PLAN_APPROVAL_V2"
PLAN_APPROVAL_CHAIN_NAME = "产品策划审批链V2"

# ── 用户角色种子 ──
SEED_USERS = [
    {"username": "admin", "full_name": "系统管理员", "role": UserRole.ADMIN, "department": "IT部"},
    {"username": "zhangzong", "full_name": "张伟明", "role": UserRole.RD_DIRECTOR, "department": "研发中心"},
    {"username": "lijingli", "full_name": "李静莉", "role": UserRole.PRODUCT_MANAGER, "department": "产品部"},
    {"username": "wangqiang", "full_name": "王强", "role": UserRole.SYSTEMS_ENGINEER, "department": "系统部"},
    {"username": "chenxiu", "full_name": "陈秀华", "role": UserRole.STRUCTURAL_ENGINEER, "department": "结构部"},
    {"username": "zhaoming", "full_name": "赵明", "role": UserRole.ELECTRICAL_CONTROL_ENGINEER, "department": "电控部"},
    {"username": "sunwei", "full_name": "孙伟", "role": UserRole.PROCUREMENT, "department": "采购部"},
    {"username": "zhouyang", "full_name": "周洋", "role": UserRole.QUALITY_ENGINEER, "department": "质量部"},
    {"username": "wujun", "full_name": "吴军", "role": UserRole.PROCESS_ENGINEER, "department": "工艺部"},
    {"username": "liuming", "full_name": "刘明", "role": UserRole.PROJECT_ADMIN, "department": "项目管理部"},
]

# ── 产品系列 ──
PRODUCT_SERIES = ["J系列", "K系列", "L系列", "M系列", "N系列", "P系列"]

# ── 竞品品牌 ──
COMPETITOR_BRANDS = ["格力", "美的", "海尔", "海信", "TCL", "奥克斯", "大金", "三菱电机", "松下", "日立"]

# ── 市场代码 ──
MARKET_CODES = [m.value for m in TargetMarketCode]

# ── 制冷剂 ──
REFRIGERANTS = ["R32", "R410A", "R290", "R134a", "R513A"]

# ── 开发类别 ──
DEV_CATEGORIES = ["全新开发", "派生开发", "升级换代", "降本优化", "定制开发"]

# ── 项目来源 ──
PROJECT_SOURCES = ["年度规划", "客户需求", "品质整改", "研发降本", "供应链二供", "工艺提效", "法规升级"]

# ── 能效等级 ──
ENERGY_RATINGS = ["新1级", "新2级", "新3级", "新5级", "SEER A+++", "SEER A++"]

# ── 电压频率 ──
VOLTAGE_FREQ_OPTIONS = ["220V~50Hz", "230V~50Hz", "115V~60Hz", "208V~60Hz", "380V~50Hz"]


def get_org_id(session: Session) -> int:
    """获取或创建默认组织，返回 org_id"""
    org = session.query(Organization).first()
    if org:
        return org.id
    org = Organization(name="空调事业部", code="AC_DIVISION", contact_email="ac@company.com")
    session.add(org)
    session.flush()
    print(f"  ✅ 创建组织: {org.name} (id={org.id})")
    return org.id


def seed_users(session: Session, org_id: int) -> dict[str, int]:
    """创建种子用户（如不存在），返回 {username: id} 映射"""
    result = {}
    for u in SEED_USERS:
        user = session.query(User).filter(User.username == u["username"]).first()
        if not user:
            user = User(
                username=u["username"],
                full_name=u["full_name"],
                role=u["role"],
                department=u["department"],
                hashed_password="",  # 沙盒用户不设密码
                org_id=org_id,
                is_active=True,
            )
            session.add(user)
            session.flush()
        result[user.username] = user.id
    return result


def seed_competitors(session: Session, count: int = 6) -> list[int]:
    """创建竞品数据（如不足），返回 competitor_id 列表"""
    existing = session.query(CompetitorModel).count()
    if existing >= count:
        return [c.id for c in session.query(CompetitorModel).limit(count).all()]

    ids = []
    for brand in COMPETITOR_BRANDS[:count]:
        comp = session.query(CompetitorModel).filter(
            CompetitorModel.brand == brand
        ).first()
        if not comp:
            comp = CompetitorModel(
                brand=brand,
                model=f"{brand} {fake.bothify('KFR-##??')}",
                market=random.choice(MARKET_CODES),
                product_type=random.choice(["分体式", "多联机", "风管机"]),
                cooling_capacity_w=random.randint(2500, 12000),
                heating_capacity_w=random.randint(2800, 14000),
                eer=round(random.uniform(3.0, 6.5), 2),
                cspf=round(random.uniform(3.5, 7.0), 2),
                noise_indoor_db=round(random.uniform(18, 45), 1),
                noise_outdoor_db=round(random.uniform(48, 65), 1),
                launch_year=random.randint(2020, 2025),
                notes=f"沙盒模拟竞品数据 - {brand}",
            )
            session.add(comp)
            session.flush()
        ids.append(comp.id)
    return ids


def seed_approval_chain(session: Session, org_id: int) -> int:
    """创建/获取产品策划审批链，返回 chain_id"""
    chain = session.query(ApprovalChain).filter(
        ApprovalChain.code == PLAN_APPROVAL_CHAIN_CODE
    ).first()
    if chain:
        return chain.id

    chain = ApprovalChain(
        code=PLAN_APPROVAL_CHAIN_CODE,
        name=PLAN_APPROVAL_CHAIN_NAME,
        description="产品策划审批：研发总监并行+模块经理并行+总经理终审",
        org_id=org_id,
        steps=[
            {"seq": 1, "role": "产品经理提交", "type": "sequential"},
            {"seq": 2, "role": "多角色并行审批", "type": "parallel"},
            {"seq": 3, "role": "总经理终审", "type": "sequential"},
        ],
    )
    session.add(chain)
    session.flush()

    # 步骤定义
    steps_data = [
        (1, UserRole.PRODUCT_MANAGER, "产品经理提交", "sequential"),
        (2, UserRole.RD_DIRECTOR, "研发总监审批", "parallel"),
        (2, UserRole.PROJECT_ADMIN, "项目经理审批", "parallel"),
        (3, UserRole.GENERAL_MANAGER, "总经理终审", "sequential"),
    ]
    for seq, role, name, step_type in steps_data:
        step = ApprovalStep(
            chain_id=chain.id,
            seq=seq,
            role=role,
            name=name,
            step_type=step_type,
        )
        session.add(step)

    session.flush()
    print(f"  ✅ 创建审批链: {chain.name} (id={chain.id})")
    return chain.id


def seed_program(session: Session, org_id: int, name: str = "2027海外新品计划") -> int:
    """创建/获取 Program"""
    prog = session.query(Program).filter(Program.name == name).first()
    if prog:
        return prog.id
    prog = Program(
        code=f"PRG-{datetime.now().year}-{random.randint(100, 999)}",
        name=name,
        description="30天沙盒模拟生成的项目群",
        status="active",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        org_id=org_id,
    )
    session.add(prog)
    session.flush()
    return prog.id


# ══════════════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════════════

def faker_sentence(prefix: str = "") -> str:
    """生成中文句子，可选前缀"""
    s = fake.sentence(nb_words=8, variable_nb_words=True)
    return f"{prefix}：{s}" if prefix else s


def random_date(start: date, end: date) -> date:
    """在 [start, end] 区间内随机日期"""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_code(prefix: str = "PP") -> str:
    """生成策划编号，如 PP-2025-001"""
    return f"{prefix}-{datetime.now().year}-{random.randint(1, 999):03d}"


def generate_project_code(prefix: str = "PJ") -> str:
    """生成项目编号"""
    return f"{prefix}-{datetime.now().year}-{random.randint(1000, 9999)}"


def pick_role_user(user_map: dict[str, int], role: str) -> str:
    """从 user_map 中挑选一个指定角色的用户名"""
    role_to_username = {
        UserRole.ADMIN: "admin",
        UserRole.RD_DIRECTOR: "zhangzong",
        UserRole.PRODUCT_MANAGER: "lijingli",
        UserRole.SYSTEMS_ENGINEER: "wangqiang",
        UserRole.STRUCTURAL_ENGINEER: "chenxiu",
        UserRole.ELECTRICAL_CONTROL_ENGINEER: "zhaoming",
        UserRole.PROCUREMENT: "sunwei",
        UserRole.QUALITY_ENGINEER: "zhouyang",
        UserRole.PROCESS_ENGINEER: "wujun",
        UserRole.PROJECT_ADMIN: "liuming",
        UserRole.GENERAL_MANAGER: "admin",
    }
    username = role_to_username.get(role, "admin")
    if username not in user_map:
        return list(user_map.keys())[0]
    return username


# ══════════════════════════════════════════════════════════════════
#  数据生成函数 — ProductPlan
# ══════════════════════════════════════════════════════════════════

def create_product_plan(
    session: Session,
    org_id: int,
    user_map: dict[str, int],
    competitor_ids: list[int],
    plan_date: date,
    **overrides,
) -> ProductPlan:
    """创建一个 ProductPlan 及其完整子表数据"""
    name = overrides.get("name") or f"{random.choice(PRODUCT_SERIES)} {fake.bothify('??-##')} 空调产品策划"
    series = overrides.get("series") or random.choice(PRODUCT_SERIES)
    market = overrides.get("market") or random.choice(MARKET_CODES)
    status = overrides.get("status", ProductPlanStage.DRAFT)

    pp = ProductPlan(
        name=name,
        series=series,
        market=market,
        product_type=overrides.get("product_type", random.choice(["分体式", "多联机", "风管机", "移动式"])),
        target_market_detail=overrides.get("target_market_detail", f"目标市场: {market}"),
        climate_zone=overrides.get("climate_zone", random.choice(["亚热带", "温带", "寒带", "全气候带"])),
        refrigerant=overrides.get("refrigerant", random.choice(REFRIGERANTS)),
        capacity_range=overrides.get("capacity_range", f"{random.choice(['0.75','1.0','1.5','2.0','2.5','3.0'])}匹"),
        voltage_freq=overrides.get("voltage_freq", random.choice(VOLTAGE_FREQ_OPTIONS)),
        series_name=overrides.get("series_name", f"{series}-{random.choice(['A','B','C','D','E'])}"),
        energy_rating=overrides.get("energy_rating", random.choice(ENERGY_RATINGS)),
        dev_category=overrides.get("dev_category", random.choice(DEV_CATEGORIES)),
        project_origin=overrides.get("project_origin", random.choice(PROJECT_SOURCES)),
        project_duration=overrides.get("project_duration", f"{random.randint(6, 24)}个月"),
        ip_ownership=overrides.get("ip_ownership", random.choice(["自有", "客户共有", "ODM"])),
        cost_target=json.dumps({
            "target": random.randint(500, 3000) * 10,
            "currency": "CNY",
        }),
        performance_target=json.dumps([
            {"param": "制冷量", "target": f"{random.randint(2500, 12000)}W", "unit": "W"},
            {"param": "能效比", "target": str(round(random.uniform(3.2, 7.0), 1)), "unit": ""},
        ]),
        status=status,
        org_id=org_id,
        created_by=random.choice(list(user_map.keys())),
    )
    session.add(pp)
    session.flush()

    # ── 子表: Initiation (Sheet1) ──
    init = ProductPlanInitiation(
        product_plan_id=pp.id,
        product_type=pp.product_type,
        target_market=market,
        climate_zone=pp.climate_zone,
        refrigerant=pp.refrigerant,
        capacity_range=pp.capacity_range,
        voltage_freq=pp.voltage_freq,
        series_name=pp.series_name,
        energy_rating=pp.energy_rating,
        ip_ownership=pp.ip_ownership,
        project_duration=pp.project_duration,
        dev_category=pp.dev_category,
        project_origin=pp.project_origin,
        background_basis=faker_sentence("市场趋势分析"),
        overall_goal=f"完成{series}新品开发，满足{market}市场需求",
        tech_goal=f"能效达到{pp.energy_rating}标准",
        cost_goal=f"目标成本控制在{random.randint(800, 2500)}元以内",
        sales_goal=f"首年销售{random.randint(5, 50)}万套",
        cert_goal=f"获得{market}地区强制认证",
        schedule_goal=f"预计{random.randint(6, 18)}个月完成开发",
        org_id=org_id,
    )
    session.add(init)

    # ── 子表: Market (Sheet2) ──
    market_info = ProductPlanMarket(
        product_plan_id=pp.id,
        main_capacity=f"{random.choice(['1.0','1.5','2.0','2.5'])}匹",
        energy_efficiency_req=pp.energy_rating,
        cert_requirements=json.dumps({
            "required_certs": [random.choice([c.value for c in CertType]) for _ in range(random.randint(1, 3))],
        }),
        target_price=f"{random.randint(200, 1500)}USD",
        customer_requirements=faker_sentence("客户关键需求"),
        org_id=org_id,
    )
    session.add(market_info)

    # ── 子表: TechSpec (Sheet3) ──
    tech_spec = ProductPlanTechSpec(
        product_plan_id=pp.id,
        core_performance=json.dumps({
            "cooling_capacity": f"{random.randint(2500, 12000)}W",
            "heating_capacity": f"{random.randint(2800, 14000)}W",
            "eer": round(random.uniform(3.0, 5.5), 1),
            "cop": round(random.uniform(3.0, 6.0), 1),
            "noise_indoor": f"{random.randint(18, 45)}dB(A)",
            "noise_outdoor": f"{random.randint(48, 65)}dB(A)",
        }),
        safety_compliance=json.dumps({
            "standard": "IEC 60335-2-40",
            "class": random.choice(["I类", "II类"]),
        }),
        optional_config=random.choice(["WIFI", "蓝牙", "红外", "485通讯", "无"]),
        org_id=org_id,
    )
    session.add(tech_spec)

    # ── 子表: Team (Sheet5) — 每个策划 2~4 人 ──
    roles_pool = [
        ("项目经理", "liuming"),
        ("系统工程师", "wangqiang"),
        ("结构工程师", "chenxiu"),
        ("电控工程师", "zhaoming"),
        ("采购代表", "sunwei"),
        ("质量代表", "zhouyang"),
        ("工艺代表", "wujun"),
    ]
    selected = random.sample(roles_pool, random.randint(2, 4))
    for role_name, uname in selected:
        user = session.query(User).filter(User.username == uname).first()
        team = ProductPlanTeam(
            product_plan_id=pp.id,
            role_name=role_name,
            member_name=user.full_name if user else uname,
            department=user.department if user else "",
            responsibility=f"负责{role_name}相关工作",
            org_id=org_id,
        )
        session.add(team)

    # ── Cost 记录 ──
    for cost_type in [CostType.TARGET, CostType.ESTIMATE]:
        cost = Cost(
            product_plan_id=pp.id,
            cost_type=cost_type,
            item_name="整机成本",
            target_value=round(random.uniform(500, 3000), 2),
            actual_value=round(random.uniform(480, 3200), 2) if cost_type == CostType.ACTUAL else None,
            currency="CNY",
        )
        session.add(cost)

    session.flush()
    return pp


def advance_plan_stage(pp: ProductPlan, target_stage: ProductPlanStage, competitor_ids: list[int] = None):
    """推进 ProductPlan 到目标阶段（模拟阶段转换）"""
    stage_order = [
        ProductPlanStage.DRAFT,
        ProductPlanStage.COMPETITOR,
        ProductPlanStage.DEFINITION,
        ProductPlanStage.COSTING,
        ProductPlanStage.TECH_INPUT,
        ProductPlanStage.PROJECT_INIT,
        ProductPlanStage.APPROVED,
        ProductPlanStage.RELEASED,
    ]
    current_idx = stage_order.index(pp.status)
    target_idx = stage_order.index(target_stage)
    if target_idx > current_idx:
        pp.status = target_stage


# ══════════════════════════════════════════════════════════════════
#  数据生成函数 — Approval
# ══════════════════════════════════════════════════════════════════

def create_approval_request(
    session: Session,
    chain_id: int,
    pp: ProductPlan,
    user_map: dict[str, int],
    org_id: int,
    days_offset: int = 0,
) -> ApprovalRequest:
    """为 ProductPlan 创建审批请求"""
    requester = pp.created_by or "lijingli"
    ar = ApprovalRequest(
        chain_id=chain_id,
        request_type="proposal",
        request_id=int(pp.id.split("-")[0].encode().hex()[:8], 16) % 100000 if "-" in pp.id else random.randint(1, 10000),
        title=f"审批: {pp.name}",
        requester=requester,
        status="pending",
        current_step=1,
        step_meta=json.dumps({"steps": []}),
        org_id=org_id,
    )
    session.add(ar)
    session.flush()
    return ar


def approve_request(
    session: Session,
    ar: ApprovalRequest,
    user_map: dict[str, int],
    chain_id: int,
    decision: str = "approved",
    reject_comment: str = "",
):
    """模拟审批流程——逐步推进审批"""
    chain = session.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
    if not chain:
        return
    steps = session.query(ApprovalStep).filter(
        ApprovalStep.chain_id == chain_id
    ).order_by(ApprovalStep.seq).all()

    step_meta = json.loads(ar.step_meta or "{}")
    if "records" not in step_meta:
        step_meta["records"] = []

    current_seq = ar.current_step or 1
    step_idx = current_seq - 1

    while step_idx < len(steps):
        step = steps[step_idx]
        approver = pick_role_user(user_map, step.role)

        if decision == "rejected" and step_idx == 0:
            # 第1步就被驳回
            rec = {
                "step_id": step.id,
                "seq": step.seq,
                "approver": approver,
                "decision": "rejected",
                "comment": reject_comment or "技术方案不成熟，需重新评估",
            }
            step_meta["records"].append(rec)
            ar.status = "rejected"
            ar.step_meta = json.dumps(step_meta)
            session.flush()

            # 记录 ApprovalRecord
            record = ApprovalRecord(
                request_id=ar.id,
                step_id=step.id,
                approver=approver,
                decision="rejected",
                comment=reject_comment or "技术方案不成熟，需重新评估",
            )
            session.add(record)
            return

        if step.step_type == "parallel":
            # 并行审批：找所有同 seq 的步骤
            parallel_steps = [s for s in steps if s.seq == step.seq]
            all_approved = True
            for ps in parallel_steps:
                p_approver = pick_role_user(user_map, ps.role)
                rec = {
                    "step_id": ps.id,
                    "seq": ps.seq,
                    "approver": p_approver,
                    "decision": decision if decision == "approved" else "rejected",
                    "comment": "同意" if decision == "approved" else (reject_comment or "不同意"),
                }
                step_meta["records"].append(rec)
                if decision != "approved":
                    all_approved = False

                # 记录 ApprovalRecord
                record = ApprovalRecord(
                    request_id=ar.id,
                    step_id=ps.id,
                    approver=p_approver,
                    decision=rec["decision"],
                    comment=rec["comment"],
                )
                session.add(record)

            if not all_approved:
                ar.status = "rejected"
                ar.step_meta = json.dumps(step_meta)
                session.flush()
                return

            step_idx += len(parallel_steps) - 1

        else:
            # 串行审批
            rec = {
                "step_id": step.id,
                "seq": step.seq,
                "approver": approver,
                "decision": decision,
                "comment": "同意" if decision == "approved" else (reject_comment or "不同意"),
            }
            step_meta["records"].append(rec)
            if decision != "approved":
                ar.status = "rejected"
                ar.step_meta = json.dumps(step_meta)
                session.flush()
                record = ApprovalRecord(
                    request_id=ar.id,
                    step_id=step.id,
                    approver=approver,
                    decision="rejected",
                    comment=reject_comment or "不同意",
                )
                session.add(record)
                return

            record = ApprovalRecord(
                request_id=ar.id,
                step_id=step.id,
                approver=approver,
                decision="approved",
                comment="同意",
            )
            session.add(record)

        step_idx += 1
        ar.current_step = step_idx + 1

    # 所有步骤通过
    ar.status = "approved"
    ar.step_meta = json.dumps(step_meta)
    session.flush()


# ══════════════════════════════════════════════════════════════════
#  数据生成函数 — Project
# ══════════════════════════════════════════════════════════════════

def create_project_from_plan(
    session: Session,
    pp: ProductPlan,
    program_id: int,
    org_id: int,
    user_map: dict[str, int],
) -> Project:
    """从已审批的 ProductPlan 生成 Project"""
    project = Project(
        code=generate_project_code(),
        name=f"{pp.name} 执行项目",
        program_id=program_id,
        product_plan_id=pp.id,
        org_id=org_id,
        project_class=random.choice(["T级", "A级", "B级", "C级"]),
        source=pp.project_origin or "年度规划",
        source_category=random.choice(["product_creation", "product_optimization"]),
        dev_modules=json.dumps(random.sample(["结构", "系统", "电控", "制冷", "外观"], random.randint(1, 4)), ensure_ascii=False),
        change_impacts=json.dumps(random.sample(["性能", "安全", "认证", "市场", "成本"], random.randint(1, 3)), ensure_ascii=False),
        status="planning",
        start_date=date.today(),
        target_end_date=date.today() + timedelta(days=random.randint(180, 540)),
        owner=random.choice(list(user_map.keys())),
        description=f"由策划「{pp.name}」自动生成的项目",
        is_draft=False,
        approval_status="approved",
    )
    session.add(project)
    session.flush()

    # 创建 M1-M4 Gate
    gates = [
        ("M1", "项目启动", 1, "项目经理"),
        ("M2", "方案设计", 2, "研发总监"),
        ("M3", "详细设计", 3, "模块经理"),
        ("M4", "设计验证", 4, "研发总监"),
    ]
    for code, name, seq, decider in gates:
        gate = ProjectGate(
            project_id=project.id,
            gate_code=code,
            gate_name=name,
            seq=seq,
            decision_level=decider,
            decider=decider,
            status="pending",
            planned_date=date.today() + timedelta(days=seq * 30),
            pass_conditions=json.dumps({
                "conditions": [f"{name}评审通过"],
            }, ensure_ascii=False),
            org_id=org_id,
        )
        session.add(gate)

    # 创建 5-8 个 Task
    task_templates = [
        ("需求分析", "wangqiang"),
        ("系统方案设计", "wangqiang"),
        ("3D结构设计", "chenxiu"),
        ("2D图档输出", "chenxiu"),
        ("电控方案设计", "zhaoming"),
        ("采购物料准备", "sunwei"),
        ("样机制作", "chenxiu"),
        ("性能测试", "zhouyang"),
    ]
    selected_tasks = random.sample(task_templates, random.randint(5, 7))
    for i, (title, assignee) in enumerate(selected_tasks):
        task = Task(
            project_id=project.id,
            title=title,
            assignee=assignee,
            status="todo",
            priority=random.choice(["low", "medium", "high"]),
            planned_date=date.today() + timedelta(days=(i + 1) * 10),
            due_date=date.today() + timedelta(days=(i + 1) * 10 + 5),
            description=f"执行{title}工作",
            org_id=org_id,
        )
        session.add(task)

    # 创建 2-3 个 Milestone
    milestones_to_create = [
        ("方案确定", 30),
        ("样机完成", 60),
        ("验证通过", 90),
    ]
    for name_text, offset_days in milestones_to_create:
        ms = Milestone(
            project_id=project.id,
            name=f"{name_text}里程碑",
            planned_date=date.today() + timedelta(days=offset_days),
            status="pending",
            gate_code=random.choice(["M1", "M2", "M3", "M4"]),
            org_id=org_id,
        )
        session.add(ms)

    # 创建 1-2 个初始 Risk
    risk_types = [
        ("模具延期风险", "模具", "高", "B级"),
        ("认证周期风险", "认证", "中", "B级"),
        ("物料供应风险", "物料", "中", "C级"),
        ("人员调配风险", "人员", "低", "C级"),
    ]
    for risk_title, source, prob, level in random.sample(risk_types, random.randint(1, 2)):
        risk = Risk(
            project_id=project.id,
            title=risk_title,
            risk_level=level,
            risk_source=source,
            probability=prob,
            impact=random.choice(["low", "medium", "high"]),
            mitigation=f"制定{source}应急预案",
            status="open",
            raised_by=project.owner,
            org_id=org_id,
        )
        session.add(risk)

    session.flush()
    # 更新 ProductPlan 关联
    pp.status = ProductPlanStage.APPROVED
    pp.project_id = project.id
    session.flush()
    return project


# ══════════════════════════════════════════════════════════════════
#  主模拟流程
# ══════════════════════════════════════════════════════════════════

def run_simulation(
    session: Session,
    user_map: dict[str, int],
    org_id: int,
    competitor_ids: list[int],
    chain_id: int,
    program_id: int,
    dry_run: bool = False,
):
    """30 天沙盒商业模拟主流程"""
    base_date = date.today()
    all_plans: list[ProductPlan] = []
    all_approval_requests: list[ApprovalRequest] = []
    all_projects: list[Project] = []

    print(f"\n{'='*60}")
    print(f"🚀 ROS 系统 30天沙盒商业模拟")
    print(f"{'='*60}")
    print(f"基础日期: {base_date}  |  组织ID: {org_id}  |  审批链ID: {chain_id}")
    print(f"用户数: {len(user_map)}  |  竞品数: {len(competitor_ids)}  |  Program: {program_id}")

    # ════════════════════════════════════════════
    #  Day 1-5: 策划启动
    # ════════════════════════════════════════════
    print(f"\n📅 Day 1-5: 策划启动阶段")

    # Day 1: 2 个全新品策划
    pp1 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="EU", series="J系列",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp1.competitor_id = competitor_ids[0]
        session.flush()
    all_plans.append(pp1)
    print(f"  ✅ [Day1] 全新品1: {pp1.name} (market=EU, status=draft)")

    pp2 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="EU", series="K系列",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp2.competitor_id = competitor_ids[1]
        session.flush()
    all_plans.append(pp2)
    print(f"  ✅ [Day1] 全新品2: {pp2.name} (market=EU, status=draft)")

    # Day 2: 1 个升级品策划
    pp3 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="CN", series="L系列",
        dev_category="升级换代",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp3.competitor_id = competitor_ids[2]
        session.flush()
    all_plans.append(pp3)
    print(f"  ✅ [Day2] 升级品: {pp3.name} (market=CN, dev_category=升级换代, status=draft)")

    # Day 3: 1 个多市场策划
    pp4 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="EU", series="M系列",
        target_market_detail="EU+AU+SA",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp4.competitor_id = competitor_ids[3]
        session.flush()
    all_plans.append(pp4)
    print(f"  ✅ [Day3] 多市场: {pp4.name} (market=EU+AU+SA, status=draft)")

    # Day 4: 2 个优化/降本项目
    pp5 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="CN", series="N系列",
        dev_category="降本优化", project_origin="研发降本",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp5.competitor_id = competitor_ids[4]
        session.flush()
    all_plans.append(pp5)
    print(f"  ✅ [Day4] 降本项目: {pp5.name} (source=研发降本, status=draft)")

    pp6 = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="US", series="P系列",
        project_origin="客户需求",
        status=ProductPlanStage.DRAFT,
    )
    if not dry_run:
        pp6.competitor_id = competitor_ids[0]
        session.flush()
    all_plans.append(pp6)
    print(f"  ✅ [Day4] 客户项目: {pp6.name} (market=US, source=客户需求, status=draft)")

    # Day 5: 推进到 COMPETITOR 阶段（3 个策划）
    # 正常推进
    if not dry_run:
        advance_plan_stage(pp1, ProductPlanStage.COMPETITOR)
        advance_plan_stage(pp2, ProductPlanStage.COMPETITOR)
        advance_plan_stage(pp3, ProductPlanStage.COMPETITOR)
        session.flush()
    print(f"  🔄 [Day5] 推进 3 个策划到 COMPETITOR 阶段")

    # ════════════════════════════════════════════
    #  Day 5-10: 策划细化 / 异常场景 E-04
    # ════════════════════════════════════════════
    print(f"\n📅 Day 6-10: 策划细化阶段")

    # Day 6: DEFINITION
    if not dry_run:
        advance_plan_stage(pp1, ProductPlanStage.DEFINITION)
        advance_plan_stage(pp2, ProductPlanStage.DEFINITION)
        session.flush()
    print(f"  🔄 [Day6] pp1/pp2 进入 DEFINITION")

    # Day 7: COSTING
    if not dry_run:
        advance_plan_stage(pp1, ProductPlanStage.COSTING)
        advance_plan_stage(pp2, ProductPlanStage.COSTING)
        session.flush()
    print(f"  🔄 [Day7] pp1/pp2 进入 COSTING")

    # Day 8: TECH_INPUT
    if not dry_run:
        advance_plan_stage(pp1, ProductPlanStage.TECH_INPUT)
        advance_plan_stage(pp2, ProductPlanStage.TECH_INPUT)
        session.flush()
    print(f"  🔄 [Day8] pp1/pp2 进入 TECH_INPUT")

    # Day 9: 异常 E-04 — 试图推进但 competitor_id 为空
    # 创建一个没有 competitor_id 的策划，尝试推进
    pp_no_comp = create_product_plan(
        session, org_id, user_map, competitor_ids,
        base_date, market="SA", series="P系列",
        status=ProductPlanStage.DRAFT,
    )
    # 不设置 competitor_id — 模拟 E-04
    if not dry_run:
        # 尝试推进到 COMPETITOR 但因为没有 competitor_id 被系统阻止
        # 我们模拟这个行为：脚本中标记特殊状态
        pp_no_comp.status = ProductPlanStage.DRAFT  # 阻塞在原地
        session.flush()
    all_plans.append(pp_no_comp)
    print(f"  ⚠️  [Day9] 异常 E-04: {pp_no_comp.name} 缺少 competitor_id，阻塞在 DRAFT")

    # Day 10: 正常策划进入 PROJECT_INIT
    if not dry_run:
        advance_plan_stage(pp1, ProductPlanStage.PROJECT_INIT)
        advance_plan_stage(pp2, ProductPlanStage.PROJECT_INIT)
        advance_plan_stage(pp3, ProductPlanStage.PROJECT_INIT)
        advance_plan_stage(pp4, ProductPlanStage.PROJECT_INIT)
        advance_plan_stage(pp5, ProductPlanStage.COSTING)
        session.flush()
    print(f"  🔄 [Day10] pp1/pp2/pp3/pp4 进入 PROJECT_INIT")
    print(f"  🔄 [Day10] pp5 进入 COSTING")

    # ════════════════════════════════════════════
    #  Day 11-15: 审批阶段
    # ════════════════════════════════════════════
    print(f"\n📅 Day 11-15: 审批阶段")

    # Day 11: 3 个正常策划提交审批
    plans_to_approve = [pp1, pp2, pp3]
    for i, pp in enumerate(plans_to_approve):
        if not dry_run:
            ar = create_approval_request(session, chain_id, pp, user_map, org_id)
            all_approval_requests.append(ar)
            pp.status = ProductPlanStage.PROJECT_INIT  # 提交后停留在 PROJECT_INIT
            session.flush()
            print(f"  📋 [Day11] 提交审批: {pp.name} → ApprovalRequest id={ar.id}")
        else:
            print(f"  📋 [Day11] 提交审批: {pp.name} → (dry-run)")

    # Day 12: 审批结果——2 个 approved, 1 个 rejected（异常 E-01）
    if not dry_run and len(all_approval_requests) >= 3:
        # pp1: approved
        approve_request(session, all_approval_requests[0], user_map, chain_id, "approved")
        pp1.status = ProductPlanStage.APPROVED
        print(f"  ✅ [Day12] pp1 审批通过")

        # pp2: approved
        approve_request(session, all_approval_requests[1], user_map, chain_id, "approved")
        pp2.status = ProductPlanStage.APPROVED
        print(f"  ✅ [Day12] pp2 审批通过")

        # pp3: rejected（异常 E-01）
        approve_request(
            session, all_approval_requests[2], user_map, chain_id,
            "rejected", "技术方案不成熟，涉及冷媒切换未充分验证，需重新评估"
        )
        pp3.status = ProductPlanStage.DRAFT  # 驳回后退回 DRAFT
        print(f"  ❌ [Day12] 异常 E-01: pp3 被驳回，退回 DRAFT")
        session.flush()

    # Day 13-14: 被驳回的策划修改后重新提交（C-02 混合场景）
    if not dry_run:
        # pp3 修改后重新提交
        pp3.name = pp3.name + " (修正版)"
        pp3.competitor_id = competitor_ids[2]
        # 更新子表数据
        init_item = session.query(ProductPlanInitiation).filter(
            ProductPlanInitiation.product_plan_id == pp3.id
        ).first()
        if init_item:
            init_item.tech_goal = "已更新冷媒切换验证方案，补充R290风险评估"
        session.flush()

        ar_resubmit = create_approval_request(session, chain_id, pp3, user_map, org_id)
        all_approval_requests.append(ar_resubmit)
        print(f"  📋 [Day13] pp3 修改后重新提交审批 (C-02)")
        pp3.status = ProductPlanStage.PROJECT_INIT

        # Day 14: 再次审批通过
        approve_request(session, ar_resubmit, user_map, chain_id, "approved")
        pp3.status = ProductPlanStage.APPROVED
        print(f"  ✅ [Day14] pp3 重新审批通过 (C-02)")
        session.flush()

    # Day 15: 多市场策划 pp4 提交审批并通过
    if not dry_run:
        ar4 = create_approval_request(session, chain_id, pp4, user_map, org_id)
        all_approval_requests.append(ar4)
        pp4.status = ProductPlanStage.PROJECT_INIT
        session.flush()
        approve_request(session, ar4, user_map, chain_id, "approved")
        pp4.status = ProductPlanStage.APPROVED
        print(f"  ✅ [Day15] pp4 多市场策划审批通过")
        session.flush()

    # ════════════════════════════════════════════
    #  Day 16-20: 项目生成与启动
    # ════════════════════════════════════════════
    print(f"\n📅 Day 16-20: 项目生成与启动")

    approved_plans = [p for p in all_plans if p.status == ProductPlanStage.APPROVED]
    for i, pp in enumerate(approved_plans):
        if not dry_run:
            project = create_project_from_plan(session, pp, program_id, org_id, user_map)
            all_projects.append(project)
            print(f"  🏗️  [Day{16+i}] 从策划生成项目: {project.name} (class={project.project_class})")
        else:
            print(f"  🏗️  [Day{16+i}] 从策划生成项目: {pp.name} → (dry-run)")

    # Day 20: 追加 1 个高等级 T 级项目（异常 E-02/E-05 潜伏）
    if not dry_run and len(approved_plans) > 0:
        pp_t = create_product_plan(
            session, org_id, user_map, competitor_ids,
            base_date, market="EU", series="J系列",
            dev_category="全新开发",
            status=ProductPlanStage.APPROVED,
        )
        pp_t.competitor_id = competitor_ids[0]
        session.flush()
        all_plans.append(pp_t)
        # 成本超限（异常 E-02 潜伏）
        cost_item = Cost(
            product_plan_id=pp_t.id,
            cost_type=CostType.TARGET,
            item_name="整机成本",
            target_value=99999.0,  # 超高成本触发预警
            currency="CNY",
        )
        session.add(cost_item)
        session.flush()

        project_t = create_project_from_plan(session, pp_t, program_id, org_id, user_map)
        project_t.project_class = "T级"
        project_t.budget = 5000000  # 500万预算
        session.flush()
        all_projects.append(project_t)
        print(f"  🏗️  [Day20] 高等级 T 级项目: {project_t.name} (budget=500万)")
        print(f"  ⚠️  异常 E-02 潜伏: 成本目标 99999 元远超预算")

    # ════════════════════════════════════════════
    #  Day 21-25: 项目执行与异常
    # ════════════════════════════════════════════
    print(f"\n📅 Day 21-25: 项目执行与异常")

    # Day 21: M1 Gate 通过
    if not dry_run and len(all_projects) >= 3:
        for i in range(3):
            pj = all_projects[i]
            gate_m1 = session.query(ProjectGate).filter(
                ProjectGate.project_id == pj.id,
                ProjectGate.gate_code == "M1"
            ).first()
            if gate_m1:
                gate_m1.status = "passed"
                gate_m1.actual_date = date.today()
                gate_m1.reviewer = pj.owner
                gate_m1.decision = "项目方案确认，同意启动"
            # 推进项目状态
            pj.status = "running"
        session.flush()
        print(f"  ✅ [Day21] 3 个项目 M1 Gate 通过，状态→running")

    # Day 22: 异常 E-05 — M4 Gate 阻塞
    if not dry_run and len(all_projects) >= 2:
        pj_gate_blocked = all_projects[1]  # 第二个项目被阻塞
        gate_m4 = session.query(ProjectGate).filter(
            ProjectGate.project_id == pj_gate_blocked.id,
            ProjectGate.gate_code == "M4"
        ).first()
        if gate_m4:
            gate_m4.status = "failed"
            gate_m4.pass_conditions = json.dumps({
                "conditions": ["设计验证通过", "样机测试通过"],
                "failed_reason": "样机性能测试不达标，制冷量低于目标值8%",
            }, ensure_ascii=False)
            gate_m4.decision = "设计验证未通过，需整改后重新评审"
        pj_gate_blocked.status = "paused"
        # 创建整改任务
        fix_task = Task(
            project_id=pj_gate_blocked.id,
            title="M4整改-性能优化",
            assignee="chenxiu",
            status="in_progress",
            priority="urgent",
            planned_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            description="针对M4评审失败项进行整改：优化风道设计，提升制冷量",
            org_id=org_id,
        )
        session.add(fix_task)
        session.flush()
        print(f"  ❌ [Day22] 异常 E-05: 项目 {pj_gate_blocked.name} M4 Gate 阻塞 → paused")

    # Day 23: 异常 E-06 — 项目取消
    if not dry_run and len(all_projects) >= 3:
        pj_cancel = all_projects[2]  # 第三个项目取消
        pj_cancel.status = "cancelled"
        # 关联任务全部取消
        tasks_to_cancel = session.query(Task).filter(Task.project_id == pj_cancel.id).all()
        for t in tasks_to_cancel:
            t.status = "done" if random.random() > 0.7 else "blocked"
        # 里程碑取消
        milestones_to_cancel = session.query(Milestone).filter(
            Milestone.project_id == pj_cancel.id
        ).all()
        for ms in milestones_to_cancel:
            ms.status = "delayed"
        session.flush()
        print(f"  🛑 [Day23] 异常 E-06: 项目 {pj_cancel.name} 被取消 → cancelled")

    # Day 24: 异常 E-08 — 里程碑延期
    if not dry_run and len(all_projects) >= 1:
        pj_delayed = all_projects[0]
        milestone_delayed = session.query(Milestone).filter(
            Milestone.project_id == pj_delayed.id
        ).first()
        if milestone_delayed:
            milestone_delayed.planned_date = date.today() - timedelta(days=10)
            milestone_delayed.status = "delayed"
            milestone_delayed.actual_date = None
        session.flush()
        print(f"  ⏰ [Day24] 异常 E-08: 项目 {pj_delayed.name} 里程碑延期 → delayed")

    # Day 25: 风险升级
    if not dry_run and len(all_projects) >= 1:
        pj_risk = all_projects[0]
        risk_a = Risk(
            project_id=pj_risk.id,
            title="供应商模具交付延期风险",
            risk_level="A级",
            risk_source="模具",
            probability="high",
            impact="high",
            mitigation="已启动备选供应商评估，预计周内完成",
            status="monitoring",
            raised_by=pj_risk.owner,
            org_id=org_id,
        )
        session.add(risk_a)
        session.flush()
        print(f"  ⚡ [Day25] 风险升级: {pj_risk.name} 新增 A 级风险")
        # 触发 E-07 — 并行审批中有拒绝记录（在额外场景中体现）
        # 创建一个新的 ApprovalRequest 模拟 E-07
        pp_e07 = create_product_plan(
            session, org_id, user_map, competitor_ids,
            base_date, market="BR", series="M系列",
            dev_category="定制开发",
            status=ProductPlanStage.PROJECT_INIT,
        )
        pp_e07.competitor_id = competitor_ids[2]
        session.flush()
        all_plans.append(pp_e07)

        ar_e07 = create_approval_request(session, chain_id, pp_e07, user_map, org_id)
        all_approval_requests.append(ar_e07)
        # 模拟并行审批中有部分拒绝
        chain = session.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
        steps = session.query(ApprovalStep).filter(
            ApprovalStep.chain_id == chain_id,
        ).order_by(ApprovalStep.seq).all()

        step_meta = {"records": []}
        for step in steps:
            if step.step_type == "parallel":
                # 并行步骤：RD_DIRECTOR 批准，PROJECT_ADMIN 拒绝
                rec1 = {
                    "step_id": step.id,
                    "seq": step.seq,
                    "approver": "zhangzong",
                    "decision": "approved",
                    "comment": "技术方案可行，同意",
                }
                rec2 = {
                    "step_id": step.id,
                    "seq": step.seq,
                    "approver": "liuming",
                    "decision": "rejected",
                    "comment": "项目资源不足，暂不启动",
                }
                step_meta["records"].append(rec1)
                step_meta["records"].append(rec2)
                record1 = ApprovalRecord(
                    request_id=ar_e07.id,
                    step_id=step.id,
                    approver="zhangzong",
                    decision="approved",
                    comment="技术方案可行，同意",
                )
                record2 = ApprovalRecord(
                    request_id=ar_e07.id,
                    step_id=step.id,
                    approver="liuming",
                    decision="rejected",
                    comment="项目资源不足，暂不启动",
                )
                session.add(record1)
                session.add(record2)
            else:
                rec = {
                    "step_id": step.id,
                    "seq": step.seq,
                    "approver": pick_role_user(user_map, step.role),
                    "decision": "approved",
                    "comment": "同意",
                }
                step_meta["records"].append(rec)

        ar_e07.step_meta = json.dumps(step_meta)
        ar_e07.status = "rejected"
        pp_e07.status = ProductPlanStage.DRAFT
        session.flush()
        print(f"  ⚠️  [Day25] 异常 E-07: 并行审批中有拒绝（资源不足），整体 rejected")

    # ════════════════════════════════════════════
    #  Day 26-30: 收尾与混合状态
    # ════════════════════════════════════════════
    print(f"\n📅 Day 26-30: 收尾与混合状态")

    # Day 26-27: 正常推进
    if not dry_run and len(all_projects) >= 1:
        pj_normal = all_projects[0]
        gate_m2 = session.query(ProjectGate).filter(
            ProjectGate.project_id == pj_normal.id,
            ProjectGate.gate_code == "M2"
        ).first()
        if gate_m2:
            gate_m2.status = "passed"
            gate_m2.actual_date = date.today()
        gate_m3 = session.query(ProjectGate).filter(
            ProjectGate.project_id == pj_normal.id,
            ProjectGate.gate_code == "M3"
        ).first()
        if gate_m3:
            gate_m3.status = "passed"
            gate_m3.actual_date = date.today()
        # 推进部分任务
        tasks_running = session.query(Task).filter(
            Task.project_id == pj_normal.id
        ).limit(3).all()
        for t in tasks_running:
            t.status = "done"
        session.flush()
        print(f"  ✅ [Day26-27] 项目 {pj_normal.name} M2/M3 通过，部分任务完成")

    # Day 28: T 级项目成本超限预警触发（E-02）
    if not dry_run:
        t_projects = [p for p in all_projects if p.project_class == "T级"]
        for pj_t in t_projects:
            # 检查 cost 是否超限
            pp_link = session.query(ProductPlan).filter(
                ProductPlan.id == pj_t.product_plan_id
            ).first()
            if pp_link:
                costs = session.query(Cost).filter(
                    Cost.product_plan_id == pp_link.id
                ).all()
                for c in costs:
                    if c.target_value and c.target_value > 50000:
                        print(f"  ⚠️  [Day28] 异常 E-02: 项目 {pj_t.name} 成本目标 {c.target_value} 超限！")
        session.flush()

    # Day 29: 正常项目推进到 M4
    if not dry_run and len(all_projects) >= 4:
        pj_opt = all_projects[3] if len(all_projects) > 3 else all_projects[0]
        pj_opt.status = "running"
        gate_m4_opt = session.query(ProjectGate).filter(
            ProjectGate.project_id == pj_opt.id,
            ProjectGate.gate_code == "M4"
        ).first()
        if gate_m4_opt:
            gate_m4_opt.status = "passed"
            gate_m4_opt.actual_date = date.today()
        session.flush()
        print(f"  ✅ [Day29] 优化项目 {pj_opt.name} M4 通过，降本目标达成")

    # Day 30: 最终状态汇总
    print(f"\n{'='*60}")
    print(f"📊 Day 30: 最终状态汇总")
    print(f"{'='*60}")

    # ── 状态统计 ──
    plan_statuses = {}
    for p in all_plans:
        plan_statuses[p.status.value] = plan_statuses.get(p.status.value, 0) + 1

    proj_statuses = {}
    for p in all_projects:
        proj_statuses[p.status] = proj_statuses.get(p.status, 0) + 1

    ar_statuses = {}
    for ar in all_approval_requests:
        ar_statuses[ar.status] = ar_statuses.get(ar.status, 0) + 1

    print(f"\n📋 ProductPlan 状态分布:")
    for status, count in sorted(plan_statuses.items()):
        print(f"    {status}: {count} 个")

    print(f"\n📋 ApprovalRequest 状态分布:")
    for status, count in sorted(ar_statuses.items()):
        print(f"    {status}: {count} 个")

    print(f"\n📋 Project 状态分布:")
    for status, count in sorted(proj_statuses.items()):
        print(f"    {status}: {count} 个")

    # ── 异常覆盖检查 ──
    print(f"\n🔍 异常场景覆盖:")
    e01 = any(ar.status == "rejected" for ar in all_approval_requests)
    e02 = any(p.budget and any(
        c.target_value and c.target_value > p.budget * 1.2
        for c in session.query(Cost).filter(
            Cost.product_plan_id == ProductPlan.id,
            ProductPlan.project_id == p.id,
        ).all()
    ) for p in all_projects) or False
    # E-02 simplified check
    e02_triggered = False
    for p in all_plans:
        costs = session.query(Cost).filter(Cost.product_plan_id == p.id).all()
        for c in costs:
            if c.target_value and c.target_value > 90000:
                e02_triggered = True
                break

    e03 = False  # 技术变更未在脚本中独立模拟（通过阶段回退隐含）
    e04 = pp_no_comp.status == ProductPlanStage.DRAFT  # 阻塞在 DRAFT
    e05 = any(p.status == "paused" for p in all_projects)
    e06 = any(p.status == "cancelled" for p in all_projects)
    # 检查 E-07: any rejected approval with parallel rejection in step_meta
    e07 = any(
        ar.status == "rejected" and ("资源不足" in (ar.step_meta or "")
                                     or "项目资源不足" in (ar.step_meta or ""))
        for ar in all_approval_requests
    )
    e08 = any(
        ms.status == "delayed"
        for p in all_projects
        for ms in session.query(Milestone).filter(Milestone.project_id == p.id).all()
    )

    print(f"    E-01 (审批驳回): {'✅' if e01 else '❌'}")
    print(f"    E-02 (成本超限): {'✅' if e02_triggered else '❌'}")
    print(f"    E-03 (技术变更): {'⏭️  脚本层面未独立模拟'}")
    print(f"    E-04 (竞品阻塞): {'✅' if e04 else '❌'}")
    print(f"    E-05 (Gate阻塞): {'✅' if e05 else '❌'}")
    print(f"    E-06 (项目取消): {'✅' if e06 else '❌'}")
    print(f"    E-07 (并行拒绝): {'✅' if e07 else '❌'}")
    print(f"    E-08 (里程碑延期): {'✅' if e08 else '❌'}")

    print(f"\n{'='*60}")
    print(f"🏁 30天沙盒模拟完成！")
    print(f"总计: {len(all_plans)} 策划 | {len(all_approval_requests)} 审批请求 | {len(all_projects)} 项目")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ROS系统 30天沙盒商业模拟数据生成器"
    )
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--db-url", type=str, default=None, help="数据库连接URL，默认使用 app.core.config 配置")
    parser.add_argument("--dry-run", action="store_true", help="仅打印不写入数据库")
    parser.add_argument("--clean", action="store_true", help="先清理旧数据再生成")
    args = parser.parse_args()

    random.seed(args.seed)
    fake.seed_instance(args.seed)

    # ── 数据库连接 ──
    engine = None
    if args.dry_run:
        print("🔍 干跑模式 — 仅打印不写入数据库\n")
        engine = create_engine("sqlite:///:memory:")
        SessionLocal_dry = sessionmaker(bind=engine)
        session = SessionLocal_dry()
        Base.metadata.create_all(bind=engine)
    else:
        if args.db_url:
            engine = create_engine(args.db_url)
            SessionLocal_custom = sessionmaker(bind=engine)
            session = SessionLocal_custom()
        else:
            from app.core.config import settings
            session = SessionLocal()
            engine = session.get_bind()

    try:
        # ── 确保所有表存在 ──
        if not args.dry_run:
            Base.metadata.create_all(bind=engine)

        # ── 清理旧数据（可选） ──
        if args.clean and not args.dry_run:
            print("🧹 清理旧数据...")
            tables_to_clean = [
                "approval_records", "approval_requests", "approval_steps", "approval_chains",
                "tasks", "risks", "milestones", "project_gates", "projects",
                "product_plan_teams", "product_plan_tech_specs", "product_plan_markets",
                "product_plan_initiations", "costs", "product_plans",
            ]
            # 检查哪些表存在，只清理存在的表
            inspector = __import__("sqlalchemy", fromlist=["inspect"]).inspect(engine)
            existing_tables = set(inspector.get_table_names())
            for tbl in tables_to_clean:
                if tbl in existing_tables:
                    session.execute(text(f"DELETE FROM {tbl}"))
                    print(f"   清空: {tbl}")
            session.commit()
            print("  ✅ 旧数据清理完成")

        # ── 种子数据 ──
        print("🔧 初始化种子数据...")
        org_id = get_org_id(session)
        user_map = seed_users(session, org_id)
        competitor_ids = seed_competitors(session)
        chain_id = seed_approval_chain(session, org_id)
        program_id = seed_program(session, org_id)

        if not args.dry_run:
            session.commit()
            print("  ✅ 种子数据写入完成")

        # ── 执行模拟 ──
        run_simulation(
            session,
            user_map,
            org_id,
            competitor_ids,
            chain_id,
            program_id,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            session.commit()
            print(f"\n  ✅ 所有数据已写入数据库")
        else:
            print(f"\n  ℹ️  干跑模式结束，未写入任何数据")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if not args.dry_run:
            session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
