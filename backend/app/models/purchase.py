"""采购订单模型: 订单 + 订单项 + 供应商"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Date, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Supplier(Base):
    """供应商主数据"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="供应商编码")
    name = Column(String(200), nullable=False, comment="供应商名称")
    contact = Column(String(100), nullable=True, comment="联系人")
    phone = Column(String(50), nullable=True, comment="联系电话")
    email = Column(String(100), nullable=True, comment="邮箱")
    address = Column(String(500), nullable=True, comment="地址")
    tax_id = Column(String(50), nullable=True, comment="税号")
    bank_info = Column(String(200), nullable=True, comment="银行信息")
    status = Column(String(20), default="active", comment="active/inactive")
    remark = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PurchaseOrder(Base):
    """采购订单"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="订单号（自动生成PO-YYYYMMDD-XXXX）")
    supplier_name = Column(String(200), nullable=False, comment="供应商名称")
    supplier_code = Column(String(50), nullable=False, comment="供应商编码")
    total_amount = Column(Float, default=0.0, comment="订单总金额")
    status = Column(String(20), default="draft", comment="draft/pending_approval/approved/ordered/received/cancelled")
    requester = Column(String(100), nullable=False, comment="申请人")
    remark = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    """采购订单明细"""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个")
    quantity = Column(Float, default=1.0, comment="采购数量")
    unit_price = Column(Float, default=0.0, comment="单价")
    total_price = Column(Float, default=0.0, comment="小计金额")
    delivery_date = Column(Date, nullable=True, comment="要求交货日期")
    received_qty = Column(Float, default=0.0, comment="已收货数量")
    remark = Column(String(500), nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())

    order = relationship("PurchaseOrder", back_populates="items")


class OutsourceRequest(Base):
    """外协送样申请 — 研发→外协工厂 送样流程"""
    __tablename__ = "outsource_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_no = Column(String(30), unique=True, index=True, nullable=False, comment="请求编号 OS-YYYYMMDD-XXXX")
    product_code = Column(String(50), nullable=False, comment="产品编码")
    part_name = Column(String(100), nullable=False, comment="物料名称")
    quantity = Column(Integer, nullable=False, comment="数量")
    target_factory = Column(String(100), nullable=False, comment="目标外协工厂")
    required_date = Column(Date, nullable=True, comment="要求交期")
    description = Column(Text, nullable=True, comment="送样说明")
    status = Column(String(20), default="pending", comment="pending/approved/rejected/completed")
    created_by = Column(String(50), nullable=False, comment="申请人")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
