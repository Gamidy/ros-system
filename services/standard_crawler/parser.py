"""标准编号/标题解析引擎

从原始文本中提取标准编号、生效日期、分类、影响等级。
"""
import re
from typing import Optional


class StandardParser:
    """标准文本解析引擎"""

    # ── 标准编号正则模式 ──
    STD_PATTERNS: list[re.Pattern] = [
        re.compile(r"EN\s+\d+(?:[:\-]\d{4})?", re.I),         # EN 14825:2022
        re.compile(r"IEC\s+\d+(?:[:\-]\d{4})?", re.I),         # IEC 60335-2-40:2024
        re.compile(r"ISO\s+\d+(?:[:\-]\d{4})?", re.I),          # ISO 5151
        re.compile(r"ANSI/ASHRAE\s+\d+[\-]\d{4}", re.I),        # ANSI/ASHRAE 34-2022
        re.compile(r"SASO\s+\d+(?:[:\-]\d{4})?", re.I),         # SASO 2663:2021
        re.compile(r"10\s*CFR\s+Part\s+\d+", re.I),             # 10 CFR Part 430
        re.compile(r"\(EU\)\s+\d{4}/\d+", re.I),                # (EU) 2024/1781
        re.compile(r"Commission\s+Regulation.*?EU.*?\d{4}/\d+", re.I),  # Commission Regulation (EU) ...
        re.compile(r"AHRI\s+Standard\s+\d+", re.I),             # AHRI Standard 210/240
        re.compile(r"UL\s+\d+", re.I),                          # UL 484
    ]

    # ── 空调关键词过滤 ──
    HVAC_KEYWORDS: list[str] = [
        "air condition", "heat pump", "refrigerant", "cooling",
        "heating", "hvac", "chiller", "ventilation", "air-to-air",
        "air-to-water", "split", "vrf", "fan coil", "dehumidif",
        "compressor", "evaporator", "condenser", "room air",
    ]

    # ── 分类关键词映射 ──
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "performance": [
            "eer", "cop", "seer", "scop", "performance", "capacity",
            "energy efficiency ratio", "coefficient of performance",
        ],
        "energy": [
            "energy label", "meps", "efficiency", "ecodesign", "erp",
            "energy consumption", "energy rating", "energy star",
        ],
        "noise": [
            "noise", "sound", "acoustic", "db(a)", "dba", "sound power",
        ],
        "safety": [
            "safety", "iec 60335", "ul 60335", "flammable", "refrigerant",
            "electrical safety", "protection against",
        ],
        "emc": [
            "emc", "electromagnetic", "emission", "immunity",
            "electromagnetic compatibility",
        ],
        "certification": [
            "ce marking", "ul listing", "certification", "conformity",
            "declaration of conformity",
        ],
    }

    # ── 影响等级判定 ──
    HIGH_IMPACT_KEYWORDS: list[str] = [
        "mandatory", "prohibition", "ban", "phased out",
        "repeal", "replace", "amendment", "revised",
    ]
    CRITICAL_KEYWORDS: list[str] = [
        "safety", "flammable", "leak", "fire",
        "immediate effect", "entry into force",
    ]

    @classmethod
    def extract_std_number(cls, text: str) -> Optional[str]:
        """从文本中提取第一个标准编号"""
        for pattern in cls.STD_PATTERNS:
            m = pattern.search(text)
            if m:
                return m.group(0).strip()
        return None

    @classmethod
    def is_hvac_related(cls, text: str) -> bool:
        """检查文本是否与空调/热泵相关"""
        lower = text.lower()
        return any(kw in lower for kw in cls.HVAC_KEYWORDS)

    @classmethod
    def classify_category(cls, text: str) -> list[str]:
        """根据文本内容推断标准分类"""
        lower = text.lower()
        matched: list[str] = []
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                matched.append(category)
        return matched

    @classmethod
    def assess_impact(cls, title: str, summary: str = "") -> str:
        """评估影响等级: critical | high | medium | low"""
        combined = f"{title} {summary}".lower()
        if any(kw in combined for kw in cls.CRITICAL_KEYWORDS):
            return "critical"
        if any(kw in combined for kw in cls.HIGH_IMPACT_KEYWORDS):
            return "high"
        return "medium"

    @classmethod
    def extract_effective_date(cls, text: str) -> Optional[str]:
        """从文本中提取疑似生效日期"""
        # 匹配 "from DD/MM/YYYY" 或 "effective DD Month YYYY"
        patterns = [
            r"(?:effective|from|as of|applicable)\s+(?:from\s+)?(\d{1,2}\s+\w+\s+\d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(?:entry into force|enter into force)\s+(?:\w+\s+){0,3}(\d{1,2}\s+\w+\s+\d{4})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(1).strip()
        return None
