"""物料+BOM+特征 CRUD"""

from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.bom import Material, SuperBOMNode
from app.models.feature import FeatureFamily, FeatureOption


class CRUDMaterial(CRUDBase[Material]):
    def __init__(self):
        super().__init__(Material)


class CRUDBOM(CRUDBase[SuperBOMNode]):
    def __init__(self):
        super().__init__(SuperBOMNode)

    async def get_tree(self, db: AsyncSession, *, model_id: int) -> List[SuperBOMNode]:
        """获取型号的BOM树(根节点+所有子孙)"""
        result = await db.execute(
            select(SuperBOMNode)
            .where(SuperBOMNode.model_id == model_id)
            .options(selectinload(SuperBOMNode.material), selectinload(SuperBOMNode.children))
            .order_by(SuperBOMNode.sequence)
        )
        return list(result.scalars().all())


class CRUDFeatureFamily(CRUDBase[FeatureFamily]):
    def __init__(self):
        super().__init__(FeatureFamily)

    async def get_with_options(self, db: AsyncSession, *, feature_id: int) -> FeatureFamily | None:
        result = await db.execute(
            select(FeatureFamily)
            .where(FeatureFamily.id == feature_id)
            .options(selectinload(FeatureFamily.options))
        )
        return result.scalar_one_or_none()

    async def create_option(self, db: AsyncSession, *, family_id: int, obj_in: dict) -> FeatureOption:
        obj_in["family_id"] = family_id
        opt = FeatureOption(**obj_in)
        db.add(opt)
        await db.flush()
        await db.refresh(opt)
        return opt


material_crud = CRUDMaterial()
bom_crud = CRUDBOM()
feature_family_crud = CRUDFeatureFamily()
