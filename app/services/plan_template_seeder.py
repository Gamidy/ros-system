"""PlanTemplate seeder — 初始化默认策划模板

在 main.py 启动时调用，确保3个默认模板存在。
"""
import logging
from sqlalchemy.orm import Session
from app.models.plan_template import PlanTemplate

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES = [
    {
        "product_type": "壁挂式空调",
        "market": "东南亚",
        "name": "壁挂式空调（东南亚）",
        "description": "适用于东南亚市场的壁挂式空调模板，预设热带气候参数和成本目标",
        "preset_fields": {
            "product_type": "壁挂式空调",
            "name": "",
            "market": "东南亚",
            "series": "壁挂式R系列",
            "target_cost": 800.00,
            "cooling_capacity_w": 3500,
            "heating_capacity_w": 0,
            "eer": 3.5,
            "energy_rating": "1级能效",
            "refrigerant": "R32",
            "voltage": "220V/50Hz",
            "capacity": "1.0-1.5匹",
            "ip_rating": "IPX4",
            "noise_indoor_db": 38,
            "noise_outdoor_db": 52,
            "target_price": 400.00,
            "sample_qty": 10,
            "dev_category": "衍生开发",
            "origin": "中国",
            "duration": 12,
        },
    },
    {
        "product_type": "柜式空调",
        "market": "中东",
        "name": "柜式空调（中东）",
        "description": "适用于中东市场的柜式空调模板，预设高温沙漠气候参数和成本目标",
        "preset_fields": {
            "product_type": "柜式空调",
            "name": "",
            "market": "中东",
            "series": "柜式T系列",
            "target_cost": 1500.00,
            "cooling_capacity_w": 7000,
            "heating_capacity_w": 0,
            "eer": 3.2,
            "energy_rating": "2级能效",
            "refrigerant": "R410A",
            "voltage": "220V/60Hz",
            "capacity": "2.0-3.0匹",
            "ip_rating": "IPX5",
            "noise_indoor_db": 45,
            "noise_outdoor_db": 58,
            "target_price": 700.00,
            "sample_qty": 5,
            "dev_category": "全新开发",
            "origin": "中国",
            "duration": 18,
        },
    },
    {
        "product_type": "中央空调",
        "market": "中亚",
        "name": "中央空调（中亚）",
        "description": "适用于中亚市场的中央空调模板，预设干燥大陆气候参数和成本目标",
        "preset_fields": {
            "product_type": "中央空调",
            "name": "",
            "market": "中亚",
            "series": "中央C系列",
            "target_cost": 5000.00,
            "cooling_capacity_w": 14000,
            "heating_capacity_w": 16000,
            "eer": 3.8,
            "energy_rating": "1级能效",
            "refrigerant": "R32",
            "voltage": "380V/50Hz",
            "capacity": "5.0匹",
            "ip_rating": "IPX4",
            "noise_indoor_db": 42,
            "noise_outdoor_db": 55,
            "target_price": 2500.00,
            "sample_qty": 3,
            "dev_category": "全新开发",
            "origin": "中国",
            "duration": 24,
        },
    },
]


def seed_default_templates(db: Session) -> None:
    """初始化3个默认策划模板（幂等：同名+同类+同市场的不重复创建）"""
    created_count = 0
    for tmpl_data in DEFAULT_TEMPLATES:
        existing = db.query(PlanTemplate).filter(
            PlanTemplate.product_type == tmpl_data["product_type"],
            PlanTemplate.market == tmpl_data["market"],
            PlanTemplate.name == tmpl_data["name"],
        ).first()
        if existing:
            continue
        template = PlanTemplate(
            product_type=tmpl_data["product_type"],
            market=tmpl_data["market"],
            name=tmpl_data["name"],
            description=tmpl_data["description"],
            preset_fields=tmpl_data["preset_fields"],
            is_active=True,
        )
        db.add(template)
        created_count += 1

    if created_count > 0:
        db.commit()
        logger.info("已创建 %d 个默认策划模板", created_count)
    else:
        logger.info("默认策划模板已存在，跳过创建")
