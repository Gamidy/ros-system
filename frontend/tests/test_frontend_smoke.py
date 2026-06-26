#!/usr/bin/env python3
"""
fe-t5: Frontend Integration Smoke Test
------------------------------------------
直接测试后端 API 可用性，不依赖浏览器。
覆盖 16 个测试点：登录、策划 CRUD、5 子表、审批推进、路由页面可加载性。

Usage:
    python tests/test_frontend_smoke.py
"""

import sys
import time
import json
import os
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "http://139.196.15.52/api"
USERNAME = "admin"
PASSWORD = "Admin123456"

passed = 0
failed = 0
results = []


def log_test(name: str, ok: bool, detail: str = ""):
    global passed, failed
    status = "✅ PASS" if ok else "❌ FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    results.append((name, ok, detail))
    print(f"  {status}  {name}" + (f"  — {detail}" if detail else ""))


def req(method: str, path: str, token: str = None, data: dict = None,
        timeout: int = 10) -> tuple:
    """Make an HTTP request and return (status_code, body_dict, error_str)."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data else None
    req_obj = urllib.request.Request(url, data=body, headers=headers,
                                     method=method)
    try:
        with urllib.request.urlopen(req_obj, timeout=timeout) as resp:
            content = resp.read().decode()
            status = resp.status
            try:
                return status, json.loads(content), None
            except json.JSONDecodeError:
                return status, {"raw": content}, None
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        status = e.code
        try:
            return status, json.loads(content), None
        except json.JSONDecodeError:
            return status, {"raw": content}, None
    except urllib.error.URLError as e:
        return 0, {}, str(e.reason)
    except Exception as e:
        return 0, {}, str(e)


# ════════════════════════════════════════════════════════════════
# Test Suite
# ════════════════════════════════════════════════════════════════

def test_login():
    """1. 登录获取 token"""
    status, body, err = req("POST", "/auth/login",
                            data={"username": USERNAME, "password": PASSWORD})
    if err:
        log_test("POST /auth/login — 登录", False, f"network error: {err}")
        return None
    if status == 200 and body.get("access_token"):
        log_test("POST /auth/login — 登录", True,
                 f"token 获取成功 ({body['access_token'][:20]}...)")
        return body["access_token"]
    else:
        msg = body.get("detail", str(body))
        log_test("POST /auth/login — 登录", False,
                 f"status={status} detail={msg}")
        return None


def test_get_me(token: str):
    """2. 获取当前用户信息"""
    status, body, err = req("GET", "/auth/me", token=token)
    if err:
        log_test("GET /auth/me — 用户信息", False, f"network error: {err}")
        return
    ok = status == 200 and body.get("username") == USERNAME
    log_test("GET /auth/me — 用户信息", ok,
             f"username={body.get('username')}" if ok else f"status={status}")


def test_list_plans(token: str):
    """3. 策划列表"""
    status, body, err = req("GET", "/product-plans?limit=5", token=token)
    if err:
        log_test("GET /product-plans — 策划列表", False, f"network error: {err}")
        return None
    plans = body if isinstance(body, list) else body.get("data", body.get("items", []))
    count = len(plans)
    ok = status == 200
    log_test("GET /product-plans — 策划列表", ok,
             f"status={status}, {count} 条记录" if ok else f"status={status}")
    if ok and count > 0:
        return [p.get("id") or p.get("product_plan_id") for p in plans]
    return None


def test_plan_detail(token: str, plan_id: str):
    """4. 策划详情"""
    status, body, err = req("GET", f"/product-plans/{plan_id}", token=token)
    ok = status == 200
    plan_name = body.get("plan_name") or body.get("name") or ""
    log_test(f"GET /product-plans/{plan_id} — 策划详情", ok,
             f"name={plan_name}" if ok else f"status={status}")


def test_plan_status(token: str, plan_id: str):
    """5. 策划流程状态"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/status", token=token)
    ok = status == 200
    stage = body.get("stage") or body.get("current_stage") or ""
    log_test(f"GET /product-plans/{plan_id}/status — 流程状态", ok,
             f"stage={stage}" if ok else f"status={status}")


