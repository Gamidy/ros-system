"""产品类型枚举定义 — 用于前后端统一校验"""

from enum import Enum


class ProductType(str, Enum):
    """产品类型枚举 — 当前仅支持分体壁挂式空调"""
    SPLIT_WALL = "split_wall"        # 分体壁挂


VALID_PRODUCT_TYPES = {e.value for e in ProductType}


def is_valid_product_type(value: str) -> bool:
    """检查产品类型值是否合法"""
    return value in VALID_PRODUCT_TYPES
