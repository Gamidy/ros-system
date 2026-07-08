"""采购订单模型: 订单 + 订单项 + 供应商 + 供应商评估"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Date, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Supplier(Base):
    """供应商主数据"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    code = Column(String(50), unique=True, index=True, nullable=False, comment="供应商编码")
    name = Column(String(200), nullable=False, comment="供应商名称")
    category = Column(String(100), nullable=True, comment="供应品类（电子/结构/包装/辅料等）")
    contact = Column(String(100), nullable=True, comment="联系人")
    phone = Column(String(50), nullable=True, comment="联系电话")
    email = Column(String(100), nullable=True, comment="邮箱")
    address = Column(String(500), nullable=True, comment="地址")
    tax_id = Column(String(50), nullable=True, comment="税号")
    bank_info = Column(String(200), nullable=True, comment="银行信息")
    status = Column(String(20), default="active", comment="potential/qualified/active/suspended/blacklisted")
    overall_score = Column(Float, default=0, comment="综合评分(0-100)")
    business_license = Column(String(500), nullable=True, comment="营业执照附件路径")
    cert_iso = Column(Integer, default=0, comment="ISO认证(0未/1有)")
    cert_rohs = Column(Integer, default=0, comment="RoHS认证")
    cert_ul = Column(Integer, default=0, comment="UL认证")
    remark = Column(Text, nullable=True,  # remark)
    is_deleted = Column(Integer, default=0, comment="软删除标记")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)


class PurchaseOrder(Base):
    """采购订单"""
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="订单号（自动生成PO-YYYYMMDD-XXXX）")
    supplier_name = Column(String(200), nullable=False, comment="供应商名称")
    supplier_code = Column(String(50), nullable=False, comment="供应商编码")
    total_amount = Column(Float, default=0.0, comment="订单总金额")
    status = Column(String(20), default="draft", comment="draft/pending_approval/approved/ordered/received/cancelled")
    requester = Column(String(100), nullable=False, comment="申请人")
    remark = Column(Text, nullable=True,  # remark)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    items = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    """采购订单明细"""
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False,  # order_id)
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True, comment="物料名称")
    spec = Column(String(500), nullable=True, comment="规格型号")
    unit = Column(String(20), default="个",  # unit)
    quantity = Column(Float, default=1.0, comment="采购数量")
    unit_price = Column(Float, default=0.0, comment="单价")
    total_price = Column(Float, default=0.0, comment="小计金额")
    delivery_date = Column(Date, nullable=True, comment="要求交货日期")
    received_qty = Column(Float, default=0.0, comment="已收货数量")
    remark = Column(String(500), nullable=True,  # remark)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)

    order = relationship("PurchaseOrder", back_populates="items")


class OutsourceRequest(Base):
    """外协送样申请 — 研发→外协工厂 送样流程"""
    __tablename__ = "outsource_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
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
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)


# ══════════════════════════════════════════════════
# 供应商评估
# ══════════════════════════════════════════════════

EVAL_DIM_QUALITY = "quality"
EVAL_DIM_DELIVERY = "delivery"
EVAL_DIM_COST = "cost"
EVAL_DIM_SERVICE = "service"
EVAL_DIM_TECH = "technology"

DIMENSION_LABELS = {
    EVAL_DIM_QUALITY: "品质", EVAL_DIM_DELIVERY: "交期",
    EVAL_DIM_COST: "成本", EVAL_DIM_SERVICE: "服务",
    EVAL_DIM_TECH: "技术能力",
}
VALID_DIMENSIONS = [EVAL_DIM_QUALITY, EVAL_DIM_DELIVERY, EVAL_DIM_COST, EVAL_DIM_SERVICE, EVAL_DIM_TECH]


class SupplierEvaluation(Base):
    """供应商评估记录"""
    __tablename__ = "supplier_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, comment="供应商ID")
    dimension = Column(String(20), nullable=False, comment="评估维度")
    score = Column(Float, nullable=False, comment="评分(0-100)")
    weight = Column(Float, default=1.0, comment="该维度权重")
    comment = Column(String(500), nullable=True, comment="评估意见")
    evaluator = Column(String(50), nullable=True, comment="评估人")
    evaluated_at = Column(DateTime, server_default=func.now(), comment="评估时间")


# ══════════════════════════════════════════════════
# 采购收货管理
# ══════════════════════════════════════════════════


class GoodsReceipt(Base):
    """采购收货单 — 对应一次到货"""
    __tablename__ = "goods_receipts"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    receipt_no = Column(String(30), unique=True, index=True, nullable=False, comment="收货单号 GR-YYYYMMDD-XXXX")
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, comment="关联采购订单ID")
    supplier_name = Column(String(200), nullable=False, comment="供应商名称(快照)")
    supplier_code = Column(String(50), nullable=False, comment="供应商编码(快照)")

    received_date = Column(DateTime, server_default=func.now(), comment="收货日期")
    warehouse = Column(String(100), nullable=True, comment="仓库")
    location = Column(String(100), nullable=True, comment="库位")
    status = Column(String(20), default="pending_inspection", comment="pending/pending_inspection/inspected/partially_rejected/rejected")
    total_qty = Column(Float, default=0, comment="总收货数量")
    total_amount = Column(Float, default=0, comment="收货金额")
    remark = Column(Text, nullable=True, comment="备注")

    created_by = Column(String(50), nullable=True,  # created_by)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    items = relationship("GoodsReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class GoodsReceiptItem(Base):
    """收货明细 — 对应PO中的一行"""
    __tablename__ = "goods_receipt_items"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    receipt_id = Column(Integer, ForeignKey("goods_receipts.id"), nullable=False,  # receipt_id)
    order_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=True, comment="关联PO明细ID")
    part_no = Column(String(50), nullable=False, comment="物料编码(快照)")
    part_name = Column(String(200), nullable=True, comment="物料名称(快照)")
    spec = Column(String(500), nullable=True, comment="规格(快照)")
    unit = Column(String(20), default="个",  # unit)
    ordered_qty = Column(Float, default=0, comment="PO数量")
    received_qty = Column(Float, default=0, comment="本次收货数量")
    accepted_qty = Column(Float, default=0, comment="合格数量")
    rejected_qty = Column(Float, default=0, comment="不合格数量")
    unit_price = Column(Float, default=0, comment="单价(快照)")
    total_price = Column(Float, default=0, comment="小计金额")
    remark = Column(String(500), nullable=True,  # remark)

    receipt = relationship("GoodsReceipt", back_populates="items")


class InspectionStatus(str):
    PASS = "pass"            # 合格
    CONCESSION = "concession"  # 让步接收
    REJECT = "reject"        # 退货


class IncomingInspection(Base):
    """来料检验记录"""
    __tablename__ = "incoming_inspections"

    id = Column(Integer, primary_key=True, autoincrement=True,  # id)
    receipt_id = Column(Integer, ForeignKey("goods_receipts.id"), nullable=False, comment="关联收货单ID")
    receipt_item_id = Column(Integer, ForeignKey("goods_receipt_items.id"), nullable=True, comment="关联收货明细ID")
    part_no = Column(String(50), nullable=False, comment="物料编码")
    sample_qty = Column(Integer, default=0, comment="抽检数量")
    defect_qty = Column(Integer, default=0, comment="不合格数")
    defect_desc = Column(Text, nullable=True, comment="缺陷描述")
    result = Column(String(20), default=InspectionStatus.PASS, comment="判定结果")
    inspector = Column(String(50), nullable=True, comment="检验员")
    remark = Column(Text, nullable=True, comment="备注")
    inspected_at = Column(DateTime, server_default=func.now(), comment="检验日期")
