"""
产品主线业务规则引擎

实现知识库中定义的架构原则：
  PR-02: Platform = 结构尺寸集合
  PR-08: Market ≠ Product（多对多）
  PR-09: Product Version升级 = 客户可感知变化
  PR-10: Product Version ≠ MBOM Version
  PR-11: Product = Market × Capacity × Indoor Platform × Outdoor Platform
  PR-18: 新版BOM不重建Product
"""
from typing import Optional, List, Tuple, Dict
from app.models.product import VersionStatus, VERSION_TRANSITIONS


class VersionRuleResult:
    """Version变更规则判定结果"""
    def __init__(self, should_create: bool, reason: str, change_type: Optional[str] = None,
                 customer_perceivable: bool = False, product_action: Optional[str] = None):
        self.should_create = should_create
        self.reason = reason
        self.change_type = change_type
        self.customer_perceivable = customer_perceivable
        self.product_action = product_action  # "new_product" / "new_version" / None

    def to_dict(self) -> dict:
        return {
            "should_create": self.should_create,
            "reason": self.reason,
            "change_type": self.change_type,
            "customer_perceivable": self.customer_perceivable,
            "product_action": self.product_action,
        }


class ProductRulesEngine:
    """产品主线业务规则引擎"""

    # PR-06: 物料关键程度 → Product/Version 影响
    MATERIAL_IMPACT = {
        "critical": "new_product",     # 压缩机 → 新建Product
        "major": "new_version",        # 风机电机 → 升Version
        "minor": "mbom_only",          # 消音棉 → 仅MBOM升版
    }

    # PR-09: 哪些变更客户可感知
    CUSTOMER_PERCEIVABLE_CHANGES = {
        "performance",    # 性能变化
        "structural",     # 结构/外观变化
        "certification",  # 认证变化
        "feature",        # 功能变化
    }

    @staticmethod
    def validate_version_transition(current: VersionStatus, target: VersionStatus) -> Tuple[bool, str]:
        """验证Version生命周期转换是否合法"""
        if current not in VERSION_TRANSITIONS:
            return False, f"未知当前状态: {current.value}"
        allowed = VERSION_TRANSITIONS[current]
        if target not in allowed:
            return False, f"不允许从 {current.value} 转换到 {target.value}，允许: {[a.value for a in allowed]}"
        return True, ""

    @staticmethod
    def evaluate_version_change(
        change_description: str,
        material_level: str = "minor",
        change_category: str = "bom_only",
        is_customer_perceivable: bool = False,
    ) -> VersionRuleResult:
        """
        评估变更是否需要创建新Version

        Args:
            change_description: 变更描述
            material_level: 物料级别 (critical/major/minor)
            change_category: 变更类别 (performance/structural/certification/bom_only/process)
            is_customer_perceivable: 客户是否可感知

        Returns:
            VersionRuleResult: 判定结果
        """
        # PR-06: 按物料关键程度判定Product级别影响
        product_action = ProductRulesEngine.MATERIAL_IMPACT.get(material_level, "mbom_only")

        # PR-09: 客户可感知 → 必须升Product Version
        customer_perceivable = (
            is_customer_perceivable or
            change_category in ProductRulesEngine.CUSTOMER_PERCEIVABLE_CHANGES
        )

        if product_action == "new_product":
            return VersionRuleResult(
                should_create=True,
                reason=f"关键物料变更(等级:{material_level}): {change_description} → 需新建Product",
                change_type=change_category,
                customer_perceivable=True,
                product_action="new_product",
            )

        if product_action == "new_version":
            return VersionRuleResult(
                should_create=True,
                reason=f"重要物料变更(等级:{material_level}): {change_description} → 需新建Product Version",
                change_type=change_category,
                customer_perceivable=customer_perceivable,
                product_action="new_version",
            )

        # PR-09/10: 仅MBOM变更 → Product Version不变，MBOM升版
        if material_level == "minor" and not customer_perceivable:
            return VersionRuleResult(
                should_create=False,
                reason=f"非关键物料变更(等级:{material_level}): {change_description} → Product Version不变，仅MBOM升版",
                change_type=change_category,
                customer_perceivable=False,
                product_action="mbom_only",
            )

        # 默认：有客户可感知变化才升版
        if customer_perceivable:
            return VersionRuleResult(
                should_create=True,
                reason=f"客户可感知变更: {change_description} → 建议新建Version",
                change_type=change_category,
                customer_perceivable=True,
                product_action="new_version",
            )

        return VersionRuleResult(
            should_create=False,
            reason=f"非客户可感知变更: {change_description} → Product Version不变",
            change_type=change_category,
            customer_perceivable=False,
            product_action=None,
        )

    @staticmethod
    def validate_product_code(code: str, market: str, capacity: str) -> Tuple[bool, str]:
        """
        验证产品编码格式 (PR-11: Product = Market × Capacity × Platform)

        建议格式: {Market}-{Capacity}
        例: EU-09K, VN-12K
        """
        parts = code.split("-")
        if len(parts) < 2:
            return False, f"产品编码格式不符合 {Market}-{Capacity} 规范: {code}"

        code_market = parts[0].upper()
        if code_market != market.upper():
            return False, f"编码中的市场 '{code_market}' 与目标市场 '{market}' 不一致"

        if capacity.upper() not in code.upper():
            return False, f"编码中应包含容量信息 '{capacity}': {code}"

        return True, ""


# 全局单例
product_rules = ProductRulesEngine()
