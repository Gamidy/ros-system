# -*- coding: utf-8 -*-
"""
ROS 系统 — 首次启动初始化脚本
================================

功能:
  1. 检查数据库中是否已存在组织 (Organization)
  2. 如果不存在，创建默认组织 "默认组织"
  3. 检查是否存在管理员用户 (admin)
  4. 如果不存在，创建默认管理员账号

运行时机:
  docker-entrypoint.sh 中自动调用，仅在首次部署时生效（幂等设计）。

依赖环境变量 (可从 .env.prod 或容器环境读取):
  ADMIN_USERNAME: 管理员用户名 (默认: admin)
  ADMIN_PASSWORD: 管理员密码 (默认: Admin123!)
  ADMIN_EMAIL:    管理员邮箱 (默认: admin@ros-system.local)
  ORG_NAME:       默认组织名称 (默认: 默认组织)
  ORG_CODE:       默认组织编码 (默认: default)
"""

import os
import sys
import logging

# 将 backend 根目录加入 Python 路径，确保可导入 app 包
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 关闭 SQLAlchemy 的 SQL 回显日志
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("init_admin")

# ── 导入项目模块 ──
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.security import get_password_hash


def get_or_create_org(db) -> Organization:
    """
    获取或创建默认组织
    - 如果已存在编码为 ORG_CODE 的组织，直接返回
    - 否则创建新的组织记录
    返回: Organization 实例
    """
    org_code = os.getenv("ORG_CODE", "default")
    org_name = os.getenv("ORG_NAME", "默认组织")

    org = db.query(Organization).filter(Organization.code == org_code).first()
    if org:
        logger.info(f"组织已存在: {org.name} (code={org.code})")
        return org

    logger.info(f"创建默认组织: {org_name} (code={org_code})")
    org = Organization(
        name=org_name,
        code=org_code,
        contact_email=os.getenv("ADMIN_EMAIL", "admin@ros-system.local"),
        is_active=True,
        max_users=1000,
    )
    db.add(org)
    db.flush()  # 获取 org.id
    logger.info(f"组织创建成功: id={org.id}")
    return org


def get_or_create_admin(db, org_id: int) -> User:
    """
    获取或创建默认管理员账号
    - 如果已存在用户名为 ADMIN_USERNAME 的用户，直接返回
    - 否则创建管理员并关联到指定组织
    返回: User 实例
    """
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "Admin123!")
    email = os.getenv("ADMIN_EMAIL", "admin@ros-system.local")

    admin = db.query(User).filter(User.username == username).first()
    if admin:
        logger.info(f"管理员账号已存在: {admin.username}")
        return admin

    logger.info("创建默认管理员账号...")
    admin = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name="系统管理员",
        role="admin",
        is_active=True,
        org_id=org_id,
        is_org_admin=True,
        application_status="approved",
    )
    db.add(admin)
    db.flush()  # 获取 admin.id

    # 创建组织成员关联记录
    member = OrganizationMember(
        org_id=org_id,
        user_id=admin.id,
        role_in_org="admin",
    )
    db.add(member)

    logger.info(f"管理员账号创建成功: {username} / 密码已加密存储")
    return admin


def main():
    """主入口：确保表结构存在 → 创建组织 → 创建管理员"""
    logger.info("=" * 50)
    logger.info("ROS 首次启动初始化脚本")
    logger.info("=" * 50)

    # 1. 确保表结构已创建
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表结构检查/创建完成")
    except Exception as e:
        logger.warning(f"表结构创建遇到警告（可能已存在）: {e}")

    # 2. 初始化数据
    db = SessionLocal()
    try:
        # 创建默认组织
        org = get_or_create_org(db)
        # 创建管理员
        admin = get_or_create_admin(db, org.id)
        # 提交事务
        db.commit()
        logger.info("初始化全部完成 ✓")
    except Exception as e:
        db.rollback()
        logger.error(f"初始化失败，已回滚: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
