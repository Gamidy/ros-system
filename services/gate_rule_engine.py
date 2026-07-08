"""
Gate Rule Engine — 可配置规则评估引擎

按 product_line + customer + gate_code 动态匹配规则
支持 fallback 到原有 pass_conditions
"""
import json
from sqlalchemy.orm import Session
from app.models.gate_rule import GateRule, GateRuleItem, GateEvalRecord
from app.models.verification_requirement import VerificationRequirement
from app.models.test import Prototype, TestResult, TestRequest
from app.models.project import Project
from app.core.enums import (
    GateEvalResult, VerificationRequirementStatus,
    VerificationRequirementCategory, PrototypeType,
)


class GateRuleEngine:
    """Gate规则引擎 — 评估Gate是否满足前置条件"""

    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, project_id: int, gate_code: str, product_line: str = None,
                 customer: str = None) -> dict:
        """
        评估指定Gate的规则满足情况

        Args:
            project_id: 项目ID
            gate_code: Gate编号 (M4/M5/M6/...)
            product_line: 产品线（从项目信息获取）
            customer: 客户（从项目信息获取）

        Returns:
            dict: {
                "overall_pass": bool,
                "rule_id": int | None,
                "rule_name": str | None,
                "checks": [{"category": str, "prototype_type": str, "pass": bool, "detail": str}],
                "auto_block": bool,
                "will_block": bool
            }
        """
        # 1. 查找匹配的规则
        rule = self._find_matching_rule(gate_code, product_line, customer)

        if not rule:
            # 无匹配规则 — 返回 None 让调用方 fallback
            return {
                "overall_pass": True,
                "rule_id": None,
                "rule_name": None,
                "checks": [],
                "auto_block": False,
                "will_block": False,
                "message": "未匹配到Gate规则，沿用原有逻辑"
            }

        # 2. 逐项检查规则条目
        checks = []
        all_pass = True

        for item in rule.items:
            check = self._check_item(project_id, item, rule.gate_code)
            checks.append(check)
            if not check["pass"]:
                all_pass = False

        # 3. 综合判定
        overall_pass = all_pass if rule.all_pass else True
        will_block = rule.auto_block and not overall_pass

        # 4. 记录评估日志
        self._log_evaluation(rule.id, project_id, gate_code, overall_pass, checks)

        return {
            "overall_pass": overall_pass,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "checks": checks,
            "auto_block": rule.auto_block,
            "will_block": will_block,
        }

    def _find_matching_rule(self, gate_code: str, product_line: str = None,
                            customer: str = None) -> GateRule | None:
        """按优先级查找匹配的规则：精确匹配 > 通配"""
        rules = self.db.query(GateRule).filter(
            GateRule.gate_code == gate_code,
            GateRule.status == "active"
        ).order_by(GateRule.priority).all()

        for rule in rules:
            # 检查 product_line 匹配
            pl_match = (rule.product_line is None or rule.product_line == product_line)
            # 检查 customer 匹配
            c_match = (rule.customer is None or rule.customer == customer)
            if pl_match and c_match:
                return rule

        return None

    def _check_item(self, project_id: int, item: GateRuleItem, gate_code: str) -> dict:
        """检查单条规则条目"""
        # 检查要求的验证需求
        if item.required_vr_category:
            return self._check_vr_requirement(project_id, item.required_vr_category, gate_code)

        # 检查要求的样机类型
        if item.required_prototype_type:
            return self._check_prototype_requirement(project_id, item.required_prototype_type)

        return {"category": None, "prototype_type": None, "pass": True, "detail": "无要求"}

    def _check_vr_requirement(self, project_id: int, category: str, gate_code: str) -> dict:
        """检查验证需求是否满足"""
        vrs = self.db.query(VerificationRequirement).filter(
            VerificationRequirement.project_id == project_id,
            VerificationRequirement.category == category,
            VerificationRequirement.gate_code == gate_code,
        ).all()

        if not vrs:
            return {
                "category": category,
                "prototype_type": None,
                "pass": False,
                "detail": f"未找到分类「{category}」的验证需求"
            }

        all_verified = all(vr.status == VerificationRequirementStatus.VERIFIED.value for vr in vrs)
        failed = [vr for vr in vrs if vr.status == VerificationRequirementStatus.FAILED.value]

        if all_verified:
            return {
                "category": category,
                "prototype_type": None,
                "pass": True,
                "detail": f"全部通过 ({len(vrs)}项)"
            }
        elif failed:
            return {
                "category": category,
                "prototype_type": None,
                "pass": False,
                "detail": f"失败 {len(failed)}项: {', '.join(vr.title for vr in failed[:3])}"
            }
        else:
            return {
                "category": category,
                "prototype_type": None,
                "pass": False,
                "detail": f"待验证: {sum(1 for vr in vrs if vr.status == 'pending')}项"
            }

    def _check_prototype_requirement(self, project_id: int, proto_type: str) -> dict:
        """检查样机类型是否已完成"""
        prototypes = self.db.query(Prototype).filter(
            Prototype.project_id == project_id,
            Prototype.version == proto_type,
        ).all()

        if not prototypes:
            return {
                "category": None,
                "prototype_type": proto_type,
                "pass": False,
                "detail": f"未创建类型「{proto_type}」的样机"
            }

        completed = [p for p in prototypes if p.status == "done"]
        if completed:
            return {
                "category": None,
                "prototype_type": proto_type,
                "pass": True,
                "detail": f"已完成 ({len(completed)}台)"
            }
        else:
            return {
                "category": None,
                "prototype_type": proto_type,
                "pass": False,
                "detail": f"样机已创建但未完成测试 ({len(prototypes)}台)"
            }

    def _log_evaluation(self, rule_id: int, project_id: int, gate_code: str,
                        passed: bool, checks: list) -> None:
        """记录评估日志"""
        record = GateEvalRecord(
            rule_id=rule_id,
            project_id=project_id,
            gate_code=gate_code,
            result=GateEvalResult.PASS.value if passed else GateEvalResult.BLOCKED.value,
            detail=json.dumps(checks, ensure_ascii=False),
            evaluated_by="auto",
        )
        self.db.add(record)
        self.db.commit()
