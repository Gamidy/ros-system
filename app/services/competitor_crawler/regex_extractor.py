"""
纯正则参数提取器 RegexParamExtractor

在 LLM 不可用时的降级方案。通过预定义的正则 PATTERNS 从原始文本中
提取空调参数，并用 UnitNormalizer 做后处理归一化。

设计原则:
  - 纯标准库 (re + typing)，无外部依赖
  - 每个字段一组 Pattern，按优先级顺序匹配
  - extract() 返回原始正则捕获结果
  - extract_all() 调用 UnitNormalizer 做数值归一化
"""

import re
from typing import Any, Pattern


class RegexParamExtractor:
    """基于纯正则的空调参数提取器（LLM 降级方案）。"""

    PATTERNS: dict[str, list[Pattern]] = {
        # ── 制冷量 (W) ──────────────────────────────────────────────
        "cooling_capacity_w": [
            # "制冷量: 3500W"
            re.compile(r'(?:制冷量|制冷能力|冷量|Cooling)[^\d]*?(\d+(?:\.\d+)?)\s*(?:W|w|瓦)', re.IGNORECASE),
            # "3500W 制冷量"
            re.compile(r'(\d+(?:\.\d+)?)\s*(?:W|w|瓦)\s*(?:制冷量|制冷能力)', re.IGNORECASE),
            # "额定制冷量(W) 3500"
            re.compile(r'额定\s*制冷[^)\]]*(?:\(?W\)?)?[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # "3500" after keyword
            re.compile(r'(?:制冷量|Cooling)[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
        ],

        # ── 制热量 (W) ──────────────────────────────────────────────
        "heating_capacity_w": [
            # "制热量: 4000W"
            re.compile(r'(?:制热量|制热能力|热量|Heating)[^\d]*?(\d+(?:\.\d+)?)\s*(?:W|w|瓦)', re.IGNORECASE),
            # "额定制热量(W) 4000"
            re.compile(r'额定\s*制热[^)\]]*(?:\(?W\)?)?[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # "3800W制热" / "4000W制热量"
            re.compile(r'(\d+(?:\.\d+)?)\s*(?:W|w|瓦)\s*(?:制热|制热量|制热能力)', re.IGNORECASE),
            # "制热量：4000"
            re.compile(r'(?:制热量|Heating)[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
        ],

        # ── 功率 (W) ────────────────────────────────────────────────
        "power_w": [
            # "额定功率: 1200W"
            re.compile(r'(?:额定)?\s*(?:功率|输入功率|耗电量|Power|Input)[^\d]*?(\d+(?:\.\d+)?)\s*(?:W|w|瓦)', re.IGNORECASE),
            # "功率(W): 1200"
            re.compile(r'(?:功率|Power)[^)\]]*(?:\(?W\)?)?[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # Standalone "1200W"
            re.compile(r'(\d+)\s*W(?!\s*[a-zA-Z])'),
        ],

        # ── 噪音 ────────────────────────────────────────────────────
        "noise_indoor_db": [
            # "室内噪音: 38dB(A)"
            re.compile(r'(?:室内|内机|室内机|Indoor|内)[^\d]*?(\d+(?:\.\d+)?)\s*(?:dB|分贝)', re.IGNORECASE),
            # "室内机噪音(低/高) 22/38dB"
            re.compile(r'(?:室内|内机|Indoor)[^)]*?(?:\d+\s*[//]\s*)?(\d+(?:\.\d+)?)\s*(?:dB|分贝)', re.IGNORECASE),
        ],
        "noise_outdoor_db": [
            # "室外噪音: 52dB(A)"
            re.compile(r'(?:室外|外机|室外机|Outdoor|外)[^\d]*?(\d+(?:\.\d+)?)\s*(?:dB|分贝)', re.IGNORECASE),
        ],

        # ── 风量 (m³/h) ────────────────────────────────────────────
        "airflow_m3h": [
            # "风量: 550m³/h"
            re.compile(r'(?:风量|循环风量|Airflow|空气流量)[^\d]*?(\d+(?:\.\d+)?)\s*m[³3](?:\s*/\s*h|/h)?', re.IGNORECASE),
            # "循环风量(m³/h) 550"
            re.compile(r'(?:循环风量|风量|Airflow)[^)\]]*(?:\(?m[³3]/h\)?)?[：:\s]*(\d+(?:\.\d+)?)', re.IGNORECASE),
            # "550m³/h" standalone
            re.compile(r'(\d+)\s*m[³3](?:\s*/\s*h|/h)'),
        ],

        # ── 能效等级 ────────────────────────────────────────────────
        "energy_rating": [
            # "能效1级" / "1级能效"
            re.compile(r'(?:能效|能效等级|EER等级)[^\d]*?(\d+)\s*级', re.IGNORECASE),
            # "1级" after "能效"
            re.compile(r'(?:能效|Energy)[：:\s]*(\d+)\s*级', re.IGNORECASE),
            # "A++" / "A+" / "A" 等能效标签
            re.compile(r'\b([A-F]\+{0,2})(?!\w)'),
            # "5 stars"
            re.compile(r'(\d+)\s*[星⭐*]', re.IGNORECASE),
        ],

        # ── EER/COP ────────────────────────────────────────────────
        "eer": [
            # "EER: 3.21"
            re.compile(r'(?:EER|eer|能源效率比)[：:\s]*(\d+\.\d+)', re.IGNORECASE),
            # "COP: 4.0"
            re.compile(r'(?:COP|cop)[：:\s]*(\d+\.\d+)', re.IGNORECASE),
        ],

        # ── CSPF (东南亚) ─────────────────────────────────────────
        "cspf": [
            # "CSPF: 5.5"
            re.compile(r'(?:CSPF|cspf|全年能源消耗效率)[：:\s]*(\d+\.\d+)', re.IGNORECASE),
        ],

        # ── 匹数 ────────────────────────────────────────────────────
        "horsepower": [
            # "1.5匹"
            re.compile(r'(\d+(?:\.\d+)?)\s*匹'),
            # "大1匹" / "小1匹"
            re.compile(r'(大|小)\s*(\d+)\s*匹'),
        ],

        # ── 适用面积 ────────────────────────────────────────────────
        "area_m2": [
            # "适用面积: 15-22m²"
            re.compile(r'(?:适用面积|覆盖面积|Area)[^\d]*?(\d+(?:\.\d+)?)\s*(?:-|~)\s*(\d+(?:\.\d+)?)\s*m[²2]', re.IGNORECASE),
            # "15-22m²"
            re.compile(r'(\d+)\s*(?:-|~)\s*(\d+)\s*m[²2]'),
        ],

        # ── 尺寸 ────────────────────────────────────────────────────
        "dimensions": [
            # "850×290×190mm"
            re.compile(r'(\d+)\s*[×*xX]\s*(\d+)\s*[×*xX]\s*(\d+)\s*mm?'),
            # "尺寸：850x290x190mm"
            re.compile(r'(?:尺寸|外形尺寸|Dimension|产品尺寸)[^\d]*?(\d+)\s*[×*xX]\s*(\d+)\s*[×*xX]\s*(\d+)', re.IGNORECASE),
        ],

        # ── 重量 ────────────────────────────────────────────────────
        "weight_kg": [
            # "净重: 12kg"
            re.compile(r'(?:净重|毛重|重量|Weight|Net)[^\d]*?(\d+(?:\.\d+)?)\s*kg', re.IGNORECASE),
            # "12.5kg"
            re.compile(r'(\d+(?:\.\d+)?)\s*kg'),
        ],

        # ── 制冷剂 ──────────────────────────────────────────────────
        "refrigerant": [
            # "制冷剂: R32"
            re.compile(r'(?:制冷剂|冷媒|Refrigerant)[：:\s]*([Rr]\d{2,3}[A-Za-z]?)', re.IGNORECASE),
            # "R410A"
            re.compile(r'\b([Rr]\d{2,3}[A-Za-z]?)\b'),
        ],

        # ── 电压/频率 ──────────────────────────────────────────────
        "voltage_hz": [
            # "220V/50Hz"
            re.compile(r'(\d{3,4})\s*V\s*[/]\s*(\d{2})\s*Hz', re.IGNORECASE),
            # "220-240V~50Hz"
            re.compile(r'(\d{3,4})\s*(?:-\s*\d{3,4})?\s*V\s*[~]\s*(\d{2})\s*Hz', re.IGNORECASE),
        ],

        # ── 价格 ────────────────────────────────────────────────────
        "price": [
            # "$599"
            re.compile(r'[\$][\s]*(\d[\d,.]*)'),
            # "¥8,990,000"
            re.compile(r'[¥￥][\s]*(\d[\d,.]*)'),
            # "8.990.000₫"
            re.compile(r'(\d[\d,.]*)\s*[₫đ]'),
        ],
    }

    def extract(self, raw_text: str) -> dict[str, Any]:
        """从原始文本中提取参数。

        返回 {field_name: matching_value, ...}，只有匹配到的字段。
        每个字段返回第一个匹配的值。
        """
        if not raw_text:
            return {}

        result: dict[str, Any] = {}

        for field_name, patterns in self.PATTERNS.items():
            for pattern in patterns:
                m = pattern.search(raw_text)
                if m:
                    groups = m.groups()
                    if not groups:
                        continue

                    # Multiple capture groups → tuple or range
                    if len(groups) >= 2 and all(g is not None for g in groups):
                        # For 3-group dimensions, return the raw tuple of strings
                        if len(groups) >= 3:
                            result[field_name] = groups
                        else:
                            # For 2-group pairs (e.g. voltage, area range), try numeric
                            try:
                                result[field_name] = (float(groups[0]), float(groups[1]))
                            except (ValueError, TypeError):
                                result[field_name] = groups
                    else:
                        captured = groups[0]
                        # Try numeric if it looks like a number
                        if captured is not None:
                            try:
                                if '.' in captured:
                                    result[field_name] = float(captured)
                                else:
                                    result[field_name] = int(captured)
                            except (ValueError, TypeError):
                                result[field_name] = captured
                    break  # First match wins per field

        return result

    def extract_all(self, raw_text: str) -> dict[str, Any]:
        """提取并归一化。

        调用 extract() 后，对特定字段通过 UnitNormalizer 做后处理归一化。
        """
        from .unit_normalizer import UnitNormalizer  # noqa: F811

        raw = self.extract(raw_text)
        result: dict[str, Any] = {}
        result.update(raw)

        # 后处理归一化
        # 制冷量: 尝试从原始文本直接归一化
        if "cooling_capacity_w" not in result:
            cc = UnitNormalizer.normalize_cooling_capacity(raw_text)
            if cc is not None:
                result["cooling_capacity_w"] = cc

        if "heating_capacity_w" not in result:
            hc = UnitNormalizer.normalize_heating_capacity(raw_text)
            if hc is not None:
                result["heating_capacity_w"] = hc

        if "power_w" not in result:
            pw = UnitNormalizer.normalize_power(raw_text)
            if pw is not None:
                result["power_w"] = pw

        if "noise_indoor_db" not in result and "noise_outdoor_db" not in result:
            noise = UnitNormalizer.normalize_noise(raw_text)
            if noise is not None:
                result["noise_indoor_db"] = noise

        if "airflow_m3h" not in result:
            af = UnitNormalizer.normalize_airflow(raw_text)
            if af is not None:
                result["airflow_m3h"] = af

        if "eer" not in result:
            eer = UnitNormalizer.normalize_eer(raw_text)
            if eer is not None:
                result["eer"] = eer

        if "dimensions" not in result:
            dim = UnitNormalizer.normalize_dimensions(raw_text)
            if dim is not None:
                result["dimensions"] = dim

        if "price" not in result:
            pr = UnitNormalizer.normalize_price(raw_text)
            if pr is not None:
                result["price"] = pr

        return result


# ═══════════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════════

def _test(name: str, actual, expected) -> None:
    status = "PASS" if actual == expected else "FAIL"
    if status == "FAIL":
        print(f"  [{status}] {name}: expected {expected!r}, got {actual!r}")
    else:
        print(f"  [{status}] {name}")


def test_extractor() -> None:
    """运行 RegexParamExtractor 测试用例。"""
    print("RegexParamExtractor 测试报告:")
    print("─" * 60)

    extractor = RegexParamExtractor()

    # ── extract() ──
    print("\n[extract - 单项提取]")

    # 制冷量
    result = extractor.extract("制冷量: 3500W")
    _test("制冷量: 3500W → cooling_capacity_w=3500",
          result.get("cooling_capacity_w"), 3500)

    result = extractor.extract("额定制冷量(W) 3500")
    _test("额定制冷量(W) 3500 → 3500",
          result.get("cooling_capacity_w"), 3500)

    # 制热量
    result = extractor.extract("制热量: 4000W")
    _test("制热量: 4000W → 4000",
          result.get("heating_capacity_w"), 4000)

    # 功率
    result = extractor.extract("额定功率: 1200W")
    _test("额定功率: 1200W → 1200",
          result.get("power_w"), 1200)

    result = extractor.extract("功率(W): 1500")
    _test("功率(W): 1500 → 1500",
          result.get("power_w"), 1500)

    # 噪音
    result = extractor.extract("室内噪音: 38dB(A)")
    _test("室内噪音: 38dB(A) → 38",
          result.get("noise_indoor_db"), 38)

    result = extractor.extract("室外噪音: 52dB")
    _test("室外噪音: 52dB → 52",
          result.get("noise_outdoor_db"), 52)

    # 风量
    result = extractor.extract("风量: 550m³/h")
    _test("风量: 550m³/h → 550",
          result.get("airflow_m3h"), 550)

    result = extractor.extract("循环风量(m³/h) 550")
    _test("循环风量(m³/h) 550 → 550",
          result.get("airflow_m3h"), 550)

    # 能效等级
    result = extractor.extract("能效1级")
    _test("能效1级 → 1",
          result.get("energy_rating"), 1)

    result = extractor.extract("A++")
    _test("A++ → 'A++'",
          result.get("energy_rating"), "A++")

    # EER/COP
    result = extractor.extract("EER: 3.21")
    _test("EER: 3.21 → 3.21",
          result.get("eer"), 3.21)

    result = extractor.extract("COP: 4.0")
    _test("COP: 4.0 → 4.0",
          result.get("eer"), 4.0)

    # CSPF
    result = extractor.extract("CSPF: 5.5")
    _test("CSPF: 5.5 → 5.5",
          result.get("cspf"), 5.5)

    # 匹数
    result = extractor.extract("1.5匹")
    _test("1.5匹 → 1.5",
          result.get("horsepower"), 1.5)

    # 尺寸
    result = extractor.extract("850×290×190mm")
    _test("850×290×190mm → ('850','290','190')",
          result.get("dimensions"), ("850", "290", "190"))

    result = extractor.extract("尺寸：750*280*180mm")
    _test("尺寸：750*280*180mm → ('750','280','180')",
          result.get("dimensions"), ("750", "280", "180"))

    # 重量
    result = extractor.extract("净重: 12kg")
    _test("净重: 12kg → 12",
          result.get("weight_kg"), 12)

    result = extractor.extract("12.5kg")
    _test("12.5kg → 12.5",
          result.get("weight_kg"), 12.5)

    # 制冷剂
    result = extractor.extract("制冷剂: R32")
    _test("制冷剂: R32 → 'R32'",
          result.get("refrigerant"), "R32")

    result = extractor.extract("R410A")
    _test("R410A → 'R410A'",
          result.get("refrigerant"), "R410A")

    # 电压/频率
    result = extractor.extract("220V/50Hz")
    _test("220V/50Hz → (220,50)",
          result.get("voltage_hz"), (220.0, 50.0))

    # 价格
    result = extractor.extract("$599")
    _test("$599 → 599",
          result.get("price"), 599)

    result = extractor.extract("¥8,990,000")
    _test("¥8,990,000 → 8,990,000",
          result.get("price"), "8,990,000")

    # ── extract_all() ──
    print("\n[extract_all - 带归一化]")

    result = extractor.extract_all("1.5匹 制冷量 3500W 3800W制热 噪音38dB")
    _test("extract_all 1.5匹 → cooling_capacity_w=3500",
          result.get("cooling_capacity_w"), 3500)
    _test("extract_all 1.5匹 → heating_capacity_w=3800",
          result.get("heating_capacity_w"), 3800)
    _test("extract_all 1.5匹 → noise_indoor_db=38",
          result.get("noise_indoor_db"), 38)

    # 纯归一化降级 (extract 没匹配到，靠 UnitNormalizer 补)
    result = extractor.extract_all("9000BTU 1.5匹")
    # 匹数被正则提取
    _test("extract_all 9000BTU 1.5匹 → horsepower=1.5",
          result.get("horsepower"), 1.5)
    # 制冷量通过 UnitNormalizer 补上
    _test("extract_all 9000BTU 1.5匹 → cooling_capacity_w=2637",
          result.get("cooling_capacity_w"), 2637)

    result = extractor.extract_all("大1匹 2200W制热")
    _test("extract_all 大1匹 → cooling_capacity_w=2800",
          result.get("cooling_capacity_w"), 2800)
    _test("extract_all 大1匹 → heating_capacity_w=2200",
          result.get("heating_capacity_w"), 2200)

    # ── 空输入 ──
    result = extractor.extract("")
    _test("空输入 → {}",
          result, {})

    result = extractor.extract_all("")
    _test("空输入 extract_all → {}",
          result, {})

    print("\n" + "─" * 60)
    print("测试完成。")


if __name__ == '__main__':
    test_extractor()
