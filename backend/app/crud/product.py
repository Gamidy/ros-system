"""产品层级 CRUD"""

from app.crud.base import CRUDBase
from app.models.product import Platform, Series, Model


class CRUDPlatform(CRUDBase[Platform]):
    def __init__(self):
        super().__init__(Platform)


class CRUDSeries(CRUDBase[Series]):
    def __init__(self):
        super().__init__(Series)


class CRUDModel(CRUDBase[Model]):
    def __init__(self):
        super().__init__(Model)


platform_crud = CRUDPlatform()
series_crud = CRUDSeries()
model_crud = CRUDModel()
