"""SOP标准作业指导书管理"""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Boolean
from app.core.database import Base


class SOP(Base):
    """标准作业指导书"""
    __tablename__ = "sops"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    code = Column(String(50), nullable=False, comment="SOP编号")
    name = Column(String(200), nullable=False, comment="SOP名称")
    product_model = Column(String(100), nullable=True, comment="适用产品型号")
    process_name = Column(String(100), nullable=True, comment="工序名称")
    step_no = Column(Integer, default=1, comment="步骤序号")
    description = Column(Text, nullable=True, comment="操作描述")
    standard_time = Column(Integer, nullable=True, comment="标准工时(秒)")
    tools = Column(String(200), nullable=True, comment="工装工具")
    quality_standard = Column(Text, nullable=True, comment="质量标准")
    image_url = Column(String(200), nullable=True, comment="示意图URL")
    version = Column(String(10), default="V1.0", comment="版本号")
    status = Column(String(20), default="draft", comment="draft/published/obsolete")
    author = Column(String(50), nullable=True, comment="编制人")
    reviewer = Column(String(50), nullable=True, comment="审批人")
    review_date = Column(Date, nullable=True,  # review_date)
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)


class ProcessRoute(Base):
    """工艺路线"""
    __tablename__ = "process_routes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    code = Column(String(50), nullable=False, comment="工艺路线编号")
    name = Column(String(200), nullable=False, comment="路线名称")
    product_model = Column(String(100), nullable=True, comment="适用产品型号")
    version = Column(String(10), default="V1.0", comment="版本号")
    # 工序列表 JSON: [{"seq":1,"name":"...","std_time":120,"workstation":"...","sop_code":"..."}]
    steps = Column(Text, nullable=True, comment="工序列表JSON")
    total_time = Column(Integer, default=0, comment="总工时(秒)")
    status = Column(String(20), default="draft", comment="draft/published/obsolete")
    author = Column(String(50), nullable=True, comment="编制人")
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)
