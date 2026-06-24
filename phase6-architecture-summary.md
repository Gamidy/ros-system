# ROS Phase 6：研发数字主线（Digital Thread）

> **架构摘要文档**
> 编写人：系统架构师 + AI-A
> 日期：2026-06-24
> 完整详细规划：`phase6-plan.md`（1415行）

---

## 一、为什么 Phase 6 必须做数字主线？

ROS 已完成 Phase 1-5，核心功能包括 ProductPlan、Workflow、Event、Saga、MQ/MRC/CDF、Multi-Tenant、Dashboard，但**实验 → 认证 → 变更 → 量产** 这条研发主线未打通。

**当前最大风险不是"没有功能"，而是"功能很多，但业务价值链是否闭环"。**

ROS 与真正 PLM 系统的最大差距正在于此。

---

## 二、数字主线全景

```
ProductPlan ──► Project ──► BOM
    │              │           │
    │   ┌──────────┘           │
    │   ▼                      ▼
    │  Test Center ──► Certification Center ──► ECR/ECO ──► Mass Production
    │  (实验中心)       (认证中心)              (变更控制)      (量产)
    │      │                │                     │
    │      │    ┌───────────┘                     │
    │      │    ▼                                 ▼
    │      └──► CDF (关键元器件清单) ◄───── 认证失效自动识别
    │
    └─── 实验必过条件绑定 ──► 方案评审门禁 ──► Gate 点亮条件
```

---

## 三、三个模块设计

### 模块1：实验中心（Test Center）

**边界**：实验项目库 → 实验方案 → 排期执行 → 实验判定

| 新表 | 说明 |
|:-----|:-----|
| `test_libraries` | 实验项目库（性能/能效/噪音风量/凝露/潮态/安全/EMC/寿命） |
| `test_standards` | 实验标准库（小米/格力/客户标准） |
| `test_plan_items` | 实验方案条目（一个方案包含多个实验项目） |
| `test_schedules` | 实验排期管理 |
| `test_judgments` | 实验判定结果（pass/fail + 测试数据） |
| `product_plan_test_bindings` | ProductPlan 方案评审与实验绑定 |

**核心 API**：35 个端点

- 实验库 CRUD + 标准库 CRUD
- 实验方案创建 + 排期日历
- 实验判定提交 + 合规检查
- ProductPlan 实验绑定 + 门禁检查

---

### 模块2：认证中心（Certification Center）

**边界**：认证申请 → 测试 → 发证 → 维护 → 到期提醒

| 新表 | 说明 |
|:-----|:-----|
| `cert_applications` | 认证申请（CCC/CB/CE/UL/SAA/SASO/NOM 等） |
| `cert_certificates` | 证书生命周期管理 |
| `cert_market_requirements` | 目标市场认证要求配置 |
| `cert_change_impacts` | 变更认证影响分析记录 |

**核心 API**：20 个端点

- 认证申请生命周期（提交→测试→发证→到期）
- 证书管理（续期/变更/注销）
- 目标市场自动匹配认证类型
- CDF 关键元器件自动提取

---

### 模块3：变更控制中心（ECR/ECO）

**边界**：ECR 提交 → 影响分析 → 审批 → ECO 发布 → BOM 应用

| 新表 | 说明 |
|:-----|:-----|
| `eco_items` | ECO 变更明细（BOM 变更行：add/remove/replace） |
| `eco_impact_analyses` | 变更影响分析记录（性能/成本/项目/生产） |
| `eco_cert_impact_results` | 认证失效自动识别结果 |
| `ecr_test_bindings` | ECR 与实验/认证的关联 |

**核心 API**：25 个端点

- ECR 增强（状态机含影响分析阶段）
- 变更影响分析引擎（性能/成本/项目/生产四维）
- 认证失效自动检测
- ECO→BOM 自动应用

---

## 四、7 大集成点（数字主线的真正价值）

### ① ProductPlan → 实验中心（方案评审门禁）
产品经理在 ProductPlan 中定义实验必过条件。方案评审提交时，系统自动检查绑定实验是否全部通过。不过 → 阻止评审。

### ② Project → 实验中心（Gate 条件绑定）
M4/M5/M6 Gate 点亮前检查实验判定。实验 NG → Gate 阻塞 → Dashboard 显示阻塞原因。

