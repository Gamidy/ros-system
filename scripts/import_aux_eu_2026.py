"""
导入 AUX 欧盟市场 2026 年新品到竞品库

来源:
1. CLIMADESIGN MONO — scheda_prodotto_2026 (9000/12000/18000/24000 BTU)
2. ARGO DELUXE — scheda_prodotto_2026 (9000/12000/18000/24000 BTU)

两个系列均为 AUX 品牌，面向欧盟(意大利)市场。
"""
import sys
sys.path.insert(0, ".")
import logging

from app.core.database import SessionLocal
from app.models.competitor import CompetitorModel, COMPETITOR_SOURCE_MANUAL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ARGO DELUXE 通用卖点
ARGO_SELLING_POINTS = """
【核心卖点】
• A+++ 能效等级（制冷），业界领先
• DC Inverter 直流变频技术，最低功耗仅130W
• iClean 自清洁：4阶段（凝露→结霜→化霜→烘干）+ 57°C高温杀菌
• Gold Fin 金色防腐翅片，延长室外机寿命
• WiFi 快速连接 + 专用App远程控制
• iFeel 智能温控：遥控器感应环境温度
• 3D Swing 立体送风（上下+左右摆风）
• Turbo 极速制冷/制热
• Cold Draft Prevention 防冷风设计
• Sleep 睡眠模式
• Max Silence 超静音运行（低至22dB(A)）
• R32环保冷媒（GWP 675）
• 适用意大利 Ecobonus 2026 / Conto Termico 3.0 / Bonus Casa 2026 税收优惠
"""

# CLIMADESIGN 通用卖点
CLIMADESIGN_SELLING_POINTS = """
【核心卖点】
• DC Inverter 直流变频技术
• 数字LCD遥控器
• R32环保冷媒（GWP 675）
• 适用意大利 Ecobonus 2026 / Conto Termico 3.0 / Bonus Casa 2026 税收优惠
"""

