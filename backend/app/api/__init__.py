"""API路由包"""
from app.api import auth, products, bom, projects, tests, alerts, dashboard, pm_workspace, admin_config

__all__ = ["auth", "products", "bom", "projects", "tests", "alerts", "dashboard", "pm_workspace", "admin_config"]
