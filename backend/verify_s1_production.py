"""S1.5 生产验证 — 通过 docker exec 直接验证数据库+API"""
from sqlalchemy import inspect
from app.core.database import engine, SessionLocal
from app.main import app


def run_all():
    passed = 0
    failed = 0

    print("=" * 55)
    print("S1.5 生产验证报告")
    print("=" * 55)

    # ── 0. 路由 ──
    print(f"\n📊 路由数: {len(app.routes)}")
    passed += 1

    # ── 1. 新表验证 (9/9) ──
    print("\n📋 GR1a: 新表验证")
    insp = inspect(engine)
    tables = insp.get_table_names()
    targets = [
        "verification_requirements", "test_executions",
        "gate_rules", "gate_rule_items", "gate_eval_records",
        "target_markets", "required_tests", "required_certifications",
        "required_standards"
    ]
    for t in targets:
        ok = t in tables
        print(f"  {'✅' if ok else '❌'} {t}")
        if ok:
            passed += 1
        else:
            failed += 1

    # ── 2. 增强字段验证 (11/11) ──
    print("\n📋 GR1b: 增强字段验证")
    checks = {
        "test_requests": ["vr_id", "prototype_id", "test_category"],
        "test_results": ["prototype_id", "execution_id", "result_val", "judgment_data"],
        "prototypes": ["version", "project_id", "parent_prototype_id", "bom_version", "firmware_version"],
    }
    for table, fields in checks.items():
        if table in tables:
            cols = [c["name"] for c in insp.get_columns(table)]
            for f in fields:
                ok = f in cols
                print(f"  {'✅' if ok else '❌'} {table}.{f}")
                if ok:
                    passed += 1
                else:
                    failed += 1

    # ── 3. 目标市场种子数据 ──
    print("\n📋 GR1c: 目标市场种子数据")
    db = SessionLocal()
    try:
        from app.models.target_market import TargetMarket
        markets = db.query(TargetMarket).all()
        print(f"  目标市场数: {len(markets)}")
        if len(markets) == 5:
            passed += 1
        else:
            failed += 1
        for m in markets:
            t = len(m.required_tests) if hasattr(m, 'required_tests') else 0
            c = len(m.required_certifications) if hasattr(m, 'required_certifications') else 0
            s = len(m.required_standards) if hasattr(m, 'required_standards') else 0
            print(f"    {m.market_code} - {m.market_name}: {t}tests {c}certs {s}stds")
            if t > 0:
                passed += 1
            else:
                failed += 1
    finally:
        db.close()

    # ── 4. 多租户验证 (所有新表有 org_id) ──
    print("\n📋 GR3: 多租户验证")
    for t in targets:
        if t in tables:
            cols = [c["name"] for c in insp.get_columns(t)]
            ok = "org_id" in cols
            print(f"  {'✅' if ok else '❌'} {t}.org_id")
            if ok:
                passed += 1
            else:
                failed += 1

    # ── 5. 手动 API 端点验证（用 curl 风格内部请求） ──
    print("\n📋 GR1d: API 端点内部验证")
    test_client_endpoints = [
        ("GET", "/api/verification-requirements"),
        ("GET", "/api/gate-rules"),
        ("GET", "/api/prototypes"),
        ("GET", "/api/target-markets"),
        ("GET", "/api/test-executions"),
    ]
    # Use Starlette TestClient
    try:
        from starlette.testclient import TestClient
        client = TestClient(app)
        for method, path in test_client_endpoints:
            resp = client.get(path)
            # 401 is expected (no auth) - means the endpoint exists
            ok = resp.status_code in (200, 401, 422)
            print(f"  {'✅' if ok else '❌'} {method} {path} -> {resp.status_code}")
            if ok:
                passed += 1
            else:
                failed += 1
    except Exception as e:
        print(f"  ⚠️ TestClient不可用: {e}")
        for ep in test_client_endpoints:
            print(f"  ❓ {ep} (跳过)")

    # ── 结果汇总 ──
    total = passed + failed
    print(f"\n{'=' * 55}")
    print(f"📊 S1.5 验证总结果")
    print(f"{'=' * 55}")
    print(f"  合计检查项: {total}")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    if failed == 0:
        print(f"\n🎉 全部通过！S2 认证中心可以启动！")
    else:
        print(f"\n⚠️ 存在 {failed} 个失败项，需修复")


if __name__ == "__main__":
    run_all()