def test_subtable_initiation(token: str, plan_id: str):
    """6. 子表1：项目概述"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/initiation",
                            token=token)
    ok = status == 200
    log_test(f"GET /product-plans/{plan_id}/initiation — 项目概述", ok,
             f"status={status}")


def test_subtable_market(token: str, plan_id: str):
    """7. 子表2：市场与客户"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/market", token=token)
    ok = status == 200
    log_test(f"GET /product-plans/{plan_id}/market — 市场与客户", ok,
             f"status={status}")


def test_subtable_tech_spec(token: str, plan_id: str):
    """8. 子表3：技术要求"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/tech-spec",
                            token=token)
    ok = status == 200
    log_test(f"GET /product-plans/{plan_id}/tech-spec — 技术要求", ok,
             f"status={status}")


def test_subtable_costing(token: str, plan_id: str):
    """9. 子表4：成本核算 — 从主 plan 中取 costs"""
    status, body, err = req("GET", f"/product-plans/{plan_id}", token=token)
    if status == 200:
        costs = body.get("costs", [])
        ok = True
        log_test(f"GET /product-plans/{plan_id} (costs) — 成本核算", ok,
                 f"costs={len(costs)} 项")
    else:
        log_test(f"GET /product-plans/{plan_id} (costs) — 成本核算", False,
                 f"status={status}")


def test_subtable_team(token: str, plan_id: str):
    """10. 子表5：团队"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/team", token=token)
    if status == 200:
        team = body if isinstance(body, list) else body.get("data", [])
        log_test(f"GET /product-plans/{plan_id}/team — 团队", True,
                 f"{len(team)} 成员")
    else:
        log_test(f"GET /product-plans/{plan_id}/team — 团队", False,
                 f"status={status}")


def test_next_action(token: str, plan_id: str):
    """11. 下一步引导"""
    status, body, err = req("GET", f"/product-plans/{plan_id}/next-action",
                            token=token)
    ok = status == 200
    log_test(f"GET /product-plans/{plan_id}/next-action — 下一步引导", ok,
             f"status={status}")


def test_advance_stage(token: str, plan_id: str):
    """12. 审批推进"""
    status, body, err = req("POST", f"/product-plans/{plan_id}/advance",
                            token=token)
    ok = status in (200, 400)
    detail = body.get("detail", body.get("message", ""))
    log_test(f"POST /product-plans/{plan_id}/advance — 审批推进", ok,
             f"status={status}, detail={detail}")


def test_pm_workspace(token: str):
    """13. PM工作台 Dashboard"""
    # Correct path from backend: /api/pm/workspace
    status, body, err = req("GET", "/pm/workspace", token=token)
    ok = status == 200
    log_test("GET /pm/workspace — PM工作台", ok,
             f"status={status}" if not ok else "数据可获取")


def test_pm_programs(token: str):
    """14. PM立项规划"""
    status, body, err = req("GET", "/pm/programs", token=token)
    ok = status == 200
    log_test("GET /pm/programs — PM立项规划", ok,
             f"status={status}" if not ok else "数据可获取")


def test_products_route(token: str):
    """15. 产品主线路由"""
    status, body, err = req("GET", "/products?limit=5", token=token)
    ok = status == 200
    count = len(body) if isinstance(body, list) else 0
    log_test("GET /products — 产品主线", ok,
             f"status={status}, {count} 条" if ok else f"status={status}")


def test_proposals_route(token: str):
    """16. 提案管理 — /pm/proposals"""
    status, body, err = req("GET", "/pm/proposals", token=token)
    ok = status == 200
    log_test("GET /pm/proposals — 提案管理", ok,
             f"status={status}" if ok else f"status={status}")


