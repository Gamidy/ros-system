"""
Phase 6 S1 — 种子数据脚本
初始化标准实验库 + 目标市场种子数据
"""
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.target_market import TargetMarket, RequiredTest, RequiredCertification, RequiredStandard
from app.core.enums import TargetMarketCode


def seed_target_markets(db: Session):
    """初始化目标市场种子数据"""
    print("正在初始化目标市场数据...")

    # ── 欧盟 ──
    eu = db.query(TargetMarket).filter(TargetMarket.market_code == "EU").first()
    if not eu:
        eu = TargetMarket(market_code="EU", market_name="欧盟")
        db.add(eu)
        db.flush()

        db.add(RequiredTest(target_market_id=eu.id, test_category="performance", standard="EN 14511", sort_order=1))
        db.add(RequiredTest(target_market_id=eu.id, test_category="energy", standard="EN 14825", sort_order=2))
        db.add(RequiredTest(target_market_id=eu.id, test_category="noise", standard="EN 12102", sort_order=3))
        db.add(RequiredTest(target_market_id=eu.id, test_category="safety", standard="EN 60335-2-40", sort_order=4))
        db.add(RequiredTest(target_market_id=eu.id, test_category="emc", standard="EN 55014", sort_order=5))

        db.add(RequiredCertification(target_market_id=eu.id, cert_type="CE", cert_body="欧盟公告机构", sort_order=1))
        db.add(RequiredCertification(target_market_id=eu.id, cert_type="ERP", cert_body="欧盟", sort_order=2))

        db.add(RequiredStandard(target_market_id=eu.id, standard_code="EN 14511", standard_name="空调器能效测试", is_core=True))
        db.add(RequiredStandard(target_market_id=eu.id, standard_code="EN 14825", standard_name="空调器部分负荷测试", is_core=True))
        db.add(RequiredStandard(target_market_id=eu.id, standard_code="EN 60335-2-40", standard_name="家用电器安全", is_core=True))
        print("  ✅ 欧盟 (EU) 初始化完成")

    # ── 美国 ──
    us = db.query(TargetMarket).filter(TargetMarket.market_code == "US").first()
    if not us:
        us = TargetMarket(market_code="US", market_name="美国")
        db.add(us)
        db.flush()

        db.add(RequiredTest(target_market_id=us.id, test_category="performance", standard="AHRI 210/240", sort_order=1))
        db.add(RequiredTest(target_market_id=us.id, test_category="energy", standard="DOE 10 CFR Part 430", sort_order=2))
        db.add(RequiredTest(target_market_id=us.id, test_category="safety", standard="UL 484", sort_order=3))

        db.add(RequiredCertification(target_market_id=us.id, cert_type="UL", cert_body="UL", sort_order=1))
        db.add(RequiredCertification(target_market_id=us.id, cert_type="AHRI", cert_body="AHRI", sort_order=2))
        db.add(RequiredCertification(target_market_id=us.id, cert_type="Energy Star", cert_body="EPA", sort_order=3))

        db.add(RequiredStandard(target_market_id=us.id, standard_code="AHRI 210/240", standard_name="单元式空调性能测试", is_core=True))
        db.add(RequiredStandard(target_market_id=us.id, standard_code="UL 484", standard_name="房间空调安全标准", is_core=True))
        print("  ✅ 美国 (US) 初始化完成")

    # ── 澳洲 ──
    au = db.query(TargetMarket).filter(TargetMarket.market_code == "AU").first()
    if not au:
        au = TargetMarket(market_code="AU", market_name="澳洲")
        db.add(au)
        db.flush()

        db.add(RequiredTest(target_market_id=au.id, test_category="performance", standard="AS/NZS 3823", sort_order=1))
        db.add(RequiredTest(target_market_id=au.id, test_category="energy", standard="AS/NZS 3823.2", sort_order=2))
        db.add(RequiredTest(target_market_id=au.id, test_category="safety", standard="AS/NZS 60335.2.40", sort_order=3))

        db.add(RequiredCertification(target_market_id=au.id, cert_type="SAA", cert_body="SAA Approvals", sort_order=1))
        db.add(RequiredCertification(target_market_id=au.id, cert_type="GEMS", cert_body="澳洲政府", sort_order=2))

        db.add(RequiredStandard(target_market_id=au.id, standard_code="AS/NZS 3823", standard_name="空调器性能标准", is_core=True))
        db.add(RequiredStandard(target_market_id=au.id, standard_code="AS/NZS 60335.2.40", standard_name="家用电器安全标准", is_core=True))
        print("  ✅ 澳洲 (AU) 初始化完成")

    # ── 中国 ──
    cn = db.query(TargetMarket).filter(TargetMarket.market_code == "CN").first()
    if not cn:
        cn = TargetMarket(market_code="CN", market_name="中国")
        db.add(cn)
        db.flush()

        db.add(RequiredTest(target_market_id=cn.id, test_category="performance", standard="GB/T 7725", sort_order=1))
        db.add(RequiredTest(target_market_id=cn.id, test_category="energy", standard="GB 21455", sort_order=2))
        db.add(RequiredTest(target_market_id=cn.id, test_category="noise", standard="GB/T 7725", sort_order=3))
        db.add(RequiredTest(target_market_id=cn.id, test_category="safety", standard="GB 4706.32", sort_order=4))

        db.add(RequiredCertification(target_market_id=cn.id, cert_type="CCC", cert_body="中国质量认证中心", sort_order=1))

        db.add(RequiredStandard(target_market_id=cn.id, standard_code="GB/T 7725", standard_name="房间空气调节器", is_core=True))
        db.add(RequiredStandard(target_market_id=cn.id, standard_code="GB 21455", standard_name="空调器能效限定值", is_core=True))
        db.add(RequiredStandard(target_market_id=cn.id, standard_code="GB 4706.32", standard_name="家用电器安全-空调", is_core=True))
        print("  ✅ 中国 (CN) 初始化完成")

    # ── 沙特 ──
    sa = db.query(TargetMarket).filter(TargetMarket.market_code == "SA").first()
    if not sa:
        sa = TargetMarket(market_code="SA", market_name="沙特")
        db.add(sa)
        db.flush()

        db.add(RequiredTest(target_market_id=sa.id, test_category="performance", standard="SASO 2663", sort_order=1))
        db.add(RequiredTest(target_market_id=sa.id, test_category="energy", standard="SASO 2663", sort_order=2))

        db.add(RequiredCertification(target_market_id=sa.id, cert_type="SASO", cert_body="SASO", sort_order=1))

        db.add(RequiredStandard(target_market_id=sa.id, standard_code="SASO 2663", standard_name="空调器能效标准", is_core=True))
        print("  ✅ 沙特 (SA) 初始化完成")

    db.commit()
    print("  目标市场数据初始化完成!")


def clear_seed_data(db: Session):
    """清除种子数据（用于重置）"""
    db.query(RequiredStandard).delete()
    db.query(RequiredCertification).delete()
    db.query(RequiredTest).delete()
    db.query(TargetMarket).delete()
    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_target_markets(db)
    except Exception as e:
        db.rollback()
        print(f"❌ 种子数据初始化失败: {e}")
        raise
    finally:
        db.close()
