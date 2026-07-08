"""TestExecution（实验执行记录）模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import TestExecutionStatus


class TestExecution(Base):
    """实验执行记录 — 挂接到 TestRequest，支持重测/复测"""
    __tablename__ = "test_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True,  # id)
    test_request_id = Column(Integer, ForeignKey("test_requests.id"), nullable=False, comment="关联实验申请")

    # 执行信息
    lab = Column(String(100), nullable=True, comment="实验室名称")
    equipment = Column(String(100), nullable=True, comment="设备编号/名称")
    operator = Column(String(50), nullable=True, comment="操作人员")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    duration_minutes = Column(Integer, nullable=True, comment="耗时(分钟)，自动计算")

    # 状态
    status = Column(String(20), nullable=False, default=TestExecutionStatus.RUNNING.value,  # status
                    comment=f"状态: {[e.value for e in TestExecutionStatus]}")
    notes = Column(Text, nullable=True, comment="执行备注")

    # 多租户
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, comment="所属组织ID")

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(,  # created_at)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(,  # updated_at)

    # 关系
    test_request = relationship("TestRequest", back_populates="executions")
    results = relationship("TestResult", back_populates="execution",
                           foreign_keys="TestResult.execution_id")
