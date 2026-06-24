"""测试/实验管理 + MRC/MQ + 认证/样机 + 品质整改模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date, Float, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


# ==== 测试/实验 ====

_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["submitted", "cancelled"],
    "submitted": ["testing", "draft"],
    "testing": ["done", "cancelled"],
    "done": [],
    "cancelled": [],
}


class TestRequest(Base):
    """测试申请"""
    __tablename__ = "test_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_no = Column(String(50), unique=True, index=True, nullable=False, comment="申请单号")
    title = Column(String(200), nullable=False)
    project_code = Column(String(50), nullable=True, comment="关联项目")
    product_code = Column(String(50), nullable=True, comment="关联产品")
    test_type = Column(String(50), nullable=False, comment="测试类型: 性能/安全/EMC/可靠性/噪音/振动")
    test_standard = Column(String(200), nullable=True, comment="测试标准")
    trigger_mode = Column(String(20), default="engineer", comment="engineer/project/auto")
    requester = Column(String(50), nullable=False)
    requirement = Column(Text, nullable=True, comment="测试要求")
    sample_info = Column(Text, nullable=True, comment="样机信息")
    priority = Column(String(10), default="medium", comment="low/medium/high/urgent")
    status = Column(String(20), default="draft", comment="draft/submitted/testing/done/cancelled")
    target_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    ng_count = Column(Integer, default=0, comment="不合格项数")
    result_summary = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    results = relationship("TestResult", back_populates="test_request", cascade="all, delete-orphan")


class TestResult(Base):
    """测试结果明细"""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    test_request_id = Column(Integer, ForeignKey("test_requests.id"), nullable=False)
    item_name = Column(String(200), nullable=False, comment="测试项目")
    standard_value = Column(String(100), nullable=True, comment="标准值")
    actual_value = Column(String(100), nullable=True, comment="实测值")
    is_pass = Column(Boolean, nullable=True, comment="是否合格")
    remark = Column(Text, nullable=True)
    tested_by = Column(String(50), nullable=True)
    tested_at = Column(DateTime, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")

    test_request = relationship("TestRequest", back_populates="results")


# ==== MQ (新物料验证) ====

class MQVerification(Base):
    """新物料验证记录"""
    __tablename__ = "mq_verifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    part_no = Column(String(50), nullable=False, comment="物料编码")
    part_name = Column(String(200), nullable=True)
    project_code = Column(String(50), nullable=True)
    product_code = Column(String(50), nullable=True)
    mq_type = Column(String(20), default="full", comment="full全项/sampling抽样")
    status = Column(String(20), default="pending", comment="pending/testing/pass/fail")
    test_items = Column(Text, nullable=True, comment="测试项目JSON")
    pass_items = Column(Integer, default=0)
    fail_items = Column(Integer, default=0)
    result_report = Column(Text, nullable=True)
    verified_by = Column(String(50), nullable=True)
    verified_at = Column(Date, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())


# ==== 认证管理 ====

class Certification(Base):
    """认证申请"""
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cert_no = Column(String(50), unique=True, index=True, nullable=False, comment="认证编号")
    product_code = Column(String(50), nullable=False, comment="关联产品")
    cert_type = Column(String(50), nullable=False, comment="认证类型: CE/UL/CCC/ERP/MEPS/GEMS")
    target_market = Column(String(20), nullable=False, comment="目标市场")
    cert_body = Column(String(100), nullable=True, comment="认证机构")
    status = Column(String(20), default="planning", comment="planning/preparing/testing/submitted/approved/rejected/expiring")
    planned_date = Column(Date, nullable=True)
    submit_date = Column(Date, nullable=True)
    approved_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    result = Column(String(20), nullable=True, comment="pass/fail")
    cdf_doc_ref = Column(String(100), nullable=True, comment="CDF文档引用")
    remark = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ==== 样机管理 ====

class Prototype(Base):
    """样机"""
    __tablename__ = "prototypes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    proto_no = Column(String(50), unique=True, index=True, nullable=False, comment="样机编号")
    product_code = Column(String(50), nullable=False, comment="关联产品")
    project_code = Column(String(50), nullable=True, comment="关联项目")
    proto_type = Column(String(20), nullable=False, comment="样机类型: hand_sample/模具首样/工程样机/小批样机/认证样机")
    stage = Column(String(20), nullable=True, comment="阶段: M4/M5/M6/M7/M8")
    status = Column(String(20), default="producing", comment="producing/testing/done/scrapped")
    quantity = Column(Integer, default=1)
    material_status = Column(String(20), nullable=True, comment="物料齐套状态")
    produced_date = Column(Date, nullable=True)
    test_date = Column(Date, nullable=True)
    result = Column(String(20), nullable=True, comment="pass/fail")
    remark = Column(Text, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ==== 品质整改 ====

class QualityIssue(Base):
    """品质整改单"""
    __tablename__ = "quality_issues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_no = Column(String(50), unique=True, index=True, nullable=False, comment="问题编号")
    title = Column(String(200), nullable=False)
    product_code = Column(String(50), nullable=True, comment="关联产品")
    project_code = Column(String(50), nullable=True, comment="关联整改项目")
    issue_source = Column(String(50), nullable=True, comment="来源: 客诉/产线/测试/审核")
    severity = Column(String(10), default="B", comment="严重度: A/B/C")
    category = Column(String(50), nullable=True, comment="类别: 结构/系统/电控/工艺/物料")
    status = Column(String(20), default="open", comment="open/analyzing/fixing/verified/closed")
    root_cause = Column(Text, nullable=True, comment="根本原因")
    solution = Column(Text, nullable=True, comment="解决方案")
    assigned_to = Column(String(50), nullable=True)
    target_date = Column(Date, nullable=True)
    closed_date = Column(Date, nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ==== ECR/ECN 变更管理 ====

class ECR(Base):
    """工程变更请求"""
    __tablename__ = "ecrs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecr_no = Column(String(50), unique=True, index=True, nullable=False, comment="ECR编号")
    title = Column(String(200), nullable=False)
    product_code = Column(String(50), nullable=True)
    change_type = Column(String(50), nullable=False, comment="变更类型: 结构/系统/电控/物料/BOM")
    trigger = Column(String(50), nullable=True, comment="触发: 品质/降本/认证/工艺/供应链")
    status = Column(String(20), default="draft", comment="draft/submitted/approved/rejected/implemented")
    description = Column(Text, nullable=True)
    impact_analysis = Column(Text, nullable=True, comment="影响分析: 性能/认证/项目/成本")
    submitted_by = Column(String(50), nullable=True)
    approved_by = Column(String(50), nullable=True)
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ECN(Base):
    """工程变更通知"""
    __tablename__ = "ecns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ecn_no = Column(String(50), unique=True, index=True, nullable=False, comment="ECN编号")
    ecr_id = Column(Integer, ForeignKey("ecrs.id"), nullable=True)
    title = Column(String(200), nullable=False)
    product_code = Column(String(50), nullable=True)
    change_scope = Column(Text, nullable=True, comment="变更范围")
    bom_changes = Column(Text, nullable=True, comment="BOM变更明细JSON")
    cdf_impact = Column(Boolean, default=False, comment="是否影响CDF")
    certification_impact = Column(Boolean, default=False, comment="是否影响认证")
    status = Column(String(20), default="draft", comment="draft/released/implemented")
    effective_date = Column(Date, nullable=True, comment="生效日期")
    # ---- 多租户 ----
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    ecr = relationship("ECR")
