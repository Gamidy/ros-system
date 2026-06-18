"""初始化 accessory_defaults 和 feature_defaults 表的占位数据

直接通过 SessionLocal 插入数据，运行前提：
- 数据库已创建 (Base.metadata.create_all 已执行)
- 表已存在 (accessory_defaults / feature_defaults)

用法: python3 init_pm_accessory.py
"""
import sys
import os

# 确保 backend 根目录在 Python path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.pm_accessory import AccessoryDefault, FeatureDefault

ACCESSORY_DATA = [
    # (name, default_selection, sort_order)
    ("除尘网", "标配", 1),
    ("WiFi模块", "选配", 2),
    ("蓝牙遥控", "选配", 3),
    ("离子发生器", "不配", 4),
]

FEATURE_DATA = [
    # (name, default_selection, sort_order)
    ("自清洁", "标配", 1),
    ("除霜", "标配", 2),
    ("快速制冷", "标配", 3),
    ("静音模式", "选配", 4),
    ("ECO模式", "选配", 5),
]


def init():
    db = SessionLocal()
    try:
        # ── accessory_defaults ──
        existing_accessory = db.query(AccessoryDefault).count()
        if existing_accessory == 0:
            for name, sel, sort in ACCESSORY_DATA:
                row = AccessoryDefault(
                    market="通用",
                    name=name,
                    default_selection=sel,
                    sort_order=sort,
                )
                db.add(row)
            print(f"[OK] 插入 accessory_defaults {len(ACCESSORY_DATA)} 条")
        else:
            print(f"[SKIP] accessory_defaults 已有 {existing_accessory} 条数据，跳过")

        # ── feature_defaults ──
        existing_feature = db.query(FeatureDefault).count()
        if existing_feature == 0:
            for name, sel, sort in FEATURE_DATA:
                row = FeatureDefault(
                    market="通用",
                    name=name,
                    default_selection=sel,
                    sort_order=sort,
                )
                db.add(row)
            print(f"[OK] 插入 feature_defaults {len(FEATURE_DATA)} 条")
        else:
            print(f"[SKIP] feature_defaults 已有 {existing_feature} 条数据，跳过")

        db.commit()
        print("[DONE] 初始化完成")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init()
