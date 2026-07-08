"""
空调参数归一化引擎 UnitNormalizer

将各种格式（中文/英文/混合）的空调参数文本归一化为标准数值或格式。
所有方法都是静态的，纯正则驱动，无外部依赖。

空调行业约定:
  - 小1匹 = 2200W, 1匹 = 2500W, 大1匹 = 2800W
  - 1.5匹 = 3500W, 2匹 = 5000W
  - 1 BTU/h ≈ 0.293071 W
  - 1 HP (空调行业) ≈ 2500W
  - 1 冷冻吨 ≈ 3516 W
  - 1 CFM ≈ 1.699 m³/h
"""

import re
from typing import Pattern


class UnitNormalizer:
    """空调参数单位归一化 —— 纯正则驱动，无外部依赖。"""

    # ── 制冷量 ──────────────────────────────────────────────────────────
    _COOLING_PATTERNS: list[tuple[Pattern, float | None]] = [
        # "大1匹" / "大一匹" → 2800W
        (re.compile(r'大(?:一|1)\s*匹', re.IGNORECASE), 2800.0),
        # "小1匹" / "小一匹" → 2200W
        (re.compile(r'小(?:一|1)\s*匹', re.IGNORECASE), 2200.0),
        # "XXXX BTU/h" or "XXXXBTU" → X * 0.293 (1BTU/h ≈ 0.293W)
        (re.compile(r'(\d+(?:\.\d+)?)\s*(?:BTU|btu)(?:\s*/\s*h)?', re.IGNORECASE), 0.293),
        # "X.X kW" or "X.Xkw" → X * 1000
        (re.compile(r'(\d+(?:\.\d+)?)\s*k[Ww]', re.IGNORECASE), 1000.0),
        # "XXXX W" or "XXXXw" (纯W值)
        (re.compile(r'(\d+(?:\.\d+)?)\s*[Ww](?![a-zA-Z])'), 1.0),
        # "X HP" or "X.XHP" → X * 2500
        (re.compile(r'(\d+(?:\.\d+)?)\s*HP\b', re.IGNORECASE), 2500.0),
        # "X 吨" (冷冻吨) → X * 3516
        (re.compile(r'(\d+(?:\.\d+)?)\s*吨', re.IGNORECASE), 3516.0),
        # "X.X匹" / "XX匹" 通用匹数 → X * 2500W (放最后，匹数估算)
        (re.compile(r'(\d+(?:\.\d+)?)\s*匹', re.IGNORECASE), None),  # None = use multiplier logic
    ]

    # ── 制热量 ──────────────────────────────────────────────────────────
    _HEATING_PATTERNS: list[tuple[Pattern, float | None]] = [
        # "大1匹" / "大一匹" → 2800W
        (re.compile(r'大(?:一|1)\s*匹', re.IGNORECASE), 2800.0),
        # "小1匹" / "小一匹" → 2200W
        (re.compile(r'小(?:一|1)\s*匹', re.IGNORECASE), 2200.0),
        # "XXXX BTU/h" or "XXXXBTU" → X * 0.293 (1BTU/h ≈ 0.293W)
        (re.compile(r'(\d+(?:\.\d+)?)\s*(?:BTU|btu)(?:\s*/\s*h)?', re.IGNORECASE), 0.293),
        # "X.X kW" or "X.Xkw" → X * 1000
        (re.compile(r'(\d+(?:\.\d+)?)\s*k[Ww]', re.IGNORECASE), 1000.0),
        # "XXXX W"
        (re.compile(r'(\d+(?:\.\d+)?)\s*[Ww](?![a-zA-Z])'), 1.0),
        # "X HP"
        (re.compile(r'(\d+(?:\.\d+)?)\s*HP\b', re.IGNORECASE), 2500.0),
        # "X 吨"
        (re.compile(r'(\d+(?:\.\d+)?)\s*吨', re.IGNORECASE), 3516.0),
        # "X.X匹" / "XX匹" (放最后，匹数估算)
        (re.compile(r'(\d+(?:\.\d+)?)\s*匹', re.IGNORECASE), None),
    ]

    # ── 功率 ────────────────────────────────────────────────────────────
    _POWER_PATTERNS: list[tuple[Pattern, float]] = [
        # "X.X kW"
        (re.compile(r'(\d+(?:\.\d+)?)\s*k[Ww]'), 1000.0),
        # "w" / "W" 结尾
        (re.compile(r'(\d+(?:\.\d+)?)\s*[Ww](?![a-zA-Z])'), 1.0),
        # "X.X HP" (压缩机功率用 HP)
        (re.compile(r'(\d+(?:\.\d+)?)\s*HP\b', re.IGNORECASE), 735.5),  # 1HP ≈ 735.5W (电功率)
    ]

    # ── 噪音 ────────────────────────────────────────────────────────────
    _NOISE_PATTERNS: list[tuple[Pattern, str]] = [
        # "≤45dB" / "<=45dB" / "<22dB"
        (re.compile(r'(?:≤|<=|<)\s*(\d+(?:\.\d+)?)\s*(?:dB|分贝)', re.IGNORECASE), 'max'),
        # "22-38dB" / "22~38dB" → 取最大值 38
        (re.compile(r'(\d+(?:\.\d+)?)\s*(?:-|~|～)\s*(\d+(?:\.\d+)?)\s*(?:dB|分贝)', re.IGNORECASE), 'range'),
        # "38dB(A)" / "38 dB(A)" / "38分贝"
        (re.compile(r'(\d+(?:\.\d+)?)\s*(?:dB|分贝)(?:\s*\([A-Za-z]\))?', re.IGNORECASE), 'direct'),
    ]

    # ── 风量 ────────────────────────────────────────────────────────────
    _AIRFLOW_PATTERNS: list[tuple[Pattern, float]] = [
        # "550 m³/h" / "550m3/h" → 原值 (multiplier 1.0)
        (re.compile(r'(\d+(?:\.\d+)?)\s*m[³3](?:\s*/\s*h|/h)?', re.IGNORECASE), 1.0),
        # "680 CFM" → 680 * 1.699
        (re.compile(r'(\d+(?:\.\d+)?)\s*(?:CFM|cfm)', re.IGNORECASE), 1.699),
    ]

    # ── 能效比 ──────────────────────────────────────────────────────────
    _EER_PATTERNS: list[tuple[Pattern, str]] = [
        # "EER 3.21" / "eer3.21"
        (re.compile(r'(?:EER|eer|COP|cop)\s*[:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE), 'eer'),
        # "CSPF 5.5" (新加坡/东南亚标准)
        (re.compile(r'(?:CSPF|cspf)\s*[:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE), 'eer'),
        # 纯数字 (≥1.0 认为是能效比)
        (re.compile(r'(\d+\.\d{1,2})'), 'bare'),
    ]

    # ── 尺寸 ────────────────────────────────────────────────────────────
    _DIMENSIONS_PATTERNS: list[Pattern] = [
        # "850×290×190mm" / "850*290*190mm"
        re.compile(r'(\d+)\s*[×*xX]\s*(\d+)\s*[×*xX]\s*(\d+)\s*mm?', re.IGNORECASE),
        # "850x290mm" (二维，少见)
        re.compile(r'(\d+)\s*[×*xX]\s*(\d+)\s*mm?', re.IGNORECASE),
    ]

    # ── 价格 ────────────────────────────────────────────────────────────
    _PRICE_PATTERNS: list[Pattern] = [
        # "$599" / "US$599" / "USD599"
        re.compile(r'([A-Z]{0,3})\$?\s*(\d[\d,.]*)\s*(?:USD|HKD|CNY|EUR|SGD|MYR|THB|VND|JPY)?', re.IGNORECASE),
        # "¥8,990,000"
        re.compile(r'[¥￥]\s*(\d[\d,.]*)'),
        # "8.990.000₫" / "₫" VND
        re.compile(r'(\d[\d,.]*)\s*[₫đ]', re.IGNORECASE),
        # 纯数字带千分位逗号
        re.compile(r'^(\d{1,3}(?:,\d{3})+(?:\.\d+)?)$'),
    ]

    # ── 匹转换辅助 ──────────────────────────────────────────────────────

    @staticmethod
    def _horsepower_to_watts(value: float) -> int:
        """匹数 → W (空调制冷量)"""
        mapping = {
            0.5: 1250,
            0.75: 1875,
            1.0: 2500,
            1.5: 3500,
            2.0: 5000,
            2.5: 6250,
            3.0: 7500,
            5.0: 12500,
        }
        # Exact match
        if value in mapping:
            return mapping[value]
        # Interpolate for non-standard values: approx value * 2500
        return round(value * 2500)

    # ── 公开方法 ────────────────────────────────────────────────────────

    @staticmethod
    def normalize_cooling_capacity(text: str) -> int | None:
        """将各种制冷量表述统一到 W。

        支持:
          - "1.5匹" → 3500W
          - "大1匹" → 2800W
          - "小1匹" → 2200W
          - "2匹" → 5000W
          - "9000BTU" → 2637W
          - "2.8kW" → 2800W
          - "3HP" → 7500W
          - "1吨" → 3516W
        """
        text = text.strip()
        if not text:
            return None

        for pattern, multiplier in UnitNormalizer._COOLING_PATTERNS:
            m = pattern.search(text)
            if m:
                groupdict = m.groupdict()
                if multiplier is not None:
                    # "大1匹" / "小1匹" — direct value
                    if not m.lastgroup and m.groups():
                        # Simple capture group with multiplier
                        try:
                            val = float(m.group(1))
                            return round(val * multiplier)
                        except (IndexError, ValueError):
                            return int(multiplier)
                    # Check if it's a named group situation; fallback
                    if not m.groups():
                        return int(multiplier)
                    try:
                        val = float(m.group(1))
                        return round(val * multiplier)
                    except (IndexError, ValueError):
                        return int(multiplier)
                else:
                    # multiplier is None → 匹数逻辑 (generic 匹 with capture group)
                    try:
                        val = float(m.group(1))
                        return UnitNormalizer._horsepower_to_watts(val)
                    except (IndexError, ValueError):
                        return None

        return None

    @staticmethod
    def normalize_heating_capacity(text: str) -> int | None:
        """制热量版 normalize_cooling_capacity。"""
        text = text.strip()
        if not text:
            return None

        for pattern, multiplier in UnitNormalizer._HEATING_PATTERNS:
            m = pattern.search(text)
            if m:
                if multiplier is not None:
                    if not m.groups():
                        return int(multiplier)
                    try:
                        val = float(m.group(1))
                        return round(val * multiplier)
                    except (IndexError, ValueError):
                        return int(multiplier)
                else:
                    try:
                        val = float(m.group(1))
                        return UnitNormalizer._horsepower_to_watts(val)
                    except (IndexError, ValueError):
                        return None

        return None

    @staticmethod
    def normalize_power(text: str) -> int | None:
        """功率归一化到 W。

        "1.2kW" → 1200W
        "800W" → 800W
        "3HP" → 2206W (电功率 HP ≈ 735.5W)
        """
        text = text.strip()
        if not text:
            return None

        for pattern, multiplier in UnitNormalizer._POWER_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    val = float(m.group(1))
                    return round(val * multiplier)
                except (IndexError, ValueError):
                    return None

        return None

    @staticmethod
    def normalize_noise(text: str) -> float | None:
        """噪音归一化到 dB(A) 数值。

        "38dB(A)" → 38.0
        "<22dB" → 22.0
        "22-38dB" → 38.0 (取最大值)
        "20分贝" → 20.0
        "≤45dB" → 45.0
        """
        text = text.strip()
        if not text:
            return None

        for pattern, mode in UnitNormalizer._NOISE_PATTERNS:
            m = pattern.search(text)
            if m:
                if mode == 'max':
                    # "<22dB", "≤45dB"
                    try:
                        return float(m.group(1))
                    except (IndexError, ValueError):
                        return None
                elif mode == 'range':
                    # "22-38dB" → take max
                    try:
                        return max(float(m.group(1)), float(m.group(2)))
                    except (IndexError, ValueError):
                        return None
                elif mode == 'direct':
                    # "38dB(A)"
                    try:
                        return float(m.group(1))
                    except (IndexError, ValueError):
                        return None

        return None

    @staticmethod
    def normalize_airflow(text: str) -> float | None:
        """风量归一化到 m³/h。

        "550m³/h" → 550.0
        "680CFM" → 1155.0
        """
        text = text.strip()
        if not text:
            return None

        for pattern, multiplier in UnitNormalizer._AIRFLOW_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    val = float(m.group(1))
                    return round(val * multiplier)
                except (IndexError, ValueError):
                    return None

        return None

    @staticmethod
    def normalize_eer(text: str) -> float | None:
        """能效比归一化。

        "EER 3.21" → 3.21
        "3.2" → 3.2
        "COP 4.0" → 4.0
        "CSPF 5.5" → 5.5
        """
        text = text.strip()
        if not text:
            return None

        for pattern, mode in UnitNormalizer._EER_PATTERNS:
            m = pattern.search(text)
            if m:
                try:
                    val = float(m.group(1))
                    # Bare number threshold: > 0.5 and <= 20
                    if mode == 'bare' and (val < 0.5 or val > 20):
                        continue
                    return val
                except (IndexError, ValueError):
                    return None

        return None

    @staticmethod
    def normalize_dimensions(text: str) -> str | None:
        """尺寸归一化，统一分隔符为 ×。

        "850×290×190mm" → "850×290×190"
        "750*280*180mm" → "750×280×180"
        "850x290mm" → "850×290"
        """
        text = text.strip()
        if not text:
            return None

        for pattern in UnitNormalizer._DIMENSIONS_PATTERNS:
            m = pattern.search(text)
            if m:
                groups = m.groups()
                if len(groups) == 3:
                    return f"{groups[0]}×{groups[1]}×{groups[2]}"
                elif len(groups) == 2:
                    return f"{groups[0]}×{groups[1]}"

        return None

    @staticmethod
    def normalize_price(text: str) -> str | None:
        """价格归一化。

        去除多余空格，保留货币符号前缀。
        "$599" → "$599"
        "¥8,990,000" → "¥8,990,000"
        "8.990.000₫" → "8.990.000₫"
        "1,234,567" → "1,234,567"
        """
        text = text.strip()
        if not text:
            return None

        for pattern in UnitNormalizer._PRICE_PATTERNS:
            m = pattern.match(text)
            if m:
                groups = m.groups()
                # Pattern with currency prefix: group(1)=currency, group(2)=number
                if len(groups) >= 2 and groups[1] is not None and groups[1].strip():
                    currency = (groups[0] or '').strip().upper()
                    number = groups[1].strip()
                    if currency:
                        return f"{currency} {number}" if currency in ('USD', 'HKD', 'CNY', 'EUR', 'SGD', 'MYR', 'THB', 'VND', 'JPY') else f"${number}" if m.group(0).startswith('$') else number
                    # Check if original had a dollar sign
                    if '$' in m.group(0):
                        return f"${number}"
                    return number
                # Pattern with yen symbol
                if len(groups) >= 1 and groups[0] is not None:
                    return f"¥{groups[0].strip()}"
                return text

        return None


# ═══════════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════════

def _test(name: str, actual, expected) -> None:
    status = "PASS" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  [{status}] {name}: expected {expected!r}, got {actual!r}")
    else:
        print(f"  [{status}] {name}")


def test_normalizer() -> None:
    """运行所有归一化测试用例。"""
    print("UnitNormalizer 测试报告:")
    print("─" * 50)

    # ── 制冷量 ──
    print("\n[制冷量 normalize_cooling_capacity]")
    _test("1.5匹 → 3500",
          UnitNormalizer.normalize_cooling_capacity("1.5匹"), 3500)
    _test("大1匹 → 2800",
          UnitNormalizer.normalize_cooling_capacity("大1匹"), 2800)
    _test("大一匹 → 2800",
          UnitNormalizer.normalize_cooling_capacity("大一匹"), 2800)
    _test("小1匹 → 2200",
          UnitNormalizer.normalize_cooling_capacity("小1匹"), 2200)
    _test("2匹 → 5000",
          UnitNormalizer.normalize_cooling_capacity("2匹"), 5000)
    _test("9000BTU → 2637",
          UnitNormalizer.normalize_cooling_capacity("9000BTU"), 2637)
    _test("12000BTU/h → 3516",
          UnitNormalizer.normalize_cooling_capacity("12000BTU/h"), 3516)
    _test("2.8kW → 2800",
          UnitNormalizer.normalize_cooling_capacity("2.8kW"), 2800)
    _test("2800W → 2800",
          UnitNormalizer.normalize_cooling_capacity("2800W"), 2800)
    _test("3HP → 7500",
          UnitNormalizer.normalize_cooling_capacity("3HP"), 7500)
    _test("1吨 → 3516",
          UnitNormalizer.normalize_cooling_capacity("1吨"), 3516)
    _test("空字符串 → None",
          UnitNormalizer.normalize_cooling_capacity(""), None)
    _test("无关文本 → None",
          UnitNormalizer.normalize_cooling_capacity("无参数"), None)

    # ── 制热量 ──
    print("\n[制热量 normalize_heating_capacity]")
    _test("1.5匹 → 3500",
          UnitNormalizer.normalize_heating_capacity("1.5匹"), 3500)
    _test("大1匹 → 2800",
          UnitNormalizer.normalize_heating_capacity("大1匹"), 2800)
    _test("9000BTU → 2637",
          UnitNormalizer.normalize_heating_capacity("9000BTU"), 2637)

    # ── 功率 ──
    print("\n[功率 normalize_power]")
    _test("1.2kW → 1200",
          UnitNormalizer.normalize_power("1.2kW"), 1200)
    _test("800W → 800",
          UnitNormalizer.normalize_power("800W"), 800)
    _test("空字符串 → None",
          UnitNormalizer.normalize_power(""), None)

    # ── 噪音 ──
    print("\n[噪音 normalize_noise]")
    _test("38dB(A) → 38.0",
          UnitNormalizer.normalize_noise("38dB(A)"), 38.0)
    _test("<22dB → 22",
          UnitNormalizer.normalize_noise("<22dB"), 22.0)
    _test("≤45dB → 45",
          UnitNormalizer.normalize_noise("≤45dB"), 45.0)
    _test("22-38dB → 38.0",
          UnitNormalizer.normalize_noise("22-38dB"), 38.0)
    _test("20分贝 → 20.0",
          UnitNormalizer.normalize_noise("20分贝"), 20.0)
    _test("空字符串 → None",
          UnitNormalizer.normalize_noise(""), None)

    # ── 风量 ──
    print("\n[风量 normalize_airflow]")
    _test("550m³/h → 550.0",
          UnitNormalizer.normalize_airflow("550m³/h"), 550.0)
    _test("550m3/h → 550.0",
          UnitNormalizer.normalize_airflow("550m3/h"), 550.0)
    _test("680CFM → 1155.0",
          UnitNormalizer.normalize_airflow("680CFM"), 1155.0)
    _test("空字符串 → None",
          UnitNormalizer.normalize_airflow(""), None)

    # ── 能效比 ──
    print("\n[能效比 normalize_eer]")
    _test("EER 3.21 → 3.21",
          UnitNormalizer.normalize_eer("EER 3.21"), 3.21)
    _test("COP 4.0 → 4.0",
          UnitNormalizer.normalize_eer("COP 4.0"), 4.0)
    _test("CSPF 5.5 → 5.5",
          UnitNormalizer.normalize_eer("CSPF 5.5"), 5.5)
    _test("纯数字 3.2 → 3.2",
          UnitNormalizer.normalize_eer("3.2"), 3.2)
    _test("无关文本 → None",
          UnitNormalizer.normalize_eer("无参数"), None)

    # ── 尺寸 ──
    print("\n[尺寸 normalize_dimensions]")
    _test("850×290×190mm → 850×290×190",
          UnitNormalizer.normalize_dimensions("850×290×190mm"), "850×290×190")
    _test("750*280*180mm → 750×280×180",
          UnitNormalizer.normalize_dimensions("750*280*180mm"), "750×280×180")
    _test("850x290mm → 850×290",
          UnitNormalizer.normalize_dimensions("850x290mm"), "850×290")
    _test("空字符串 → None",
          UnitNormalizer.normalize_dimensions(""), None)

    # ── 价格 ──
    print("\n[价格 normalize_price]")
    _test("$599 → $599",
          UnitNormalizer.normalize_price("$599"), "$599")
    _test("¥8,990,000 → ¥8,990,000",
          UnitNormalizer.normalize_price("¥8,990,000"), "¥8,990,000")
    _test("空字符串 → None",
          UnitNormalizer.normalize_price(""), None)

    print("\n" + "─" * 50)
    print("测试完成。")


if __name__ == '__main__':
    test_normalizer()
