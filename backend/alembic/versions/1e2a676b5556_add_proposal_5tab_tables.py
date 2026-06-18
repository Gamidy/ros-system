"""add_proposal_5tab_tables — 产品立项书5-Tab重构 6张新表

Revision ID: 1e2a676b5556
Revises:
Create Date: 2026-06-19 01:20:28.683722

新增表:
  - team_role_templates        团队角色模板
  - role_position_mappings     角色→岗位映射
  - material_component_templates  物料与部件清单模板
  - capacity_unit_costs        能力段原型单价
  - indirect_cost_configs      间接成本配置
  - trial_qty_configs          试制数量配置
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '1e2a676b5556'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════
# 初始默认数据
# ═══════════════════════════════════════════════════════════════

TEAM_ROLE_SEEDS = [
    # 全新开发 — 14个角色
    {"project_type": "全新开发", "role_name": "项目经理", "headcount": 1, "responsibility_default": "统筹项目全局，把控进度/质量/成本", "seq": 1},
    {"project_type": "全新开发", "role_name": "产品经理", "headcount": 1, "responsibility_default": "市场调研、产品定义、需求规格书", "seq": 2},
    {"project_type": "全新开发", "role_name": "结构工程师", "headcount": 2, "responsibility_default": "结构设计、3D建模、DFM评审", "seq": 3},
    {"project_type": "全新开发", "role_name": "系统工程师", "headcount": 1, "responsibility_default": "系统方案、制冷匹配、性能仿真", "seq": 4},
    {"project_type": "全新开发", "role_name": "电控软件工程师", "headcount": 1, "responsibility_default": "软件架构、控制逻辑、通讯协议", "seq": 5},
    {"project_type": "全新开发", "role_name": "电控硬件工程师", "headcount": 1, "responsibility_default": "PCB设计、EMC、电控可靠性", "seq": 6},
    {"project_type": "全新开发", "role_name": "采购工程师", "headcount": 1, "responsibility_default": "供应商开发、物料寻源、成本谈判", "seq": 7},
    {"project_type": "全新开发", "role_name": "品质工程师", "headcount": 1, "responsibility_default": "品质策划、检验标准、问题闭环", "seq": 8},
    {"project_type": "全新开发", "role_name": "工艺工程师", "headcount": 1, "responsibility_default": "工艺路线、工装设计、试产跟进", "seq": 9},
    {"project_type": "全新开发", "role_name": "认证工程师", "headcount": 1, "responsibility_default": "安规认证、能效认证、市场准入", "seq": 10},
    {"project_type": "全新开发", "role_name": "测试工程师", "headcount": 1, "responsibility_default": "测试方案、可靠性测试、问题追踪", "seq": 11},
    {"project_type": "全新开发", "role_name": "工业设计师", "headcount": 1, "responsibility_default": "外观造型、人机交互、CMF定义", "seq": 12},
    {"project_type": "全新开发", "role_name": "包装工程师", "headcount": 1, "responsibility_default": "包装方案、跌落测试、装箱设计", "seq": 13},
    {"project_type": "全新开发", "role_name": "技术支持工程师", "headcount": 1, "responsibility_default": "售后资料、安装维修手册、培训", "seq": 14},
    # 改型 — 6个角色
    {"project_type": "改型", "role_name": "项目经理", "headcount": 1, "responsibility_default": "统筹改型项目", "seq": 1},
    {"project_type": "改型", "role_name": "产品经理", "headcount": 1, "responsibility_default": "改型需求定义", "seq": 2},
    {"project_type": "改型", "role_name": "结构工程师", "headcount": 2, "responsibility_default": "结构变更设计与评审", "seq": 3},
    {"project_type": "改型", "role_name": "系统工程师", "headcount": 1, "responsibility_default": "系统匹配调整", "seq": 4},
    {"project_type": "改型", "role_name": "品质工程师", "headcount": 1, "responsibility_default": "变更点品质验证", "seq": 5},
    {"project_type": "改型", "role_name": "采购工程师", "headcount": 1, "responsibility_default": "变更物料采购跟进", "seq": 6},
    # 引用 — 3个角色
    {"project_type": "引用", "role_name": "项目经理", "headcount": 1, "responsibility_default": "引用项目统筹", "seq": 1},
    {"project_type": "引用", "role_name": "结构工程师", "headcount": 1, "responsibility_default": "引用适配与验证", "seq": 2},
    {"project_type": "引用", "role_name": "品质工程师", "headcount": 1, "responsibility_default": "引用件验证确认", "seq": 3},
]

ROLE_POSITION_SEEDS = [
    {"project_role": "结构工程师", "system_role": "主任结构工程师"},
    {"project_role": "结构工程师", "system_role": "结构工程师"},
    {"project_role": "系统工程师", "system_role": "主任系统工程师"},
    {"project_role": "系统工程师", "system_role": "系统工程师"},
    {"project_role": "电控硬件工程师", "system_role": "主任电控硬件工程师"},
    {"project_role": "电控硬件工程师", "system_role": "电控硬件工程师"},
    {"project_role": "电控软件工程师", "system_role": "主任电控软件工程师"},
    {"project_role": "电控软件工程师", "system_role": "电控软件工程师"},
    {"project_role": "品质工程师", "system_role": "品质主管工程师"},
    {"project_role": "品质工程师", "system_role": "品质工程师"},
]

MATERIAL_COMPONENT_SEEDS = [
    # 北美市场 — 物料
    {"market": "北美", "type": "物料", "name": "压缩机", "spec": "R454B/变频", "unit": "台"},
    {"market": "北美", "type": "物料", "name": "电机", "spec": "BLDC", "unit": "台"},
    {"market": "北美", "type": "物料", "name": "四通阀", "spec": "1-1/4\"", "unit": "个"},
    {"market": "北美", "type": "物料", "name": "电子膨胀阀", "spec": "脉冲式", "unit": "个"},
    {"market": "北美", "type": "物料", "name": "冷凝器", "spec": "铜管翅片", "unit": "台"},
    {"market": "北美", "type": "物料", "name": "蒸发器", "spec": "铜管翅片", "unit": "台"},
    # 北美市场 — 部件
    {"market": "北美", "type": "部件", "name": "钣金外壳", "spec": "SGCC/GE标准", "unit": "套"},
    {"market": "北美", "type": "部件", "name": "风扇叶片", "spec": "轴流/3叶", "unit": "个"},
    {"market": "北美", "type": "部件", "name": "导风板", "spec": "ABS+PM2.5滤网", "unit": "个"},
    {"market": "北美", "type": "部件", "name": "电装盒", "spec": "IP56防水", "unit": "个"},
    # 欧洲市场 — 物料
    {"market": "欧洲", "type": "物料", "name": "压缩机", "spec": "R32/变频", "unit": "台"},
    {"market": "欧洲", "type": "物料", "name": "电机", "spec": "BLDC", "unit": "台"},
    {"market": "欧洲", "type": "物料", "name": "四通阀", "spec": "1\"", "unit": "个"},
    # 欧洲市场 — 部件
    {"market": "欧洲", "type": "部件", "name": "钣金外壳", "spec": "SGCC/CE标准", "unit": "套"},
    {"market": "欧洲", "type": "部件", "name": "风扇叶片", "spec": "轴流/3叶", "unit": "个"},
]

CAPACITY_UNIT_COST_SEEDS = [
    {"capacity_key": "07K", "btu": 7000, "unit_cost_w": 0.098},
    {"capacity_key": "09K", "btu": 9000, "unit_cost_w": 0.115},
    {"capacity_key": "12K", "btu": 12000, "unit_cost_w": 0.132},
    {"capacity_key": "18K", "btu": 18000, "unit_cost_w": 0.156},
    {"capacity_key": "22K", "btu": 22000, "unit_cost_w": 0.178},
    {"capacity_key": "24K", "btu": 24000, "unit_cost_w": 0.198},
    {"capacity_key": "30K", "btu": 30000, "unit_cost_w": 0.225},
    {"capacity_key": "36K", "btu": 36000, "unit_cost_w": 0.260},
    {"capacity_key": "48K", "btu": 48000, "unit_cost_w": 0.320},
    {"capacity_key": "60K", "btu": 60000, "unit_cost_w": 0.390},
]

INDIRECT_COST_SEEDS = [
    {"key": "default", "amount": 5000, "description": "间接成本默认值(元/台)"},
    {"key": "北美", "amount": 6500, "description": "北美市场间接成本(元/台)，含UL认证分摊"},
    {"key": "欧洲", "amount": 5500, "description": "欧洲市场间接成本(元/台)，含CE/ERP分摊"},
    {"key": "国内", "amount": 3500, "description": "国内市场间接成本(元/台)"},
]

TRIAL_QTY_SEEDS = [
    {"project_class": "T", "trial_qty": 30, "remark": "T级关键项目，试制30台"},
    {"project_class": "A", "trial_qty": 20, "remark": "A级重点项目，试制20台"},
    {"project_class": "B", "trial_qty": 10, "remark": "B级常规项目，试制10台"},
    {"project_class": "C", "trial_qty": 5, "remark": "C级小型项目，试制5台"},
]


def _bulk_insert(table_name: str, seeds: list[dict]) -> None:
    """批量插入种子数据"""
    if not seeds:
        return
    columns = list(seeds[0].keys())
    t = table(table_name, *(column(c, type_=None) for c in columns))
    op.bulk_insert(t, seeds)


def upgrade() -> None:
    # 1. 团队角色模板
    op.create_table('team_role_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_type', sa.String(length=30), nullable=False, comment='项目类型: 全新开发/改型/引用'),
        sa.Column('role_name', sa.String(length=50), nullable=False, comment='角色名称'),
        sa.Column('headcount', sa.Integer(), nullable=True, comment='默认人数'),
        sa.Column('responsibility_default', sa.Text(), nullable=True, comment='默认职责描述'),
        sa.Column('seq', sa.Integer(), nullable=True, comment='排序'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_team_role_templates_project_type'), 'team_role_templates', ['project_type'], unique=False)
    _bulk_insert('team_role_templates', TEAM_ROLE_SEEDS)

    # 2. 角色→岗位映射
    op.create_table('role_position_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_role', sa.String(length=50), nullable=False, comment="项目角色名, 如'结构工程师'"),
        sa.Column('system_role', sa.String(length=100), nullable=False, comment="系统岗位名, 如'主任结构工程师'"),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_role_position_mappings_project_role'), 'role_position_mappings', ['project_role'], unique=False)
    _bulk_insert('role_position_mappings', ROLE_POSITION_SEEDS)

    # 3. 物料与部件清单模板
    op.create_table('material_component_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('market', sa.String(length=50), nullable=False, comment='目标市场'),
        sa.Column('type', sa.String(length=20), nullable=False, comment='类型: 物料/部件'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='名称'),
        sa.Column('spec', sa.String(length=200), nullable=True, comment='规格/型号'),
        sa.Column('unit', sa.String(length=20), nullable=True, comment='单位'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_material_component_templates_market'), 'material_component_templates', ['market'], unique=False)
    _bulk_insert('material_component_templates', MATERIAL_COMPONENT_SEEDS)

    # 4. 能力段原型单价
    op.create_table('capacity_unit_costs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('capacity_key', sa.String(length=20), nullable=False, comment="冷量段标识, 如'22K'"),
        sa.Column('btu', sa.Integer(), nullable=False, comment='BTU值, 如22000'),
        sa.Column('unit_cost_w', sa.Float(), nullable=False, comment='单价(万元), 如0.178'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_capacity_unit_costs_capacity_key'), 'capacity_unit_costs', ['capacity_key'], unique=False)
    _bulk_insert('capacity_unit_costs', CAPACITY_UNIT_COST_SEEDS)

    # 5. 间接成本配置
    op.create_table('indirect_cost_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False, comment="配置键, 如'default'"),
        sa.Column('amount', sa.Float(), nullable=False, comment='金额(元)'),
        sa.Column('description', sa.Text(), nullable=True, comment='说明'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_indirect_cost_configs_key'), 'indirect_cost_configs', ['key'], unique=True)
    _bulk_insert('indirect_cost_configs', INDIRECT_COST_SEEDS)

    # 6. 试制数量配置
    op.create_table('trial_qty_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_class', sa.String(length=10), nullable=False, comment='项目等级: T/A/B/C'),
        sa.Column('trial_qty', sa.Integer(), nullable=False, comment='试制数量'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注说明'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trial_qty_configs_project_class'), 'trial_qty_configs', ['project_class'], unique=True)
    _bulk_insert('trial_qty_configs', TRIAL_QTY_SEEDS)


def downgrade() -> None:
    op.drop_index(op.f('ix_trial_qty_configs_project_class'), table_name='trial_qty_configs')
    op.drop_table('trial_qty_configs')
    op.drop_index(op.f('ix_indirect_cost_configs_key'), table_name='indirect_cost_configs')
    op.drop_table('indirect_cost_configs')
    op.drop_index(op.f('ix_capacity_unit_costs_capacity_key'), table_name='capacity_unit_costs')
    op.drop_table('capacity_unit_costs')
    op.drop_index(op.f('ix_material_component_templates_market'), table_name='material_component_templates')
    op.drop_table('material_component_templates')
    op.drop_index(op.f('ix_role_position_mappings_project_role'), table_name='role_position_mappings')
    op.drop_table('role_position_mappings')
    op.drop_index(op.f('ix_team_role_templates_project_type'), table_name='team_role_templates')
    op.drop_table('team_role_templates')
