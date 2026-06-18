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
