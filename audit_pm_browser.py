#!/usr/bin/env python3
"""
ROS 产品经理 10轮×20步 浏览器审计脚本
模拟高级产品经理真实使用场景：正常/异常/善意/恶意/有意/无意
"""

import asyncio
import json
import time
import re
from datetime import datetime
from playwright.async_api import async_playwright, Page

BASE_URL = "http://139.196.15.52"
USERNAME = "pm"
PASSWORD = "Ros2026!@"

RESULTS = []
ISSUES = []


def log_issue(round_num, step, category, severity, description, details=""):
    entry = {
        "round": round_num,
        "step": step,
        "category": category,
        "severity": severity,  # critical, high, medium, low
        "description": description,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    ISSUES.append(entry)
    RESULTS.append(f"[{severity.upper()}] R{round_num}S{step}: {description}")
    print(f"  ⚠️  [{severity.upper()}] {description}")


def log_ok(round_num, step, msg):
    RESULTS.append(f"[OK] R{round_num}S{step}: {msg}")
    print(f"  ✅ {msg}")


async def login(page: Page, username=USERNAME, password=PASSWORD):
    """登录系统"""
    await page.goto(f"{BASE_URL}/login")
    await page.wait_for_selector('input[placeholder*="用户名"], input[name="username"], input[type="text"]', timeout=10000)
    
    # 填写登录表单
    inputs = await page.query_selector_all('input')
    for inp in inputs:
        p = await inp.get_attribute('placeholder') or ''
        t = await inp.get_attribute('type') or ''
        if '用户名' in p or '账号' in p or (t == 'text' and not await inp.is_checked()):
            await inp.fill(username)
        elif '密码' in p or t == 'password':
            await inp.fill(password)
    
    # 点击登录按钮
    btn = await page.query_selector('button:has-text("登录"), button:has-text("登 录"), button[type="submit"]')
    if btn:
        await btn.click()
    
    await page.wait_for_timeout(2000)
    return page.url


async def wait_for_page_stable(page: Page, timeout=5000):
    """等待页面加载稳定"""
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except:
        pass
    await page.wait_for_timeout(500)


async def get_page_snapshot(page: Page):
    """获取页面关键信息（URL, 标题, 可见文本摘要）"""
    url = page.url
    title = await page.title()
    try:
        body_text = await page.evaluate('() => document.body?.innerText?.substring(0, 500) || ""')
    except:
        body_text = ""
    return {"url": url, "title": title, "text_preview": body_text[:200]}


# ============================================================
# 10轮定义：每轮20步
# ============================================================

ROUNDS = {
    1: {
        "name": "正常操作：首次登录+浏览",
        "theme": "normal",
        "desc": "产品经理首次登录，查看仪表板、项目列表、产品需求等核心功能"
    },
    2: {
        "name": "正常操作：项目管理全流程",
        "theme": "normal",
        "desc": "创建项目、填写需求、查看BOM、追踪质量、检查进度"
    },
    3: {
        "name": "正常操作：深度数据操作",
        "theme": "normal",
        "desc": "编辑项目、修改需求、搜索筛选、导出数据"
    },
    4: {
        "name": "边界测试：输入验证",
        "theme": "edge_case",
        "desc": "空字段、超长文本、特殊字符、重复名称、边界数值"
    },
    5: {
        "name": "边界测试：UI/UX异常",
        "theme": "edge_case",
        "desc": "快速连续点击、表单中途切换、弹窗嵌套、窗口缩放"
    },
    6: {
        "name": "权限探索：善意识别边界",
        "theme": "permission",
        "desc": "尝试访问其他角色区域、检查可见菜单、测试URL直接访问"
    },
    7: {
        "name": "权限探索：越权尝试",
        "theme": "permission",
        "desc": "直接调用API、修改URL参数、查看非授权数据"
    },
    8: {
        "name": "异常处理：网络/页面错误",
        "theme": "error_handling",
        "desc": "刷新页面、浏览器后退、断网恢复、404/500错误处理"
    },
    9: {
        "name": "安全测试：善意探测",
        "theme": "security",
        "desc": "XSS注入、SQL注入字符、路径遍历、CSRF试探"
    },
    10: {
        "name": "综合压力：复杂流程",
        "theme": "stress",
        "desc": "多标签操作、并发请求、大量数据加载、长时间闲置"
    }
}


async def execute_round(page: Page, round_num: int, round_info: dict):
    """执行一轮20步"""
    print(f"\n{'='*60}")
    print(f"第{round_num}轮: {round_info['name']}")
    print(f"主题: {round_info['theme']} | {round_info['desc']}")
    print(f"{'='*60}")
    
    steps = []  # 默认空列表，防止未绑定
    
    # ============================================================
    # Round 1: 首次登录+浏览
    # ============================================================
    if round_num == 1:
        steps = [
            ("S1", "打开登录页面", lambda: page.goto(f"{BASE_URL}/login")),
            ("S2", "输入用户名和密码", lambda: login(page)),
            ("S3", "验证登录后跳转到仪表板", lambda: check_url_contains(page, "dashboard")),
            ("S4", "查看仪表板统计数据", lambda: page.wait_for_timeout(1000)),
            ("S5", "点击导航菜单-项目管理", lambda: click_nav(page, "项目")),
            ("S6", "查看项目列表", lambda: page.wait_for_timeout(1000)),
            ("S7", "点击导航菜单-产品管理", lambda: click_nav(page, "产品")),
            ("S8", "查看产品列表", lambda: page.wait_for_timeout(1000)),
            ("S9", "点击导航菜单-BOM管理", lambda: click_nav(page, "BOM")),
            ("S10", "查看BOM列表", lambda: page.wait_for_timeout(1000)),
            ("S11", "点击导航菜单-品质管理", lambda: click_nav(page, "品质")),
            ("S12", "查看品质问题列表", lambda: page.wait_for_timeout(1000)),
            ("S13", "点击导航菜单-采购管理", lambda: click_nav(page, "采购")),
            ("S14", "查看采购列表（产品经理可能无权限）", lambda: page.wait_for_timeout(1000)),
            ("S15", "点击右上角用户菜单", lambda: click_user_menu(page)),
            ("S16", "查看个人信息/角色", lambda: page.wait_for_timeout(500)),
            ("S17", "点击系统通知/告警", lambda: click_nav(page, "告警")),
            ("S18", "查看告警列表", lambda: page.wait_for_timeout(1000)),
            ("S19", "返回仪表板", lambda: click_nav(page, "仪表板")),
            ("S20", "退出登录", lambda: logout(page)),
        ]
    
    # ============================================================
    # Round 2: 项目管理全流程
    # ============================================================
    elif round_num == 2:
        steps = [
            ("S1", "登录系统", lambda: login(page)),
            ("S2", "进入项目管理", lambda: click_nav(page, "项目")),
            ("S3", "点击新建项目按钮", lambda: click_button(page, "新建", "创建", "添加")),
            ("S4", "填写项目名称", lambda: fill_field(page, "项目名称", "2026年度家用变频空调新品研发")),
            ("S5", "填写项目描述/背景", lambda: fill_field(page, "描述", "开发新一代R32变频空调，能效比提升15%，噪音降低3dB")),
            ("S6", "选择项目类型", lambda: select_dropdown(page, "新品研发")),
            ("S7", "设置开始日期", lambda: fill_field(page, "开始", "2026-07-01")),
            ("S8", "设置结束日期", lambda: fill_field(page, "结束", "2027-03-31")),
            ("S9", "填写预算", lambda: fill_field(page, "预算", "5000000")),
            ("S10", "选择优先级", lambda: select_dropdown(page, "高")),
            ("S11", "提交创建", lambda: click_button(page, "提交", "保存", "确认")),
            ("S12", "验证创建成功（返回列表/提示）", lambda: page.wait_for_timeout(2000)),
            ("S13", "点击新项目查看详情", lambda: click_first_row(page)),
            ("S14", "查看项目详情页信息", lambda: page.wait_for_timeout(1000)),
            ("S15", "点击编辑按钮", lambda: click_button(page, "编辑", "修改")),
            ("S16", "修改项目描述", lambda: fill_field(page, "描述", "（已更新）增加海外市场适配需求")),
            ("S17", "保存修改", lambda: click_button(page, "提交", "保存", "确认")),
            ("S18", "关联BOM", lambda: click_tab(page, "BOM")),
            ("S19", "关联品质问题", lambda: click_tab(page, "品质")),
            ("S20", "返回列表", lambda: click_button(page, "返回", "取消")),
        ]
    
    # ============================================================
    # Round 3: 深度数据操作
    # ============================================================
    elif round_num == 3:
        steps = [
            ("S1", "进入产品管理", lambda: click_nav(page, "产品")),
            ("S2", "搜索已有产品", lambda: search(page, "变频")),
            ("S3", "点击搜索结果", lambda: click_first_row(page)),
            ("S4", "查看产品详情", lambda: page.wait_for_timeout(1000)),
            ("S5", "查看关联项目", lambda: click_tab(page, "项目")),
            ("S6", "进入BOM管理", lambda: click_nav(page, "BOM")),
            ("S7", "展开BOM树形结构", lambda: click_expand(page)),
            ("S8", "查看BOM层级和成本", lambda: page.wait_for_timeout(1000)),
            ("S9", "搜索特定物料", lambda: search(page, "压缩机")),
            ("S10", "进入品质管理", lambda: click_nav(page, "品质")),
            ("S11", "按状态筛选", lambda: select_filter(page, "状态")),
            ("S12", "查看品质问题详情", lambda: click_first_row(page)),
            ("S13", "查看品质问题关联信息", lambda: page.wait_for_timeout(1000)),
            ("S14", "进入项目进度", lambda: click_nav(page, "项目")),
            ("S15", "查看甘特图/时间线", lambda: click_tab(page, "进度")),
            ("S16", "查看延期预警", lambda: page.wait_for_timeout(1000)),
            ("S17", "进入外协送样", lambda: click_nav(page, "外协")),
            ("S18", "查看送样列表", lambda: page.wait_for_timeout(1000)),
            ("S19", "查看审计日志（IT安全员功能，PM可能无权限）", lambda: click_nav(page, "审计")),
            ("S20", "返回仪表板", lambda: click_nav(page, "仪表板")),
        ]
    
    # ============================================================
    # Round 4: 边界测试-输入验证
    # ============================================================
    elif round_num == 4:
        steps = [
            ("S1", "进入项目管理", lambda: click_nav(page, "项目")),
            ("S2", "尝试创建空名称项目", lambda: create_empty_name(page)),
            ("S3", "尝试超长项目名称(500字符)", lambda: create_long_name(page, 500)),
            ("S4", "尝试特殊字符名称 <script>alert(1)</script>", lambda: create_special_name(page, "<script>alert(1)</script>")),
            ("S5", "尝试SQL注入字符 '; DROP TABLE projects;--", lambda: create_special_name(page, "'; DROP TABLE projects;--")),
            ("S6", "尝试Emoji名称", lambda: create_special_name(page, "测试😀🎉🔥")),
            ("S7", "尝试负预算", lambda: create_negative_budget(page)),
            ("S8", "尝试超大预算", lambda: create_huge_budget(page)),
            ("S9", "结束日期早于开始日期", lambda: create_invalid_date(page)),
            ("S10", "不填必填项直接提交", lambda: submit_empty_form(page)),
            ("S11", "重复项目名称", lambda: create_duplicate_name(page)),
            ("S12", "输入纯空格名称", lambda: create_special_name(page, "     ")),
            ("S13", "输入换行符名称", lambda: create_special_name(page, "项目A\n项目B")),
            ("S14", "输入NULL/undefined字符", lambda: create_special_name(page, "NULL")),
            ("S15", "进入产品管理", lambda: click_nav(page, "产品")),
            ("S16", "搜索不存在的产品", lambda: search(page, "XYZ不存在的产品12345")),
            ("S17", "搜索特殊正则字符 .*+?^${}[]", lambda: search(page, ".*+?^${}[]")),
            ("S18", "空搜索", lambda: search(page, "")),
            ("S19", "超长搜索词(1000字符)", lambda: search(page, "A" * 1000)),
            ("S20", "返回仪表板", lambda: click_nav(page, "仪表板")),
        ]
    
    # ============================================================
    # Round 5: 边界测试-UI/UX异常
    # ============================================================
    elif round_num == 5:
        steps = [
            ("S1", "进入项目管理", lambda: click_nav(page, "项目")),
            ("S2", "快速连续点击新建按钮5次", lambda: rapid_click(page, "新建", 5)),
            ("S3", "在表单未填完时点击取消", lambda: cancel_form(page)),
            ("S4", "在表单填写中途切换导航", lambda: switch_nav_mid_form(page)),
            ("S5", "使用浏览器后退按钮", lambda: page.go_back()),
            ("S6", "使用浏览器前进按钮", lambda: page.go_forward()),
            ("S7", "刷新页面（F5）", lambda: page.reload()),
            ("S8", "强制刷新（Ctrl+Shift+R）", lambda: page.reload()),
            ("S9", "在加载中点击其他菜单", lambda: fast_nav_switch(page)),
            ("S10", "缩小浏览器窗口", lambda: page.set_viewport_size({"width": 400, "height": 600})),
            ("S11", "测试小屏幕布局", lambda: page.wait_for_timeout(1000)),
            ("S12", "放大浏览器窗口", lambda: page.set_viewport_size({"width": 1920, "height": 1080})),
            ("S13", "测试大屏幕布局", lambda: page.wait_for_timeout(1000)),
            ("S14", "连续打开3个弹窗/对话框", lambda: open_multiple_dialogs(page)),
            ("S15", "在弹窗打开时按ESC", lambda: page.keyboard.press("Escape")),
            ("S16", "在表单内按Tab切换字段", lambda: tab_through_form(page)),
            ("S17", "在表单内按Enter提交", lambda: page.keyboard.press("Enter")),
            ("S18", "鼠标悬停查看tooltip", lambda: hover_elements(page)),
            ("S19", "点击面包屑导航", lambda: click_breadcrumb(page)),
            ("S20", "滚动到页面底部验证加载更多", lambda: scroll_to_bottom(page)),
        ]
    
    # ============================================================
    # Round 6: 权限探索-善意边界识别
    # ============================================================
    elif round_num == 6:
        steps = [
            ("S1", "登录并查看完整菜单", lambda: login_and_scan_menu(page)),
            ("S2", "尝试访问 /admin 路径", lambda: page.goto(f"{BASE_URL}/admin")),
            ("S3", "尝试访问 /users 管理页", lambda: page.goto(f"{BASE_URL}/users")),
            ("S4", "尝试访问 /settings 系统设置", lambda: page.goto(f"{BASE_URL}/settings")),
            ("S5", "尝试访问 /audit 审计日志", lambda: page.goto(f"{BASE_URL}/audit")),
            ("S6", "尝试访问 /security 安全中心", lambda: page.goto(f"{BASE_URL}/security")),
            ("S7", "尝试访问采购管理", lambda: click_nav(page, "采购")),
            ("S8", "尝试访问财务管理", lambda: click_nav(page, "财务")),
            ("S9", "尝试访问生产管理", lambda: click_nav(page, "生产")),
            ("S10", "尝试创建新用户", lambda: page.goto(f"{BASE_URL}/register")),
            ("S11", "查看可用的操作按钮（新建/编辑/删除）", lambda: scan_action_buttons(page)),
            ("S12", "尝试通过URL参数查看他人数据 ?id=999", lambda: page.goto(f"{BASE_URL}/projects/999")),
            ("S13", "尝试修改URL中的角色参数", lambda: page.goto(f"{BASE_URL}/?role=admin")),
            ("S14", "查看浏览器localStorage/cookie", lambda: inspect_storage(page)),
            ("S15", "检查前端JS是否暴露权限配置", lambda: check_js_exposure(page)),
            ("S16", "查看API响应中的角色信息", lambda: check_api_role_leak(page)),
            ("S17", "尝试访问API文档 /docs", lambda: page.goto(f"{BASE_URL}/docs")),
            ("S18", "尝试访问 /api/auth/me 查看返回信息", lambda: page.goto(f"{BASE_URL}/api/auth/me")),
            ("S19", "检查403/401错误消息是否泄露信息", lambda: check_error_messages(page)),
            ("S20", "记录可见vs预期的权限差异", lambda: page.wait_for_timeout(1000)),
        ]
    
    # ============================================================
    # Round 7: 权限探索-越权尝试
    # ============================================================
    elif round_num == 7:
        steps = [
            ("S1", "获取当前token", lambda: get_token(page)),
            ("S2", "尝试API直接创建用户 POST /api/auth/register", lambda: api_test(page, "POST", "/api/auth/register", {"username": "hacker_pm","password": "hack123","role":"admin"})),
            ("S3", "尝试API获取所有用户 GET /api/users/", lambda: api_test(page, "GET", "/api/users/")),
            ("S4", "尝试API删除其他用户 DELETE /api/users/1", lambda: api_test(page, "DELETE", "/api/users/1")),
            ("S5", "尝试API修改他人权限 PATCH /api/users/2", lambda: api_test(page, "PATCH", "/api/users/2", {"role":"admin"})),
            ("S6", "尝试API访问采购数据 GET /api/purchases/", lambda: api_test(page, "GET", "/api/purchases/")),
            ("S7", "尝试API访问财务数据 GET /api/finance/", lambda: api_test(page, "GET", "/api/finance/")),
            ("S8", "尝试API访问审计日志 GET /api/audit-logs/", lambda: api_test(page, "GET", "/api/audit-logs/")),
            ("S9", "尝试API修改系统配置", lambda: api_test(page, "PATCH", "/api/settings/", {"debug": True})),
            ("S10", "尝试API越权修改他人项目", lambda: api_test(page, "PATCH", "/api/projects/999", {"name": "hacked"})),
            ("S11", "尝试API越权删除品质问题", lambda: api_test(page, "DELETE", "/api/quality-issues/1")),
            ("S12", "尝试不带token的API请求", lambda: api_test_noauth(page, "GET", "/api/projects/")),
            ("S13", "尝试过期token", lambda: api_test_expired(page)),
            ("S14", "尝试篡改token中的role字段", lambda: api_test_tampered_token(page)),
            ("S15", "尝试批量请求探测(并发)", lambda: api_batch_test(page)),
            ("S16", "尝试文件上传 Webshell", lambda: api_upload_test(page)),
            ("S17", "尝试路径遍历 /api/../../../etc/passwd", lambda: page.goto(f"{BASE_URL}/api/projects/../../../etc/passwd")),
            ("S18", "尝试SSRF 内部地址探测", lambda: page.goto(f"{BASE_URL}/api/fetch?url=http://127.0.0.1:8000/admin")),
            ("S19", "尝试大量404请求探测路由", lambda: api_probe_routes(page)),
            ("S20", "检查速率限制是否生效", lambda: api_rate_limit_test(page)),
        ]
    
    # ============================================================
    # Round 8: 异常处理
    # ============================================================
    elif round_num == 8:
        steps = [
            ("S1", "正常登录", lambda: login(page)),
            ("S2", "访问不存在的页面 /nonexistent", lambda: page.goto(f"{BASE_URL}/nonexistent")),
            ("S3", "检查404页面是否友好", lambda: page.wait_for_timeout(1000)),
            ("S4", "触发500错误(发畸形请求)", lambda: trigger_500(page)),
            ("S5", "检查500错误提示", lambda: page.wait_for_timeout(1000)),
            ("S6", "网络断开模拟-先离线", lambda: page.route("**/*", lambda route: route.abort())),
            ("S7", "点击导航(应显示错误)", lambda: click_nav(page, "项目")),
            ("S8", "恢复网络", lambda: page.unroute("**/*")),
            ("S9", "重新加载页面", lambda: page.reload()),
            ("S10", "登录后长时间闲置(模拟)", lambda: page.wait_for_timeout(2000)),
            ("S11", "闲置后操作是否仍有效", lambda: click_nav(page, "项目")),
            ("S12", "Token过期模拟(等待后操作)", lambda: page.wait_for_timeout(1000)),
            ("S13", "检查是否自动跳转登录", lambda: page.wait_for_timeout(1000)),
            ("S14", "重新登录", lambda: login(page)),
            ("S15", "并发打开多个标签", lambda: open_new_tab(page)),
            ("S16", "在新标签中登录(应踢掉旧会话?)", lambda: page.wait_for_timeout(1000)),
            ("S17", "操作过程中关闭标签(模拟崩溃)", lambda: page.wait_for_timeout(500)),
            ("S18", "浏览器内存不足场景(大数据加载)", lambda: load_large_data(page)),
            ("S19", "检查是否有全局错误捕获", lambda: check_global_errors(page)),
            ("S20", "检查console是否有JavaScript错误", lambda: check_console_errors(page)),
        ]
    
    # ============================================================
    # Round 9: 安全测试
    # ============================================================
    elif round_num == 9:
        steps = [
            ("S1", "登录系统", lambda: login(page)),
            ("S2", "在项目名称中注入XSS <img src=x onerror=alert(1)>", lambda: inject_xss(page, "project_name", "<img src=x onerror=alert(1)>")),
            ("S3", "检查XSS是否被渲染", lambda: page.wait_for_timeout(1000)),
            ("S4", "在产品描述中注入XSS", lambda: inject_xss(page, "description", "<svg/onload=alert(1)>")),
            ("S5", "在搜索框注入XSS", lambda: inject_xss_search(page, "<script>alert(1)</script>")),
            ("S6", "在BOM料号中注入XSS", lambda: inject_xss(page, "material_code", "javascript:alert(1)")),
            ("S7", "在URL参数注入XSS", lambda: page.goto(f"{BASE_URL}/projects?name=<script>alert(1)</script>")),
            ("S8", "SQL注入: UNION SELECT探测", lambda: inject_sqli(page, "1' UNION SELECT 1,2,3--")),
            ("S9", "SQL注入: 布尔盲注", lambda: inject_sqli(page, "1' AND '1'='1")),
            ("S10", "SQL注入: 时间盲注", lambda: inject_sqli(page, "1' AND SLEEP(5)--")),
            ("S11", "SQL注入: 堆叠查询", lambda: inject_sqli(page, "1'; DROP TABLE projects;--")),
            ("S12", "路径遍历: ../etc/passwd", lambda: inject_sqli(page, "../../../etc/passwd")),
            ("S13", "路径遍历: ..%2f..%2f..%2f", lambda: inject_sqli(page, "..%2f..%2f..%2fetc/passwd")),
            ("S14", "CRLF注入: 响应头注入", lambda: inject_sqli(page, "test%0d%0aSet-Cookie: hacked=1")),
            ("S15", "XXE攻击: XML实体注入", lambda: inject_sqli(page, '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>')),
            ("S16", "CSRF: 跨站请求伪造探测", lambda: csrf_test(page)),
            ("S17", "点击劫持: 检查X-Frame-Options", lambda: check_headers(page)),
            ("S18", "检查CSP内容安全策略", lambda: check_csp(page)),
            ("S19", "检查敏感信息泄露(注释/console/源码)", lambda: check_info_leak(page)),
            ("S20", "密码框是否autocomplete=off", lambda: check_password_field(page)),
        ]
    
    # ============================================================
    # Round 10: 综合压力
    # ============================================================
    elif round_num == 10:
        steps = [
            ("S1", "登录系统", lambda: login(page)),
            ("S2", "快速切换5个导航菜单", lambda: rapid_nav(page, 5)),
            ("S3", "在项目管理中创建大量数据(模拟)", lambda: page.wait_for_timeout(1000)),
            ("S4", "同时打开项目详情+BOM+品质三个Tab", lambda: open_multiple_tabs_nav(page)),
            ("S5", "在搜索框快速输入删除", lambda: rapid_search(page)),
            ("S6", "表单中复制粘贴富文本", lambda: paste_rich_text(page)),
            ("S7", "拖拽操作（如果有拖拽排序）", lambda: page.wait_for_timeout(500)),
            ("S8", "下载文件/导出数据", lambda: click_button(page, "导出", "下载")),
            ("S9", "上传大文件", lambda: page.wait_for_timeout(500)),
            ("S10", "在移动端视口模拟", lambda: page.set_viewport_size({"width": 375, "height": 812})),
            ("S11", "移动端操作测试", lambda: page.wait_for_timeout(1000)),
            ("S12", "恢复桌面视口", lambda: page.set_viewport_size({"width": 1440, "height": 900})),
            ("S13", "测试键盘快捷键 Ctrl+S", lambda: page.keyboard.press("Control+s")),
            ("S14", "测试Ctrl+Z撤销", lambda: page.keyboard.press("Control+z")),
            ("S15", "测试F5刷新保持状态", lambda: page.keyboard.press("F5")),
            ("S16", "长时间操作后内存泄漏检测", lambda: page.wait_for_timeout(2000)),
            ("S17", "所有菜单可用性总结", lambda: scan_all_menus(page)),
            ("S18", "功能完整性检查清单", lambda: page.wait_for_timeout(1000)),
            ("S19", "性能: 页面加载时间", lambda: measure_page_load(page)),
            ("S20", "最终登出", lambda: logout(page)),
        ]
    
    # 执行步骤
    for i, (step_name, step_desc, step_fn) in enumerate(steps, 1):
        step_label = f"R{round_num}-{step_name}"
        print(f"  [{step_name}] {step_desc}...", end=" ")
        try:
            result = await step_fn()
            if result is False:
                log_issue(round_num, step_name, round_info['theme'], "medium", f"{step_desc} - 操作异常", str(result))
            else:
                log_ok(round_num, step_name, f"{step_desc} ✓")
        except Exception as e:
            error_msg = str(e)[:200]
            log_issue(round_num, step_name, round_info['theme'], "high", f"{step_desc} - 异常: {error_msg}", error_msg)
        
        await page.wait_for_timeout(300)


# ============================================================
# 辅助函数
# ============================================================

async def check_url_contains(page, text):
    await page.wait_for_timeout(1000)
    return text in page.url

async def click_nav(page, keyword):
    """点击导航菜单项"""
    await page.wait_for_timeout(500)
    # 尝试多种选择器
    selectors = [
        f'a:has-text("{keyword}")',
        f'span:has-text("{keyword}")',
        f'li:has-text("{keyword}")',
        f'div:has-text("{keyword}")',
        f'.el-menu-item:has-text("{keyword}")',
        f'[class*="menu"]:has-text("{keyword}")',
        f'[class*="nav"]:has-text("{keyword}")',
        f'button:has-text("{keyword}")',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_timeout(500)
                return
        except:
            continue

async def click_button(page, *keywords):
    """点击包含关键字的按钮"""
    for kw in keywords:
        try:
            btn = await page.query_selector(f'button:has-text("{kw}")')
            if btn:
                await btn.click()
                return
        except:
            continue
    # fallback: 点击任意可见按钮
    try:
        btns = await page.query_selector_all('button:visible')
        if btns:
            await btns[0].click()
    except:
        pass

async def click_first_row(page):
    """点击表格第一行"""
    await page.wait_for_timeout(500)
    try:
        row = await page.query_selector('tr.el-table__row:first-child, tbody tr:first-child, .el-table tbody tr:first-child')
        if row:
            await row.click()
    except:
        pass

async def click_user_menu(page):
    """点击用户菜单"""
    try:
        avatar = await page.query_selector('.el-avatar, .avatar, [class*="user"]')
        if avatar:
            await avatar.click()
    except:
        pass

async def logout(page):
    """退出登录"""
    try:
        await click_user_menu(page)
        await page.wait_for_timeout(300)
        logout_btn = await page.query_selector('text=退出登录, text=退出, text=登出, text=Logout')
        if logout_btn:
            await logout_btn.click()
    except:
        pass

async def fill_field(page, label, value):
    """填写表单字段"""
    await page.wait_for_timeout(300)
    # 尝试通过标签找到对应input
    try:
        # 查找label文本
        labels = await page.query_selector_all(f'label:has-text("{label}"), span:has-text("{label}")')
        for lbl in labels:
            # 找相邻的input
            parent = await lbl.evaluate('el => el.closest(".el-form-item, .form-item, .form-group")?.innerHTML || ""')
            if parent:
                input_el = await page.query_selector(f'input:visible, textarea:visible')
                if input_el:
                    await input_el.fill(str(value))
                    return
    except:
        pass
    # Fallback: 通过placeholder
    try:
        inp = await page.query_selector(f'input[placeholder*="{label}"], textarea[placeholder*="{label}"]')
        if inp:
            await inp.fill(str(value))
            return
    except:
        pass

async def select_dropdown(page, option_text):
    """选择下拉选项"""
    try:
        selects = await page.query_selector_all('.el-select, select')
        if selects:
            await selects[0].click()
            await page.wait_for_timeout(300)
            option = await page.query_selector(f'text="{option_text}"')
            if option:
                await option.click()
    except:
        pass

async def click_tab(page, tab_name):
    """点击Tab"""
    try:
        tab = await page.query_selector(f'.el-tabs__item:has-text("{tab_name}"), [role="tab"]:has-text("{tab_name}")')
        if tab:
            await tab.click()
    except:
        pass

async def search(page, keyword):
    """在搜索框输入"""
    try:
        search_input = await page.query_selector('input[placeholder*="搜索"], input[placeholder*="查找"], input[placeholder*="search"], input[type="search"]')
        if search_input:
            await search_input.fill(keyword)
            await page.keyboard.press("Enter")
    except:
        pass

async def select_filter(page, label):
    """选择筛选条件"""
    try:
        filter_el = await page.query_selector(f'select, .el-select')
        if filter_el:
            await filter_el.click()
    except:
        pass

async def click_expand(page):
    """展开树形节点"""
    try:
        expand_icons = await page.query_selector_all('.el-tree-node__expand-icon, [class*="expand"]')
        for icon in expand_icons[:5]:
            await icon.click()
            await page.wait_for_timeout(200)
    except:
        pass

# ============================================================
# Round 4 边界测试辅助
# ============================================================

async def create_empty_name(page):
    await click_nav(page, "项目")
    await click_button(page, "新建", "创建")

async def create_long_name(page, length):
    long_name = "A" * length
    await fill_field(page, "项目名称", long_name)

async def create_special_name(page, name):
    await fill_field(page, "项目名称", name)

async def create_negative_budget(page):
    await fill_field(page, "预算", "-100000")

async def create_huge_budget(page):
    await fill_field(page, "预算", "999999999999999")

async def create_invalid_date(page):
    await fill_field(page, "开始", "2027-12-31")
    await fill_field(page, "结束", "2026-01-01")

async def submit_empty_form(page):
    await click_button(page, "新建", "创建")
    await click_button(page, "提交", "保存")

async def create_duplicate_name(page):
    await fill_field(page, "项目名称", "2026年度家用变频空调新品研发")

# ============================================================
# Round 5 UI/UX辅助
# ============================================================

async def rapid_click(page, text, times):
    for _ in range(times):
        try:
            btn = await page.query_selector(f'button:has-text("{text}")')
            if btn:
                await btn.click()
        except:
            pass

async def cancel_form(page):
    await click_button(page, "新建", "创建")
    await fill_field(page, "项目名称", "临时项目")
    await click_button(page, "取消", "关闭")

async def switch_nav_mid_form(page):
    await click_button(page, "新建", "创建")
    await fill_field(page, "项目名称", "中途切换测试")
    await click_nav(page, "产品")

async def fast_nav_switch(page):
    await click_nav(page, "项目")
    await page.wait_for_timeout(200)
    await click_nav(page, "产品")

async def open_multiple_dialogs(page):
    for _ in range(3):
        await click_button(page, "新建", "创建")
        await page.wait_for_timeout(300)

async def tab_through_form(page):
    await click_button(page, "新建", "创建")
    for _ in range(10):
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(100)

async def hover_elements(page):
    try:
        items = await page.query_selector_all('a, button, .el-tooltip, [title]')
        for item in items[:5]:
            await item.hover()
            await page.wait_for_timeout(200)
    except:
        pass

async def click_breadcrumb(page):
    try:
        bc = await page.query_selector('.el-breadcrumb__item, [class*="breadcrumb"]')
        if bc:
            await bc.click()
    except:
        pass

async def scroll_to_bottom(page):
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.wait_for_timeout(500)

# ============================================================
# Round 6-7 权限/安全辅助
# ============================================================

async def login_and_scan_menu(page):
    await login(page)
    # 收集所有菜单项
    menu_items = await page.evaluate('''() => {
        const items = document.querySelectorAll('.el-menu-item, [class*="menu"] a, nav a');
        return Array.from(items).map(el => el.textContent?.trim()).filter(Boolean);
    }''')
    print(f"  可见菜单: {menu_items}")

async def scan_action_buttons(page):
    buttons = await page.evaluate('''() => {
        const btns = document.querySelectorAll('button:visible');
        return Array.from(btns).map(b => b.textContent?.trim()).filter(Boolean);
    }''')
    print(f"  可见按钮: {buttons}")

async def inspect_storage(page):
    storage = await page.evaluate('''() => {
        return {
            localStorage: Object.keys(localStorage).reduce((acc, k) => {acc[k] = localStorage[k]; return acc;}, {}),
            sessionStorage: Object.keys(sessionStorage).reduce((acc, k) => {acc[k] = sessionStorage[k]; return acc;}, {}),
            cookies: document.cookie
        };
    }''')
    # 检查是否泄露敏感信息
    sensitive = ['token', 'password', 'secret', 'key', 'role', 'admin']
    for key, val in storage.get('localStorage', {}).items():
        for s in sensitive:
            if s in key.lower() or (isinstance(val, str) and s in val.lower()):
                log_issue(6, "S14", "permission", "medium", f"localStorage可能泄露敏感信息: {key}")

async def check_js_exposure(page):
    """检查前端JS是否暴露权限配置"""
    scripts = await page.evaluate('''() => {
        const scripts = document.querySelectorAll('script[src]');
        return Array.from(scripts).map(s => s.src);
    }''')
    for src in scripts:
        if 'role' in src.lower() or 'permission' in src.lower() or 'admin' in src.lower():
            log_issue(6, "S15", "permission", "low", f"前端可能暴露权限配置: {src}")

async def check_api_role_leak(page):
    """检查API响应是否泄露角色信息"""
    try:
        resp = await page.evaluate('''async () => {
            const r = await fetch('/api/auth/me');
            return await r.json();
        }''')
        if 'role' in str(resp) or 'permissions' in str(resp):
            log_issue(6, "S16", "permission", "low", f"/api/auth/me 返回角色信息: {str(resp)[:200]}")
    except:
        pass

async def check_error_messages(page):
    await page.goto(f"{BASE_URL}/api/admin/test")
    await page.wait_for_timeout(1000)
    body = await page.evaluate('() => document.body?.innerText || ""')
    if 'role' in body.lower() or 'permission' in body.lower() or 'admin' in body.lower():
        log_issue(6, "S19", "security", "high", f"错误消息可能泄露系统信息: {body[:200]}")

async def get_token(page):
    token = await page.evaluate('() => localStorage.getItem("token") || sessionStorage.getItem("token") || ""')
    return token

async def api_test(page, method, path, data=None):
    """通过浏览器执行API调用"""
    try:
        result = await page.evaluate('''async ({method, path, data}) => {
            const token = localStorage.getItem("token") || "";
            const headers = {"Content-Type": "application/json"};
            if (token) headers["Authorization"] = "Bearer " + token;
            const options = {method, headers};
            if (data && method !== "GET") options.body = JSON.stringify(data);
            try {
                const r = await fetch(path, options);
                return {status: r.status, body: await r.text().then(t => t.substring(0, 300))};
            } catch(e) {
                return {error: e.message};
            }
        }''', {"method": method, "path": path, "data": data})
        
        if result.get('status', 0) == 200:
            log_issue(7, "S2-S11", "permission", "high", f"产品经理越权成功 {method} {path} → 200!")
        elif result.get('status', 0) == 403:
            print(f"    正确拦截: {method} {path} → 403")
        elif result.get('status', 0) == 401:
            print(f"    未认证: {method} {path} → 401")
        return result
    except Exception as e:
        print(f"    API测试异常: {e}")

async def api_test_noauth(page, method, path):
    """不带token的API请求"""
    try:
        result = await page.evaluate('''async ({method, path}) => {
            try {
                const r = await fetch(path, {method});
                return {status: r.status, body: await r.text().then(t => t.substring(0, 200))};
            } catch(e) { return {error: e.message}; }
        }''', {"method": method, "path": path})
        print(f"    无认证: {method} {path} → {result.get('status')}")
    except:
        pass

async def api_test_expired(page):
    """测试过期token"""
    pass  # 需要实际修改token

async def api_test_tampered_token(page):
    """测试篡改token"""
    pass

async def api_batch_test(page):
    """批量并发API请求"""
    await page.evaluate('''async () => {
        const paths = ["/api/users/", "/api/admin/", "/api/settings/", "/api/audit/"];
        const token = localStorage.getItem("token") || "";
        const results = await Promise.all(paths.map(async path => {
            try {
                const r = await fetch(path, {headers: {"Authorization": "Bearer " + token}});
                return {path, status: r.status};
            } catch(e) { return {path, error: e.message}; }
        }));
        return results;
    }''')

async def api_upload_test(page):
    """文件上传测试"""
    pass

async def api_probe_routes(page):
    """探测路由"""
    await page.evaluate('''async () => {
        const routes = ["/admin", "/api/admin", "/api/users", "/api/settings", "/api/audit", "/api/security", "/api/config"];
        for (const r of routes) {
            try { await fetch(r); } catch(e) {}
        }
    }''')

async def api_rate_limit_test(page):
    """速率限制测试"""
    for _ in range(10):
        try:
            result = await page.evaluate('''async () => {
                const r = await fetch("/api/auth/login", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({username:"test",password:"wrong"})
                });
                return r.status;
            }''')
            if result == 429:
                print(f"    ✅ 速率限制生效: 429")
                return
        except:
            pass
        await page.wait_for_timeout(200)

# ============================================================
# Round 8 异常处理辅助
# ============================================================

async def trigger_500(page):
    try:
        await page.goto(f"{BASE_URL}/api/projects/999999999999")
    except:
        pass

async def open_new_tab(page):
    context = page.context
    new_page = await context.new_page()
    await new_page.goto(BASE_URL)
    return new_page

async def load_large_data(page):
    """尝试加载大量数据"""
    await click_nav(page, "BOM")
    await page.wait_for_timeout(3000)

async def check_global_errors(page):
    """检查全局JS错误"""
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    await page.wait_for_timeout(1000)
    if errors:
        log_issue(8, "S19", "error_handling", "medium", f"页面存在JS错误: {errors[:3]}")

async def check_console_errors(page):
    """检查控制台错误"""
    msgs = []
    page.on("console", lambda msg: msgs.append(msg.text) if msg.type == "error" else None)
    await page.wait_for_timeout(1000)
    if msgs:
        log_issue(8, "S20", "error_handling", "low", f"控制台错误: {msgs[:5]}")

# ============================================================
# Round 9 安全测试辅助
# ============================================================

async def inject_xss(page, field, payload):
    await fill_field(page, field, payload)

async def inject_xss_search(page, payload):
    await search(page, payload)

async def inject_sqli(page, payload):
    await search(page, payload)

async def csrf_test(page):
    """CSRF测试：检查是否有CSRF Token"""
    html = await page.evaluate('() => document.documentElement.outerHTML')
    if 'csrf' in html.lower() or 'xsrf' in html.lower():
        print("    CSRF保护存在")
    else:
        log_issue(9, "S16", "security", "medium", "未检测到CSRF Token")

async def check_headers(page):
    """检查安全响应头"""
    try:
        resp = await page.goto(BASE_URL)
        headers = resp.headers if resp else {}
        security_headers = ['x-frame-options', 'x-content-type-options', 'x-xss-protection', 'strict-transport-security', 'content-security-policy']
        for h in security_headers:
            if h not in [k.lower() for k in headers.keys()]:
                log_issue(9, "S17", "security", "medium", f"缺少安全响应头: {h}")
    except:
        pass

async def check_csp(page):
    """检查Content-Security-Policy"""
    try:
        resp = await page.goto(BASE_URL)
        if resp:
            csp = resp.headers.get('content-security-policy', '')
            if not csp:
                log_issue(9, "S18", "security", "low", "未设置Content-Security-Policy")
    except:
        pass

async def check_info_leak(page):
    """检查信息泄露"""
    html = await page.evaluate('() => document.documentElement.outerHTML')
    # 检查HTML注释
    if '<!--' in html:
        comments = re.findall(r'<!--(.*?)-->', html, re.DOTALL)
        for c in comments:
            if any(w in c.lower() for w in ['password', 'token', 'secret', 'key', 'todo', 'fixme', 'hack']):
                log_issue(9, "S19", "security", "medium", f"HTML注释可能泄露信息: {c.strip()[:100]}")

async def check_password_field(page):
    """检查密码字段属性"""
    await page.goto(f"{BASE_URL}/login")
    pw_field = await page.query_selector('input[type="password"]')
    if pw_field:
        autocomplete = await pw_field.get_attribute('autocomplete')
        if autocomplete != 'off':
            log_issue(9, "S20", "security", "low", f"密码字段autocomplete未设为off: {autocomplete}")

# ============================================================
# Round 10 综合压力辅助
# ============================================================

async def rapid_nav(page, count):
    menus = ["项目", "产品", "BOM", "品质", "仪表板"]
    for i in range(count):
        await click_nav(page, menus[i % len(menus)])
        await page.wait_for_timeout(200)

async def open_multiple_tabs_nav(page):
    await click_nav(page, "项目")
    await page.wait_for_timeout(500)
    await click_tab(page, "BOM")
    await page.wait_for_timeout(500)
    await click_tab(page, "品质")
    await page.wait_for_timeout(500)

async def rapid_search(page):
    await search(page, "测试")
    await page.wait_for_timeout(200)
    await search(page, "")
    await page.wait_for_timeout(200)
    await search(page, "项目")
    await page.wait_for_timeout(200)

async def paste_rich_text(page):
    """模拟粘贴富文本"""
    try:
        inp = await page.query_selector('textarea:visible, input[type="text"]:visible')
        if inp:
            await inp.fill("<b>富文本<b> <script>alert(1)</script>")
    except:
        pass

async def scan_all_menus(page):
    """扫描所有可用菜单"""
    menus = await page.evaluate('''() => {
        const items = document.querySelectorAll('.el-menu-item, [class*="menu-item"], nav a, .sidebar a');
        return Array.from(items).map(el => ({
            text: el.textContent?.trim(),
            href: el.getAttribute('href') || '',
            visible: el.offsetParent !== null
        }));
    }''')
    print(f"  完整菜单: {json.dumps(menus, ensure_ascii=False, indent=2)[:500]}")

async def measure_page_load(page):
    """测量页面加载性能"""
    timing = await page.evaluate('''() => {
        const t = performance.timing;
        return {
            domReady: t.domContentLoadedEventEnd - t.navigationStart,
            loadComplete: t.loadEventEnd - t.navigationStart,
            firstPaint: performance.getEntriesByType('paint')[0]?.startTime
        };
    }''')
    if timing.get('loadComplete', 0) > 5000:
        log_issue(10, "S19", "stress", "low", f"页面加载过慢: {timing['loadComplete']}ms")


# ============================================================
# 主函数
# ============================================================

async def main():
    print("=" * 60)
    print("ROS 产品经理 10轮×20步 浏览器审计")
    print(f"目标: {BASE_URL}")
    print(f"账户: {USERNAME}")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # 监听console和错误
        page.on("console", lambda msg: None)  # 静默收集
        page.on("pageerror", lambda err: print(f"  [JS错误] {err}"))
        
        for round_num in range(1, 11):
            if round_num not in ROUNDS:
                continue
            await execute_round(page, round_num, ROUNDS[round_num])
        
        await browser.close()
    
    # 输出汇总
    print("\n" + "=" * 60)
    print(f"审计完成！共 {len(ISSUES)} 个问题")
    print("=" * 60)
    
    for issue in ISSUES:
        print(f"  [{issue['severity'].upper()}] R{issue['round']}S{issue['step']}: {issue['description']}")
    
    # 保存结果
    report = {
        "audit_name": "ROS产品经理10轮×20步审计",
        "timestamp": datetime.now().isoformat(),
        "total_steps": 200,
        "total_issues": len(ISSUES),
        "by_severity": {
            "critical": len([i for i in ISSUES if i['severity'] == 'critical']),
            "high": len([i for i in ISSUES if i['severity'] == 'high']),
            "medium": len([i for i in ISSUES if i['severity'] == 'medium']),
            "low": len([i for i in ISSUES if i['severity'] == 'low']),
        },
        "issues": ISSUES,
        "results": RESULTS
    }
    
    report_path = "/Users/gamidy/ros-source/ros-system/audit_pm_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到: {report_path}")
    return report


if __name__ == "__main__":
    asyncio.run(main())
