"""策划提交前的完整性自动校验引擎

配置驱动 — 规则从数据库 validation_rules 表读取，非硬编码。
预置5条默认规则在 seed_default_rules() 中定义。

用法:
    from app.services.plan_validator import validate_plan
    result = validate_plan(plan_data, db)
    # result = {"valid": True, "errors": []}
"""
import json
import re
import logging
from typing import Optional, Protocol, Union

from sqlalchemy.orm import Session

from app.models.plan_validation import ValidationRule

logger = logging.getLogger(__name__)


# ── 类型别名 ──

ValidationError = dict[str, str]
ValidationResult = dict[str, object]

# 规则对象的联合类型（DB记录或内存占位）
RuleType = Union[ValidationRule, "_RulePlaceholder"]


# ── 业务规则函数签名 ──

class BusinessRuleFn(Protocol):
    """业务规则函数签名"""
    def __call__(self, plan_data: dict[str, object], config: dict[str, object]) -> bool: ...


# ── 业务规则函数注册表 ──

_business_rule_registry: dict[str, BusinessRuleFn] = {}


def register_business_rule(name: str) -> callable:
    """装饰器：注册业务规则函数到全局注册表"""
    def decorator(fn: BusinessRuleFn) -> BusinessRuleFn:
        _business_rule_registry[name] = fn
        return fn
    return decorator


def get_business_rule(name: str) -> Optional[BusinessRuleFn]:
    """根据名称获取业务规则函数"""
    return _business_rule_registry.get(name)


# ── 预置业务规则 ──


@register_business_rule("at_least_two_tech_fields")
def _check_at_least_two_tech_fields(plan_data: dict[str, object], _config: dict[str, object]) -> bool:
    """检查技术指标字段中至少2个不为空"""
    fields = ["cooling_capacity_w", "heating_capacity_w", "eer", "noise_indoor_db"]
    filled = 0
    for f in fields:
        val = plan_data.get(f)
        if val is not None and val != "" and val != 0:
            filled += 1
    return filled >= 2


# ── 校验引擎 ──


def validate_plan(plan_data: dict[str, object], db: Session) -> ValidationResult:
    """校验策划数据完整性

    Args:
        plan_data: 策划数据字典（包含所有 ProductPlan 字段）
        db: 数据库会话（用于读取规则配置）

    Returns:
        {"valid": bool, "errors": [{"field": str, "message": str}, ...]}
    """
    errors: list[ValidationError] = []

    # 从数据库读取所有启用规则
    rules = db.query(ValidationRule).filter(
        ValidationRule.is_active == True  # noqa: E712
    ).all()

    # 如果数据库中没有规则，尝试注入默认规则
    if not rules:
        rules = _get_default_rules_list()

    for rule in rules:
        try:
            _apply_rule(rule, plan_data, errors)
        except Exception as exc:
            logger.warning("校验规则执行异常 [规则=%s] %s: %s", _rule_label(rule), rule.error_message, exc)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def _rule_label(rule: RuleType) -> str:
    """获取规则的简标签（用于日志）"""
    try:
        return f"{rule.rule_type}:{rule.target_field}"
    except Exception:
        logger.exception("unexpected error")
        return str(id(rule))


def _rule_type(rule: RuleType) -> str:
    """安全获取 rule_type"""
    val = getattr(rule, 'rule_type', '')
    return str(val) if val is not None else ''


def _target_field(rule: RuleType) -> str:
    """安全获取 target_field"""
    val = getattr(rule, 'target_field', '')
    return str(val) if val is not None else ''


def _config_raw(rule: RuleType) -> str:
    """安全获取 rule_config"""
    val = getattr(rule, 'rule_config', '{}')
    return str(val) if val is not None else '{}'


def _error_message(rule: RuleType) -> str:
    """安全获取 error_message"""
    val = getattr(rule, 'error_message', '')
    return str(val) if val is not None else ''


