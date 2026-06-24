"""S1 部署验证脚本"""
from sqlalchemy import inspect, text
from app.core.database import engine, SessionLocal
from app.main import app


def verify_tables():
    print("=" * 50)
    print("S1 部署验证报告")
    print("=" * 50)

    # 1. 路由
    print(f"\n1. 路由数: {len(app.routes)}")

    # 2. 新表
    insp = inspect(engine)
    tables = insp.get_table_names()
    targets = [
        "verification_requirements", "test_executions",
        "gate_rules", "gate_rule_items", "gate_eval_records",
        "target_markets", "required_tests", "required_certifications",
        "required_standards"
    ]
    ok = 0
    for t in targets:
        exists = t in tables
        if exists:
            ok += 1
        print(f"  {'OK' if exists else 'MISS'} {t}")
    print(f"  新表: {ok}/9")

    # 3. 增强字段
    enhanced_cols = {
        "test_requests": ["vr_id", "prototype_id", "test_category"],
        "test_results": ["prototype_id", "execution_id", "result_val", "judgment_data"],
        "prototypes": ["version", "project_id", "parent_prototype_id", "bom_version", "firmware_version"],
    }
    for table, fields in enhanced_cols.items():
        if table in tables:
            cols = [c["name"] for c in insp.get_columns(table)]
            for f in fields:
                exists = f in cols
                print(f"  {'OK' if exists else 'MISS'} {table}.{f}")

    # 4. 目标市场种子数据
    db = SessionLocal()
    try:
        from app.models.target_market import TargetMarket
        markets = db.query(TargetMarket).all()
        print(f"\n4. 目标市场: {len(markets)}")
        for m in markets:
            print(f"  {m.market_code} - {m.market_name}: "
                  f"{len(m.required_tests)}tests {len(m.required_certifications)}certs {len(m.required_standards)}stds")
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("验证完成")
    print("=" * 50)


if __name__ == "__main__":
    verify_tables()
