"""Phase 6 S2 — 认证门禁评估服务

评估认证Gate门禁：按 target_market + gate_code 匹配 CertificationGateRule，
检查项目是否已取得要求的认证。
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.cert_gate_rule import CertificationGateRule
from app.models.certification import Certificate, CertificationProject


class CertGateEvalService:
    """认证门禁评估服务"""

    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, project_id: int, gate_code: str) -> dict:
        """评估认证门禁

        1. 查询 CertificationGateRule
        2. 按 target_market + gate_code 匹配
        3. 检查该项目是否已取得要求的认证
        4. 返回评估结果
        """
        # 1. 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "message": f"项目 {project_id} 不存在"}

        # 解析项目的 target_market
        market_codes = []
        if project.target_market:
            market_codes = [m.strip() for m in project.target_market.split(",") if m.strip()]

        # 2. 查询规则：按 gate_code + target_market_id 匹配
        rules = self.db.query(CertificationGateRule).filter(
            CertificationGateRule.gate_code == gate_code,
            CertificationGateRule.status == "active",
        ).all()

        if not rules:
            return {
                "success": True,
                "project_id": project_id,
                "gate_code": gate_code,
                "overall_pass": True,
                "checks": [],
                "message": f"Gate '{gate_code}' 未配置认证门禁规则，默认放行",
            }

        # 3. 检查每个规则
        checks = []
        all_pass = True

        for rule in rules:
            # 如果有 target_market_id 限制，检查是否匹配
            if rule.target_market_id is not None:
                # 看项目的 market_codes 是否能匹配到该 target_market
                from app.models.target_market import TargetMarket
                tm = self.db.query(TargetMarket).filter(
                    TargetMarket.id == rule.target_market_id
                ).first()
                if tm and tm.market_code not in market_codes:
                    continue  # 不匹配当前项目的市场，跳过

            # 检查该项目是否有对应 cert_type 的有效证书
            has_cert = self._check_certification(project_id, rule.cert_type)

            check = {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "gate_code": rule.gate_code,
                "cert_type": rule.cert_type,
                "is_required": rule.is_required,
                "has_certification": has_cert,
                "pass": has_cert if rule.is_required else True,
            }
            checks.append(check)

            if rule.is_required and not has_cert:
                all_pass = False

        # 是否有 auto_block 规则不满足
        blocking_rules = [c for c in checks if not c["pass"] and c["is_required"]]
        has_block = any(
            r for r in rules
            if r.auto_block and r.id in [c["rule_id"] for c in blocking_rules]
        )

        return {
            "success": True,
            "project_id": project_id,
            "gate_code": gate_code,
            "overall_pass": all_pass,
            "will_block": has_block and not all_pass,
            "checks": checks,
        }

    def _check_certification(self, project_id: int, cert_type: str) -> bool:
        """检查项目是否已有指定类型的有效证书

        通过 CertificationProject → CertificationSample → CertificationExecution
        → CertificationResult → Certificate 链路查找
        """
        # 直接查该项目下关联的有效证书
        cert_projects = self.db.query(CertificationProject).filter(
            CertificationProject.project_id == project_id,
        ).all()

        cp_ids = [cp.id for cp in cert_projects]
        if not cp_ids:
            return False

        # 通过 CertificationSample → CertificationExecution → CertificationResult → Certificate
        from app.models.certification import CertificationSample, CertificationExecution, CertificationResult
        certs = self.db.query(Certificate).join(
            CertificationResult, Certificate.cert_result_id == CertificationResult.id
        ).join(
            CertificationExecution, CertificationResult.cert_execution_id == CertificationExecution.id
        ).join(
            CertificationSample, CertificationExecution.cert_sample_id == CertificationSample.id
        ).filter(
            CertificationSample.cert_project_id.in_(cp_ids),
            Certificate.cert_type == cert_type,
            Certificate.status == "active",
        ).count()

        return certs > 0
