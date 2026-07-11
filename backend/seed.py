"""种子数据 — 创建默认角色和初始用户（PostgreSQL）"""
import asyncio
from sqlalchemy import select
from app.database import async_engine, AsyncSessionLocal, Base
from app.models.user import User, Role
from app.core.security import hash_password


async def seed():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Roles
        roles_data = [
            {"name": "admin"},
            {"name": "engineer"},
            {"name": "viewer"},
        ]
        for rd in roles_data:
            existing = (await db.execute(select(Role).where(Role.name == rd["name"]))).scalar_one_or_none()
            if not existing:
                db.add(Role(name=rd["name"]))

        await db.flush()

        # Demo user (for development)
        existing = (await db.execute(select(User).where(User.username == "demo"))).scalar_one_or_none()
        if not existing:
            viewer_role = (await db.execute(select(Role).where(Role.name == "viewer"))).scalar_one()
            admin_role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
            user = User(
                username="demo",
                email="demo@jide.com",
                password_hash=hash_password("demo123"),
                is_active=True,
            )
            user.roles = [viewer_role, admin_role]
            db.add(user)

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
        print("✅ Seed: roles(admin/engineer/viewer), users(demo/demo123, admin/admin123)")


if __name__ == "__main__":
    asyncio.run(seed())
