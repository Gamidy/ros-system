"""DFM可制造性分析 — 种子数据（幂等可重复执行）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.manufacturability import DFMChecklist, DFMScoreWeight


def seed_dfm(db):
    """填充DFM初始数据"""
    existing_codes = {c.item_code for c in db.query(DFMChecklist).all()}

    items = [
        # 结构DFM
        {"item_code": "DFM-STR-001", "item_name": "壁厚均匀性检查", "description": "检查塑胶件壁厚是否均匀，避免缩水和应力集中",
         "dfm_category": "structural", "severity": "major", "applicable_product_types": "split_ac,portable_ac",
         "check_method": "目视+卡尺测量", "reference_standard": "≥2.0mm", "weight": 1.0, "sort_order": 1},
        {"item_code": "DFM-STR-002", "item_name": "拔模角度检查", "description": "检查脱模斜度是否满足模具要求",
         "dfm_category": "structural", "severity": "major", "applicable_product_types": "split_ac,portable_ac",
         "check_method": "角度量规", "reference_standard": "≥1°", "weight": 1.0, "sort_order": 2},
        {"item_code": "DFM-STR-003", "item_name": "加强筋设计检查", "description": "检查加强筋厚度和高度比例",
         "dfm_category": "structural", "severity": "minor", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "目视+图纸比对", "reference_standard": "筋厚≤0.6倍壁厚", "weight": 1.0, "sort_order": 3},
        # 装配DFM
        {"item_code": "DFM-ASM-001", "item_name": "装配间隙检查", "description": "检查配合零件之间的装配间隙是否合理",
         "dfm_category": "assembly", "severity": "critical", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "组装验证", "reference_standard": "≥0.1mm ≤0.5mm", "weight": 1.0, "sort_order": 10},
        {"item_code": "DFM-ASM-002", "item_name": "螺钉装配检查", "description": "检查螺钉柱高度、孔径与螺钉规格是否匹配",
         "dfm_category": "assembly", "severity": "major", "applicable_product_types": "split_ac,portable_ac",
         "check_method": "装配测试", "reference_standard": "螺钉柱高度≥3倍螺距", "weight": 1.0, "sort_order": 11},
        {"item_code": "DFM-ASM-003", "item_name": "卡扣装配检查", "description": "检查卡扣的弹性变形量和装配力是否合理",
         "dfm_category": "assembly", "severity": "major", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "推拉力计测试", "reference_standard": "装配力≤50N", "weight": 1.0, "sort_order": 12},
        # 工艺DFM
        {"item_code": "DFM-PRO-001", "item_name": "焊接可达性检查", "description": "检查焊接工位是否便于操作",
         "dfm_category": "process", "severity": "critical", "applicable_product_types": "split_ac",
         "check_method": "工艺仿真", "reference_standard": "焊接角度≥45°", "weight": 1.0, "sort_order": 20},
        {"item_code": "DFM-PRO-002", "item_name": "管路走向检查", "description": "检查制冷剂管路是否避免干涉和死弯",
         "dfm_category": "process", "severity": "major", "applicable_product_types": "split_ac,portable_ac",
         "check_method": "3D干涉检查", "reference_standard": "弯曲半径≥3D", "weight": 1.0, "sort_order": 21},
        # 电气DFM
        {"item_code": "DFM-ELEC-001", "item_name": "PCB固定检查", "description": "检查PCB板固定方式和接地连续性",
         "dfm_category": "electrical", "severity": "critical", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "目视+万用表", "reference_standard": "接地电阻≤0.1Ω", "weight": 1.0, "sort_order": 30},
        {"item_code": "DFM-ELEC-002", "item_name": "线束走向检查", "description": "检查线束走向是否避开锐边和热源",
         "dfm_category": "electrical", "severity": "major", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "目视", "reference_standard": "距锐边≥5mm", "weight": 1.0, "sort_order": 31},
        # 模具DFM
        {"item_code": "DFM-MOLD-001", "item_name": "分型面位置检查", "description": "检查分型面位置是否合理",
         "dfm_category": "mold", "severity": "major", "applicable_product_types": "split_ac,portable_ac",
         "check_method": "模流分析", "reference_standard": "分型面避开外观面", "weight": 1.0, "sort_order": 40},
        {"item_code": "DFM-MOLD-002", "item_name": "浇口位置检查", "description": "检查浇口位置是否不影响外观和功能",
         "dfm_category": "mold", "severity": "major", "applicable_product_types": "split_ac,portable_ac,dehumidifier",
         "check_method": "模流分析", "reference_standard": "浇口位于非外观面", "weight": 1.0, "sort_order": 41},
    ]

    created = 0
    for item in items:
        if item["item_code"] not in existing_codes:
            db.add(DFMChecklist(**item))
            existing_codes.add(item["item_code"])
            created += 1
    print(f"  ✅ DFM检查项: 新增 {created} 条")

    # 权重配置
    existing_weights = {(w.product_type, w.dfm_category) for w in db.query(DFMScoreWeight).all()}
    weight_configs = [
        # 分体空调
        {"product_type": "split_ac", "dfm_category": "structural", "weight": 0.20},
        {"product_type": "split_ac", "dfm_category": "assembly", "weight": 0.20},
        {"product_type": "split_ac", "dfm_category": "process", "weight": 0.25},
        {"product_type": "split_ac", "dfm_category": "electrical", "weight": 0.20},
        {"product_type": "split_ac", "dfm_category": "mold", "weight": 0.15},
        # 移动空调
        {"product_type": "portable_ac", "dfm_category": "structural", "weight": 0.25},
        {"product_type": "portable_ac", "dfm_category": "assembly", "weight": 0.25},
        {"product_type": "portable_ac", "dfm_category": "process", "weight": 0.20},
        {"product_type": "portable_ac", "dfm_category": "electrical", "weight": 0.20},
        {"product_type": "portable_ac", "dfm_category": "mold", "weight": 0.10},
        # 除湿机
        {"product_type": "dehumidifier", "dfm_category": "structural", "weight": 0.25},
        {"product_type": "dehumidifier", "dfm_category": "assembly", "weight": 0.25},
        {"product_type": "dehumidifier", "dfm_category": "process", "weight": 0.20},
        {"product_type": "dehumidifier", "dfm_category": "electrical", "weight": 0.20},
        {"product_type": "dehumidifier", "dfm_category": "mold", "weight": 0.10},
    ]
    wc = 0
    for w in weight_configs:
        if (w["product_type"], w["dfm_category"]) not in existing_weights:
            db.add(DFMScoreWeight(**w))
            existing_weights.add((w["product_type"], w["dfm_category"]))
            wc += 1
    print(f"  ✅ DFM权重配置: 新增 {wc} 条")

    db.commit()
    print("  ✅ DFM种子数据完成")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_dfm(db)
    finally:
        db.close()
