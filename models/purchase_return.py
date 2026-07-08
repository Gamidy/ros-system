"""采购退货管理模型: 退货单 + 退货明细"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PurchaseReturn(Base):
    """采购退货单 — 质检不合格/其他原因退货给供应商"""
    __tablename__ = "purchase_returns"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    return_no = Column(String(30), unique=True, index=True, nullable=False, comment="退货单号 PR-YYYYMMDD-XXXX")
    # 来源单据
    source_type = Column(String(20), nullable=False, comment="来源类型: inspection(质检)/receipt(直接退货)/manual(手工)")
    source_id = Column(Integer, nullable=True, comment="来源单据ID(质检单/收货单ID)")
    source_no = Column(String(50), nullable=True, comment="来源单据编号")
    # 供应商信息
    supplier_name = Column(String(200), nullable=False, comment="供应商名称(快照)")
    supplier_code = Column(String(50), nullable=False, comment="供应商编码(快照)")
    # 订单关联
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True, comment="关联采购订单ID")
    order_no = Column(String(50), nullable=True, comment="关联订单号(快照)")
    # 退货信息
    return_date = Column(DateTime, server_default=func.now(), comment="退货日期")
    total_qty = Column(Float, default=0, comment="退货总数量")
    total_amount = Column(Float, default=0, comment="退货总金额")
    return_reason = Column(String(50), nullable=False, comment="退货原因: quality/overdue/damaged/other")
    reason_detail = Column(Text, nullable=True, comment="退货原因详细说明")
    responsibility = Column(String(20), default="supplier", comment="责任方: supplier/logistics/internal/other")
    # 物流信息
    logistics_company = Column(String(100), nullable=True, comment="物流公司")
    logistics_no = Column(String(100), nullable=True, comment="物流单号")
    # 退款信息
    refund_amount = Column(Float, default=0, comment="退款金额")
    refund_date = Column(DateTime, nullable=True, comment="退款日期")
    refund_method = Column(String(50), nullable=True, comment="退款方式: bank_transfer/deduction/cash/other")
    # 状态
    status = Column(String(20), default="draft", comment="draft/pending_approval/approved/returned/refunded/cancelled")
    # 经办信息
    created_by = Column(String(100), nullable=False, comment="创建人")
    approved_by = Column(String(100), nullable=True, comment="审批人")
    approved_at = Column(DateTime, nullable=True, comment="审批时间")
    remark = Column(Text, nullable=True, comment="备注")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True,  # org_id)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    items = relationship("PurchaseReturnItem", back_populates="return_order", cascade="all, delete-orphan")


class PurchaseReturnItem(Base):
    """退货明细"""
    __tablename__ = "purchase_return_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    return_id = Column(Integer, ForeignKey("purchase_returns.id"), nullable=False,  # return_id)
    # 物料信息
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)
    # 数量金额
    return_qty = Column(Float, nullable=False, comment="退货数量")
    unit_price = Column(Float, default=0.0, comment="单价")
    total_price = Column(Float, default=0.0, comment="小计金额")
    # 关联质检明细
    inspection_item_id = Column(Integer, nullable=True, comment="关联质检明细ID")
    # 缺陷信息
    defect_type = Column(String(50), nullable=True, comment="缺陷类型: appearance/dimension/function/material/packaging/other")
    defect_desc = Column(Text, nullable=True, comment="缺陷说明")
    # 处理方式
    disposal = Column(String(20), default="return", comment="处理方式: return/scrap/rework")
    remark = Column(String(500), nullable=True,  # remark)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    return_order = relationship("PurchaseReturn", back_populates="items")
