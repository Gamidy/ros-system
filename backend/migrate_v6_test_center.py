"""
Phase 6 S1 — 数据库迁移脚本
向现有数据库追加新表和字段，不破坏现有数据结构。
"""
from sqlalchemy import text, inspect
from app.core.database import engine, SessionLocal


def _has_column(table: str, column: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _has_table(table: str) -> bool:
    """检查表是否存在"""
    inspector = inspect(engine)
    return table in inspector.get_table_names()


def run_migration():
    """执行 Phase 6 S1 数据库迁移"""
    print("=" * 50)
    print("Phase 6 S1 — 数据库迁移")
    print("=" * 50)

    with engine.connect() as conn:
        trans = conn.begin()

        try:
            # ════════════════════════════════════
            # 1. 新建表
            # ════════════════════════════════════

            if not _has_table("verification_requirements"):
                conn.execute(text("""
                    CREATE TABLE verification_requirements (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        vr_code VARCHAR(50) NOT NULL UNIQUE,
                        title VARCHAR(200) NOT NULL,
                        category VARCHAR(30) NOT NULL,
                        target_value VARCHAR(100),
                        unit VARCHAR(30),
                        source_type VARCHAR(30) NOT NULL,
                        source_id VARCHAR(100),
                        source_detail TEXT,
                        project_id INTEGER,
                        product_plan_id INTEGER,
                        gate_code VARCHAR(10),
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        remark TEXT,
                        org_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_vr_category (category),
                        INDEX idx_vr_source (source_type),
                        INDEX idx_vr_project (project_id),
                        INDEX idx_vr_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 verification_requirements 表")
            else:
                print("⏭️  verification_requirements 表已存在")

            if not _has_table("test_executions"):
                conn.execute(text("""
                    CREATE TABLE test_executions (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        test_request_id INTEGER NOT NULL,
                        lab VARCHAR(100),
                        equipment VARCHAR(100),
                        operator VARCHAR(50),
                        start_time DATETIME,
                        end_time DATETIME,
                        duration_minutes INTEGER,
                        status VARCHAR(20) NOT NULL DEFAULT 'running',
                        notes TEXT,
                        org_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_te_request (test_request_id),
                        INDEX idx_te_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 test_executions 表")
            else:
                print("⏭️  test_executions 表已存在")

            if not _has_table("gate_rules"):
                conn.execute(text("""
                    CREATE TABLE gate_rules (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        product_line VARCHAR(50),
                        customer VARCHAR(50),
                        gate_code VARCHAR(10) NOT NULL,
                        all_pass BOOLEAN DEFAULT TRUE,
                        auto_block BOOLEAN DEFAULT FALSE,
                        priority INTEGER DEFAULT 100,
                        status VARCHAR(20) NOT NULL DEFAULT 'active',
                        created_by VARCHAR(50),
                        org_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_gr_gate (gate_code),
                        INDEX idx_gr_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 gate_rules 表")
            else:
                print("⏭️  gate_rules 表已存在")

            if not _has_table("gate_rule_items"):
                conn.execute(text("""
                    CREATE TABLE gate_rule_items (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        rule_id INTEGER NOT NULL,
                        required_vr_category VARCHAR(30) NOT NULL,
                        required_prototype_type VARCHAR(10),
                        is_required BOOLEAN DEFAULT TRUE,
                        sort_order INTEGER DEFAULT 0,
                        INDEX idx_gri_rule (rule_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 gate_rule_items 表")
            else:
                print("⏭️  gate_rule_items 表已存在")

            if not _has_table("gate_eval_records"):
                conn.execute(text("""
                    CREATE TABLE gate_eval_records (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        rule_id INTEGER,
                        project_id INTEGER NOT NULL,
                        gate_code VARCHAR(10) NOT NULL,
                        result VARCHAR(20) NOT NULL,
                        detail TEXT,
                        evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        evaluated_by VARCHAR(50),
                        org_id INTEGER,
                        INDEX idx_ger_project (project_id),
                        INDEX idx_ger_gate (gate_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 gate_eval_records 表")
            else:
                print("⏭️  gate_eval_records 表已存在")

            if not _has_table("target_markets"):
                conn.execute(text("""
                    CREATE TABLE target_markets (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        market_code VARCHAR(10) NOT NULL UNIQUE,
                        market_name VARCHAR(100) NOT NULL,
                        description TEXT,
                        org_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 target_markets 表")
            else:
                print("⏭️  target_markets 表已存在")

            if not _has_table("required_tests"):
                conn.execute(text("""
                    CREATE TABLE required_tests (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        target_market_id INTEGER NOT NULL,
                        test_category VARCHAR(30) NOT NULL,
                        standard VARCHAR(100),
                        is_required BOOLEAN DEFAULT TRUE,
                        sort_order INTEGER DEFAULT 0,
                        INDEX idx_rt_market (target_market_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 required_tests 表")
            else:
                print("⏭️  required_tests 表已存在")

            if not _has_table("required_certifications"):
                conn.execute(text("""
                    CREATE TABLE required_certifications (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        target_market_id INTEGER NOT NULL,
                        cert_type VARCHAR(20) NOT NULL,
                        cert_body VARCHAR(100),
                        is_mandatory BOOLEAN DEFAULT TRUE,
                        sort_order INTEGER DEFAULT 0,
                        INDEX idx_rc_market (target_market_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 required_certifications 表")
            else:
                print("⏭️  required_certifications 表已存在")

            if not _has_table("required_standards"):
                conn.execute(text("""
                    CREATE TABLE required_standards (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        target_market_id INTEGER NOT NULL,
                        standard_code VARCHAR(50) NOT NULL,
                        standard_name VARCHAR(200),
                        is_core BOOLEAN DEFAULT TRUE,
                        sort_order INTEGER DEFAULT 0,
                        INDEX idx_rs_market (target_market_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))
                print("✅ 创建 required_standards 表")
            else:
                print("⏭️  required_standards 表已存在")

            # ════════════════════════════════════
            # 2. 增强已有表（新增列）
            # ════════════════════════════════════

            # TestRequest
            if not _has_column("test_requests", "vr_id"):
                conn.execute(text("ALTER TABLE test_requests ADD COLUMN vr_id INTEGER NULL"))
                print("✅ test_requests 新增 vr_id")
            if not _has_column("test_requests", "prototype_id"):
                conn.execute(text("ALTER TABLE test_requests ADD COLUMN prototype_id INTEGER NULL"))
                print("✅ test_requests 新增 prototype_id")
            if not _has_column("test_requests", "test_category"):
                conn.execute(text("ALTER TABLE test_requests ADD COLUMN test_category VARCHAR(30) NULL"))
                print("✅ test_requests 新增 test_category")

            # TestResult
            if not _has_column("test_results", "prototype_id"):
                conn.execute(text("ALTER TABLE test_results ADD COLUMN prototype_id INTEGER NULL"))
                print("✅ test_results 新增 prototype_id")
            if not _has_column("test_results", "execution_id"):
                conn.execute(text("ALTER TABLE test_results ADD COLUMN execution_id INTEGER NULL"))
                print("✅ test_results 新增 execution_id")
            if not _has_column("test_results", "result_val"):
                conn.execute(text("ALTER TABLE test_results ADD COLUMN result_val VARCHAR(10) NULL"))
                print("✅ test_results 新增 result_val")
            if not _has_column("test_results", "judgment_data"):
                conn.execute(text("ALTER TABLE test_results ADD COLUMN judgment_data TEXT NULL"))
                print("✅ test_results 新增 judgment_data")

            # Prototype
            if not _has_column("prototypes", "version"):
                conn.execute(text("ALTER TABLE prototypes ADD COLUMN version VARCHAR(10) NULL"))
                print("✅ prototypes 新增 version")
            if not _has_column("prototypes", "project_id"):
                conn.execute(text("ALTER TABLE prototypes ADD COLUMN project_id INTEGER NULL"))
                print("✅ prototypes 新增 project_id")
            if not _has_column("prototypes", "parent_prototype_id"):
                conn.execute(text("ALTER TABLE prototypes ADD COLUMN parent_prototype_id INTEGER NULL"))
                print("✅ prototypes 新增 parent_prototype_id")
            if not _has_column("prototypes", "bom_version"):
                conn.execute(text("ALTER TABLE prototypes ADD COLUMN bom_version VARCHAR(50) NULL"))
                print("✅ prototypes 新增 bom_version")
            if not _has_column("prototypes", "firmware_version"):
                conn.execute(text("ALTER TABLE prototypes ADD COLUMN firmware_version VARCHAR(50) NULL"))
                print("✅ prototypes 新增 firmware_version")

            trans.commit()
            print("=" * 50)
            print("✅ Phase 6 S1 数据库迁移完成!")
            print("=" * 50)

        except Exception as e:
            trans.rollback()
            print(f"❌ 迁移失败: {e}")
            raise


if __name__ == "__main__":
    run_migration()
