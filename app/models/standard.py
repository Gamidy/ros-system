"""海外空调标准监控 — ORM 模型

4 张表:
- StandardRegion     — 标准发布机构/地区（欧盟/美国/沙特/IEC）
- StandardCategory   — 标准分类（性能/能效/噪音/安规/EMC/认证）
- Standard           — 核心标准条目
- StandardCrawl      — 爬取任务日志

关系:
- Standard.region   → StandardRegion
- Standard.category → StandardCategory
- StandardCrawl.region → StandardRegion
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    ForeignKey, UniqueConstraint, func, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ════════════════════════════════════════════════════════════════════════════
# 预置常量
# ════════════════════════════════════════════════════════════════════════════

REGION_CODES: list[str] = [
    "EU", "US", "SA", "IEC",
    "VN", "ID", "MY", "PK",
    "AE", "KW", "IR", "IL",
    "RU", "UA",
    "ZA", "EG", "NG", "GH",
    "TW",
    "BR", "AR", "CL", "CO", "MX",
]
"""监控的地区/机构代码"""

REGION_PRESETS: list[dict] = [
    # ── 已有（带爬虫） ──
    {"code": "EU",  "name": "欧盟",   "name_en": "European Union",
     "base_url": "https://eur-lex.europa.eu", "scan_method": "rss", "is_active": True},
    {"code": "US",  "name": "美国",   "name_en": "United States",
     "base_url": "https://www.federalregister.gov", "scan_method": "html", "is_active": False},
    {"code": "SA",  "name": "沙特阿拉伯", "name_en": "Saudi Arabia",
     "base_url": "https://saso.gov.sa", "scan_method": "html", "is_active": False},
    {"code": "IEC", "name": "国际电工委员会", "name_en": "IEC",
     "base_url": "https://webstore.iec.ch", "scan_method": "api", "is_active": False},

    # ── 东南亚 ──
    {"code": "VN", "name": "越南", "name_en": "Vietnam",
     "base_url": "https://tcvn.gov.vn", "scan_method": "manual", "is_active": False},
    {"code": "ID", "name": "印度尼西亚", "name_en": "Indonesia",
     "base_url": "https://bsn.go.id", "scan_method": "manual", "is_active": False},
    {"code": "MY", "name": "马来西亚", "name_en": "Malaysia",
     "base_url": "https://www.jsm.gov.my", "scan_method": "manual", "is_active": False},
    {"code": "PK", "name": "巴基斯坦", "name_en": "Pakistan",
     "base_url": "https://psqca.gov.pk", "scan_method": "manual", "is_active": False},

    # ── 中东 ──
    {"code": "AE", "name": "阿联酋", "name_en": "UAE",
     "base_url": "https://www.esma.gov.ae", "scan_method": "manual", "is_active": False},
    {"code": "KW", "name": "科威特", "name_en": "Kuwait",
     "base_url": "https://www.kowsmd.gov.kw", "scan_method": "manual", "is_active": False},
    {"code": "IR", "name": "伊朗", "name_en": "Iran",
     "base_url": "https://www.isiri.gov.ir", "scan_method": "manual", "is_active": False},
    {"code": "IL", "name": "以色列", "name_en": "Israel",
     "base_url": "https://www.sii.org.il", "scan_method": "manual", "is_active": False},

    # ── 独联体 ──
    {"code": "RU", "name": "俄罗斯", "name_en": "Russia",
     "base_url": "https://www.gost.ru", "scan_method": "manual", "is_active": False},
    {"code": "UA", "name": "乌克兰", "name_en": "Ukraine",
     "base_url": "https://www.dstu.gov.ua", "scan_method": "manual", "is_active": False},

    # ── 非洲 ──
    {"code": "ZA", "name": "南非", "name_en": "South Africa",
     "base_url": "https://www.sabs.co.za", "scan_method": "manual", "is_active": False},
    {"code": "EG", "name": "埃及", "name_en": "Egypt",
     "base_url": "https://www.eos.org.eg", "scan_method": "manual", "is_active": False},
    {"code": "NG", "name": "尼日利亚", "name_en": "Nigeria",
     "base_url": "https://www.son.gov.ng", "scan_method": "manual", "is_active": False},
    {"code": "GH", "name": "加纳", "name_en": "Ghana",
     "base_url": "https://www.gsa.gov.gh", "scan_method": "manual", "is_active": False},

    # ── 东亚 ──
    {"code": "TW", "name": "台湾", "name_en": "Taiwan",
     "base_url": "https://www.bsmi.gov.tw", "scan_method": "manual", "is_active": False},

    # ── 南美 ──
    {"code": "BR", "name": "巴西", "name_en": "Brazil",
     "base_url": "https://www.abnt.org.br", "scan_method": "manual", "is_active": False},
    {"code": "AR", "name": "阿根廷", "name_en": "Argentina",
     "base_url": "https://www.iram.org.ar", "scan_method": "manual", "is_active": False},
    {"code": "CL", "name": "智利", "name_en": "Chile",
     "base_url": "https://www.inn.cl", "scan_method": "manual", "is_active": False},
    {"code": "CO", "name": "哥伦比亚", "name_en": "Colombia",
     "base_url": "https://www.icontec.org", "scan_method": "manual", "is_active": False},
    {"code": "MX", "name": "墨西哥", "name_en": "Mexico",
     "base_url": "https://www.dof.gob.mx", "scan_method": "manual", "is_active": False},
]

CATEGORY_CODES: list[str] = [
    "performance", "energy", "noise", "safety", "emc", "certification",
]
"""标准分类代码"""

CATEGORY_PRESETS: list[dict] = [
    {"code": "performance",   "name": "性能标准",     "name_en": "Performance"},
    {"code": "energy",        "name": "能效标准",     "name_en": "Energy Efficiency"},
    {"code": "noise",         "name": "噪音标准",     "name_en": "Noise"},
    {"code": "safety",        "name": "安规标准",     "name_en": "Safety"},
    {"code": "emc",           "name": "EMC电磁兼容", "name_en": "EMC"},
    {"code": "certification", "name": "认证要求",     "name_en": "Certification"},
]

STANDARD_STATUSES: list[str] = ["active", "superseded", "draft", "repealed"]
"""标准状态枚举"""

IMPACT_LEVELS: list[str] = ["critical", "high", "medium", "low"]
"""影响等级"""


# ════════════════════════════════════════════════════════════════════════════
# ORM 模型
# ════════════════════════════════════════════════════════════════════════════


class StandardRegion(Base):
    """标准发布机构/地区"""
    __tablename__ = "standard_regions"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    code: str = Column(String(20), unique=True, nullable=False, comment="地区/机构代码: EU, US, SA, IEC")
    name: str = Column(String(100), nullable=False, comment="中文名称")
    name_en: Optional[str] = Column(String(100), comment="英文名称")
    base_url: Optional[str] = Column(String(512), comment="官网 URL")
    scan_method: str = Column(String(32), nullable=False, default="rss", comment="爬取方式: rss | html | api")
    scan_config: Optional[dict] = Column(JSON, comment="爬取配置（选择器/API 参数等）")
    is_active: bool = Column(Boolean, nullable=False, default=True, comment="是否启用爬取")
    sort_order: int = Column(Integer, nullable=False, default=0)
    created_at: datetime = Column(DateTime, nullable=False, server_default=func.now())
    updated_at: datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 关系
    standards: list["Standard"] = relationship("Standard", back_populates="region")
    crawls: list["StandardCrawl"] = relationship("StandardCrawl", back_populates="region")

    def __repr__(self) -> str:
        return f"<StandardRegion(id={self.id}, code={self.code!r}, name={self.name!r})>"


class StandardCategory(Base):
    """标准分类"""
    __tablename__ = "standard_categories"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    code: str = Column(String(32), unique=True, nullable=False, comment="分类编码")
    name: str = Column(String(100), nullable=False, comment="分类名称")
    name_en: Optional[str] = Column(String(100), comment="英文名称")
    sort_order: int = Column(Integer, nullable=False, default=0)

    # 关系
    standards: list["Standard"] = relationship("Standard", back_populates="category")

    def __repr__(self) -> str:
        return f"<StandardCategory(id={self.id}, code={self.code!r})>"


class Standard(Base):
    """核心标准条目"""
    __tablename__ = "standards"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    region_id: int = Column(Integer, ForeignKey("standard_regions.id"), nullable=False, comment="所属地区 ID")
    category_id: Optional[int] = Column(Integer, ForeignKey("standard_categories.id"), comment="标准分类 ID")

    # 标准标识
    std_number: str = Column(String(100), nullable=False, comment="标准编号（如 EN 14825:2022）")
    title: str = Column(String(500), nullable=False, comment="标准标题")
    title_en: Optional[str] = Column(String(500), comment="英文标题")

    # 版本信息
    version: Optional[str] = Column(String(50), comment="版本号")
    amendment: Optional[str] = Column(String(200), comment="修订信息")
    status: str = Column(String(32), nullable=False, default="active", comment="状态: active|superseded|draft|repealed")
    effective_date: Optional[date] = Column(Date, comment="生效日期")
    repeal_date: Optional[date] = Column(Date, comment="废止日期")

    # 来源
    source_url: Optional[str] = Column(String(1024), comment="原文链接")
    source_text: Optional[str] = Column(Text, comment="原文摘要/正文（截取）")
    crawl_id: Optional[int] = Column(Integer, comment="来源爬取记录 ID")

    # 空调产品标签（JSON 数组）
    tags: Optional[dict] = Column(JSON, comment='["split-ac","vrf","window-ac","heat-pump"]')

    # 影响评估
    impact_level: Optional[str] = Column(String(16), comment="影响等级: critical|high|medium|low")
    impact_scope: Optional[str] = Column(Text, comment="影响范围描述（对当前在研产品的影响）")

    # 元数据
    created_by: Optional[str] = Column(String(64), comment="创建人（爬虫 = system）")
    created_at: datetime = Column(DateTime, nullable=False, server_default=func.now())
    updated_at: datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 关系
    region: StandardRegion = relationship("StandardRegion", back_populates="standards")
    category: Optional[StandardCategory] = relationship("StandardCategory", back_populates="standards")

    # 索引
    __table_args__ = (
        UniqueConstraint("region_id", "std_number", name="uq_standard_region_number"),
        {"comment": "空调海外标准条目库"},
    )

    def __repr__(self) -> str:
        return f"<Standard(id={self.id}, std_number={self.std_number!r}, status={self.status!r})>"


class StandardCrawl(Base):
    """标准爬取任务日志"""
    __tablename__ = "standard_crawls"

    __allow_unmapped__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    region_id: int = Column(Integer, ForeignKey("standard_regions.id"), nullable=False, comment="爬取来源地区 ID")
    started_at: datetime = Column(DateTime, nullable=False, comment="开始时间")
    finished_at: Optional[datetime] = Column(DateTime, comment="结束时间")
    status: str = Column(String(20), nullable=False, default="running", comment="状态: running|success|failed")

    # 结果统计
    total_fetched: int = Column(Integer, nullable=False, default=0, comment="本次抓取到的条目数")
    new_added: int = Column(Integer, nullable=False, default=0, comment="新增入库数")
    updated: int = Column(Integer, nullable=False, default=0, comment="更新数")
    skipped: int = Column(Integer, nullable=False, default=0, comment="跳过（重复/不相关）数")

    # 错误信息
    error_message: Optional[str] = Column(Text, comment="失败时的错误详情")
    raw_response: Optional[str] = Column(Text, comment="爬取原始响应（调试用，保留 7 天）")

    created_at: datetime = Column(DateTime, nullable=False, server_default=func.now())

    # 关系
    region: StandardRegion = relationship("StandardRegion", back_populates="crawls")

    def __repr__(self) -> str:
        return f"<StandardCrawl(id={self.id}, region_id={self.region_id}, status={self.status!r})>"
