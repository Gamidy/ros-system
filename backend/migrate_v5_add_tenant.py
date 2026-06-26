"""
ROS Phase 5 — 多租户数据迁移脚本
===============================
创建 organizations / organization_members 表
为所有业务表添加 org_id 列

执行: python3 migrate_v5_add_tenant.py
兼容: MariaDB / SQLite
"""

import logging
import sys
import os

# 确保能找到 app 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
from sqlalchemy import text, inspect

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── 需要添加 org_id 的表 ──
TABLES_NEED_ORG_ID = [
    "users",
    "product_plans",
    "programs", "projects", "project_gates", "milestones", "tasks", "risks",
    "parts", "part_avls", "boms", "bom_items",
    "alert_rules", "alerts", "notifications",
    "test_requests", "test_results", "mq_verifications",
    "certifications", "prototypes", "quality_issues", "ecrs", "ecns",
    "approval_chains", "approval_requests",
    "suppliers", "purchase_orders", "purchase_order_items", "outsource_requests",
    "annual_plans",
    "platforms", "products", "versions",
    "manufacturing_variants",
]


def table_exists(conn, table_name: str) -> bool:
    """检查表是否存在"""
    try:
        # SQLite 兼容
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        ), {"name": table_name}).fetchone()
        if result:
            return True
        # MariaDB 兼容
        result = conn.execute(text(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :name"
        ), {"name": table_name}).fetchone()
        return result is not None
    except Exception as e:
        logger.warning(f"table_exists 检查失败({table_name}): {e}")
        try:
            # 通用: 直接 SELECT 1
            conn.execute(text(f"SELECT 1 FROM {table_name} LIMIT 0"))
            return True
        except Exception as e:
            logger.warning(f"table_exists 备选检查失败({table_name}): {e}")
            return False


def column_exists(conn, table_name: str, column: str) -> bool:
    """检查列是否存在"""
    try:
        inspector = inspect(engine)
        cols = [c["name"] for c in inspector.get_columns(table_name)]
        return column in cols
    except Exception as e:
        logger.warning(f"column_exists 检查失败({table_name}.{column}): {e}")
        return False


def migrate():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("ROS Phase 5: 多租户数据迁移")
    logger.info("=" * 60)

    conn = engine.connect()
    trans = conn.begin()
    try:
        # 1. 创建 organizations 表
        if not table_exists(conn, "organizations"):
            logger.info("创建 organizations 表...")
            conn.execute(text("""
                CREATE TABLE organizations (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(200) NOT NULL COMMENT '组织名称',
                    code VARCHAR(50) NOT NULL UNIQUE COMMENT '组织代码(唯一)',
                    contact_email VARCHAR(200) COMMENT '联系邮箱',
                    phone VARCHAR(50) COMMENT '联系电话',
                    address TEXT COMMENT '地址',
                    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
                    max_users INT DEFAULT 100 COMMENT '最大用户数',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组织表'
            """))
            logger.info("✓ organizations 表已创建")
        else:
            logger.info("✓ organizations 表已存在")

        # 2. 创建 organization_members 表
        if not table_exists(conn, "organization_members"):
            logger.info("创建 organization_members 表...")
            conn.execute(text("""
                CREATE TABLE organization_members (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    org_id INTEGER NOT NULL COMMENT '组织ID',
                    user_id INTEGER NOT NULL COMMENT '用户ID',
                    role_in_org VARCHAR(20) DEFAULT 'member' COMMENT '组织内角色(admin/member)',
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_org_user (org_id, user_id),
                    FOREIGN KEY (org_id) REFERENCES organizations(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组织成员表'
            """))
            logger.info("✓ organization_members 表已创建")
        else:
            logger.info("✓ organization_members 表已存在")

        # 3. 为业务表添加 org_id 列
        logger.info("\n添加 org_id 列到业务表...")
        for table in TABLES_NEED_ORG_ID:
            if not table_exists(conn, table):
                logger.warning(f"  跳过 {table} (表不存在)")
                continue
            if column_exists(conn, table, "org_id"):
                logger.info(f"  ✓ {table}.org_id 已存在")
                continue
            try:
                conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN org_id INTEGER DEFAULT NULL"
                ))
                logger.info(f"  ✓ {table}.org_id 已添加")
            except Exception as e:
                logger.warning(f"  ⚠ {table}.org_id 添加失败: {e}")

        # 4. 添加索引
        for table in TABLES_NEED_ORG_ID:
            if not table_exists(conn, table):
                continue
            if not column_exists(conn, table, "org_id"):
                continue
            try:
                conn.execute(text(
                    f"CREATE INDEX ix_{table}_org_id ON {table}(org_id)"
                ))
                logger.info(f"  ✓ ix_{table}_org_id 索引已创建")
            except Exception as e:
                logger.warning(f"创建索引 ix_{table}_org_id 失败（可能已存在）: {e}")
                # 索引可能已存在
                pass

        # 5. 创建默认组织
        result = conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
        if result == 0:
            logger.info("\n创建默认组织...")
            conn.execute(text("""
                INSERT INTO organizations (name, code, contact_email, is_active, max_users)
                VALUES ('默认组织', 'default', 'admin@ros.com', 1, 1000)
            """))
            logger.info("✓ 默认组织已创建")

        trans.commit()
        logger.info("\n" + "=" * 60)
        logger.info("迁移完成 ✅")
        logger.info("=" * 60)

    except Exception as e:
        trans.rollback()
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
