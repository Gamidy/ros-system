"""产品主线模型: Platform → Product → Version + ManufacturingVariant"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum, Table, func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class VersionStatus(str, enum.Enum):
    DRAFT = "draft"
    DEVELOPING = "developing"
    RELEASED = "released"
    PRODUCTION = "production"
    OBSOLETE = "obsolete"
    RETIRED = "retired"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    OBSOLETE = "obsolete"


# Version生命周期合法转换映射
VERSION_TRANSITIONS = {
    VersionStatus.DRAFT:        [VersionStatus.DEVELOPING],
    VersionStatus.DEVELOPING:   [VersionStatus.RELEASED, VersionStatus.DRAFT],
    VersionStatus.RELEASED:     [VersionStatus.PRODUCTION, VersionStatus.DEVELOPING],
    VersionStatus.PRODUCTION:   [VersionStatus.OBSOLETE, VersionStatus.RELEASED],
    VersionStatus.OBSOLETE:     [VersionStatus.RETIRED, VersionStatus.PRODUCTION],
    VersionStatus.RETIRED:      [],
}


# Product ↔ Market 多对多关联表
product_market_table = Table(
    "product_markets", Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("market_code", String(20), primary_key=True, comment="市场代码: EU/VN/TW/..."),
)


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="平台编码，如 IDU900, ODU18K")
    name = Column(String(100), nullable=False, comment="平台名称")
    platform_type = Column(String(20), nullable=False, comment="IDU室内机 / ODU室外机")
    status = Column(String(20), default="active", comment="active/developing/obsolete")
    description = Column(Text, nullable=True)
    # 平台尺寸约束（PR-02）
    dimensions = Column(String(200), nullable=True, comment="外观尺寸约束描述")
    hard_constraints = Column(Text, nullable=True, comment="硬约束JSON: 外观结构件清单")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    products = relationship("Product", back_populates="platform", foreign_keys="Product.platform_id")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="产品编码/整机成品码")
    name = Column(String(200), nullable=False, comment="产品名称")
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    # 产品定义要素（PR-11: Product = Market × Capacity × Platform）
    capacity = Column(String(20), nullable=True, comment="容量: 09K/12K/18K/24K")
    indoor_platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True, comment="室内平台引用")
    outdoor_platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True, comment="室外平台引用")
    indoor_product_code = Column(String(50), nullable=True, comment="内机成品码")
    outdoor_product_code = Column(String(50), nullable=True, comment="外机成品码")
    status = Column(String(20), default=ProductStatus.ACTIVE.value, comment="active/obsolete")
    description = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    platform = relationship("Platform", back_populates="products", foreign_keys=[platform_id])
    indoor_platform = relationship("Platform", foreign_keys=[indoor_platform_id], overlaps="platform")
    outdoor_platform = relationship("Platform", foreign_keys=[outdoor_platform_id], overlaps="platform")
    versions = relationship("Version", back_populates="product")
    markets = relationship("Market", secondary="product_markets",
                          primaryjoin="Product.id == product_markets.c.product_id",
                          secondaryjoin="Market.code == product_markets.c.market_code",
                          back_populates="products")


class Market(Base):
    """市场字典表"""
    __tablename__ = "markets"

    code = Column(String(20), primary_key=True, comment="市场代码: VN/TH/ID/SA/AE/..." )
    name = Column(String(100), nullable=False, comment="市场名称")
    region = Column(String(50), nullable=True, comment="区域: SEA/GCC/ME/...")
    energy_standard = Column(String(20), nullable=True, comment="能效标准代码: cspf/iseer/seer/eer")
    energy_label = Column(String(20), nullable=True, comment="能效标准显示名: CSPF/ISEER/SEER/EER")
    energy_unit = Column(String(20), nullable=True, comment="能效单位: W/W/BTU/Wh")
    # ── 新增国家级参数（PR-12: 市场级别竞品对标参数） ──
    energy_standard_detail = Column(String(100), nullable=True, comment="能效标准细分（如 2025新标准/MEPS等级）")
    national_standard = Column(String(100), nullable=True, comment="国家标准编号，如 GB/T 7725")
    voltage_freq = Column(String(50), nullable=True, comment="电压/频率，如 220V/50Hz")
    cooling_max_temp = Column(Float, nullable=True, comment="制冷最高环境温度 °C")
    heating_min_temp = Column(Float, nullable=True, comment="制热最低环境温度 °C")
    structure_type = Column(String(100), nullable=True, comment="机型结构（分体壁挂/天花/风管/柜机）")
    main_selling_model = Column(String(200), nullable=True, comment="主销机型描述")
    refrigerant = Column(String(50), nullable=True, comment="主要制冷剂，如 R32/R410A/R290")
    refrigerant_charge = Column(Float, nullable=True, comment="标准制冷剂灌注量 g")
    # ── 结束新增 ──
    is_active = Column(String(5), default="true")

    products = relationship("Product", secondary="product_markets",
                          primaryjoin="Market.code == product_markets.c.market_code",
                          secondaryjoin="Product.id == product_markets.c.product_id",
                          back_populates="markets")


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    version_no = Column(String(50), nullable=False, comment="版本号，如 V1.0, V1.1, V2.0")
    status = Column(SAEnum(VersionStatus), default=VersionStatus.DRAFT, nullable=False)
    reason = Column(String(500), nullable=True, comment="版本变更原因")
    change_type = Column(String(50), nullable=True, comment="变更类型: performance/structural/certification/bom_only")
    customer_perceivable = Column(String(5), default="false", comment="客户是否可感知（PR-09）")
    effective_date = Column(DateTime, nullable=True, comment="生效日期")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="versions")
    manufacturing_variants = relationship("ManufacturingVariant", back_populates="version")


class ManufacturingVariant(Base):
    """制造变体：同一Version在不同工厂的差异化MBOM（PR-10: Product Version ≠ MBOM Version）"""
    __tablename__ = "manufacturing_variants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    factory_code = Column(String(50), nullable=False, comment="工厂代码")
    factory_name = Column(String(100), nullable=True, comment="工厂名称")
    mbom_version = Column(String(20), nullable=False, comment="该工厂的MBOM版本号")
    description = Column(Text, nullable=True, comment="差异化说明（如辅料/工艺不同）")
    is_active = Column(String(5), default="true")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    version = relationship("Version", back_populates="manufacturing_variants")
