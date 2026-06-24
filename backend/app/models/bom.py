"""BOM物料模型: 6层体系 + Part主数据 + AVL + 替代料 + CDF + 市场认证标记"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Date, Table, func
from sqlalchemy.orm import relationship
from app.core.database import Base


# ==== Part ↔ 替代料 多对多关联表 ====
part_alternative_table = Table(
    "part_alternatives", Base.metadata,
    Column("part_id", Integer, ForeignKey("parts.id"), primary_key=True),
    Column("alternative_part_id", Integer, ForeignKey("parts.id"), primary_key=True),
    Column("priority", Integer, default=1, comment="替代优先级 1首选 2备选"),
)


class PartCategory(Base):
    """物料分类: 一级→二级→三级→四级"""
    __tablename__ = "part_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    level = Column(Integer, nullable=False, comment="分类层级 1-4")
    code = Column(String(20), nullable=False, comment="分类编码")
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("part_categories.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    children = relationship("PartCategory", backref="parent", remote_side=[id])


class Part(Base):
    """物料主数据 — 全局唯一"""
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    part_no = Column(String(50), unique=True, index=True, nullable=False, comment="物料编码（全局唯一）")
    name = Column(String(200), nullable=False, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    category_id = Column(Integer, ForeignKey("part_categories.id"), nullable=True)
    unit = Column(String(20), default="个")
    lifecycle = Column(String(20), default="developing", comment="developing/trial/production/discontinued/obsolete")
    supplier_info = Column(String(500), nullable=True, comment="供应商信息（主供应商）")
    risk_level = Column(String(10), default="low", comment="low/medium/high")
    # CDF相关
    is_cdf_item = Column(Boolean, default=False, comment="是否CDF物料")
    cdf_type = Column(String(50), nullable=True, comment="CDF类型: 安全件/EMC件/能效件")
    cdf_cert_no = Column(String(100), nullable=True, comment="CDF证书编号")
    cdf_expiry_date = Column(Date, nullable=True, comment="CDF证书有效期")
    # 市场认证标记 (JSON string of market codes)
    market_cert_marks = Column(String(300), nullable=True, comment="市场认证标记JSON: {\"CE\":true,\"UL\":false,\"CCC\":true}")
    # MQ验证
    mq_required = Column(Boolean, default=False, comment="是否需要MQ验证")
    mq_status = Column(String(20), nullable=True, comment="MQ验证状态: pending/pass/fail")
    # MRC属性
    mrc_level = Column(String(10), nullable=True, comment="MRC风险等级: A/B/C")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("PartCategory")
    # 替代料关系
    alternatives = relationship(
        "Part", secondary="part_alternatives",
        primaryjoin="Part.id == part_alternatives.c.part_id",
        secondaryjoin="Part.id == part_alternatives.c.alternative_part_id",
        backref="alternative_of",
    )
    # AVL供应商
    avl_entries = relationship("PartAVL", back_populates="part", cascade="all, delete-orphan")


class PartAVL(Base):
    """物料批准供应商清单 (Approved Vendor List)"""
    __tablename__ = "part_avls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    vendor_code = Column(String(50), nullable=False, comment="供应商编码")
    vendor_name = Column(String(200), nullable=False, comment="供应商名称")
    is_primary = Column(Boolean, default=False, comment="是否主供应商")
    status = Column(String(20), default="approved", comment="approved/suspended/disqualified")
    approved_date = Column(Date, nullable=True)
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    part = relationship("Part", back_populates="avl_entries")


class BOM(Base):
    """BOM结构: 6层体系 — 研发唯一MBOM"""
    __tablename__ = "boms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bom_no = Column(String(50), unique=True, index=True, nullable=False, comment="BOM编号")
    product_code = Column(String(50), nullable=False, comment="关联产品编码")
    version = Column(String(20), default="V1.0", comment="BOM版本")
    bom_type = Column(String(20), default="MBOM", comment="MBOM（唯一）")
    description = Column(Text, nullable=True)
    factory_code = Column(String(50), nullable=True, comment="工厂代码（制造变体级别）")
    status = Column(String(20), default="draft", comment="draft/released/obsolete")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BOMItem(Base):
    """BOM条目 — 6层体系"""
    __tablename__ = "bom_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bom_id = Column(Integer, ForeignKey("boms.id"), nullable=False)
    parent_item_id = Column(Integer, ForeignKey("bom_items.id"), nullable=True, comment="父级BOM条目")
    part_no = Column(String(50), nullable=False, comment="物料编码（TODO: 清理孤儿子记录后改为 ForeignKey(\"parts.part_no\")）")
    part_name = Column(String(200), nullable=True)
    item_type = Column(String(20), default="Part", comment="Assembly/Component/Part/Consumable")
    level = Column(Integer, nullable=False, comment="层级: 1整机 2内外机 3总成 4组件 5子件 6零部件")
    quantity = Column(Float, default=1.0, comment="数量")
    unit = Column(String(20), default="个", comment="单位")
    unit_price = Column(Float, default=0.0, comment="单价（元）")
    amount = Column(Float, default=1.0, comment="用量/系数，用于成本计算: cost=unit_price×amount×quantity")
    position_no = Column(String(50), nullable=True, comment="位置号（ECN定位+ERP同步）")
    remark = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bom = relationship("BOM")
    children = relationship("BOMItem", backref="parent", remote_side=[id])
