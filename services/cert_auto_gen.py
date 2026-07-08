"""Phase 6 S2 — 认证需求自动生成引擎

当 Project 设置了 target_market 时，自动从 TargetMarket.RequiredCertification
生成 CertificationRequirement，同时创建 CertificationProject，
并记录生成日志到 CertAutoGenLog。
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.target_market import TargetMarket, RequiredCertification
from app.models.certification import CertificationRequirement, CertificationProject
from app.models.cert_auto_gen import CertAutoGenLog
from app.core.enums_s2 import CertRequirementSource, CertProjectStatus, CertExecutionStatus
from datetime import date, datetime


def _gen_cert_project_code() -> str:
    """生成认证项目编号: CP-YYYYMMDD-XXXX"""
    from uuid import uuid4
    return f"CP-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4].upper()}"


class CertAutoGenService:
    """认证需求自动生成引擎"""

    def __init__(self, db: Session):
        self.db = db

    def generate_from_project(self, project_id: int) -> dict:
        """项目设置目标市场后，自动生成认证需求和认证项目

        1. 获取项目信息（含 target_market 字段）
        2. 解析 target_market 逗号分隔的市场代码列表
        3. 查找 TargetMarket
        4. 获取 RequiredCertification
        5. 为每个 cert_type 创建 CertificationRequirement
        6. 创建 CertificationProject
        7. 记录日志到 CertAutoGenLog
        8. 返回生成结果
        """
        # 1. 获取项目信息
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "message": f"项目 {project_id} 不存在"}

        if not project.target_market:
            return {"success": False, "message": f"项目 {project_id} 未设置 target_market"}

        # 2. 解析 target_market 逗号分隔
        market_codes = [m.strip() for m in project.target_market.split(",") if m.strip()]
        if not market_codes:
            return {"success": False, "message": "target_market 为空"}

        generated_reqs = []
        generated_cert_project_ids = []
        overall_status = "success"
        errors = []

        for market_code in market_codes:
            # 3. 查找 TargetMarket
            tm = self.db.query(TargetMarket).filter(
                TargetMarket.market_code == market_code
            ).first()
            if not tm:
                errors.append(f"目标市场代码 '{market_code}' 未找到")
                overall_status = "partial"
                continue

            # 4. 获取 RequiredCertification
            required_certs = self.db.query(RequiredCertification).filter(
                RequiredCertification.target_market_id == tm.id
            ).all()
            if not required_certs:
                errors.append(f"目标市场 '{market_code}' 未配置 RequiredCertification")
                overall_status = "partial"
                continue

            # 5. 为每个 cert_type 创建 CertificationRequirement
            cert_types = []
            for rc in required_certs:
                # 检查是否已存在相同 project + target_market + cert_type
                existing = self.db.query(CertificationRequirement).filter(
                    CertificationRequirement.project_id == project.id,
                    CertificationRequirement.target_market_id == tm.id,
                    CertificationRequirement.cert_type == rc.cert_type,
                ).first()
                if existing:
                    continue

                req = CertificationRequirement(
                    project_id=project.id,
                    target_market_id=tm.id,
                    cert_type=rc.cert_type,
                    cert_body=rc.cert_body,
                    is_mandatory=rc.is_mandatory,
                    status=CertExecutionStatus.PENDING.value,
                    source_type=CertRequirementSource.TARGET_MARKET.value,
                    org_id=getattr(project, "org_id", None),
                )
                self.db.add(req)
                self.db.flush()
                cert_types.append(rc.cert_type)
                generated_reqs.append({
                    "id": req.id,
                    "cert_type": rc.cert_type,
                    "target_market_id": tm.id,
                })

            if not cert_types:
                errors.append(f"目标市场 '{market_code}' 的认证需求已存在，跳过")
                continue

            # 6. 创建 CertificationProject
            cert_project = CertificationProject(
                code=_gen_cert_project_code(),
                name=f"{project.name} - {tm.market_name}",
                project_id=project.id,
                target_market_id=tm.id,
                cert_types=json.dumps(cert_types, ensure_ascii=False),
                status=CertProjectStatus.PLANNING.value,
                org_id=getattr(project, "org_id", None),
            )
            self.db.add(cert_project)
            self.db.flush()
            generated_cert_project_ids.append(cert_project.id)

        # 7. 记录日志到 CertAutoGenLog
        log_entry = CertAutoGenLog(
            project_id=project.id,
            target_market_id=None,  # 可能关联多个市场
            generated_cert_requirements=json.dumps(generated_reqs, ensure_ascii=False),
            generated_cert_project_id=generated_cert_project_ids[0] if generated_cert_project_ids else None,
            status=overall_status,
            message="; ".join(errors) if errors else "自动生成完成",
            org_id=getattr(project, "org_id", None),
        )
        self.db.add(log_entry)
        self.db.commit()

        # 8. 返回生成结果
        return {
            "success": overall_status != "failed",
            "status": overall_status,
            "project_id": project.id,
            "project_name": project.name,
            "market_codes": market_codes,
            "generated_requirements": generated_reqs,
            "generated_cert_project_ids": generated_cert_project_ids,
            "errors": errors,
        }

    def generate_from_project_cron(self) -> list[dict]:
        """定时任务：检查所有已设置目标市场但未生成认证需求的项目"""
        results = []
        # 查找所有已设置 target_market 的项目
        projects = self.db.query(Project).filter(
            Project.target_market.isnot(None),
            Project.target_market != "",
        ).all()

        for project in projects:
            # 检查是否已有 CertificationRequirement
            existing_count = self.db.query(CertificationRequirement).filter(
                CertificationRequirement.project_id == project.id,
            ).count()

            if existing_count == 0:
                result = self.generate_from_project(project.id)
                results.append(result)

        return results
