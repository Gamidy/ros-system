"""PM 配置表 — 安规标准 & 性能默认参数"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class CertStandard(Base):
    """安规标准配置表"""
    __tablename__ = "cert_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(50), nullable=False, index=True, comment="目标市场")
    standard = Column(String(200), nullable=False, comment="标准名称")
    key_requirement = Column(String(200), nullable=True, comment="关键要求")
    verification_method = Column(String(200), nullable=True, comment="验证方式")
    cert_cycle = Column(String(50), nullable=True, comment="认证周期")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, server_default=func.now())


class MarketCertification(Base):
    """市场认证要求表（国家级认证要求：安规/能效/EMC/环保）"""
    __tablename__ = "market_certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_code = Column(String(20), nullable=False, index=True, comment="关联市场代码")
    cert_type = Column(String(30), nullable=False, comment="认证类型: safety/energy/emc/environmental")
    cert_standard = Column(String(200), nullable=False, comment="认证标准/要求")
    description = Column(String(500), nullable=True, comment="详细说明")
    is_required = Column(String(5), default="true", comment="是否强制")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class MarketCompressor(Base):
    """市场关键元器件限制信息表（国家级元器件品牌/结构限制配置）"""
    __tablename__ = "market_compressors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_code = Column(String(20), nullable=False, index=True, comment="关联市场代码")
    manufacturer = Column(String(100), nullable=False, comment="元器件类别（压缩机/风机/换热器/电控板等）")
    model = Column(String(100), nullable=True, comment="限制类型（不接受品牌/不接受结构/特殊要求）")
    capacity_range = Column(String(50), nullable=True, comment="受限对象（品牌名/结构描述）")
    notes = Column(String(500), nullable=True, comment="详细说明）")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class PerfDefault(Base):
    """性能默认参数配置表"""
    __tablename__ = "perf_defaults"

    id = Column(Integer, primary_key=True, autoincrement=True)
    capacity_range = Column(String(20), nullable=False, index=True, comment="冷量段, 如07K/09K/12K/18K/24K")
    market = Column(String(50), nullable=False, index=True, comment="目标市场")
    param_name = Column(String(100), nullable=False, comment="参数名称")
    target_value = Column(String(100), nullable=True, comment="目标值")
    aux_competitor = Column(String(100), nullable=True, comment="AUX竞品值")
    tcl_competitor = Column(String(100), nullable=True, comment="TCL竞品值")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
