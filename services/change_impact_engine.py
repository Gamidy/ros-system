"""Phase 6 S2+S3 — 变更影响引擎

当 Prototype / ECR / ECO 发生变更时，自动判断对已有认证的影响。
使用 ChangeImpactRule 进行规则匹配（非硬编码）。
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.test import Prototype
from app.models.certification import CertificationSample, CertificationProject, Certificate
from app.models.change_impact import ChangeImpactRule, ChangeImpactRecord
from app.models.ecr_eco import ECRRequest, ECO, ECOItem
from app.models.bom import BOMItem, BOM
from app.core.enums_s2 import ImpactLevel


class ChangeImpactEngine:
    """变更影响引擎 — 分析样机/BOM变更对认证的影响"""

    def __init__(self, db: Session):
        self.db = db

    # ── 工具方法 ──────────────────────────────────────────

    def _compute_overall_level(self, impact_records: list[dict]) -> str:
        """从 impact_records 计算整体影响等级"""
        if not impact_records:
            return ImpactLevel.NONE.value
        levels = [r["impact_level"] for r in impact_records]
        if ImpactLevel.CRITICAL.value in levels:
            return ImpactLevel.CRITICAL.value
        if ImpactLevel.MAJOR.value in levels:
            return ImpactLevel.MAJOR.value
        if ImpactLevel.MINOR.value in levels:
            return ImpactLevel.MINOR.value
        return ImpactLevel.NONE.value

    # ── ECR 触发 ──────────────────────────────────────────

    def analyze_by_ecr(self, ecr_id: int) -> dict:
        """分析 ECR 变更对认证的影响

        1. 读取 ECR 的变更内容
        2. 匹配 ChangeImpactRule（trigger_type='ecr_change'）
        3. 创建 ChangeImpactRecord
        """
        # 1. 读取 ECR
        ecr = self.db.query(ECRRequest).filter(ECRRequest.id == ecr_id).first()
        if not ecr:
            return {"success": False, "message": f"ECR {ecr_id} 不存在"}

        # 2. 匹配规则（按 ecr_type 维度匹配）
        impact_records = []
        trigger_values = [ecr.ecr_type, "ecr_change"]
        for val in trigger_values:
            rules = self._match_rules("ecr_change", val)
            for rule in rules:
                affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types

                # 尝试查找关联的 prototype
                prototype_id = None
                if hasattr(ecr, "prototype_id") and ecr.prototype_id:
                    prototype_id = ecr.prototype_id

                # 3. 创建 ChangeImpactRecord
                record = ChangeImpactRecord(
                    ecr_id=ecr_id,
                    prototype_id=prototype_id,
                    changed_part=f"ECR变更: {ecr.ecr_type} - {ecr.title}",
                    matched_rule_id=rule.id,
                    impact_level=rule.impact_level,
                    affected_cert_types=rule.affected_cert_types,
                    analysis_detail=f"规则 '{rule.name}' 匹配: ECR类型={ecr.ecr_type} → 影响 {rule.affected_cert_types}",
                    org_id=getattr(ecr, "org_id", None),
                )
                self.db.add(record)
                self.db.flush()

                impact_records.append({
                    "record_id": record.id,
                    "ecr_id": ecr_id,
                    "matched_rule": rule.name,
                    "impact_level": rule.impact_level,
                    "affected_cert_types": affected_cert_types,
                })

        self.db.commit()

        return {
            "success": True,
            "ecr_id": ecr_id,
            "ecr_code": getattr(ecr, "code", None),
            "ecr_title": getattr(ecr, "title", None),
            "overall_impact_level": self._compute_overall_level(impact_records),
            "impact_records": impact_records,
        }

    # ── ECO 触发 ──────────────────────────────────────────

    def analyze_by_eco(self, eco_id: int) -> dict:
        """分析 ECO 变更对认证的影响

        1. 读取 ECO 的变更内容（含 ECOItem 明细）
        2. 匹配 ChangeImpactRule（trigger_type='eco_change'）
        3. 创建 ChangeImpactRecord
        """
        # 1. 读取 ECO
        eco = self.db.query(ECO).filter(ECO.id == eco_id).first()
        if not eco:
            return {"success": False, "message": f"ECO {eco_id} 不存在"}

        # 获取 ECO 变更明细
        items = self.db.query(ECOItem).filter(ECOItem.eco_id == eco_id).all()

        impact_records = []
        # 按整体维度匹配
        rules = self._match_rules("eco_change", "eco_change")
        for rule in rules:
            affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types

            changed_part_text = f"ECO变更: {eco.change_summary or eco.title}"
            if items:
                change_types = list(set(i.change_type for i in items))
                changed_part_text += f" (类型: {', '.join(change_types)})"

            # 获取 ecr_id 用于关联
            record_ecr_id = eco.ecr_id

            record = ChangeImpactRecord(
                ecr_id=record_ecr_id,
                prototype_id=None,
                changed_part=changed_part_text,
                matched_rule_id=rule.id,
                impact_level=rule.impact_level,
                affected_cert_types=rule.affected_cert_types,
                analysis_detail=f"规则 '{rule.name}' 匹配: ECO变更 → 影响 {rule.affected_cert_types}",
                org_id=getattr(eco, "org_id", None),
            )
            self.db.add(record)
            self.db.flush()

            impact_records.append({
                "record_id": record.id,
                "eco_id": eco_id,
                "matched_rule": rule.name,
                "impact_level": rule.impact_level,
                "affected_cert_types": affected_cert_types,
            })

        # 按每个 item 的 change_type 匹配
        for item in items:
            item_rules = self._match_rules("eco_change", item.change_type)
            for rule in item_rules:
                affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types

                record = ChangeImpactRecord(
                    ecr_id=eco.ecr_id,
                    prototype_id=None,
                    changed_part=f"ECO明细: {item.object_name or item.object_code} ({item.change_type})",
                    matched_rule_id=rule.id,
                    impact_level=rule.impact_level,
                    affected_cert_types=rule.affected_cert_types,
                    analysis_detail=f"规则 '{rule.name}' 匹配: 变更类型={item.change_type}, 对象={item.object_name} → 影响 {rule.affected_cert_types}",
                    org_id=getattr(eco, "org_id", None),
                )
                self.db.add(record)
                self.db.flush()

                impact_records.append({
                    "record_id": record.id,
                    "eco_id": eco_id,
                    "matched_rule": rule.name,
                    "impact_level": rule.impact_level,
                    "affected_cert_types": affected_cert_types,
                })

        self.db.commit()

        return {
            "success": True,
            "eco_id": eco_id,
            "eco_code": getattr(eco, "code", None),
            "eco_title": getattr(eco, "title", None),
            "overall_impact_level": self._compute_overall_level(impact_records),
            "impact_records": impact_records,
        }

    # ── Prototype 触发 ──────────────────────────────────────

    def analyze_prototype_change(
        self, prototype_id: int, changed_parts: Optional[list[str]] = None
    ) -> dict:
        """分析样机变更对认证的影响

        1. 获取原型信息
        2. 查找该原型关联的 CertificationSample → CertificationProject
        3. 获取该产品的有效证书
        4. 匹配 ChangeImpactRule（同时匹配 part_category 和 prototype_change 规则）
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

        # 4b. 匹配 prototype_change 规则（样机级别的变更触发）
        proto_rules = self._match_rules("prototype_change", prototype.proto_type)
        for rule in proto_rules:
            affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types
            impacted_certs = [
                c for c in active_certificates
                if c.cert_type in affected_cert_types
            ]
            record = ChangeImpactRecord(
                prototype_id=prototype_id,
                changed_part=f"样机变更: {prototype.proto_type} - {prototype.proto_no}",
                matched_rule_id=rule.id,
                impact_level=rule.impact_level,
                affected_cert_types=rule.affected_cert_types,
                analysis_detail=f"规则 '{rule.name}' 匹配: 样机类型={prototype.proto_type} → 影响 {rule.affected_cert_types}",
                org_id=getattr(prototype, "org_id", None),
            )
            self.db.add(record)
            self.db.flush()
            impact_records.append({
                "record_id": record.id,
                "changed_part": f"样机变更: {prototype.proto_type}",
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
        overall_level = self._compute_overall_level(impact_records)

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
        """分析BOM变更对认证的影响（集成ECR/ECO流程）

        通过变更的物料号查找BOM信息，匹配 ChangeImpactRule，
        生成影响记录。产品-证书的精确链路由 CIE ImpactGraph 分析。
        """
        impact_records = []

        # 1. 查找 BOMItem
        bom_item = self.db.query(BOMItem).filter(
            (BOMItem.part_no == new_part_no) | (BOMItem.part_no == old_part_no)
        ).first()

        changed_part_desc = f"BOM物料变更: {new_part_no}"
        if bom_item:
            changed_part_desc = f"BOM变更: {bom_item.part_name or new_part_no} ({bom_item.item_type})"

        # 2. 按 BOM 变更维度匹配规则
        for trigger_val in ["bom_change", new_part_no, old_part_no]:
            rules = self._match_rules("bom_change", trigger_val)
            for rule in rules:
                affected_cert_types = json.loads(rule.affected_cert_types) if isinstance(rule.affected_cert_types, str) else rule.affected_cert_types

                record = ChangeImpactRecord(
                    prototype_id=None,
                    changed_part=changed_part_desc,
                    matched_rule_id=rule.id,
                    impact_level=rule.impact_level,
                    affected_cert_types=rule.affected_cert_types,
                    analysis_detail=(
                        f"规则 '{rule.name}' 匹配: 物料={new_part_no}"
                        f"(原={old_part_no}) → 影响 {rule.affected_cert_types}"
                    ),
                )
                self.db.add(record)
                self.db.flush()

                impact_records.append({
                    "record_id": record.id,
                    "bom_item_id": bom_item_id,
                    "changed_part": new_part_no,
                    "matched_rule": rule.name,
                    "impact_level": rule.impact_level,
                    "affected_cert_types": affected_cert_types,
                })

        self.db.commit()

        return {
            "success": True,
            "bom_item_id": bom_item_id,
            "old_part_no": old_part_no,
            "new_part_no": new_part_no,
            "overall_impact_level": self._compute_overall_level(impact_records),
            "impact_records": impact_records,
            "message": "BOM变更影响分析完成",
        }

    # ── EventBus 事件注册 ──────────────────────────────────

    def register_events(self) -> None:
        """在 EventBus 上注册处理器

        - on('ecr.status_changed') → analyze_by_ecr
        - on('eco.status_changed') → analyze_by_eco
        - on('prototype.updated')  → analyze_prototype_change
        """
        from app.services.events import bus

        bus.on("ecr.status_changed", self._on_ecr_status_changed)
        bus.on("eco.status_changed", self._on_eco_status_changed)
        bus.on("prototype.updated", self._on_prototype_updated)

    # ── EventBus 内部处理器 ────────────────────────────────

    def _on_ecr_status_changed(self, ecr_id: Optional[int] = None, **kwargs) -> None:
        """ECR 状态变更事件处理器"""
        if ecr_id is None:
            return
        try:
            self.analyze_by_ecr(ecr_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "analyze_by_ecr failed for ecr_id=%s: %s", ecr_id, e
            )

    def _on_eco_status_changed(self, eco_id: Optional[int] = None, **kwargs) -> None:
        """ECO 状态变更事件处理器"""
        if eco_id is None:
            return
        try:
            self.analyze_by_eco(eco_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "analyze_by_eco failed for eco_id=%s: %s", eco_id, e
            )

    def _on_prototype_updated(self, prototype_id: Optional[int] = None, **kwargs) -> None:
        """样机更新事件处理器"""
        if prototype_id is None:
            return
        try:
            self.analyze_prototype_change(prototype_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "analyze_prototype_change failed for prototype_id=%s: %s",
                prototype_id, e,
            )

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
