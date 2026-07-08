"""市场参数配置 — 定义每个市场有哪些专有参数

产品经理可自行配置，配置后前端动态渲染表单。
值存储在 competitor_models.extra_fields JSON列。"""
from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from app.core.database import Base


class MarketParamConfig(Base):
    """市场参数配置"""
    __tablename__ = "market_param_configs"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    market_code = Column(String(20), ForeignKey("markets.code", ondelete="CASCADE"), nullable=False, index=True,  # market_code
                         comment="市场代码")
    param_key = Column(String(50), nullable=False, comment="参数键名，存于 extra_fields JSON")
    param_label = Column(String(100), nullable=False, comment="显示标签，如 AEER/CSPF/SCOP")
    param_unit = Column(String(50), nullable=True, comment="单位，如 W/W/kW/dB")
    data_type = Column(String(20), nullable=False, server_default="float",  # data_type
                       comment="数据类型: float/int/string/select")
    sort_order = Column(Integer, nullable=False, server_default="0", comment="排序")
    is_required = Column(String(5), nullable=False, server_default="false",  # is_required)
    options = Column(JSON, nullable=True, comment="当 data_type=select 时的选项列表")
    is_active = Column(String(5), nullable=False, server_default="true",  # is_active)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    __table_args__ = (
        UniqueConstraint("market_code", "param_key", name="uq_market_param"),
    )
