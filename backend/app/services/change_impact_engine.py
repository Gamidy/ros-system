"""Phase 6 S2 — 变更影响引擎（S2 核心价值）

当 Prototype 发生变更时，自动判断对已有认证的影响。
使用 ChangeImpactRule 进行规则匹配（非硬编码）。
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.test import Prototype
from app.models.certification import CertificationSample, CertificationProject, Certificate
from app.models.change_impact import ChangeImpactRule, ChangeImpactRecord
from app.core.enums_s2 import ImpactLevel


class ChangeImpactEngine:
    """变更影响引擎 — 分析样机/BOM变更对认证的影响"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_prototype_change(
        self, prototype_id: int, changed_parts: Optional[list[str]] = None
    ) -> dict:
        """分析样机变更对认证的影响

        1. 获取原型信息
        2. 查找该原型关联的 CertificationSample → CertificationProject
        3. 获取该产品的有效证书
        4. 匹配 ChangeImpactRule
        5. 生成 ChangeImpactRecord
        6. 返回影响报告
        """
        # 1. 获取原型信息
        prototype = self.db.query(Prototype).filter(Prototype.id == prototype_id).first()
        if not prototype:
            return {"success": False, "message": f"原型 {prototype_id} 不存在"}

        # 2. 查找关联的 CertificationSample → CertificationProject
        samples = self.db.query(CertificationSample).filter(
            CertificationSample.prototype_id == prototype_id
        ).all()

        cert_project_ids = list(set(s.cert_project_id for s in samples))
        cert_projects = self.db.query(CertificationProject).filter(
            CertificationProject.id.in_(cert_project_ids)
        ).all() if cert_project_ids else []

        # 3. 获取该产品的有效证书
        # 通过样机的 cert_project 获取 cert_type 列表，再找对应证书
        active_certificates = []
        for cp in cert_projects:
            if cp.cert_types:
                cert_types = json.loads(cp.cert_types) if isinstance(cp.cert_types, str) else cp.cert_types
                for ct in cert_types:
                    certs = self.db.query(Certificate).filter(
                        Certificate.cert_type == ct,
                        Certificate.status == "active",
                    ).all()
                    active_certificates.extend(certs)

        # 4. 匹配 ChangeImpactRule
        impact_records = []
        changed_parts_list = changed_parts or ["general_change"]

        for part in changed_parts_list:
            rules = self._match_rules("part_category", part)
            for rule in rules:
                affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types

                # 检查是否有实际受影响的证书
                impacted_certs = [
                    c for c in active_certificates
                    if c.cert_type in affected_cert_types
                ]

                # 5. 生成 ChangeImpactRecord
                record = ChangeImpactRecord(
                    prototype_id=prototype_id,
                    changed_part=part,
                    matched_rule_id=rule.id,
                    impact_level=rule.impact_level,
                    affected_cert_types=rule.affected_cert_types,
                    analysis_detail=f"规则 '{rule.name}' 匹配: {part} → 影响 {rule.affected_cert_types}",
                    org_id=getattr(prototype, "org_id", None),
                )
                self.db.add(record)
                self.db.flush()

                impact_records.append({
                    "record_id": record.id,
                    "changed_part": part,
                    "matched_rule": rule.name,
                    "impact_level": rule.impact_level,
                    "affected_cert_types": affected_cert_types,
                    "impacted_certificates": [
                        {"id": c.id, "cert_no": c.cert_no, "cert_type": c.cert_type}
                        for c in impacted_certs
                    ],
                })

        self.db.commit()

        # 6. 返回影响报告
        overall_level = ImpactLevel.NONE.value
        if impact_records:
            levels = [r["impact_level"] for r in impact_records]
            if ImpactLevel.CRITICAL.value in levels:
                overall_level = ImpactLevel.CRITICAL.value
            elif ImpactLevel.MAJOR.value in levels:
                overall_level = ImpactLevel.MAJOR.value
            elif ImpactLevel.MINOR.value in levels:
                overall_level = ImpactLevel.MINOR.value

        return {
            "success": True,
            "prototype_id": prototype_id,
            "prototype_no": getattr(prototype, "proto_no", None),
            "overall_impact_level": overall_level,
            "impact_records": impact_records,
            "total_affected_certificates": len(active_certificates),
            "cert_projects": [
                {"id": cp.id, "name": cp.name, "code": cp.code}
                for cp in cert_projects
            ],
        }

    def analyze_bom_change(
        self, bom_item_id: int, old_part_no: str, new_part_no: str
    ) -> dict:
        """分析BOM变更对认证的影响（预留ECR/ECO集成）

        通过变更的物料号查找物料信息，匹配 ChangeImpactRule，
        找出受影响的认证类型。
        """
        # TODO: 集成 ECR/ECO 流程后完善
        # 1. 查找 BOMItem 和 Part 信息
        # 2. 获取 Part 的 category / cdf_type 等属性
        # 3. 匹配规则
        # 4. 查找关联该物料的产品 → 证书
        # 5. 生成记录
        return {
            "success": True,
            "bom_item_id": bom_item_id,
            "old_part_no": old_part_no,
            "new_part_no": new_part_no,
            "impact_level": ImpactLevel.NONE.value,
            "impact_records": [],
            "message": "BOM变更影响分析 — 预留实现，需集成ECR/ECO流程",
        }

    def _match_rules(self, trigger_type: str, trigger_value: str) -> list[ChangeImpactRule]:
        """匹配变更影响规则

        按 trigger_type + trigger_value 查找活跃的 ChangeImpactRule
        """
        rules = self.db.query(ChangeImpactRule).filter(
            ChangeImpactRule.trigger_type == trigger_type,
            ChangeImpactRule.is_active == True,
        ).all()

        matched = []
        for rule in rules:
            # 支持逗号分隔的 trigger_value
            rule_values = [v.strip() for v in rule.trigger_value.split(",") if v.strip()]
            if trigger_value in rule_values or rule.trigger_value == "*":
                matched.append(rule)

        return matched
