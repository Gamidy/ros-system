"""
清除欧盟竞品的上市年份（未经证实，不可从PDF日期推断）
同时更新SCOP、制热能效等级、声功率数据
"""
import sys
sys.path.insert(0, ".")
import logging

from app.core.database import SessionLocal
from app.models.competitor import CompetitorModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 欧盟8条型号的完整数据（补全SCOP、制热能效、声功率，清除上市年份）
EU_UPDATES = {
    "CLIMADESIGN 9000": {
        "scop": 4.0,
        "heating_energy_rating": "A+",
        "noise_indoor_power_db": 52.0,
        "noise_outdoor_power_db": 59.0,
        "launch_year": None,
    },
    "CLIMADESIGN 12000": {
        "scop": 4.0,
        "heating_energy_rating": "A+",
        "noise_indoor_power_db": 54.0,
        "noise_outdoor_power_db": 61.0,
        "launch_year": None,
    },
    "CLIMADESIGN 18000": {
        "scop": 4.0,
        "heating_energy_rating": "A+",
        "noise_indoor_power_db": 56.0,
        "noise_outdoor_power_db": 62.0,
        "launch_year": None,
    },
    "CLIMADESIGN 24000": {
        "scop": 4.0,
        "heating_energy_rating": "A+",
        "noise_indoor_power_db": 64.0,
        "noise_outdoor_power_db": 63.0,
        "launch_year": None,
    },
    "ARGO DELUXE 9000": {
        "scop": 4.6,
        "heating_energy_rating": "A++",
        "noise_indoor_power_db": 54.0,
        "noise_outdoor_power_db": 61.0,
        "launch_year": None,
    },
    "ARGO DELUXE 12000": {
        "scop": 4.6,
        "heating_energy_rating": "A++",
        "noise_indoor_power_db": 56.0,
        "noise_outdoor_power_db": 62.0,
        "launch_year": None,
    },
    "ARGO DELUXE 18000": {
        "scop": 4.6,
        "heating_energy_rating": "A++",
        "noise_indoor_power_db": 56.0,
        "noise_outdoor_power_db": 63.0,
        "launch_year": None,
    },
    "ARGO DELUXE 24000": {
        "scop": 4.6,
        "heating_energy_rating": "A++",
        "noise_indoor_power_db": 62.0,
        "noise_outdoor_power_db": 65.0,
        "launch_year": None,
    },
}


def update_eu_data():
    db = SessionLocal()
    try:
        updated = 0
        for model_name, data in EU_UPDATES.items():
            record = db.query(CompetitorModel).filter(
                CompetitorModel.brand == "AUX",
                CompetitorModel.model == model_name,
                CompetitorModel.market == "欧盟",
            ).first()

            if not record:
                logger.warning("未找到: AUX %s 欧盟", model_name)
                continue

            for field, value in data.items():
                setattr(record, field, value)

            updated += 1
            logger.info(
                "更新: AUX %s → scop=%.1f heating=%s 声功率内=%.0f/外=%.0f launch_year=已清除",
                model_name,
                record.scop or 0,
                record.heating_energy_rating or "-",
                record.noise_indoor_power_db or 0,
                record.noise_outdoor_power_db or 0,
            )

        db.commit()
        logger.info("✅ 完成: 更新 %d 条欧盟竞品记录", updated)
    except Exception as e:
        db.rollback()
        logger.error("❌ 失败: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_eu_data()