### ③ 认证中心 → 实验中心（认证测试自动创建）
认证申请进入 testing 阶段时，自动创建测试工单，结果回流到认证判定。

### ④ ECR/ECO → 认证中心（认证失效自动识别）⭐
**Phase 6 最关键的数字主线打通点。**

```
规则1: 变更物料在 CDF 清单中 → 认证失效
规则2: 安全件/EMC件变更 → 需重新测试
规则3: 物料市场认证标记变更 → 需更新申报
规则4: 供应商变更 → 认证需 update/redeclare

输出到 Dashboard 红色告警："认证失效风险"
```

### ⑤ ECO → BOM（变更自动应用）
ECO 发布后，系统自动将 `eco_items` 应用到 BOM 树，BOM 版本升级。

### ⑥ CDF 联动（贯穿三模块）
关键元器件在实验中心→认证中心→ECR/ECO 三模块中流转：
- 实验中心：CDF 物料自动标记为 high priority
- 认证中心：自动提取 CDF 物料关联认证
- ECR/ECO：CDF 物料变更 → 自动触发认证失效检测

### ⑦ Dashboard 看板增强
| 新增风险卡片 | 说明 |
|:------------|:-----|
| 实验合规红灯 | ProductPlan 绑定实验未通过 |
| 认证即将到期 | 证书 30 天内到期预警 |
| 认证失效风险 | ECO 变更导致认证失效 |
| 待实施 ECO | 已发布未实施的变更 |
| Gate 阻塞 | 实验未通过导致项目停滞 |

---

## 五、实施路线图

```
S1 (2周)          S2 (2周)           S4 (2周)
实验中心          变更控制           数字主线集成
                                    ┌─────────────────┐
• 实验项目库 CRUD  • ECR 增强        │ • 实验绑定+门禁  │
• 标准库管理       • 影响分析引擎     │ • 认证失效自动识别│
• 排期日历        • ECO→BOM明细     │ • ECO→BOM自动应用│
• 实验判定        • 影响分析API      │ • Dashboard看板  │
• MQ验证增强                         │ • 全链路测试     │
                                    └─────────────────┘
         ↕ 可并行
    S3 (2周) 认证中心
    • 认证申请增强
    • 证书生命周期管理
    • 目标市场匹配
    • CDF自动提取
```

**先做实验中心的理由**：
1. 依赖最少，可独立运行
2. ProductPlan 联动需求最急（当前业务阻塞点）
3. 认证和变更都依赖实验数据作为基础输入
4. CRUD 为主，可在 1-2 周内快速交付

**总周期**：8-10 周

---

## 六、与现有系统集成方式

| 现有模块 | 集成方式 |
|:---------|:---------|
| **ProductPlan** | 方案评审阶段插入实验合规检查钩子 |
| **Project** | Gate 条件增强引用实验判定 |
| **BOM** | ECO→BOM 自动应用 + Part CDF 标记匹配认证 |
| **Dashboard** | 新增 5 个风险卡片 + 预警规则 |
| **Event Bus** | 新增事件类型 plan.tech_input_check、cert.invalidated 等 |
| **RBAC** | 扩展 MENU_PERMISSIONS（新增 test_library、cert_certificates、change_impact 等子菜单） |

---

## 七、交付物总览

| 指标 | 数据 |
|:-----|:----:|
| 新表 | 15 张 |
| 新 API 端点 | ~80 个 |
| 新前端页面 | ~20 个 |
| 新增后端文件 | ~10 个 |
| 新增前端文件 | ~15 个 |
| 核心业务规则引擎 | 2 个（影响分析引擎 + 认证失效引擎） |

---

## 八、Phase 6 完成后 ROS 形态

```
ProductPlan → Project → BOM → Test Center → Certification → ECR/ECO → Mass Production
     ↑           ↑        ↑         ↑              ↑            ↑           ↑
     └───────────┴────────┴─────────┴──────────────┴────────────┴───────────┘
                              数字主线贯通
```

届时 Phase 7（AI-A 执行者池）才能真正有意义——Agent 能接管：
- 实验排期调度
- 实验判定辅助
- 认证匹配推荐
- 风险预警推送
- 变更影响分析

而不是在价值链未闭环的情况下做辅助工作。