def _apply_rule(
    rule: RuleType,
    plan_data: dict[str, object],
    errors: list[ValidationError],
) -> None:
    """对一条规则执行校验，失败时将错误追加到 errors"""
    rule_type = _rule_type(rule)
    target_field_str = _target_field(rule)
    config_raw_str = _config_raw(rule)
    err_msg = _error_message(rule)

    # 解析 target_field：可能是单个字段名，也可能是 JSON 数组字符串
    fields: list[str] = _parse_target_field(target_field_str)

    if rule_type == "required":
        _validate_required(plan_data, fields, err_msg, errors)
    elif rule_type == "range":
        _validate_range(plan_data, fields, config_raw_str, err_msg, errors)
    elif rule_type == "pattern":
        _validate_pattern(plan_data, fields, config_raw_str, err_msg, errors)
    elif rule_type == "business_rule":
        _validate_business_rule(plan_data, target_field_str, config_raw_str, err_msg, errors)
    else:
        logger.warning("未知规则类型: %s", rule_type)


def _parse_target_field(raw: str) -> list[str]:
    """解析 target_field 字段值

    如果 raw 是 JSON 数组字符串，解析为列表；
    否则视为单个字段名。
    """
    raw_stripped = raw.strip()
    if raw_stripped.startswith("["):
        try:
            parsed = json.loads(raw_stripped)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    return [raw_stripped]


def _validate_required(
    plan_data: dict[str, object],
    fields: list[str],
    err_msg: str,
    errors: list[ValidationError],
) -> None:
    """required 类型校验：字段不能为空"""
    for field in fields:
        val = plan_data.get(field)
        if val is None or val == "" or val == 0:
            errors.append({
                "field": field,
                "message": err_msg,
            })


