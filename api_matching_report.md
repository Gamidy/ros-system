# ROS 系统前后端功能匹配度交叉分析报告

**生成日期**: 2026-07-03  
**数据来源**: 
- 后端清单: `/Users/gamidy/ros-source/ros-system/backend_api_inventory.json` (693 endpoints)
- 前端清单: `/Users/gamidy/ros-source/ros-system/frontend_scan_result.json` (568 API call references, 108 routes)

---

## 一、总体概览

| 指标 | 数值 |
|---|---|
| 后端 API 端点总数 | **693** |
| 前端 API 调用引用总数 | **568** |
| 前端页面路由数 | **108** |
| ✅ 前后端匹配成功数 | ~291 (后端视角) / ~483 (前端视角) |
| ❌ **P0 - 前端调用缺后端API** | **85** |
| 🟡 **P1 - 后端孤岛API** | **242** |
| 🔄 **P2 - 路径不一致** | ~15 (含参数风格差异) |
| 🔴 **P3 - HTTP方法不匹配** | **33** |

---

## 二、后端 API 模块分布 (按文件/路径归类)

| 模块 | 端点数量 | 说明 |
|---|---|---|
| pm | 68 | 产品管理/提案/竞品对标 |
| projects | 46 | 项目管理(含任务/工时/风险) |
| other | 42 | 未分类(含部分 S2/CI v2) |
| product-plans | 39 | 产品策划 |
| s2-cert | 37 | S2 认证中心(后端已实现) |
| cost-accounting | 33 | 成本核算 |
| inventory | 33 | 库存管理 |
| admin | 32 | 系统管理配置 |
| purchases | 27 | 采购模块(订单/收货) |
| dfm | 20 | DFM可制造性分析 |
| safety | 20 | 安规管理 |
| bom | 19 | BOM物料管理(全部孤岛) |
| products | 17 | 产品主线 |
| target-markets | 16 | 目标市场 |
| auth | 15 | 认证授权 |
| certifications | 15 | 认证管理(旧) |
| eco | 15 | ECO变更指令 |
| quality | 15 | 质量管理 |
| outsource | 14 | 外协管理 |
| purchase-supplier | 14 | 供应商管理 |
| ecr | 12 | ECR变更申请 |
| tests | 12 | 实验与测试 |
| knowledge-base | 11 | 知识库 |
| approvals | 10 | 审批管理 |
| bi-analytics | 10 | BI分析 |
| dashboard | 10 | 驾驶舱 |
| process | 10 | 工艺管理 |
| cost-recalc | 9 | 成本重算 |
| gate-rules | 7 | 门禁规则 |
| prototypes | 7 | 样机管理 |
| purchase-rfq | 7 | 询比价 |
| cost-alert | 6 | 成本预警 |
| notifications | 6 | 通知 |
| standards | 6 | 标准知识库 |
| verification-requirements | 6 | 验证需求 |
| product-requirements | 6 | 产品需求 |
| events | 5 | 事件日志 |
| reviews | 4 | 复盘 |
| alerts | 3 | 预警体系 |
| plan-templates | 3 | 计划模板 |
| audit-logs | 2 | 审计日志 |
| review-templates | 2 | 复盘模板 |
| ai | 1 | AI配置 |
| tasks | 1 | 任务 |

---

## 三、问题清单

### P0 - 前端页面存在但后端没有对应 API（缺后端） — 85 项

| 模块 | 缺失数 | 关键缺失路径 |
|---|---|---|
| **ci-v2** (Saga/CI) | **22** | `/api/v2/risk/:ecrId`, `/api/v2/impact-graph/:ecrId`, `/api/v2/dashboard/*`, `/api/v2/events/*`, `/api/s2/change-impact/*` |
| **admin** | **10** | `/admin/ai-configs*`, `/admin/users`, `/admin/users/search` |
| **quality** | **9** | `/quality/dashboard`, `/quality/improvement-tasks*`(全部 CRUD), PATCH 方法缺失 |
| **bi-analytics** | **9** | `/bi/planning/kpi`, `/bi/planning/phase-distribution`, `/bi/planning/approval-timeline`, `/bi/cost/budget-vs-actual`, `/bi/cost/department-ratio` 等 |
| **tests** | **8** | `DELETE /tests/:id`, `POST /tests/verification-requirements`, `POST /tests/gate-rules`, `PUT /tests/:id`, test-requests/executions 等 |
| **pm** | **6** | `/pm/proposals/:draftId`, `/pm/proposals`, `/pm/market-presets`, `/pm/markets/energy-levels`, `/pm/crawls/logs` |
| **inventory** | **4** | `PATCH /inventory/:id`, `PATCH /inventory/warehouses/:id`, `PATCH /inventory/counts/:id`, `GET /inventory`(无前缀) |
| **product-plans** | **2** | `/product-plans/:id/knowledge`, `/product-plans/:id/costs` |
| **gate-rules** | **2** | `POST /gate-rules/:id/deactivate`, `POST /gate-rules/:id/activate` |
| **projects** | **1** | `PATCH /projects/gates/:gateId` |
| **certifications** | **1** | `PUT /certifications/prototypes/:id` |
| **prototypes** | **1** | `GET /prototypes/:id/test-timeline` |
| **verification-requirements** | **1** | `DELETE /verification-requirements/:id` |
| **target-markets** | **1** | `GET /target-markets/:id/certifications` |
| **review-templates** | **1** | `DELETE /review-templates/:id` |
| **knowledge-base** | **1** | `GET /kb/team-roles` |

