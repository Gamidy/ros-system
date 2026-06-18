"""初始化 cert_standards 和 perf_defaults 表的占位数据

直接通过 SessionLocal 插入数据，运行前提：
- 数据库已创建 (Base.metadata.create_all 已执行)
- 表已存在 (cert_standards / perf_defaults)

用法: python3 init_pm_config.py
"""
import sys
import os

# 确保 backend 根目录在 Python path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.pm_config import CertStandard, PerfDefault


CERT_DATA = [
    # (standard, key_requirement, verification_method, cert_cycle, sort_order)
    ("IEC 60335-2-40", "电气安全", "型式试验", "3个月", 1),
    ("IEC 60335-2-31", "电机安全", "型式试验", "2个月", 2),
    ("EMC", "电磁兼容", "EMC测试", "2个月", 3),
    ("ErP", "能效要求", "第三方测试", "4个月", 4),
    ("RoHS", "有害物质", "化学检测", "1个月", 5),
]

PERF_DATA = [
    # (capacity_range, param_name, target_value, sort_order)
    # 07K
    ("07K", "制冷量", "2000W", 1),
    ("07K", "EER", "3.8", 2),
    ("07K", "噪音内", "35dB(A)", 3),
    ("07K", "噪音外", "50dB(A)", 4),
    ("07K", "风量", "450m³/h", 5),
    # 09K
    ("09K", "制冷量", "2600W", 1),
    ("09K", "EER", "3.7", 2),
    ("09K", "噪音内", "36dB(A)", 3),
    ("09K", "噪音外", "52dB(A)", 4),
    ("09K", "风量", "550m³/h", 5),
    # 12K
    ("12K", "制冷量", "3500W", 1),
    ("12K", "EER", "3.6", 2),
    ("12K", "噪音内", "38dB(A)", 3),
    ("12K", "噪音外", "55dB(A)", 4),
    ("12K", "风量", "650m³/h", 5),
    # 18K
    ("18K", "制冷量", "5300W", 1),
    ("18K", "EER", "3.4", 2),
    ("18K", "噪音内", "42dB(A)", 3),
    ("18K", "噪音外", "58dB(A)", 4),
    ("18K", "风量", "950m³/h", 5),
    # 24K
    ("24K", "制冷量", "7000W", 1),
    ("24K", "EER", "3.2", 2),
    ("24K", "噪音内", "45dB(A)", 3),
    ("24K", "噪音外", "60dB(A)", 4),
    ("24K", "风量", "1200m³/h", 5),
]


def init():
    db = SessionLocal()
    try:
        # ── cert_standards ──
        existing_certs = db.query(CertStandard).count()
        if existing_certs == 0:
            for standard, key_req, method, cycle, sort in CERT_DATA:
                row = CertStandard(
                    market="通用",
                    standard=standard,
                    key_requirement=key_req,
                    verification_method=method,
                    cert_cycle=cycle,
                    sort_order=sort,
                )
                db.add(row)
            print(f"[OK] 插入 cert_standards {len(CERT_DATA)} 条")
        else:
            print(f"[SKIP] cert_standards 已有 {existing_certs} 条数据，跳过")

        # ── perf_defaults ──
        existing_perf = db.query(PerfDefault).count()
        if existing_perf == 0:
            for cap, param, target, sort in PERF_DATA:
                row = PerfDefault(
                    capacity_range=cap,
                    market="通用",
                    param_name=param,
                    target_value=target,
                    aux_competitor="",
                    tcl_competitor="",
                    sort_order=sort,
                )
                db.add(row)
            print(f"[OK] 插入 perf_defaults {len(PERF_DATA)} 条")
        else:
            print(f"[SKIP] perf_defaults 已有 {existing_perf} 条数据，跳过")

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