def _parse_range_config(config_raw_str: str) -> tuple[Optional[float], Optional[float]]:
    """解析 range 规则的 min/max 配置，返回 (min_val, max_val)"""
    try:
        config = json.loads(config_raw_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning("range规则配置解析失败: %s", config_raw_str)
        return None, None

    min_val: Optional[float] = None
    max_val: Optional[float] = None
    raw_min = config.get("min")
    raw_max = config.get("max")
    if raw_min is not None:
        try:
            min_val = float(raw_min)
        except (ValueError, TypeError):
            pass
    if raw_max is not None:
        try:
            max_val = float(raw_max)
        except (ValueError, TypeError):
            pass
    return min_val, max_val


def _validate_range(
    plan_data: dict[str, object],
    fields: list[str],
    config_raw_str: str,
    err_msg: str,
    errors: list[ValidationError],
) -> None:
    """range 类型校验：数值在 [min, max] 范围内"""
    min_val, max_val = _parse_range_config(config_raw_str)
    if min_val is None and max_val is None:
        return

    for field in fields:
        raw_val = plan_data.get(field)
        if raw_val is None or raw_val == "":
            # 空值不触发 range 校验（由 required 规则处理）
            continue
        try:
            if isinstance(raw_val, (int, float)):
                val = float(raw_val)
            else:
                raise TypeError
        except (ValueError, TypeError):
            errors.append({
                "field": field,
                "message": f"{err_msg} (无法转为数值)",
            })
            continue

        if min_val is not None and val < min_val:
            errors.append({
                "field": field,
                "message": err_msg,
            })
        elif max_val is not None and val > max_val:
            errors.append({
                "field": field,
                "message": err_msg,
            })


def _validate_pattern(
    plan_data: dict[str, object],
    fields: list[str],
    config_raw_str: str,
    err_msg: str,
    errors: list[ValidationError],
) -> None:
    """pattern 类型校验：字符串匹配正则"""
    pattern_str = config_raw_str.strip()
    if not pattern_str:
        logger.warning("pattern规则未提供正则表达式")
        return
    try:
        compiled = re.compile(pattern_str)
    except re.error as exc:
        logger.warning("pattern规则正则编译失败: %s — %s", pattern_str, exc)
        return

    for field in fields:
        val = plan_data.get(field)
        if val is None or val == "":
            continue
        if not compiled.search(str(val)):
            errors.append({
                "field": field,
                "message": err_msg,
            })


def _validate_business_rule(
    plan_data: dict[str, object],
    target_field_str: str,
    config_raw_str: str,
    err_msg: str,
    errors: list[ValidationError],
) -> None:
    """business_rule 类型校验：由注册函数执行"""
    func_name = config_raw_str.strip() if config_raw_str else ""
    if not func_name:
        logger.warning("business_rule规则未指定函数名")
        return

    fn = get_business_rule(func_name)
    if fn is None:
        logger.warning("business_rule函数未注册: %s", func_name)
        return

    config: dict[str, object] = {}
    try:
        config["fields"] = _parse_target_field(target_field_str)
    except Exception:
        logger.exception("unexpected error")
        config["fields"] = []

    passed = fn(plan_data, config)
    if not passed:
        errors.append({
            "field": target_field_str,
            "message": err_msg,
        })


# ── 默认规则注入（新装系统无规则时使用）──


class _RulePlaceholder:
    """内存中的规则占位对象（无DB记录时使用）"""
    def __init__(
        self,
        rule_type: str,
        target_field: str,
        rule_config: str,
        error_message: str,
    ) -> None:
        self.rule_type = rule_type
        self.target_field = target_field
        self.rule_config = rule_config
        self.error_message = error_message


def _get_default_rules_list() -> list[_RulePlaceholder]:
    """返回默认规则对象列表（内存对象，不持久化）"""
    defaults = [
        ("required", "name", "{}", "产品名称不能为空"),
        ("required", "market", "{}", "目标市场不能为空"),
        ("range", "target_cost", json.dumps({"min": 0.01}), "成本预算必须大于0"),
        ("business_rule",
         json.dumps(["cooling_capacity_w", "heating_capacity_w", "eer", "noise_indoor_db"]),
         "at_least_two_tech_fields",
         "至少2个技术指标不能为空"),
        ("range", "cooling_capacity_w", json.dumps({"min": 1500, "max": 36000}),
         "冷量不在合理范围(1500~36000W)"),
    ]
    return [_RulePlaceholder(*d) for d in defaults]


# ── 种子规则定义（DB持久化用）──

_SEED_RULES: list[ValidationRule] = [
    ValidationRule(
        rule_type="required",
        target_field="name",
        rule_config="{}",
        error_message="产品名称不能为空",
        description="产品名称必填",
    ),
    ValidationRule(
        rule_type="required",
        target_field="market",
        rule_config="{}",
        error_message="目标市场不能为空",
        description="目标市场必填",
    ),
    ValidationRule(
        rule_type="range",
        target_field="target_cost",
        rule_config=json.dumps({"min": 0.01}),
        error_message="成本预算必须大于0",
        description="成本预算>0",
    ),
    ValidationRule(
        rule_type="business_rule",
        target_field=json.dumps(["cooling_capacity_w", "heating_capacity_w", "eer", "noise_indoor_db"]),
        rule_config="at_least_two_tech_fields",
        error_message="至少2个技术指标不能为空",
        description="至少2个技术指标(cooling_capacity_w, heating_capacity_w, eer, noise_indoor_db)必填",
    ),
    ValidationRule(
        rule_type="range",
        target_field="cooling_capacity_w",
        rule_config=json.dumps({"min": 1500, "max": 36000}),
        error_message="冷量不在合理范围(1500~36000W)",
        description="冷量在1500~36000W范围内",
    ),
]


def seed_default_rules(db: Session) -> None:
    """向数据库写入预置默认规则（如果尚未存在）

    在应用启动时或首次部署时调用。
    """
    existing_count = db.query(ValidationRule).count()
    if existing_count > 0:
        logger.info("validation_rules 表已有 %d 条规则，跳过 seed", existing_count)
        return

    for rule in _SEED_RULES:
        db.add(rule)
    db.commit()
    logger.info("已插入 %d 条默认校验规则", len(_SEED_RULES))
