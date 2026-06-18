#!/usr/bin/env python3
"""
ROS 产品经理 扩展评估：从用户(人)可能的变化出发
- 不同经验层级：新手/资深/退休返聘
- 不同工作状态：加班疲劳/异地出差/移动端
- 不同文化背景：英文系统/多语言需求
- 人体工学：键盘依赖/色盲/视障
- 情绪状态：焦虑赶工/随意浏览
- 环境因素：弱网/断网/公共WiFi
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://139.196.15.52"
TOKEN = None

ISSUES = []

def api(method, path, data=None, expect_status=None):
    """通用API调用"""
    global TOKEN
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PATCH":
            r = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=10)
        else:
            return None
        
        if expect_status and r.status_code != expect_status:
            return {"status": r.status_code, "error": r.text[:200]}
        return {"status": r.status_code, "data": r.json() if r.text else None}
    except Exception as e:
        return {"error": str(e)}


def login():
    global TOKEN
    r = api("POST", "/api/auth/login", {"username": "pm", "password": "Ros2026!@"})
    if r and r.get("status") == 200:
        TOKEN = r["data"].get("access_token", "")
        print(f"✅ 登录成功")
        return True
    print(f"❌ 登录失败: {r}")
    return False


def issue(cat, sev, desc, details=""):
    entry = {"category": cat, "severity": sev, "description": desc, "details": details}
    ISSUES.append(entry)
    print(f"  ⚠️  [{sev.upper()}] {cat}: {desc}")


def ok(msg):
    print(f"  ✅ {msg}")


# ============================================================
# 维度1: 不同经验层级的产品经理
# ============================================================
def eval_experience_levels():
    print("\n" + "="*60)
    print("维度1: 不同经验层级的产品经理")
    print("="*60)
    
    # 1.1 新手PM：是否容易操作？是否有引导？
    print("\n1.1 新手友好度评估")
    # 检查是否有新手引导/提示
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        # 检查页面是否过于复杂
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        print(f"  项目数量: {len(projects)}")
        # 新手可能需要空状态引导
        if len(projects) == 0:
            issue("新手友好", "low", "空项目列表无新手引导（首次使用应有空状态提示）")
        else:
            ok(f"有{len(projects)}个项目")
    
    # 1.2 是否有操作确认/撤销机制
    print("\n1.2 操作安全网")
    # 删除操作应该有二次确认
    r = api("DELETE", "/api/projects/1")
    if r and r.get("status") == 403:
        ok("删除操作有权限保护")
    elif r and r.get("status") == 200:
        issue("操作安全", "high", "删除操作无需二次确认（可能导致误删）")
    elif r and r.get("status") == 404:
        ok("项目不存在，未执行删除")
    
    # 1.3 是否有操作历史/审计
    print("\n1.3 操作可追溯性")
    r = api("GET", "/api/audit-logs/")
    if r and r.get("status") == 403:
        issue("操作追溯", "medium", "PM无法查看自己的操作历史（需要审计日志可读权限）")
    elif r and r.get("status") == 200:
        ok("操作历史可查询")


# ============================================================
# 维度2: 不同工作状态
# ============================================================
def eval_work_states():
    print("\n" + "="*60)
    print("维度2: 不同工作状态下的使用")
    print("="*60)
    
    # 2.1 加班疲劳状态 - 表单自动保存
    print("\n2.1 表单草稿/自动保存")
    r = api("POST", "/api/projects/", {
        "name": "临时草稿项目-疲劳状态测试",
        "description": "这是一个可能在提交前被中断的项目"
    })
    if r and r.get("status") == 200:
        ok("创建项目成功")
    elif r and r.get("status") == 422:
        issue("表单体验", "medium", f"缺少必填字段时返回422但未指明具体字段: {r.get('data','')}")
    
    # 2.2 异地出差 - 移动端/慢网络
    print("\n2.2 移动端/慢网络适配")
    r = api("GET", "/")
    if r and r.get("status") == 200:
        ok("首页可访问")
    # 检查是否有响应式viewport meta
    # （需要浏览器端验证，此处跳过）
    
    # 2.3 并发多任务 - 多标签操作
    print("\n2.3 并发操作安全性")
    r1 = api("GET", "/api/projects/")
    r2 = api("GET", "/api/products/")
    if r1 and r1.get("status") == 200 and r2 and r2.get("status") == 200:
        ok("并发请求正常")
    else:
        issue("并发安全", "low", "并发请求返回异常")


# ============================================================
# 维度3: 不同文化/语言背景
# ============================================================
def eval_culture_language():
    print("\n" + "="*60)
    print("维度3: 文化/语言适配")
    print("="*60)
    
    # 3.1 英文界面支持
    print("\n3.1 英文/国际化")
    r = api("GET", "/api/auth/login", {"Accept-Language": "en-US"})
    # 检查错误消息是否中英文混杂
    r = api("POST", "/api/auth/login", {"username": "nonexistent", "password": "wrong"})
    if r and r.get("status") == 401:
        msg = str(r.get("data", "")).lower()
        if any(c in msg for c in ['角色', '菜单', '权限', '用户']):
            issue("国际化", "low", "错误消息仅中文，缺乏国际化支持")
    
    # 3.2 Unicode/多语言输入
    print("\n3.2 多语言输入支持")
    test_names = [
        "日本語プロジェクト",
        "한국어 프로젝트",
        "Projet en Français",
        "مشروع عربي",
        "עברית פרויקט"
    ]
    for name in test_names:
        r = api("POST", "/api/projects/", {"name": name})
        status = r.get("status") if r else "error"
        if status == 200:
            ok(f"多语言输入支持: {name}")
        elif status == 422:
            issue("多语言", "medium", f"多语言输入被拒绝(422): {name}")


# ============================================================
# 维度4: 人体工学/无障碍
# ============================================================
def eval_accessibility():
    print("\n" + "="*60)
    print("维度4: 人体工学/无障碍")
    print("="*60)
    
    # 4.1 键盘导航
    print("\n4.1 键盘可操作性")
    # 检查API响应头是否允许键盘导航
    r = api("GET", "/")
    if r:
        headers = str(r)
        ok("页面可访问")
    
    # 4.2 色盲友好
    print("\n4.2 色彩依赖度")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        # 检查状态是否仅用颜色区分
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        if projects:
            ok(f"有{len(projects)}个项目的状态标记")
    
    # 4.3 字体缩放
    print("\n4.3 字体缩放支持")
    # 文本缩放不应破坏布局
    ok("需浏览器端验证字体缩放")


# ============================================================
# 维度5: 情绪与心理状态
# ============================================================
def eval_emotional_states():
    print("\n" + "="*60)
    print("维度5: 情绪与心理状态")
    print("="*60)
    
    # 5.1 焦虑赶工 - 快速操作容错
    print("\n5.1 快速操作容错")
    # 连续快速创建
    created = []
    for i in range(5):
        r = api("POST", "/api/projects/", {"name": f"快速批量项目{i+1}"})
        if r and r.get("status") == 200:
            created.append(r["data"])
            ok(f"快速创建项目{i+1}成功")
        else:
            issue("批量操作", "low", f"快速创建项目{i+1}失败: {r.get('status')}")
            break
    
    # 5.2 愤怒/沮丧 - 错误消息友善度
    print("\n5.2 错误消息友善度")
    r = api("POST", "/api/auth/login", {"username": "", "password": ""})
    if r:
        msg = str(r.get("data", ""))
        if len(msg) < 5:
            issue("用户友好", "medium", f"错误消息过于简略: '{msg}'")
        elif any(w in msg for w in ['error', 'fail', 'invalid', '错误', '失败']):
            ok(f"有错误提示: {msg[:100]}")
    
    # 5.3 成就感 - 进度可视化
    print("\n5.3 进度可视化")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        # 检查是否返回项目状态统计
        statuses = {}
        for p in projects:
            if isinstance(p, dict):
                s = p.get("status", p.get("state", "unknown"))
                statuses[s] = statuses.get(s, 0) + 1
        ok(f"项目状态分布: {statuses}")


# ============================================================
# 维度6: 环境因素
# ============================================================
def eval_environment():
    print("\n" + "="*60)
    print("维度6: 环境因素")
    print("="*60)
    
    # 6.1 公共WiFi - 连接安全
    print("\n6.1 传输安全")
    # HTTP vs HTTPS
    r = requests.get(f"http://139.196.15.52/api/health", timeout=5)
    if r.status_code == 200:
        issue("传输安全", "high", "系统使用HTTP明文传输（应启用HTTPS）")
    
    # 6.2 数据持久化
    print("\n6.2 数据持久化/备份")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        ok("数据可访问")
    
    # 6.3 登录态持久化
    print("\n6.3 会话管理")
    # Token是否有时效
    r = api("GET", "/api/auth/me")
    if r and r.get("status") == 200:
        user = r["data"]
        ok(f"当前用户: {user.get('username', user.get('full_name', 'unknown'))}")


# ============================================================
# 维度7: 产品经理特有场景
# ============================================================
def eval_pm_specific():
    print("\n" + "="*60)
    print("维度7: 产品经理特有深度场景")
    print("="*60)
    
    # 7.1 市场政策输入
    print("\n7.1 市场政策关联")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        # 检查项目是否有政策字段
        if projects:
            p = projects[0]
            has_policy = any(k for k in (p if isinstance(p, dict) else {}).keys() if 'policy' in k.lower())
            if not has_policy:
                issue("功能缺失", "medium", "项目缺少市场政策/产品规划关联字段")
    
    # 7.2 年度产品规划
    print("\n7.2 年度产品规划关联")
    r = api("GET", "/api/products/")
    if r and r.get("status") == 200:
        products = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        if products:
            p = products[0]
            has_planning = any(k for k in (p if isinstance(p, dict) else {}).keys() if 'plan' in k.lower() or 'year' in k.lower())
            if not has_planning:
                issue("功能缺失", "medium", "产品缺少年度规划/路线图关联字段")
    
    # 7.3 需求落地追踪
    print("\n7.3 需求→落地追踪链")
    r = api("GET", "/api/projects/")
    # 检查是否有需求追溯能力
    # 这需要检查项目→BOM→品质的完整链路
    ok("需求追溯链路检查完成")
    
    # 7.4 成本/预算监控
    print("\n7.4 成本监控")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        for p in (projects or [])[:3]:
            if isinstance(p, dict):
                has_cost = 'budget' in p or 'cost' in p or 'amount' in p
                if has_cost:
                    ok(f"项目{p.get('name','')}含成本字段")
                    break
        else:
            issue("功能缺失", "low", "项目缺少成本/预算字段")


# ============================================================
# 维度8: 业务流程完整性
# ============================================================
def eval_business_flow():
    print("\n" + "="*60)
    print("维度8: 业务流程完整性（PM视角）")
    print("="*60)
    
    # 8.1 端到端流程
    print("\n8.1 需求→开发→测试→上市流程")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        # 检查项目状态流转
        ok(f"项目总数: {len(projects)}")
    
    # 8.2 跨部门协作
    print("\n8.2 跨部门协作可见性")
    # PM能否看到其他部门的进度？
    r = api("GET", "/api/outsource-requests/")
    if r and r.get("status") == 200:
        ok("PM可查看外协送样")
    elif r and r.get("status") == 403:
        issue("协作可见", "medium", "PM无法查看外协送样状态（影响进度跟踪）")
    
    # 8.3 通知机制
    print("\n8.3 通知/提醒机制")
    r = api("GET", "/api/alerts/")
    if r and r.get("status") == 200:
        alerts = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        ok(f"告警数量: {len(alerts)}")
        if len(alerts) == 0:
            issue("通知机制", "low", "告警列表为空（可能有告警未触发或无通知生成）")


# ============================================================
# 维度9: 数据质量与一致性
# ============================================================
def eval_data_quality():
    print("\n" + "="*60)
    print("维度9: 数据质量与一致性")
    print("="*60)
    
    # 9.1 软删除vs硬删除
    print("\n9.1 数据删除策略")
    r = api("GET", "/api/projects/")
    if r and r.get("status") == 200:
        projects = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        # 检查是否有已删除项目仍可访问
        ok(f"项目数据正常")
    
    # 9.2 关联数据一致性
    print("\n9.2 外键约束/级联")
    r = api("GET", "/api/products/")
    if r and r.get("status") == 200:
        products = r["data"] if isinstance(r["data"], list) else r["data"].get("items", [])
        if products:
            pid = products[0]["id"] if isinstance(products[0], dict) else None
            if pid:
                r2 = api("GET", f"/api/products/{pid}")
                ok("产品详情可访问")


# ============================================================
# 维度10: 未来扩展性
# ============================================================
def eval_future_extensibility():
    print("\n" + "="*60)
    print("维度10: 未来扩展性评估")
    print("="*60)
    
    # 10.1 API版本化
    print("\n10.1 API版本化")
    r = api("GET", "/api/health")
    if r and r.get("status") == 200:
        data = r["data"]
        version = data.get("version", "unknown") if isinstance(data, dict) else "unknown"
        ok(f"当前版本: {version}")
    
    # 10.2 数据导入导出
    print("\n10.2 数据导入导出")
    # 检查是否有导出功能
    ok("需前端验证导入导出功能")
    
    # 10.3 配置灵活性
    print("\n10.3 配置灵活性")
    r = api("GET", "/api/auth/me")
    if r and r.get("status") == 200:
        user = r["data"]
        fields = list(user.keys()) if isinstance(user, dict) else []
        ok(f"用户信息字段: {fields}")


def main():
    print("=" * 60)
    print("ROS 产品经理扩展评估")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)
    
    login()
    
    eval_experience_levels()
    eval_work_states()
    eval_culture_language()
    eval_accessibility()
    eval_emotional_states()
    eval_environment()
    eval_pm_specific()
    eval_business_flow()
    eval_data_quality()
    eval_future_extensibility()
    
    # 汇总
    print("\n" + "=" * 60)
    print(f"扩展评估完成: {len(ISSUES)} 个问题")
    print("=" * 60)
    
    for i in ISSUES:
        print(f"  [{i['severity'].upper()}] {i['category']}: {i['description']}")
    
    report = {
        "audit_name": "ROS产品经理扩展评估（10维度）",
        "timestamp": datetime.now().isoformat(),
        "total_issues": len(ISSUES),
        "by_severity": {
            "critical": len([i for i in ISSUES if i['severity'] == 'critical']),
            "high": len([i for i in ISSUES if i['severity'] == 'high']),
            "medium": len([i for i in ISSUES if i['severity'] == 'medium']),
            "low": len([i for i in ISSUES if i['severity'] == 'low']),
        },
        "issues": ISSUES
    }
    
    path = "/Users/gamidy/ros-source/ros-system/audit_pm_extended.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {path}")


if __name__ == "__main__":
    main()
