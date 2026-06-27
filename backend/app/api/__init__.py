"""API路由包"""
from app.api import (
    auth, products, bom, projects,
    tests, alerts, dashboard,
    pm_workspace, admin_config, pm_config,
    pm_proposal_api,
    state_machine_api, event_timeline, risk_dashboard,
    webhooks,
    # Phase 5 — 基础功能扩展
    approvals, certifications, purchases,
    knowledge,
    # Phase 6 S1 — 实验中心
    verification_requirements, gate_rules,
    target_markets, test_executions, prototypes,
    # Phase 6 S2 — 认证中心
    s2_cert_requirements, s2_cert_projects, s2_cert_samples,
    s2_cert_executions, s2_cert_results, s2_certificates,
    s2_gate_rules, s2_change_impact,
    # Phase 6 — 产品管理扩展
    competitor, competitor_bench,
    pm_accessory, pm_roadmap, pm_statistics,
    product_plan, product_plan_subs,
    # Phase 6 S3 — ECR/ECO 工程变更控制
    ecr, eco,
    safety,
    manufacturability,
    outsource,
    # 审计日志查询
    audit_logs,
    # 管理功能
    admin_cost_configs, admin_role_mappings,
    admin_role_templates, admin_tenant,
    rd_panel,
    # D1 BI分析看板
    bi_analytics,
    cost_alert_api,
    cost_accounting,
    # D3 消息通知增强
    user_notification_api,
    # D4 AI辅助策划
    ai_plan_api,
    # 密码重置
    password_reset_api,
    # Event Log 事件类型管理
    event_logs,
    # P2 产品需求录入
    product_requirements,
    # P4 复盘
    product_plan_review,
    improvement_task_api,
    # D4-3 复盘看板
    review_dashboard,
)

__all__ = [
    "auth", "products", "bom", "projects",
    "tests", "alerts", "dashboard",
    "pm_workspace", "admin_config", "pm_config",
    "pm_proposal_api",
    "state_machine_api", "event_timeline", "risk_dashboard",
    "webhooks",
    "approvals", "certifications", "purchases",
    "knowledge",
    "verification_requirements", "gate_rules",
    "target_markets", "test_executions", "prototypes",
    "s2_cert_requirements", "s2_cert_projects", "s2_cert_samples",
    "s2_cert_executions", "s2_cert_results", "s2_certificates",
    "s2_gate_rules", "s2_change_impact",
    "competitor", "competitor_bench",
    "pm_accessory", "pm_roadmap", "pm_statistics",
    "product_plan", "product_plan_subs",
    "ecr", "eco",
    "safety",
    "manufacturability",
    "outsource",
    "audit_logs",
    "admin_cost_configs", "admin_role_mappings",
    "admin_role_templates", "admin_tenant",
    "rd_panel",
    "cost_accounting",
    "bi_analytics",
    "cost_alert_api",
    "user_notification_api",
    "ai_plan_api",
    "password_reset_api",
    "event_logs",
    "product_requirements",
    "product_plan_review",
    "improvement_task_api",
    "review_dashboard",
]
