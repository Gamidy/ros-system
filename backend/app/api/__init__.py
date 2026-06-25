"""API路由包"""
from app.api import (
    auth, products, bom, projects,
    tests, alerts, dashboard,
    pm_workspace, admin_config, pm_config,
    proposal_approval, pm_proposal_api,
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
    product_plan, product_plan_subs, proposal_utils,
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
)

__all__ = [
    "auth", "products", "bom", "projects",
    "tests", "alerts", "dashboard",
    "pm_workspace", "admin_config", "pm_config",
    "proposal_approval", "pm_proposal_api",
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
    "product_plan", "product_plan_subs", "proposal_utils",
    "ecr", "eco",
    "safety",
    "manufacturability",
    "outsource",
    "audit_logs",
    "admin_cost_configs", "admin_role_mappings",
    "admin_role_templates", "admin_tenant",
    "rd_panel",
    "cost_accounting",
]
