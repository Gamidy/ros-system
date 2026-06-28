"""
变更影响规则种子数据 — 空调(AC)产品常见变更场景

用于 ChangeImpactRule 表，ECO/ECR 生效时自动匹配影响。
"""
import json

SEED_RULES = [
    # ── ECR 变更类型匹配 ──
    {
        "name": "设计变更→影响全部安全认证",
        "description": "设计变更可能涉及结构/电气/安全性能，需重新评估全部认证",
        "trigger_type": "ecr_change",
        "trigger_value": "design_change",
        "affected_cert_types": json.dumps(["CE", "CB", "CCC", "UL", "KC", "SASO"]),
        "impact_level": "major",
    },
    {
        "name": "物料变更→影响EMC/安全",
        "description": "关键物料(压缩机/电机/PCB)变更需重新EMC+安全认证",
        "trigger_type": "ecr_change",
        "trigger_value": "material_change",
        "affected_cert_types": json.dumps(["CE-EMC", "CE-LVD", "CCC"]),
        "impact_level": "major",
    },
    {
        "name": "工艺变更→影响安规较小",
        "description": "生产工艺调整通常不影响认证，除非涉及安全关键工序",
        "trigger_type": "ecr_change",
        "trigger_value": "process_change",
        "affected_cert_types": json.dumps(["CE-LVD"]),
        "impact_level": "minor",
    },
    {
        "name": "认证变更→全部受影响",
        "description": "认证变更直接触发重新认证",
        "trigger_type": "ecr_change",
        "trigger_value": "cert_change",
        "affected_cert_types": json.dumps(["ALL"]),
        "impact_level": "critical",
    },
    {
        "name": "标准变更→需检查全部认证",
        "description": "标准更新涉及全部相关认证更新",
        "trigger_type": "ecr_change",
        "trigger_value": "standard_change",
        "affected_cert_types": json.dumps(["CE", "CB", "CCC", "UL"]),
        "impact_level": "critical",
    },

    # ── ECO 变更类型匹配 ──
    {
        "name": "ECO add → 新增物料需认证评估",
        "description": "新增物料需要评估是否影响已有认证",
        "trigger_type": "eco_change",
        "trigger_value": "add",
        "affected_cert_types": json.dumps(["CE-EMC", "CE-LVD", "CCC"]),
        "impact_level": "major",
    },
    {
        "name": "ECO modify → 变更物料需安全评估",
        "description": "修改物料参数需要评估安全/EMC影响",
        "trigger_type": "eco_change",
        "trigger_value": "modify",
        "affected_cert_types": json.dumps(["CE-LVD", "CCC"]),
        "impact_level": "major",
    },
    {
        "name": "ECO replace → 替换物料需全面评估",
        "description": "替换关键物料需要全面评估认证影响",
        "trigger_type": "eco_change",
        "trigger_value": "replace",
        "affected_cert_types": json.dumps(["CE", "CB", "CCC", "UL"]),
        "impact_level": "major",
    },
    {
        "name": "ECO delete → 删除物料影响较小",
        "description": "删除物料通常不引入新风险",
        "trigger_type": "eco_change",
        "trigger_value": "delete",
        "affected_cert_types": json.dumps([]),
        "impact_level": "minor",
    },
    {
        "name": "ECO disable → 禁用物料需评估",
        "description": "禁用物料需检查替代物料认证状态",
        "trigger_type": "eco_change",
        "trigger_value": "disable",
        "affected_cert_types": json.dumps(["CCC"]),
        "impact_level": "minor",
    },

    # ── 物料类别匹配 ──
    {
        "name": "压缩机变更→影响CE/CB+CCC",
        "description": "压缩机是AC核心部件，变更需重新CE/CB和CCC认证",
        "trigger_type": "part_category",
        "trigger_value": "compressor",
        "affected_cert_types": json.dumps(["CE", "CB", "CCC"]),
        "impact_level": "critical",
    },
    {
        "name": "电机/风扇变更→影响EMC+安全",
        "description": "电机变更影响EMC和LVD安全认证",
        "trigger_type": "part_category",
        "trigger_value": "motor,fan",
        "affected_cert_types": json.dumps(["CE-EMC", "CE-LVD"]),
        "impact_level": "major",
    },
    {
        "name": "PCB/电控变更→影响EMC+CCC",
        "description": "PCB变更影响EMC兼容性和CCC安全",
        "trigger_type": "part_category",
        "trigger_value": "pcb,controller,display_board",
        "affected_cert_types": json.dumps(["CE-EMC", "CCC", "UL"]),
        "impact_level": "critical",
    },
    {
        "name": "制冷剂变更→影响全部安全认证",
        "description": "制冷剂类型变更影响全部安全认证和能效标准",
        "trigger_type": "part_category",
        "trigger_value": "refrigerant",
        "affected_cert_types": json.dumps(["CE", "CB", "CCC", "UL", "KC", "SASO"]),
        "impact_level": "critical",
    },
    {
        "name": "换热器变更→影响能效认证",
        "description": "换热器变更主要影响能效和制冷性能认证",
        "trigger_type": "part_category",
        "trigger_value": "heat_exchanger,evaporator,condenser",
        "affected_cert_types": json.dumps(["CE", "CCC", "ENERGY_STAR"]),
        "impact_level": "major",
    },

    # ── 样机类型匹配 ──
    {
        "name": "全新样机→所有认证需重新评估",
        "description": "全新样机涉及所有目标市场认证",
        "trigger_type": "prototype_change",
        "trigger_value": "new",
        "affected_cert_types": json.dumps(["ALL"]),
        "impact_level": "critical",
    },
    {
        "name": "变更样机→增量评估",
        "description": "变更样机只需评估变更部分涉及的认证",
        "trigger_type": "prototype_change",
        "trigger_value": "modified",
        "affected_cert_types": json.dumps(["CE", "CCC"]),
        "impact_level": "major",
    },

    # ── BOM 变更匹配 ──
    {
        "name": "BOM变更→通用影响",
        "description": "BOM变更需全面评估产品认证影响",
        "trigger_type": "bom_change",
        "trigger_value": "*",
        "affected_cert_types": json.dumps(["CE", "CCC", "UL"]),
        "impact_level": "major",
    },
]
