"""种子数据 — 创建默认角色和初始用户"""
import asyncio
from sqlalchemy import select
from app.database import async_engine, async_sessionmaker, AsyncSession, Base
from app.models.user import User, Role
from app.core.security import hash_password


async def seed():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        # Roles
        roles_data = [
            {"name": "admin", "description": "系统管理员"},
            {"name": "engineer", "description": "工程师"},
            {"name": "viewer", "description": "只读用户"},
        ]
        for rd in roles_data:
            existing = (await db.execute(select(Role).where(Role.name == rd["name"]))).scalar_one_or_none()
            if not existing:
                db.add(Role(name=rd["name"]))

        # Admin user
        existing = (await db.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
        if not existing:
            admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
            user = User(
                username="admin",
                email="admin@jide.com",
                password_hash=hash_password("admin123"),
                is_active=True,
            )
            user.roles = [admin_role]
            db.add(user)

        await db.commit()
        print("✅ Seed data created: roles(admin/engineer/viewer), user(admin/admin123)")


if __name__ == "__main__":
    from sqlalchemy import select
    asyncio.run(seed())
