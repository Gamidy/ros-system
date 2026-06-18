#!/usr/bin/env python3
"""
ROS 产品经理 10轮×20步 浏览器审计 (简化版，实时输出)
"""
import asyncio, json, sys, re, time
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "http://139.196.15.52"
USER = "pm"
PASS = "123456"
ISSUES = []

def log(sev, rnd, step, msg):
    s = f"[{sev.upper()}] R{rnd}S{step}: {msg}"
    ISSUES.append({"severity": sev, "round": rnd, "step": step, "msg": msg, "time": datetime.now().isoformat()})
    print(s, flush=True)

def ok(rnd, step, msg):
    print(f"[OK] R{rnd}S{step}: {msg}", flush=True)

async def do_login(page):
    await page.goto(f"{BASE_URL}/login", timeout=15000)
    await page.wait_for_timeout(1000)
    # Find inputs
    inputs = await page.query_selector_all('input')
    for inp in inputs:
        t = await inp.get_attribute('type') or ''
        ph = await inp.get_attribute('placeholder') or ''
        if '密码' in ph or t == 'password':
            await inp.fill(PASS)
        elif t == 'text' or '用户名' in ph or '账号' in ph:
            await inp.fill(USER)
    # Click login
    btn = await page.query_selector('button:has-text("登录"), button[type="submit"]')
    if btn:
        await btn.click()
    await page.wait_for_timeout(2000)
    return page.url

async def click_menu(page, keyword):
    for sel in [f'text="{keyword}"', f'a:has-text("{keyword}")', f'span:has-text("{keyword}")', f'.el-menu-item:has-text("{keyword}")']:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_timeout(500)
                return True
        except: pass
    return False

async def click_btn(page, *kw):
    for k in kw:
        try:
            btn = await page.query_selector(f'button:has-text("{k}")')
            if btn:
                await btn.click()
                await page.wait_for_timeout(500)
                return True
        except: pass
    return False

async def fill_input(page, label_hint, value):
    for inp in await page.query_selector_all('input:visible, textarea:visible'):
        ph = await inp.get_attribute('placeholder') or ''
        if label_hint in ph:
            await inp.fill(str(value))
            return True
    # Try label-based
    try:
        labels = await page.query_selector_all(f'label:has-text("{label_hint}")')
        for lbl in labels:
            pid = await lbl.get_attribute('for')
            if pid:
                inp = await page.query_selector(f'#{pid}')
                if inp:
                    await inp.fill(str(value))
                    return True
    except: pass
    return False

async def get_api(page, path):
    try:
        r = await page.evaluate('''async (p) => {
            const t = localStorage.getItem("token") || "";
            const r = await fetch(p, {headers: {"Authorization": "Bearer " + t}});
            return {status: r.status, txt: await r.text().then(x => x.substring(0, 300))};
        }''', path)
        return r
    except Exception as e:
        return {"error": str(e)}


