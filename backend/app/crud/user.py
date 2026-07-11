"""用户CRUD + 认证"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User, Role
from app.core.security import hash_password, verify_password


class CRUDUser(CRUDBase[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def authenticate(self, db: AsyncSession, *, username: str, password: str) -> Optional[User]:
        user = await self.get_by_username(db, username=username)
        if not user or not verify_password(password, user.password_hash):
            return None
        return user

    async def create(self, db: AsyncSession, *, obj_in: dict) -> User:
        if "password" in obj_in:
            obj_in["password_hash"] = hash_password(obj_in.pop("password"))
        # 默认为viewer角色
        result = await db.execute(select(Role).where(Role.name == "viewer"))
        viewer_role = result.scalar_one_or_none()
        db_obj = User(**obj_in)
        if viewer_role:
            db_obj.roles = [viewer_role]
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


user_crud = CRUDUser()
