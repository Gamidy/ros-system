"""安规管理模块 — 种子数据（幂等可重复执行）"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.core.database import SessionLocal
from app.models.safety import (
    SafetyStandard, SafetyInspectionItem,
    SupplierSafetyQualification, SupplierSafetyAuditRecord,
)
from datetime import date


def seed_safety(db):
    """填充安规管理初始数据"""
    # ── 安全标准种子数据（幂等：检查标准编号） ──
    existing_codes = {s.standard_code for s in db.query(SafetyStandard).all()}

    standards = [
        # 国际通用安全标准
        {"standard_code": "IEC 60335-1", "standard_name_cn": "家用和类似用途电器安全 通用要求",
         "standard_name_en": "Household and similar electrical appliances - Safety - Part 1: General requirements",
         "issuing_body": "IEC", "applicable_market": "全球", "standard_type": "safety",
         "version": "6.0", "publish_date": date(2020, 9, 1), "effective_date": date(2021, 3, 1),
         "status": "active"},
        {"standard_code": "IEC 60335-2-40", "standard_name_cn": "家用和类似用途电器安全 热泵、空调器和除湿机的特殊要求",
         "standard_name_en": "Safety of household and similar appliances - Part 2-40: Particular requirements for electrical heat pumps, air-conditioners and dehumidifiers",
         "issuing_body": "IEC", "applicable_market": "全球", "standard_type": "safety",
         "version": "7.0", "publish_date": date(2022, 1, 15), "effective_date": date(2022, 7, 15),
         "status": "active"},
        # 中国国标
        {"standard_code": "GB/T 7725", "standard_name_cn": "房间空气调节器",
         "standard_name_en": "Room air conditioners",
         "issuing_body": "中国国家标准化管理委员会", "applicable_market": "中国",
         "standard_type": "safety", "version": "2021",
         "publish_date": date(2021, 3, 9), "effective_date": date(2022, 3, 1),
         "status": "active"},
        {"standard_code": "GB 4706.1", "standard_name_cn": "家用和类似用途电器安全 通用要求",
         "standard_name_en": "Safety of household and similar electrical appliances - General requirements",
         "issuing_body": "中国国家标准化管理委员会", "applicable_market": "中国",
         "standard_type": "safety", "version": "2018",
         "publish_date": date(2018, 12, 28), "effective_date": date(2020, 1, 1),
         "status": "active"},
        {"standard_code": "GB 4706.32", "standard_name_cn": "家用和类似用途电器安全 热泵、空调器和除湿机的特殊要求",
         "standard_name_en": "Safety of household and similar electrical appliances - Particular requirements for heat pumps, air-conditioners and dehumidifiers",
         "issuing_body": "中国国家标准化管理委员会", "applicable_market": "中国",
         "standard_type": "safety", "version": "2019",
         "publish_date": date(2019, 6, 4), "effective_date": date(2020, 6, 4),
         "status": "active"},
        # 美国/北美
        {"standard_code": "UL 484", "standard_name_cn": "房间空调器安全标准",
         "standard_name_en": "Standard for Safety for Room Air Conditioners",
         "issuing_body": "UL", "applicable_market": "美国",
         "standard_type": "safety", "version": "10th",
         "publish_date": date(2019, 5, 1), "effective_date": date(2020, 1, 1),
         "status": "active"},
        {"standard_code": "UL 1995", "standard_name_cn": "暖通空调设备安全标准",
         "standard_name_en": "Standard for Safety for Heating and Cooling Equipment",
         "issuing_body": "UL", "applicable_market": "美国",
         "standard_type": "safety", "version": "5th",
         "publish_date": date(2020, 3, 1), "effective_date": date(2020, 9, 1),
         "status": "active"},
        # 欧盟
        {"standard_code": "EN 60335-1", "standard_name_cn": "家用和类似用途电器安全 通用要求（欧盟版）",
         "standard_name_en": "Safety of household and similar appliances - General requirements (European version)",
         "issuing_body": "CENELEC", "applicable_market": "欧盟",
         "standard_type": "safety", "version": "A15:2021",
         "publish_date": date(2021, 6, 1), "effective_date": date(2022, 1, 1),
         "status": "active"},
        {"standard_code": "EN 60335-2-40", "standard_name_cn": "热泵、空调器和除湿机的特殊要求（欧盟版）",
         "standard_name_en": "Particular requirements for heat pumps, air-conditioners and dehumidifiers (European version)",
         "issuing_body": "CENELEC", "applicable_market": "欧盟",
         "standard_type": "safety", "version": "A13:2021",
         "publish_date": date(2021, 6, 1), "effective_date": date(2022, 1, 1),
         "status": "active"},
        # 澳大利亚/新西兰
        {"standard_code": "AS/NZS 60335.1", "standard_name_cn": "家用和类似用途电器安全 通用要求（澳新版）",
         "standard_name_en": "Safety of household and similar appliances - General requirements (AU/NZ version)",
         "issuing_body": "Standards Australia", "applicable_market": "澳大利亚/新西兰",
         "standard_type": "safety", "version": "2022",
         "publish_date": date(2022, 3, 1), "effective_date": date(2022, 9, 1),
         "status": "active"},
        {"standard_code": "AS/NZS 60335.2.40", "standard_name_cn": "家用和类似用途电器安全 热泵、空调器和除湿机的特殊要求（澳新版）",
         "standard_name_en": "Safety of household and similar appliances - Part 2.40: Particular requirements for heat pumps, air-conditioners and dehumidifiers (AU/NZ version)",
         "issuing_body": "Standards Australia", "applicable_market": "澳大利亚/新西兰",
         "standard_type": "safety", "version": "2022",
         "publish_date": date(2022, 3, 1), "effective_date": date(2022, 9, 1),
         "status": "active"},
        # 沙特
        {"standard_code": "SASO 2663", "standard_name_cn": "沙特空调器能效和安全要求",
         "standard_name_en": "Saudi Arabian air conditioner energy efficiency and safety requirements",
         "issuing_body": "SASO", "applicable_market": "沙特阿拉伯",
         "standard_type": "safety", "version": "2021",
         "publish_date": date(2021, 1, 1), "effective_date": date(2021, 7, 1),
         "status": "active"},
        # 能效标准（非安规，用于参考）
        {"standard_code": "IEC 61591", "standard_name_cn": "家用抽油烟机性能测试方法",
         "standard_name_en": "Performance test methods for household range hoods",
         "issuing_body": "IEC", "applicable_market": "全球",
         "standard_type": "performance", "version": "2.0",
         "publish_date": date(2020, 4, 1), "effective_date": date(2020, 10, 1),
         "status": "active"},
    ]

    created_count = 0
    for std in standards:
        if std["standard_code"] not in existing_codes:
            db.add(SafetyStandard(**std))
            existing_codes.add(std["standard_code"])
            created_count += 1
    print(f"  ✅ 安全标准: 新增 {created_count} 条")

    # ── 安规检测项种子数据 ──
    existing_items = {(i.standard_id, i.item_code) for i in db.query(SafetyInspectionItem).all()}

    # 获取刚插入的标准ID
    iec_60335_1 = db.query(SafetyStandard).filter(
        SafetyStandard.standard_code == "IEC 60335-1").first()
    iec_60335_2_40 = db.query(SafetyStandard).filter(
        SafetyStandard.standard_code == "IEC 60335-2-40").first()
    gb4706_1 = db.query(SafetyStandard).filter(
        SafetyStandard.standard_code == "GB 4706.1").first()
    ul484 = db.query(SafetyStandard).filter(
        SafetyStandard.standard_code == "UL 484").first()

    inspection_items = []

    if iec_60335_1:
        inspection_items.extend([
            {"standard_id": iec_60335_1.id, "item_code": "IEC-001",
             "item_name": "接地电阻", "inspection_category": "electrical",
             "param_name": "接地电阻值", "standard_value_max": 0.1, "unit": "Ω",
             "test_method": "接地电阻测试仪测量", "reference_clause": "Clause 27.5",
             "sort_order": 1},
            {"standard_id": iec_60335_1.id, "item_code": "IEC-002",
             "item_name": "泄漏电流", "inspection_category": "electrical",
             "param_name": "泄漏电流", "standard_value_max": 0.75, "unit": "mA",
             "test_method": "泄漏电流测试仪", "reference_clause": "Clause 13.2",
             "sort_order": 2},
            {"standard_id": iec_60335_1.id, "item_code": "IEC-003",
             "item_name": "介电强度", "inspection_category": "electrical",
             "param_name": "测试电压", "standard_value_nominal": "1250V/1min", "unit": "V",
             "test_method": "耐压测试仪", "reference_clause": "Clause 16.3",
             "sort_order": 3},
            {"standard_id": iec_60335_1.id, "item_code": "IEC-004",
             "item_name": "爬电距离", "inspection_category": "electrical",
             "param_name": "最小爬电距离", "standard_value_min": 3.0, "unit": "mm",
             "test_method": "卡尺/量规测量", "reference_clause": "Clause 29.2",
             "sort_order": 4},
            {"standard_id": iec_60335_1.id, "item_code": "IEC-005",
             "item_name": "电气间隙", "inspection_category": "electrical",
             "param_name": "最小电气间隙", "standard_value_min": 3.0, "unit": "mm",
             "test_method": "量规测量", "reference_clause": "Clause 29.1",
             "sort_order": 5},
        ])

    if iec_60335_2_40:
        inspection_items.extend([
            {"standard_id": iec_60335_2_40.id, "item_code": "IEC2-001",
             "item_name": "制冷剂泄漏检测", "inspection_category": "mechanical",
             "param_name": "制冷剂年泄漏率", "standard_value_max": 5.0, "unit": "%",
             "test_method": "检漏仪检测", "reference_clause": "Clause 22.106",
             "sort_order": 1},
            {"standard_id": iec_60335_2_40.id, "item_code": "IEC2-002",
             "item_name": "管路压力测试", "inspection_category": "mechanical",
             "param_name": "测试压力", "standard_value_min": 4.15, "unit": "MPa",
             "test_method": "压力测试台", "reference_clause": "Clause 22.107",
             "sort_order": 2},
            {"standard_id": iec_60335_2_40.id, "item_code": "IEC2-003",
             "item_name": "风扇防护", "inspection_category": "mechanical",
             "param_name": "防护网间隙", "standard_value_max": 10.0, "unit": "mm",
             "test_method": "测试指", "reference_clause": "Clause 20.2",
             "sort_order": 3},
        ])

    if gb4706_1:
        inspection_items.extend([
            {"standard_id": gb4706_1.id, "item_code": "GB-001",
             "item_name": "接地电阻(GB)", "inspection_category": "electrical",
             "param_name": "接地电阻值", "standard_value_max": 0.1, "unit": "Ω",
             "test_method": "接地电阻测试仪", "reference_clause": "第27章",
             "sort_order": 1},
            {"standard_id": gb4706_1.id, "item_code": "GB-002",
             "item_name": "泄漏电流(GB)", "inspection_category": "electrical",
             "param_name": "泄漏电流", "standard_value_max": 0.75, "unit": "mA",
             "test_method": "泄漏电流测试仪", "reference_clause": "第13章",
             "sort_order": 2},
        ])

    if ul484:
        inspection_items.extend([
            {"standard_id": ul484.id, "item_code": "UL-001",
             "item_name": "泄漏电流(UL)", "inspection_category": "electrical",
             "param_name": "泄漏电流", "standard_value_max": 0.5, "unit": "mA",
             "test_method": "UL泄漏电流测试", "reference_clause": "Section 30",
             "sort_order": 1},
        ])

    item_count = 0
    for item in inspection_items:
        key = (item["standard_id"], item["item_code"])
        if key not in existing_items:
            db.add(SafetyInspectionItem(**item))
            existing_items.add(key)
            item_count += 1
    print(f"  ✅ 安规检测项: 新增 {item_count} 条")

    db.commit()
    print("  ✅ 安规模块种子数据完成")
    sys.stdout.flush()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_safety(db)
    finally:
        db.close()