### P1 - 后端有 API 但前端没有页面使用（孤岛API）— 242 项

| 模块 | 孤岛数 | 关键孤岛说明 |
|---|---|---|
| **s2-cert** | **36** | 后端37个端点中仅1个被前端调用(其他由S2 Vue页面直接调用但路径不匹配) |
| **pm** | **26** | 辅助配置类API未找到前端调用: `/pm/accessory-defaults`, `/pm/capacity-cost-config`, `/pm/cert-standards*`, `/pm/safety-compliance-standards`, `/pm/programs` 等 |
| **purchases** | **20** | `/purchases/orders*` 系列完整 CRUD 未找到前端调用 |
| **bom** | **19** | 全部19个BOM端点未被前端 `api/bom.ts` 或 Vue 组件直接调用 |
| **products** | **17** | `/products*` 系列未被前端调用 |
| **projects** | **17** | 任务依赖/工时/评论/风险子模块部分端点未用 |
| **admin** | **12** | `/admin/role-mappings`, `/admin/team-role-templates`, `/admin/capacity-unit-costs` 等 |
| **auth** | **7** | `/auth/applications`, `/auth/users`, `/auth/register`, `/auth/apply`, 密码重设管理端 |
| **prototypes** | **6** | 部分样机端点(后端7个中6个孤岛) |
| **events** | **5** | `/events*` 系列未被前端调用 |
| **dashboard** | **5** | `/dashboard/alerts`, `/dashboard/alerts/rules` 等 |
| **others** | **42** | 含 `/kb/team` 等未被前端直接调用的 |

### P2 - 路径不一致 — ~15 项

主要问题:
1. **参数风格**: 后端使用 `{param_id}` (花括号), 前端使用 `:param` (冒号) — 语法级差异，逻辑上匹配
2. **采购路径**: 前端混用 `/purchase/` 和 `/purchases/` (如 RFQ 用 `purchase/rfqs`, 供应商用 `purchases/suppliers`)
3. **库存路径**: 前端 `api/inventory.ts` 用 `/inventory` 但 Vue 组件用 `/inventory/items`

### P3 - HTTP 方法不匹配 — 33 项

| 后端路径 | 后端方法 | 前端方法 | 影响 |
|---|---|---|---|
| `/admin/config` | PUT | GET | 前端只读但后端要求PUT |
| `/admin/tenants/{org_id}` | DELETE/PATCH/GET | 混用 | 前端 PATCH 但后端 DELETE |
| `/approval/requests` | POST | GET | 前端查列表但后端需POST创建 |
| `/gate-rules/{rid}` | GET | PUT | 前端更新但后端只读 |
| `/process/routes/{rid}` | GET | PUT | 同上 |
| `/projects/{pid}/risks` | GET | POST | 前端查询但后端需要POST创建 |
| `/quality/8d-reports/{rid}` | PUT | GET | 前端读但后端需要PUT更新 |
| 等 26 项更多 | ... | ... | 分布在 quality/process/projects/eco 等 |

---

## 四、关键模块逐项验证

### 4.1 认证 (auth)
- **后端**: 15 endpoints (login/logout/me/password/forgot/reset/register/apply/users等)
- **前端**: 9 个调用引用
- **匹配率**: ✅ 核心流程匹配 (login/logout/me/forgot-password/reset-password/verify-reset-token)
- **问题**: 7个孤岛API — 账号申请(apply)、用户管理(users/applications)、密码重设管理(admin-reset-password) 前端未直接调用

### 4.2 产品管理 (products/markets)
- **后端**: 17 products + 16 target-markets + 68 pm = 101
- **前端**: 0 products + 18 target-markets + 48 pm = 66
- **问题**: ❌ `products/` 系列17个端点完全未被调用；`pm/` 模块有6个P0 + 26个P1

### 4.3 项目管理 (projects)
- **后端**: 46 endpoints
- **前端**: 37 calls
- **匹配率**: ⚠️ 约70% — 核心CRUD匹配，但任务/工时/评论/依赖子模块部分孤岛

### 4.4 BOM 管理
- **后端**: 19 endpoints (完整CRUD + 树/成本/AVL/替代料)
- **前端**: **0 calls**
- **结论**: ❌ **所有BOM后端API未被前端调用**。前端 BOM 页面 (`bom/BOMView.vue`) 可能通过其他方式加载数据或尚未对接

