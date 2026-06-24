"""
Phase 6 S2 — 认证中心 种子数据脚本
第一批: CE/CB/UL/SAA, 预留 RoHS/REACH
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.core.database import engine, Base, SessionLocal
from app.models.pm_config import CertStandard, MarketCertification
from app.models.cert_gate_rule import CertificationGateRule

def seed_cert_standards(session):
    """安规标准参考数据"""
    standards = [
        # CE 认证 — 欧盟
        CertStandard(market="EU", standard="EN 14511", key_requirement="能效等级A+++~D", verification_method="实验室测试", cert_cycle="4-6周", sort_order=1),
        CertStandard(market="EU", standard="EN 14825", key_requirement="部分负荷能效SEER/SCOP", verification_method="实验室测试", cert_cycle="4-6周", sort_order=2),
        CertStandard(market="EU", standard="EN 60335-1", key_requirement="安全要求", verification_method="安规测试", cert_cycle="4-6周", sort_order=3),
        CertStandard(market="EU", standard="EN 55014-1", key_requirement="EMC电磁兼容", verification_method="EMC测试", cert_cycle="4-6周", sort_order=4),
        # CB 认证 — 国际CB体系
        CertStandard(market="Global", standard="IEC 60335-1", key_requirement="家用电器安全通用要求", verification_method="CBTL实验室", cert_cycle="6-8周", sort_order=5),
        CertStandard(market="Global", standard="IEC 60335-2-40", key_requirement="热泵/空调特殊要求", verification_method="CBTL实验室", cert_cycle="6-8周", sort_order=6),
        # UL 认证 — 美国
        CertStandard(market="US", standard="UL 484", key_requirement="房间空调器安全标准", verification_method="UL实验室", cert_cycle="8-12周", sort_order=7),
        CertStandard(market="US", standard="UL 1995", key_requirement="暖通空调设备安全标准", verification_method="UL实验室", cert_cycle="8-12周", sort_order=8),
        CertStandard(market="US", standard="AHRI 210/240", key_requirement="性能评级标准SEER2", verification_method="AHRI认证", cert_cycle="8-12周", sort_order=9),
        # SAA 认证 — 澳洲
        CertStandard(market="AU", standard="AS/NZS 60335.1", key_requirement="安全通用要求", verification_method="SAA认证", cert_cycle="6-8周", sort_order=10),
        CertStandard(market="AU", standard="AS/NZS 60335.2.40", key_requirement="空调特殊安全要求", verification_method="SAA认证", cert_cycle="6-8周", sort_order=11),
        CertStandard(market="AU", standard="AS/NZS 3823.2", key_requirement="能效评级", verification_method="实验室测试", cert_cycle="6-8周", sort_order=12),
        # RoHS (预留)
        CertStandard(market="EU", standard="2011/65/EU", key_requirement="有害物质限制(RoHS)", verification_method="化学分析", cert_cycle="2-4周", sort_order=13),
        # REACH (预留)
        CertStandard(market="EU", standard="EC 1907/2006", key_requirement="化学品注册/评估/授权/限制", verification_method="化学分析", cert_cycle="4-8周", sort_order=14),
    ]
    for std in standards:
        session.add(std)
    session.commit()
    print(f"✅ 写入 {len(standards)} 条 cert_standards")

def seed_market_certifications(session):
    """市场认证要求映射"""
    mappings = [
        # 欧盟 — CE
        MarketCertification(market_code="EU", cert_type="safety", cert_standard="CE (EN 60335-1)", description="欧盟安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="EU", cert_type="energy", cert_standard="CE (EN 14511/14825)", description="欧盟能效标签", is_required="true", sort_order=2),
        MarketCertification(market_code="EU", cert_type="emc", cert_standard="CE (EN 55014-1)", description="欧盟EMC认证", is_required="true", sort_order=3),
        MarketCertification(market_code="EU", cert_type="environmental", cert_standard="RoHS/REACH", description="环保合规", is_required="true", sort_order=4),
        # 美国 — UL
        MarketCertification(market_code="US", cert_type="safety", cert_standard="UL 484/UL 1995", description="美国安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="US", cert_type="energy", cert_standard="AHRI 210/240 (SEER2)", description="美国能效认证", is_required="true", sort_order=2),
        MarketCertification(market_code="US", cert_type="emc", cert_standard="FCC Part 15", description="美国EMC认证", is_required="true", sort_order=3),
        # 澳洲 — SAA
        MarketCertification(market_code="AU", cert_type="safety", cert_standard="SAA (AS/NZS 60335)", description="澳洲安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="AU", cert_type="energy", cert_standard="AS/NZS 3823.2", description="澳洲能效认证", is_required="true", sort_order=2),
        MarketCertification(market_code="AU", cert_type="emc", cert_standard="AS/NZS CISPR 14", description="澳洲EMC认证", is_required="true", sort_order=3),
        # 沙特
        MarketCertification(market_code="SA", cert_type="safety", cert_standard="SASO 2663", description="沙特安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="SA", cert_type="energy", cert_standard="SASO 2874 (EER)", description="沙特能效认证", is_required="true", sort_order=2),
        # 东南亚通用 — CB
        MarketCertification(market_code="TH", cert_type="safety", cert_standard="CB (IEC 60335)", description="泰国安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="VN", cert_type="safety", cert_standard="CB (IEC 60335)", description="越南安全认证", is_required="true", sort_order=1),
        MarketCertification(market_code="ID", cert_type="safety", cert_standard="CB/SNI", description="印尼安全认证", is_required="true", sort_order=1),
    ]
    for m in mappings:
        session.add(m)
    session.commit()
    print(f"✅ 写入 {len(mappings)} 条 market_certifications")

def seed_cert_gate_rules(session):
    """认证门禁规则 — M6~M9 门禁 × 认证类型"""
    rules = [
        # M6: 样机完成 → 认证启动
        CertificationGateRule(name="M6 样机 → CE启动", gate_code="M6", cert_type="CE", is_required=True, auto_block=True, priority=10),
        CertificationGateRule(name="M6 样机 → CB启动", gate_code="M6", cert_type="CB", is_required=True, auto_block=True, priority=20),
        CertificationGateRule(name="M6 样机 → UL启动", gate_code="M6", cert_type="UL", is_required=False, auto_block=False, priority=30),
        CertificationGateRule(name="M6 样机 → SAA启动", gate_code="M6", cert_type="SAA", is_required=True, auto_block=True, priority=30),
        # M7: 认证完成
        CertificationGateRule(name="M7 认证完成 → CE", gate_code="M7", cert_type="CE", is_required=True, auto_block=True, priority=10),
        CertificationGateRule(name="M7 认证完成 → CB", gate_code="M7", cert_type="CB", is_required=True, auto_block=True, priority=20),
        CertificationGateRule(name="M7 认证完成 → UL", gate_code="M7", cert_type="UL", is_required=False, auto_block=False, priority=30),
        CertificationGateRule(name="M7 认证完成 → SAA", gate_code="M7", cert_type="SAA", is_required=True, auto_block=True, priority=30),
        # M8: 证书获证
        CertificationGateRule(name="M8 获证 → CE", gate_code="M8", cert_type="CE", is_required=True, auto_block=True, priority=10),
        CertificationGateRule(name="M8 获证 → UL", gate_code="M8", cert_type="UL", is_required=True, auto_block=True, priority=20),
        # M9: 量产放行
        CertificationGateRule(name="M9 量产 → CE有效", gate_code="M9", cert_type="CE", is_required=True, auto_block=True, priority=10),
        CertificationGateRule(name="M9 量产 → UL有效", gate_code="M9", cert_type="UL", is_required=True, auto_block=True, priority=20),
        CertificationGateRule(name="M9 量产 → SAA有效", gate_code="M9", cert_type="SAA", is_required=True, auto_block=True, priority=30),
        CertificationGateRule(name="M9 量产 → CB有效", gate_code="M9", cert_type="CB", is_required=False, auto_block=False, priority=40),
    ]
    for r in rules:
        session.add(r)
    session.commit()
    print(f"✅ 写入 {len(rules)} 条 certification_gate_rules")

if __name__ == "__main__":
    # 检查表是否存在
    from sqlalchemy import inspect
    insp = inspect(engine)
    existing = insp.get_table_names()
    required = ["cert_standards", "market_certifications", "certification_gate_rules"]
    missing = [t for t in required if t not in existing]
    if missing:
        print(f"❌ 表不存在: {missing}，请先创建表")
        print("用以下命令创建所有表:")
        print("  from app.core.database import Base; Base.metadata.create_all(bind=engine)")
        sys.exit(1)
    
    session = SessionLocal()
    try:
        # 先清空（幂等）
        for t in reversed(required):
            session.execute(text(f"DELETE FROM {t}"))
        session.commit()
        
        seed_cert_standards(session)
        seed_market_certifications(session)
        seed_cert_gate_rules(session)
        print("\n🎉 S2 种子数据填充完成!")
    except Exception as e:
        session.rollback()
        print(f"❌ 出错: {e}")
        raise
    finally:
        session.close()
