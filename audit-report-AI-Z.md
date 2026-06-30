# ROS 系统全面审核报告（AI-Z 角色）

**审核日期**: 2026-06-30  
**审核范围**: 品类约束修改、中国市场移除、角色权限、安全漏洞、UI/UX一致性  
**审核文件数**: 18+ 前端文件 + 6 后端文件 + 1 路由文件 + 1 auth store  
**工作目录**: /Users/gamidy/ros-source/ros-system

---

## 目录

1. [品类约束修改审核](#1-品类约束修改审核)
2. [中国市场移除审核](#2-中国市场移除审核)
3. [角色权限审核](#3-角色权限审核)
4. [安全漏洞审核](#4-安全漏洞审核)
5. [UI/UX一致性审核](#5-uiux一致性审核)
6. [总结与修复优先级](#6-总结与修复优先级)

---

## 1. 品类约束修改审核

### 1.1 原始8文件核查

| # | 文件 | 位置 | 修改内容 | 状态 |
|---|------|------|----------|------|
| 1 | ReviewTemplateView.vue | L220-222 | productTypeOptions 仅 split_wall | ✅ 正确 |
| 2 | OverviewMarketTab.vue | L376 | structureTypes 仅 ['分体壁挂'] | ✅ 正确 |
| 3 | PlanTemplateView.vue | L7, L58 | 两个 el-select 仅 分体壁挂 | ✅ 正确 |
| 4 | MarketMgmt.vue | L193 | structure_type 仅 分体壁挂 | ✅ 正确 |
| 5 | AdminConfig.vue | L261 | shortNameRows 仅 分体式壁挂机 | ✅ 正确 |
| 6 | CostAlertRuleView.vue | L203-205 | projectTypeMap 仅 split_wall | ✅ 正确 |
| 7 | DFMReportTab.vue | L125 | 仅 split_ac | ✅ 正确 |
| 8 | DFMChecklistTab.vue | L82 | 仅 split_ac | ✅ 正确 |

**结论**: 原始8个文件的品类约束修改 **全部正确应用**，无遗漏。

### 1.2 ⚠️ 新增发现：3个未列入清单的文件也有限制

在审核过程中发现以下3个文件也包含了品类约束，但**未在原始修改列表中提及**：

| # | 文件 | 位置 | 内容 | 状态 |
|---|------|------|------|------|
| 1 | **RequirementSubmit.vue** | L48-50 | `<el-option label="壁挂分体机" value="壁挂分体机" />` | ⚠️ 已约束但值有差异 |
| 2 | **ProductPlanningCenter.vue** | L259-263 | `<el-option label="壁挂分体机" value="split_wall" />` | ⚠️ 已约束但值有差异 |
| 3 | **CompetitorStandalone.vue** | L651 | `productTypes = ['壁挂分体机']` | ⚠️ 已约束但值有差异 |

### 1.3 🔴 严重问题：产品类型值不一致

系统中有 **5种不同的产品类型标识方式**，将导致数据库数据不一致：

| 系统中使用的值 | 文件来源 | 含义 |
|------|------|------|
| `split_wall` | ReviewTemplateView, CostAlertRuleView, ProductPlanningCenter | 分体壁挂 |
| `分体壁挂` | PlanTemplateView, MarketMgmt, OverviewMarketTab | 分体壁挂 |
| `壁挂分体机` | RequirementSubmit, CompetitorStandalone | 壁挂分体机 |
| `分体式壁挂机` | AdminConfig (shortNameRows) | 分体式壁挂机 |
| `split_ac` | DFMReportTab, DFMChecklistTab | 分体空调(←不同品类!) |

**关键问题**:
- **RequirementSubmit.vue** 使用中文 `壁挂分体机` 作为 value（非代码值），而 ProductPlanningCenter.vue 使用 `split_wall` 作为 value（代码值）。两种值会被存入数据库的不同字段中，导致查不到、对不上。
- **DFM模块** 使用 `split_ac`（分体空调），与 PM 模块的 `split_wall`（分体壁挂）**不是同一概念**——分体空调包括壁挂、柜机、天花、风管等多种结构。

### 1.4 🟡 遗漏检查：SafetyInspectionTab.vue

**文件**: `/views/safety/SafetyInspectionTab.vue` (L136)  
**问题**: 该处为 `<el-input>` 自由文本输入框，`:placeholder="如 分体式空调"`，没有任何类型约束。虽然产品类型是该处的一个自由文本字段（applicable_product_type），但如果需要统一约束，此处是遗漏点。

---

## 2. 中国市场移除审核

### 2.1 原始3文件核查

| # | 文件 | 原始位置 | 修改内容 | 状态 |
|---|------|---------|----------|------|
| 1 | PlanTemplateView.vue | L9-17, L66-74 | 两个市场下拉移除了"中国" | ✅ 确认移除 |
| 2 | CrawlAdminView.vue | L311-319 | MARKET_OPTIONS 移除 `{code:'CN', label:'中国'}` | ✅ 确认移除 |
| 3 | CertificationsView.vue | L25-34(筛选), L84-92(新建弹窗) | 移除"中国"选项 | ✅ 确认移除 |

### 2.2 额外核查

对整个 `frontend/src/` 目录下的 `.vue` 和 `.ts` 文件进行了 **"中国" 和 "CN" 关键词全量搜索**，未发现任何残留的中国市场选项。

**结论**: 中国市场移除 **✅ 完成，无遗漏**。

---

## 3. 角色权限审核

### 3.1 权限架构总览

```
┌─────────────────────────────────────────────────┐
│ 前端 (Vue Router)                                │
│  router.beforeEach → authStore.hasRouteAccess()  │
│     ↓                                            │
│  authStore.fetchUser() → GET /api/auth/me        │
│     ↓                                            │
│  后端 auth.py → _enrich_user_out()               │
│     → get_allowed_paths(role)                    │
│     → permissions_data.py (ROLE_MENU_MAP)        │
│     → 返回 allowed_paths[] 给前端                 │
│     ↓                                            │
│  hasRouteAccess() 精确匹配+前缀匹配               │
│  无权限 → 重定向到 /dashboard                     │
└─────────────────────────────────────────────────┘
```

**架构评价**: 权限架构设计合理。前端不存储全局角色权限表，由后端动态下发 allowed_paths，避免了前端权限泄露。

### 3.2 8个角色账号权限验证

| 用户 | 角色 | 预期菜单 | 对应 MENU_GROUPS | 状态 |
|------|------|----------|-----------------|------|
| pm/pm123 | product_manager | 驾驶舱, 策划与立项(全部), 验证合规(部分), 供应链与成本, 系统(部分) | dashboard, pm-workspace, competitor_bench, market_mgmt, product-plans, cert-*, cost-accounting | ✅ |
| se/se123 | systems_engineer | 驾驶舱, 研发执行(部分), 验证合规(部分) | dashboard, products, tests, dfm-checklist, dfm-reports, cert-*, ecr/eco | ✅ |
| rd/rd123 | rd_director | 全部研发, 研发总监驾驶舱, 智能决策看板 | dashboard, rd_dashboard, risk-dashboard, products, projects, tests, cert-*, cost-accounting, inventory | ✅ |
| proc/proc123 | procurement | 驾驶舱, 采购+外协+库存 | dashboard, purchases, outsource-*, inventory, cert-* | ✅ |
| qe/qe123 | quality_engineer | 驾驶舱, 质量, 测试, DFM, 外协 | dashboard, quality, tests, dfm-*, outsource-*, cert-* | ✅ |
| gm/gm123 | general_manager | 全部菜单 | SUPER_ROLE → ALL_MENUS | ✅ |
| struct/struct123 | structural_engineer | 驾驶舱, 研发执行(部分), DFM | dashboard, products, dfm-*, cert-*, ecr/eco | ✅ |
| fin/fin123 | finance_manager | 驾驶舱, 成本核算, 库存 | dashboard, cost-accounting, inventory, bi-analytics | ✅ |

### 3.3 发现的问题

#### 🟡 rd_director 缺少 market_mgmt
`rd_director` 的角色菜单中没有 `market_mgmt`（市场管理），但产品经理拥有此权限。如果研发总监需要查看市场信息，这是遗漏。

#### 🟡 finance_manager 包含 inventory
财务经理拥有库存管理权限，这可能是为了成本核算所需。需确认业务上是否合理。

#### ✅ 系统设计优点
- 前端路由守卫与后端权限联动，权限数据不硬编码在前端
- 超级角色（admin/general_manager）自动放行
- require_menu() / require_role() / require_org_access() 三层授权机制

---

## 4. 安全漏洞审核

### 4.1 🔴 严重：后端无产品类型枚举校验

**问题描述**: 后端所有包含 `product_type` 字段的模型均使用无约束的 `Column(String(...))`，没有任何后端层面的枚举校验或 CHECK 约束。

```python
# 问题示例（所有模型文件）
product_type = Column(String(100), nullable=True, comment="产品类型")
```

**受影响模型**:
- `ProductPlanInitiation` (product_plan_subs.py)
- `ReviewTemplate` (review_template.py)
- `DFMReport` / `DFMScoreWeight` / `DFMCheckItem` (manufacturability.py)
- `Competitor` (competitor.py)
- `CompetitorSearchTerm` (competitor_search_term.py)

**风险**: 直接调用 API 可以写入任意 `product_type` 值，绕过前端约束。前端的品类限制仅是一层遮罩，不是真正的安全机制。

### 4.2 🟡 API 端点权限校验覆盖不全

**问题**: 搜索了 `backend/app/` 下所有使用 `require_menu()` 或 `require_role()` 的装饰器调用，发现：

- `permissions.py` 定义了 `require_menu()` 和 `require_role()` 函数
- `security.py` 中有 `get_current_user()` 和 `require_role()`
- 但搜索结果显示直接在这些装饰器中使用的 API 路由有限

这意味着**不是所有 API 端点都应用了权限检查**。部分端点可能仅依赖前端路由守卫，而没有后端校验。

### 4.3 🟢 安全措施评估

| 安全机制 | 状态 | 说明 |
|---------|------|------|
| JWT Token | ✅ | 使用 jose 库，含过期时间 |
| Token 黑名单 | ✅ | 支持登出使 token 失效 |
| 密码哈希 | ✅ | bcrypt |
| XSS 防护 | ✅ | sanitize_html() + sanitize_dict() |
| CSRF 防护 | ✅ | SameSite cookie + 双提交模式 |
| RBAC 权限模型 | ✅ | 三层授权 |
| 产品类型校验 | ❌ | **缺失，需添加** |
| API 全量覆盖校验 | ⚠️ | 部分覆盖 |

---

## 5. UI/UX一致性审核

### 5.1 🔴 产品类型标签不统一

系统中同一个产品类型使用了 **4种不同中文标签**：

| 标签 | 出现位置 |
|------|---------|
| **分体壁挂** | PlanTemplateView, MarketMgmt, OverviewMarketTab, CostAlertRuleView |
| **壁挂分体机** | RequirementSubmit, ProductPlanningCenter(操作界面), CompetitorStandalone |
| **分体式壁挂机** | AdminConfig(短名配置) |
| **分体空调** | DFMReportTab, DFMChecklistTab |

**影响**: 用户在系统不同页面看到同一产品的不同名称，造成混淆。

### 5.2 🟡 下拉值类型不一致

**问题**: 不同模块使用不同值类型发送到后端：

| 模块 | 下发的值 | 类型 |
|------|---------|------|
| ProductPlanningCenter | `split_wall` | 代码值 (enum-like) |
| RequirementSubmit | `壁挂分体机` | 中文文本 |
| PlanTemplateView | `分体壁挂` | 中文文本 |
| MarketMgmt | `分体壁挂` | 中文文本 |

**风险**: 如果不同字段共用同一个查询条件，中文值和代码值会导致查询结果不匹配。

### 5.3 🟡 市场下拉值类型不一致

| 模块 | 下拉值格式 | 示例 |
|------|-----------|------|
| PlanTemplateView | 中文名 | `美国`, `欧盟` |
| CrawlAdminView | ISO代码 | `US`, `EU` |
| CertificationsView | ISO代码 | `EU`, `VN`, `TW` |

> PlanTemplateView 的市场值是直接当展示文本用（不发给后端做业务查询），所以影响有限。

### 5.4 🟡 已知问题的影响

| 已知问题 | 影响程度 | 说明 |
|---------|---------|------|
| 数据库数据为空 | 🔴 高 | 所有模块无数据可展示，无法验收 |
| rd_dashboard 空白 | 🟡 中 | 研发总监角色的核心功能不可用 |
| /api/product-requirements 404 | 🟡 中 | 需求管理功能不可用 |

---

## 6. 总结与修复优先级

### 6.1 修复优先级矩阵

| 优先级 | 问题 | 级别 | 影响范围 |
|--------|------|------|---------|
| **P0 立即** | 后端 product_type 字段添加枚举校验 | 安全 | 全系统 |
| **P0 立即** | 统一 product_type 的 value 标准为 `split_wall` | 数据一致性 | 7+文件 |
| **P1 高** | 统一产品类型中文标签 | UI/UX | 7+文件 |
| **P1 高** | API 端点全面应用 require_menu() | 安全 | 后端 |
| **P1 高** | 数据库数据修复 / 迁移 | 功能 | 全系统 |
| **P2 中** | rd_director 添加 market_mgmt 权限 | 权限 | 1个角色 |
| **P2 中** | SafetyInspectionTab 添加类型约束 | UI一致 | 1个文件 |
| **P3 低** | /api/product-requirements 后端实现 | 功能 | 1个API |

### 6.2 建议修复方案

#### P0: 后端添加产品类型枚举

在 `backend/app/core/` 下创建 `constants.py`:

```python
from enum import Enum

class ProductType(str, Enum):
    SPLIT_WALL = "split_wall"        # 分体壁挂
    # 后续扩展时在此添加

VALID_PRODUCT_TYPES = {e.value for e in ProductType}
```

然后在所有 API schema 中添加 validation:

```python
from app.core.constants import VALID_PRODUCT_TYPES

class PlanCreate(BaseModel):
    product_type: str = Field(..., min_length=1)
    
    @validator('product_type')
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v
```

#### P0: 统一前端 product_type 值

| 文件 | 当前值 | 目标值 |
|------|-------|-------|
| RequirementSubmit.vue L49 | `壁挂分体机` | `split_wall` (label不变) |
| CompetitorStandalone.vue L651 | `壁挂分体机` | `split_wall` |
| ProductPlanningCenter.vue L262 | `split_wall` | ✅ 已正确，仅确认 |
| PlanTemplateView.vue L7, L58 | `分体壁挂` | `split_wall` |
| MarketMgmt.vue L193 | `分体壁挂` | `split_wall` |
| OverviewMarketTab.vue L376 | `分体壁挂` | `split_wall` |

#### P1: 统一产品类型中文标签

统一为 **"分体壁挂"**：
- RequirementSubmit.vue: `壁挂分体机` → `分体壁挂`
- ProductPlanningCenter.vue: `壁挂分体机` → `分体壁挂`
- CompetitorStandalone.vue: `壁挂分体机` → `分体壁挂`

DFM模块的 `分体空调` / `split_ac` 暂保留，因为 DFM 范围可能确实包含所有分体空调类型。但建议添加说明注释。

### 6.3 总体评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 品类约束 | ⚠️ 7/10 | 前端约束完整，但后端缺失校验，值不统一 |
| 中国市场移除 | ✅ 10/10 | 彻底完成，无残留 |
| 角色权限 | ✅ 9/10 | 架构合理，仅 minor 遗漏 |
| 安全机制 | ⚠️ 6/10 | 基础安全机制完善，但缺少后端数据校验 |
| UI/UX 一致 | ⚠️ 5/10 | 产品类型标签/值不统一问题突出 |
| **总体** | **⚠️ 7.4/10** | **核心修改完成，但数据一致性和后端校验需修复** |

---

*报告生成: AI-Z 角色审核 | 审核范围: ROS 系统已完成工作*
