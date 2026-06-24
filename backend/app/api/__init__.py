"""API路由包"""
from app.api import auth, products, bom, projects, tests, alerts, dashboard, pm_workspace, admin_config, pm_config, proposal_approval, pm_proposal_api, state_machine_api

__all__ = ["auth", "products", "bom", "projects", "tests", "alerts", "dashboard", "pm_workspace", "admin_config", "pm_config", "proposal_approval", "pm_proposal_api", "state_machine_api"]