MODELS = [
    # ═══════════════ CLIMADESIGN MONO 系列 ═══════════════
    {
        "brand": "AUX",
        "model": "CLIMADESIGN 9000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "9000 BTU/h (2.60 kW)",
        "cooling_capacity_w": 2600,
        "heating_capacity_w": 2610,
        "energy_rating": "A++",
        "cooling_w": 800,
        "heating_w": 700,
        "eer": 3.25,
        "noise_indoor_db": 40.0,
        "noise_outdoor_db": 51.0,
        "airflow_m3h": 550.0,
        "indoor_size_mm": "283×690×199",
        "outdoor_size_mm": "455×650×278",
        "launch_year": 2026,
        "notes": f"AUX CLIMADESIGN MONO 系列 9000 BTU/h (EU)。{CLIMADESIGN_SELLING_POINTS}室内机: CLIMADESIGN 9000 UI, 室外机: CLIMADESIGN 9000 UE。SEER 6.1 / SCOP 4.0。",
    },
    {
        "brand": "AUX",
        "model": "CLIMADESIGN 12000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "12000 BTU/h (3.40 kW)",
        "cooling_capacity_w": 3400,
        "heating_capacity_w": 3500,
        "energy_rating": "A++",
        "cooling_w": 1050,
        "heating_w": 940,
        "eer": 3.24,
        "noise_indoor_db": 40.0,
        "noise_outdoor_db": 52.0,
        "airflow_m3h": 600.0,
        "indoor_size_mm": "285×750×200",
        "outdoor_size_mm": "455×650×278",
        "launch_year": 2026,
        "notes": f"AUX CLIMADESIGN MONO 系列 12000 BTU/h (EU)。{CLIMADESIGN_SELLING_POINTS}室内机: CLIMADESIGN 12000 UI, 室外机: CLIMADESIGN 12000 UE。SEER 6.1 / SCOP 4.0。",
    },
    {
        "brand": "AUX",
        "model": "CLIMADESIGN 18000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "18000 BTU/h (5.10 kW)",
        "cooling_capacity_w": 5100,
        "heating_capacity_w": 5200,
        "energy_rating": "A++",
        "cooling_w": 1570,
        "heating_w": 1390,
        "eer": 3.25,
        "noise_indoor_db": 46.0,
        "noise_outdoor_db": 54.0,
        "airflow_m3h": 850.0,
        "indoor_size_mm": "310×900×225",
        "outdoor_size_mm": "537×715×280",
        "launch_year": 2026,
        "notes": f"AUX CLIMADESIGN MONO 系列 18000 BTU/h (EU)。{CLIMADESIGN_SELLING_POINTS}室内机: CLIMADESIGN 18000 UI, 室外机: CLIMADESIGN 18000 UE N。SEER 6.7 / SCOP 4.0。",
    },
    {
        "brand": "AUX",
        "model": "CLIMADESIGN 24000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "24000 BTU/h (7.20 kW)",
        "cooling_capacity_w": 7200,
        "heating_capacity_w": 7200,
        "energy_rating": "A++",
        "cooling_w": 2200,
        "heating_w": 1940,
        "eer": 3.27,
        "noise_indoor_db": 47.0,
        "noise_outdoor_db": 58.0,
        "airflow_m3h": 1310.0,
        "indoor_size_mm": "330×1082×233",
        "outdoor_size_mm": "655×823×302",
        "launch_year": 2026,
        "notes": f"AUX CLIMADESIGN MONO 系列 24000 BTU/h (EU)。{CLIMADESIGN_SELLING_POINTS}室内机: CLIMADESIGN 24000 UI N, 室外机: CLIMADESIGN 24000 UE N。SEER 6.1 / SCOP 4.0。",
    },
    # ═══════════════ ARGO DELUXE 系列 ═══════════════
    {
        "brand": "AUX",
        "model": "ARGO DELUXE 9000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "9000 BTU/h (2.70 kW)",
        "cooling_capacity_w": 2700,
        "heating_capacity_w": 3300,
        "energy_rating": "A+++",
        "cooling_w": 720,
        "heating_w": 760,
        "eer": 3.75,
        "noise_indoor_db": 43.0,
        "noise_outdoor_db": 54.0,
        "airflow_m3h": 600.0,
        "indoor_size_mm": "296×761×199",
        "outdoor_size_mm": "530×708×258",
        "launch_year": 2026,
        "notes": f"AUX ARGO DELUXE 系列 9000 BTU/h (EU)。{ARGO_SELLING_POINTS}室内机: ARGO DELUXE 9000 UI, 室外机: ARGO DELUXE 9000 UE。SEER 8.5 / SCOP 4.6。",
    },
    {
        "brand": "AUX",
        "model": "ARGO DELUXE 12000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "12000 BTU/h (3.50 kW)",
        "cooling_capacity_w": 3500,
        "heating_capacity_w": 4200,
        "energy_rating": "A+++",
        "cooling_w": 870,
        "heating_w": 1060,
        "eer": 4.02,
        "noise_indoor_db": 45.0,
        "noise_outdoor_db": 56.0,
        "airflow_m3h": 650.0,
        "indoor_size_mm": "295×822×198",
        "outdoor_size_mm": "530×708×258",
        "launch_year": 2026,
        "notes": f"AUX ARGO DELUXE 系列 12000 BTU/h (EU)。{ARGO_SELLING_POINTS}室内机: ARGO DELUXE 12000 UI, 室外机: ARGO DELUXE 12000 UE。SEER 8.5 / SCOP 4.6。",
    },
    {
        "brand": "AUX",
        "model": "ARGO DELUXE 18000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "18000 BTU/h (5.30 kW)",
        "cooling_capacity_w": 5300,
        "heating_capacity_w": 5600,
        "energy_rating": "A+++",
        "cooling_w": 1430,
        "heating_w": 1330,
        "eer": 3.71,
        "noise_indoor_db": 45.0,
        "noise_outdoor_db": 56.0,
        "airflow_m3h": 1000.0,
        "indoor_size_mm": "328×1089×227",
        "outdoor_size_mm": "548×785×281",
        "launch_year": 2026,
        "notes": f"AUX ARGO DELUXE 系列 18000 BTU/h (EU)。{ARGO_SELLING_POINTS}室内机: ARGO DELUXE 18000 UI, 室外机: ARGO DELUXE 18000 UE。SEER 8.5 / SCOP 4.6。",
    },
    {
        "brand": "AUX",
        "model": "ARGO DELUXE 24000",
        "market": "欧盟",
        "product_type": "分体壁挂式空调",
        "cooling_capacity": "24000 BTU/h (7.26 kW)",
        "cooling_capacity_w": 7260,
        "heating_capacity_w": 7810,
        "energy_rating": "A+++",
        "cooling_w": 2230,
        "heating_w": 2095,
        "eer": 3.26,
        "noise_indoor_db": 51.0,
        "noise_outdoor_db": 62.0,
        "airflow_m3h": 1300.0,
        "indoor_size_mm": "328×1089×227",
        "outdoor_size_mm": "695×890×319",
        "launch_year": 2026,
        "notes": f"AUX ARGO DELUXE 系列 24000 BTU/h (EU)。{ARGO_SELLING_POINTS}室内机: ARGO DELUXE 24000 UI, 室外机: ARGO DELUXE 24000 UE。SEER 8.5 / SCOP 4.6。",
    },
]


def import_data():
    db = SessionLocal()
    try:
        imported = 0
        skipped = 0
        for m in MODELS:
            existing = db.query(CompetitorModel).filter(
                CompetitorModel.brand == m["brand"],
                CompetitorModel.model == m["model"],
                CompetitorModel.market == m["market"],
            ).first()
            if existing:
                logger.info("已存在，跳过: %s %s %s", m["brand"], m["model"], m["market"])
                skipped += 1
                continue

            record = CompetitorModel(
                brand=m["brand"],
                model=m["model"],
                market=m["market"],
                product_type=m["product_type"],
                cooling_capacity=m["cooling_capacity"],
                cooling_capacity_w=m["cooling_capacity_w"],
                heating_capacity_w=m["heating_capacity_w"],
                energy_rating=m["energy_rating"],
                cooling_w=m["cooling_w"],
                heating_w=m["heating_w"],
                eer=m["eer"],
                noise_indoor_db=m["noise_indoor_db"],
                noise_outdoor_db=m["noise_outdoor_db"],
                airflow_m3h=m["airflow_m3h"],
                indoor_size_mm=m["indoor_size_mm"],
                outdoor_size_mm=m["outdoor_size_mm"],
                launch_year=m["launch_year"],
                notes=m["notes"],
                source=COMPETITOR_SOURCE_MANUAL,
            )
            db.add(record)
            db.flush()
            imported += 1
            logger.info(
                "导入: %s %s %s (ID=%s, %s→%sW, EER=%.2f)",
                m["brand"], m["model"], m["market"], record.id,
                m["cooling_capacity"], m["cooling_capacity_w"], m["eer"],
            )

        db.commit()
        logger.info("✅ 完成: 导入 %d, 跳过 %d", imported, skipped)
    except Exception as e:
        db.rollback()
        logger.error("❌ 失败: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import_data()