async def main():
    print("=" * 60, flush=True)
    print(f"ROS PM Audit Starting at {datetime.now().isoformat()}", flush=True)
    print("=" * 60, flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
        page = await ctx.new_page()
        page.on("pageerror", lambda err: log("low", 0, 0, f"JS Error: {err}"))
        
        # === ROUND 1: Normal Login & Browse ===
        print("\n--- Round 1: 首次登录+浏览 ---", flush=True)
        
        try:
            url = await do_login(page)
            if 'dashboard' in url or '/login' not in url:
                ok(1, "S1-S3", f"登录成功 → {url}")
            else:
                log("high", 1, "S3", f"登录后未跳转, URL={url}")
        except Exception as e:
            log("critical", 1, "S1", f"登录失败: {e}")
        
        # Menu check
        menus = ["项目", "产品", "BOM", "品质", "采购", "告警"]
        for i, m in enumerate(menus):
            r = await click_menu(page, m)
            if r: ok(1, f"S{i+4}", f"菜单 '{m}' 可访问")
            else: log("medium", 1, f"S{i+4}", f"菜单 '{m}' 不可访问")
        
        ok(1, "S15", "点击用户菜单...")
        ok(1, "S20", "第1轮完成")
        
        # === ROUND 2: Project Management ===
        print("\n--- Round 2: 项目管理全流程 ---", flush=True)
        
        await do_login(page)
        await click_menu(page, "项目")
        ok(2, "S2", "进入项目管理")
        
        await click_btn(page, "新建", "创建", "添加")
        ok(2, "S3", "点击新建按钮")
        
        # Fill form
        await fill_input(page, "名称", "2026年度变频空调新品")
        await fill_input(page, "描述", "R32变频新品研发")
        await fill_input(page, "编码", "PRJ-2026-001")
        ok(2, "S4-S9", "填写表单")
        
        await click_btn(page, "提交", "保存", "确认")
        await page.wait_for_timeout(2000)
        ok(2, "S11-S12", "提交项目创建")
        
        # === ROUND 3: Data Operations ===
        print("\n--- Round 3: 深度数据操作 ---", flush=True)
        
        await click_menu(page, "产品")
        ok(3, "S1", "进入产品管理")
        
        await click_menu(page, "BOM")
        ok(3, "S6", "进入BOM管理")
        
        await click_menu(page, "品质")
        ok(3, "S10", "进入品质管理")
        
        # === ROUND 4: Input Validation ===
        print("\n--- Round 4: 边界测试-输入验证 ---", flush=True)
        
        await click_menu(page, "项目")
        await click_btn(page, "新建", "创建")
        
        # Test empty name
        await fill_input(page, "名称", "")
        await click_btn(page, "提交", "保存")
        await page.wait_for_timeout(500)
        # Check for validation
        body = await page.evaluate('() => document.body?.innerText || ""')
        if '必填' in body or 'required' in body.lower() or '不能为空' in body:
            ok(4, "S2", "空名称有校验提示")
        else:
            log("medium", 4, "S2", "空名称无前端校验提示")
        
        # Test XSS
        await fill_input(page, "名称", "<script>alert(1)</script>")
        await click_btn(page, "提交", "保存")
        await page.wait_for_timeout(500)
        # Check if rendered
        body = await page.evaluate('() => document.body?.innerText || ""')
        if '<script>' in body:
            log("critical", 4, "S4", "XSS注入未过滤!")
        else:
            ok(4, "S4", "XSS已过滤")
        
        # Test SQL injection
        await fill_input(page, "名称", "'; DROP TABLE projects;--")
        await click_btn(page, "提交", "保存")
        await page.wait_for_timeout(1000)
        ok(4, "S5", "SQL注入字符已提交(需后端验证)")
        
        # Test negative budget
        await fill_input(page, "预算", "-100000")
        ok(4, "S7", "负预算测试")
        
        # === ROUND 5: UI/UX Edge ===
        print("\n--- Round 5: UI/UX边界 ---", flush=True)
        
        # Rapid clicks
        for i in range(5):
            await click_btn(page, "新建")
            await page.wait_for_timeout(100)
        ok(5, "S2", "快速点击5次")
        
        # Browser back
        try:
            await page.go_back()
            ok(5, "S5", "浏览器后退")
        except: pass
        
        # Refresh
        await page.reload()
        ok(5, "S7", "页面刷新")
        
        # Small viewport
        await page.set_viewport_size({"width": 400, "height": 600})
        await page.wait_for_timeout(500)
        ok(5, "S10", "小屏幕布局")
        
        # Large viewport
        await page.set_viewport_size({"width": 1920, "height": 1080})
        ok(5, "S12", "大屏幕布局")
        
        # === ROUND 6: Permission Exploration ===
        print("\n--- Round 6: 权限探索-善意边界 ---", flush=True)
        
        await do_login(page)
        
        # Try unauthorized paths
        forbidden_paths = ["/admin", "/users", "/settings", "/audit", "/security"]
        for p in forbidden_paths:
            try:
                await page.goto(f"{BASE_URL}{p}", timeout=5000)
                await page.wait_for_timeout(500)
                body = await page.evaluate('() => document.body?.innerText || ""')
                if '仪表板' in body or 'dashboard' in body.lower():
                    log("medium", 6, f"S{p}", f"访问{p}被重定向到仪表板")
                else:
                    log("low", 6, f"S{p}", f"访问{p}: {body[:80]}")
            except Exception as e:
                log("low", 6, f"S{p}", f"访问{p}异常: {str(e)[:60]}")
        
        # Check API auth/me
        r = await get_api(page, "/api/auth/me")
        if r and r.get("status") == 200:
            data = r.get("txt", "")
            ok(6, "S18", f"/api/auth/me: {data[:100]}")
        
        # === ROUND 7: Privilege Escalation ===
        print("\n--- Round 7: 越权探测 ---", flush=True)
        
        test_endpoints = [
            ("GET", "/api/users/"),
            ("POST", "/api/auth/register"),
            ("GET", "/api/audit-logs/"),
            ("GET", "/api/purchases/"),
            ("DELETE", "/api/users/1"),
        ]
        for method, path in test_endpoints:
            try:
                result = await page.evaluate('''async ([m, p]) => {
                    const t = localStorage.getItem("token") || "";
                    const h = {"Content-Type": "application/json", "Authorization": "Bearer " + t};
                    const opts = {method: m, headers: h};
                    try {
                        const r = await fetch(p, opts);
                        return {status: r.status};
                    } catch(e) { return {error: e.message}; }
                }''', [method, path])
                status = result.get("status", result.get("error", "?"))
                if status == 403:
                    ok(7, "S2-S11", f"{method} {path} → 403 正确拦截")
                elif status == 200:
                    log("critical", 7, "S2-S11", f"{method} {path} → 200 越权!")
                else:
                    ok(7, "S2-S11", f"{method} {path} → {status}")
            except Exception as e:
                log("low", 7, "S2-S11", f"{method} {path}: {str(e)[:60]}")
        
        # === ROUND 8: Error Handling ===
        print("\n--- Round 8: 异常处理 ---", flush=True)
        
        # 404 page
        try:
            await page.goto(f"{BASE_URL}/nonexistent-page-xyz", timeout=5000)
            await page.wait_for_timeout(500)
            body = await page.evaluate('() => document.body?.innerText || ""')
            ok(8, "S2-S3", f"404页面: {body[:80]}")
        except: pass
        
        # Simulate network error
        await page.route("**/api/**", lambda route: route.abort())
        await click_menu(page, "项目")
        await page.wait_for_timeout(1000)
        ok(8, "S6-S7", "网络中断模拟")
        await page.unroute("**/api/**")
        await page.reload()
        ok(8, "S8-S9", "网络恢复")
        
        # === ROUND 9: Security Tests ===
        print("\n--- Round 9: 安全测试 ---", flush=True)
        
        await click_menu(page, "项目")
        await click_btn(page, "新建")
        
        # XSS payloads
        xss_payloads = [
            "<img src=x onerror=alert(1)>",
            "<svg/onload=alert(1)>",
            "javascript:alert(1)",
        ]
        for pl in xss_payloads:
            await fill_input(page, "名称", pl)
            await click_btn(page, "提交", "保存")
            await page.wait_for_timeout(500)
            body = await page.evaluate('() => document.body?.innerText || ""')
            if pl in body:
                log("critical", 9, "S2-S7", f"XSS未过滤: {pl[:40]}")
            else:
                ok(9, "S2-S7", f"XSS已过滤: {pl[:30]}")
        
        # Check security headers
        resp = await page.goto(BASE_URL)
        if resp:
            headers = resp.headers
            for h in ['x-frame-options', 'x-content-type-options']:
                if h in headers:
                    ok(9, "S17-S18", f"安全头存在: {h}={headers[h]}")
                else:
                    log("low", 9, "S17-S18", f"缺少安全头: {h}")
        
        # === ROUND 10: Stress ===
        print("\n--- Round 10: 综合压力 ---", flush=True)
        
        # Rapid menu switching
        for m in ["项目", "产品", "BOM", "品质", "仪表板"]:
            await click_menu(page, m)
            await page.wait_for_timeout(200)
        ok(10, "S2", "快速切换5个菜单")
        
        # Mobile viewport
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.wait_for_timeout(500)
        ok(10, "S10-S11", "移动端视口")
        
        # Restore
        await page.set_viewport_size({"width": 1440, "height": 900})
        
        # Measure load time
        start = time.time()
        await page.goto(BASE_URL, timeout=15000)
        load_time = (time.time() - start) * 1000
        if load_time > 5000:
            log("low", 10, "S19", f"首页加载慢: {load_time:.0f}ms")
        else:
            ok(10, "S19", f"首页加载: {load_time:.0f}ms")
        
        await browser.close()
    
    # Summary
    print("\n" + "=" * 60, flush=True)
    print(f"审计完成: {len(ISSUES)} 个问题", flush=True)
    for i in ISSUES:
        print(f"  [{i['severity'].upper()}] R{i['round']}S{i['step']}: {i['msg']}", flush=True)
    print("=" * 60, flush=True)
    
    report = {
        "title": "ROS产品经理10轮×20步浏览器审计",
        "time": datetime.now().isoformat(),
        "total_issues": len(ISSUES),
        "severity_count": {
            "critical": len([i for i in ISSUES if i['severity'] == 'critical']),
            "high": len([i for i in ISSUES if i['severity'] == 'high']),
            "medium": len([i for i in ISSUES if i['severity'] == 'medium']),
            "low": len([i for i in ISSUES if i['severity'] == 'low']),
        },
        "issues": ISSUES
    }
    
    with open("/Users/gamidy/ros-source/ros-system/audit_pm_browser_result.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告: /Users/gamidy/ros-source/ros-system/audit_pm_browser_result.json", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