### 4.5 采购管理 (purchases/RFQ/supplier)
- **后端**: 27+7+14 = 48 endpoints
- **前端**: 7+4+15 = 26 calls
- **匹配率**: ⚠️ purchases 20个孤岛（订单模块），RFQ 2个孤岛（报价管理），supplier 全部匹配

### 4.6 库存管理 (inventory)
- **后端**: 33 endpoints
- **前端**: 52 calls
- **匹配率**: ✅ 32/33 后端有前端匹配；但有4个前端PATCH/GET路径后端不存在

### 4.7 成本核算 (cost-accounting)
- **后端**: 33 + 9(cost-recalc) + 6(cost-alert) = 48
- **前端**: 32 + 9 + 6 = 47
- **匹配率**: ✅ **几乎完美匹配** — 成本模块是系统中前后端匹配度最高的模块

### 4.8 竞品对标 (competitor)
- **后端**: 14 endpoints (CRUD + benchmark/import/export/history)
- **前端**: 密集调用 (CrawlAdminView + CompetitorStandalone)
- **匹配率**: ✅ 核心功能匹配，仅 crawl 管理中有1个P0

### 4.9 认证管理 (certifications/S2)
- **旧认证 (certifications)**: 后端15个，前端7 — ⚠️ 已废弃但仍被部分调用
- **S2认证中心**: 后端37个专有端点，前端仅1个调用引用 — ❌ 严重不匹配，前端所有S2页面(`views/s2/*`) 的API调用未正确归入

### 4.10 ECR/ECO 变更管理
- **ECR**: 后端12，前端12 — ✅ 几乎完全匹配
- **ECO**: 后端15，前端14 — ✅ 几乎完全匹配

### 4.11 外协管理 (outsource)
- **后端**: 14 endpoints
- **前端**: 14 calls
- **匹配率**: ✅ **100%匹配** — partners/orders/quality-records 全部对齐

---

## 五、风险评级

| 风险等级 | 模块 | 问题类型 | 紧急度 |
|---|---|---|---|
| 🔴 **CRITICAL** | **BOM** | 19个后端API完全未对接前端 | P0 |
| 🔴 **CRITICAL** | **ci-v2** (Saga/CI/Risk Dashboard) | 22个前端调用无后端实现 | P0+P1 |
| 🔴 **CRITICAL** | **S2认证中心** | 37个后端API, 仅1个前端可见调用 | P1 |
| 🟠 **HIGH** | **Quality** (改进任务/看板) | 9个前端调用缺后端, 9个PATCH方法缺失 | P0+P3 |
| 🟠 **HIGH** | **Admin** (AI配置/用户管理) | 10个前端调用无后端 | P0 |
| 🟠 **HIGH** | **Tests** (测试执行/门禁规则) | 8个前端调用无后端 | P0 |
| 🟠 **HIGH** | **BI Analytics** | 9个前端BI调用无后端 | P0 |
| 🟡 **MEDIUM** | **Purchases** (订单模块) | 20个后端API无人调用 | P1 |
| 🟡 **MEDIUM** | **Products** | 17个后端API无人调用 | P1 |
| 🟡 **MEDIUM** | **Inventory** | 4个PATCH方法前端调用后端不支持 | P0 |
| 🟡 **MEDIUM** | **Projects** | 17个后端孤岛 + 1个P0 | P0+P1 |
| 🟢 **LOW** | **Auth** | 7个管理端孤岛(非核心流程) | P1 |
| 🟢 **LOW** | **HTTP方法不匹配** | 33项需对齐 | P3 |

---

## 六、改进建议

1. **BOM模块紧急对接**: BOM是系统核心模块(物料/成本基线)，19个API完全未被前端调用，需排查前端BOM页面(frontend/src/views/bom/)的API调用方式。

2. **S2认证中心前端调用梳理**: 后端已完整实现S2(37个API)，但前端扫描器未能捕获`views/s2/*`的API调用，需人工检查这些Vue文件的调用方式。

3. **Quality改进任务模块**: 后端缺失 `/quality/improvement-tasks*` 完整CRUD和 `/quality/dashboard` 端点，需补充实现。

4. **CI v2模块**: 22个前端路径以 `/api/v2/` 开头，后端清单中不存在这些路径，需确认是否由独立微服务提供。

5. **HTTP方法对齐**: 33处前后端方法不匹配需逐一修复，建议前端统一用 RESTful 标准(GET查询/POST创建/PUT全面更新/PATCH部分更新/DELETE删除)。

6. **路径统一**: 采购模块应统一为 `/purchase/` 或 `/purchases/`，避免混用。

7. **前端扫描器优化**: 当前扫描器未能捕获部分Vue组件(`views/s2/*`, `views/changes/*`, `views/bi/*`等)中的内联API调用。

---

*报告自动生成于 2026-07-03 | 分析脚本: analyze_api_match.py*