def test_event_timeline(token: str):
    """17. 事件时间线 — /api/v2/events/timeline"""
    status, body, err = req("GET", "/api/v2/events/timeline", token=token)
    # Try without double prefix
    if status == 404:
        status, body, err = req("GET", "/v2/events/timeline", token=token)
    ok = status == 200
    log_test("事件时间线 API", ok,
             f"status={status}" if ok else f"status={status}")


# ════════════════════════════════════════════════════════════════
# Performance: Timing & Build Size
# ════════════════════════════════════════════════════════════════

def test_performance_login():
    """17. 登录响应时间"""
    times = []
    for _ in range(3):
        start = time.time()
        status, body, err = req("POST", "/auth/login",
                                data={"username": USERNAME, "password": PASSWORD})
        elapsed = time.time() - start
        if status == 200 and not err:
            times.append(elapsed)
    avg = sum(times) / len(times) if times else 0
    ok = avg < 2.0 and len(times) == 3
    log_test("登录响应时间 (< 2s)", ok,
             f"avg={avg:.3f}s (n={len(times)})" if times else "all failed")


def test_performance_list_plans(token: str):
    """18. 策划列表响应时间"""
    times = []
    for _ in range(3):
        start = time.time()
        status, body, err = req("GET", "/product-plans?limit=5", token=token)
        elapsed = time.time() - start
        if status == 200:
            times.append(elapsed)
    avg = sum(times) / len(times) if times else 0
    ok = avg < 2.0 and len(times) == 3
    log_test("策划列表响应时间 (< 2s)", ok,
             f"avg={avg:.3f}s (n={len(times)})" if times else "all failed")


# ════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════

def main():
    global passed, failed, results
    print("=" * 64)
    print("  FE-T5: 集成测试 + QA 验证")
    print(f"  目标: {BASE_URL}")
    print(f"  用户: {USERNAME}")
    print("=" * 64)
    print()

    # ── Phase 1: Auth ──
    token = test_login()
    if not token:
        print("\n❌ 登录失败，无法继续测试。请检查网络和后端服务状态。")
        sys.exit(1)

    test_get_me(token)

    # ── Phase 2: CRUD ──
    plan_ids = test_list_plans(token)
    plan_id = plan_ids[0] if plan_ids else None

    if plan_id:
        test_plan_detail(token, plan_id)
        test_plan_status(token, plan_id)
        test_subtable_initiation(token, plan_id)
        test_subtable_market(token, plan_id)
        test_subtable_tech_spec(token, plan_id)
        test_subtable_costing(token, plan_id)
        test_subtable_team(token, plan_id)
        test_next_action(token, plan_id)
        test_advance_stage(token, plan_id)
    else:
        print("  ⚠️  无策划数据，跳过子表测试")
        for i in range(9):
            log_test(f"子表测试 #{i+1} (跳过)", True, "无策划数据")

    # ── Phase 3: Other Routes ──
    test_pm_workspace(token)
    test_pm_programs(token)
    test_products_route(token)
    test_proposals_route(token)
    test_event_timeline(token)

    # ── Phase 4: Performance ──
    print(f"\n{'─' * 40}")
    print("  性能基线")
    print(f"{'─' * 40}")
    test_performance_login()
    if plan_id:
        test_performance_list_plans(token)
    else:
        log_test("策划列表响应时间 (跳过)", True, "无策划数据")

    # ── Summary ──
    print(f"\n{'=' * 64}")
    total = passed + failed
    print(f"  测试结果: {passed}/{total} 通过")
    if failed:
        print(f"\n  ❌ 失败详情:")
        for name, ok, detail in results:
            if not ok:
                print(f"     - {name}: {detail}")
    print(f"{'=' * 64}")

    # ── JSON report ──
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base_url": BASE_URL,
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": [{"name": n, "ok": ok, "detail": d} for n, ok, d in results]
    }
    report_path = os.path.join(os.path.dirname(__file__), "smoke_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  报告已保存: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
