"""API v1 路由聚合"""

from fastapi import APIRouter
from app.api.v1 import auth, users, platforms, series_models, materials_bom, projects, ecr, eco

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(platforms.router)
v1_router.include_router(series_models.series_router)
v1_router.include_router(series_models.model_router)
v1_router.include_router(materials_bom.materials_router)
v1_router.include_router(materials_bom.bom_router)
v1_router.include_router(materials_bom.features_router)
v1_router.include_router(projects.project_router)
v1_router.include_router(projects.wbs_router)
v1_router.include_router(projects.task_router)
v1_router.include_router(ecr.router)
v1_router.include_router(eco.router)
