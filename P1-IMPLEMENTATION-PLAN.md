# P1 重构实施规划 — ROS系统

## 审计结果

### 1. ProductPlan (当前: 6字段, 84行model)
| 项目 | 内容 |
|------|------|
| **模型** | `backend/app/models/product_plan.py` — ProductPlan(84行) + Cost(子表) |
| **现有字段** | id, name, series, market, competitor_id, cost_target, performance_target |
| **API** | `backend/app/api/product_plan.py` (370行) — 6个端点 + 2个Cost子端点 |
| **状态机** | `backend/app/services/product_plan_workflow.py` (258行) — 8阶段: DRAFT→COMPETITOR→DEFINITION→COSTING→TECH_INPUT→PROJECT_INIT→APPROVED→RELEASED |
| **前端** | `ProductPlanningCenter.vue`(294行,列表) + `ProductPlanDetail.vue`(259行,详情6Tab) |
| **问题** | DRAFT阶段可直接创建,DEAD-END无校验; APPROVED自动生成Project但映射极简(只用name/series/market); 无审批集成 |

### 2. Project (当前: 148列 God Object, 250行model)
| 项目 | 内容 |
|------|------|
| **模型** | `backend/app/models/project.py` — Project(148列) + Program/ProjectGate/Milestone/Task/Risk |
| **数据分布** | 核心字段(~20列) + Sheet1-5立项数据(~100+列JSON/Text) |
| **API** | `backend/app/api/projects.py` (972行!) — 严重超限,需拆分 |
| **前端** | `PMWorkspace.vue` (2863行!) — 单体工作台,含5个立项Tab组件 |
| **Cost关联** | CostAccountingSheet已关联product_plans.id(P0-4已完成) |
| **问题** | 148列混搭执行+立项; 972行API文件超限; 无product_plan_id外键 |

### 3. ProposalApproval (退役中)
| 项目 | 内容 |
|------|------|
| **模型** | `backend/app/models/proposal_approval.py` (88行) — 已标记DEPRECATED |
| **API** | `backend/app/api/proposal_approval.py` (879行) — 仍为主审批流 |
| **双写逻辑** | `proposal_utils.py` 含 `_sync_approval_request()` / `_sync_pa_from_ar()` — 新旧表双向同步 |
| **并行审批** | ProposalParallelReviewer独立表(4角色并行→研发总监终审) |
| **前端** | `ProposalApprovals.vue` (561行) — 专用审批页面 |
| **问题** | 双写增加复杂性; 仍通过Project草稿提交流程; 应统一到ApprovalRequest |

### 4. ApprovalRequest (通用审批引擎)
| 项目 | 内容 |
|------|------|
| **模型** | `backend/app/models/approval.py` (74行) — 4表: Chain→Step→Request→Record |
| **已有功能** | sequential/parallel/or步骤类型; step_meta JSON支持并行快照 |
| **前端** | `ApprovalsView.vue` (430行) — 统一审批列表(除proposal类型特殊处理) |
| **proposal路由** | ApprovalsView对request_type='proposal'跳转到ProposalApprovals,未原生处理 |
| **优势** | 部署就绪, 可直接接入ProductPlan审批 |

### 5. 基础设施状态
| 组件 | 状态 |
|------|------|
| **事件总线** | ✅ 已就绪 — `EventTypes.PLAN_APPROVED`等已定义,支持同步/异步 |
| **Saga引擎** | ✅ 已就绪 — `core/saga_engine.py` |
| **Event Store** | ✅ 已就绪 — `core/event_store.py` |
| **Gate规则引擎** | ✅ 已就绪 — `services/gate_rule_engine.py` |
| **成本核算(S4)** | ✅ 已就绪 — `models/cost_accounting.py` + 前端5页面,已关联product_plan_id |
| **多租户** | ✅ 全部核心表含org_id |

---

## 实施规划 (JSON)

```json
{
  "architecture_overview": "ProductPlan升级为立项数据中枢(6字段→5子表), Project瘦身至~25执行字段, 统一审批出口为ApprovalRequest, 通过数据迁移脚本完成平滑过渡",
  "creation_date": "2026-06-25",
  "audit_summary": {
    "product_plan": "6字段 model(84行) + 370行API + 258行workflow + 2个前端页面. 阶段机完整但数据承载不足, APPROVED→Project映射极简",
    "project": "148列 God Object(250行model). ~100列立项数据(Sheet1-5) + ~25列执行字段, 972行API(超限), 2863行前端PMWorkspace(超限)",
    "proposal_approval": "已标记DEPRECATED(88行model), 但仍为主审批流(879行API). 双写同步到ApprovalRequest增加复杂性",
    "approval_request": "通用审批引擎就绪(74行model 4表), 支持sequential/parallel/or. 前端ApprovalsView(430行)对proposal类型有特殊分支跳转",
    "infrastructure": "事件总线✅ Saga引擎✅ Event Store✅ Gate规则引擎✅ 成本核算(S4)已关联product_plan_id✅ 多租户✅"
  },
  "phase_tasks": [
    {
      "id": "p1-t1",
      "title": "ProductPlan子表模型创建",
      "domain_tags": ["python", "sqlalchemy", "migration"],
      "risk_level": "high",
      "estimated_complexity": 5,
      "description": "创建4个新子表(ProductPlanInitiation/ProductPlanMarket/ProductPlanTechSpec/ProductPlanTeam)承接Sheet1-5立项数据。ProductPlan主表新增~12个直接字段(product_type/target_market/climate_zone/refrigerant/capacity_range/voltage_freq/series_name/energy_rating/dev_category/project_origin/project_duration/ip_ownership)。Cost模型已存在不做大改,但增加cost_category枚举映射",
      "files_to_create": [
        "backend/app/models/product_plan_initiation.py — 项目概述表(背景目标交付物)",
        "backend/app/models/product_plan_market.py — 市场与客户需求表",
        "backend/app/models/product_plan_tech_spec.py — 技术要求表(核心性能/安全/配置)",
        "backend/app/models/product_plan_team.py — 团队与职责表(1:N角色成员)"
      ],
      "files_to_modify": [
        "backend/app/models/product_plan.py — 追加~12个直接字段,加relationship到4个子表",
        "backend/app/models/__init__.py — 注册4个新模型"
      ],
      "dependencies": []
    },
    {
      "id": "p1-t2",
      "title": "ProductPlan数据迁移脚本",
      "domain_tags": ["python", "sqlalchemy", "data-migration"],
      "risk_level": "high",
      "estimated_complexity": 4,
      "description": "编写可重复执行的数据迁移脚本: ①遍历所有现存Project(非草稿+草稿), ②按Sheet1-5提取字段值写入新ProductPlan子表, ③更新ProductPlan外键project_id回链, ④迁移现存的ProposalApproval快照数据。脚本需幂等(idempotent),支持dry-run模式",
      "files_to_create": [
        "backend/app/migrate_p1_sheet_data.py — Sheet1-5数据从Project→ProductPlan迁移脚本"
      ],
      "files_to_modify": [],
      "dependencies": ["p1-t1"]
    },
    {
      "id": "p1-t3",
      "title": "ProductPlan API扩展",
      "domain_tags": ["python", "fastapi", "pydantic"],
      "risk_level": "high",
      "estimated_complexity": 4,
      "description": "扩展ProductPlan API支持子表CRUD。新增端点: POST/PUT/DELETE 子表数据(initiation/market/tech-spec/team)。修改GET /{id}详情返回嵌套所有子表。修改PATCH支持新字段。注意文件≤600行约束,超限则拆分到product_plan_subs.py子路由",
      "files_to_create": [
        "backend/app/api/product_plan_subs.py — 4个子表的CRUD端点(若product_plan.py超600行)"
      ],
      "files_to_modify": [
        "backend/app/api/product_plan.py — 增加子表嵌套响应,扩展更新schema",
        "backend/app/main.py — 可能注册新子路由"
      ],
      "dependencies": ["p1-t1", "p1-t2"]
    },
    {
      "id": "p1-t4",
      "title": "ProductPlanWorkflow升级",
      "domain_tags": ["python", "fastapi", "state-machine"],
      "risk_level": "medium",
      "estimated_complexity": 3,
      "description": "扩展现有workflow的stage requirements校验, 加入子表数据完成度检查: DEFINITION阶段→检查initiation表有数据; COSTING→检查costs表数据; TECH_INPUT→检查tech_spec表; PROJECT_INIT→检查market+team表。APPROVED阶段对接正式审批(触发ApprovalRequest创建而非自动创建Project)",
      "files_to_modify": [
        "backend/app/services/product_plan_workflow.py — 增强STAGE_REQUIREMENTS, 修改APPROVED逻辑",
        "backend/app/services/product_plan_workflow.py — 新增子表数据校验函数"
      ],
      "dependencies": ["p1-t1", "p1-t3"]
    },
    {
      "id": "p1-t5",
      "title": "ApprovalRequest接入ProductPlan审批",
      "domain_tags": ["python", "fastapi", "approval", "state-machine"],
      "risk_level": "medium",
      "estimated_complexity": 5,
      "description": "ProductPlan的APPROVED阶段改为: 创建ApprovalRequest(type='proposal', chain_id查找或创建PLAN_APPROVAL审批链)→等待审批完成→审批通过后推进到APPROVED并生成Project。新建审批链定义PLAN_APPROVAL(并行多角色→研发总监终审,与旧ProposalApproval一致)。新增approval回调handler订阅ApprovalRequest approved事件来推进ProductPlan",
      "files_to_create": [
        "backend/app/services/product_plan_approval.py — ProductPlan审批接入服务(创建ApprovalRequest+回调处理)"
      ],
      "files_to_modify": [
        "backend/app/services/product_plan_workflow.py — APPROVED阶段改走审批",
        "backend/app/services/events.py — 注册新handler监听approval事件",
        "backend/app/api/approvals.py — 可能扩展proposal类型的处理"
      ],
      "dependencies": ["p1-t4"]
    },
    {
      "id": "p1-t6",
      "title": "Project模型瘦身",
      "domain_tags": ["python", "sqlalchemy", "migration"],
      "risk_level": "critical",
      "estimated_complexity": 3,
      "description": "从Project模型移除Sheet1-5的~120列(保留核心执行字段+PM业务字段~25列)。新增product_plan_id外键(FK→product_plans.id)。处理存量数据兼容:将现有Project字段值保留到JSON列snapshot或迁移后清理。注意:直接影响所有引用Project的API和前端,需同步修改",
      "files_to_modify": [
        "backend/app/models/project.py — 移除~120列,加product_plan_id FK",
        "backend/app/api/projects.py — 更新schema排除已移除字段",
        "backend/app/schemas/ — 更新ProjectCreate/ProjectUpdate/ProjectOut"
      ],
      "dependencies": ["p1-t2"]
    },
    {
      "id": "p1-t7",
      "title": "前端ProductPlan详情页扩展",
      "domain_tags": ["vue3", "typescript", "element-plus"],
      "risk_level": "high",
      "estimated_complexity": 5,
      "description": "扩展ProductPlanDetail.vue增加5个Tab页签: ①项目概述(复用ProposalOverview组件) ②市场与客户需求(新) ③技术要求(复用ProposalTechSpec) ④成本核算(复用ProposalCosting+现有Cost表) ⑤团队与职责(复用ProposalTeam)。原有6个Tab不动(竞品对标/产品定义/成本目标/技术输入/项目关联/BOM规划)做精简合并。注意:子表数据通过新API保存",
      "files_to_create": [
        "frontend/src/views/pm/PlanInitiationTab.vue — 项目概述Tab(从ProposalOverview改造)",
        "frontend/src/views/pm/PlanMarketTab.vue — 市场与客户需求Tab",
        "frontend/src/views/pm/PlanTechSpecTab.vue — 技术要求Tab(从ProposalTechSpec改造)",
        "frontend/src/views/pm/PlanTeamTab.vue — 团队Tab(从ProposalTeam改造)"
      ],
      "files_to_modify": [
        "frontend/src/views/pm/ProductPlanDetail.vue — 增加5个Tab,调整Tab布局",
        "frontend/src/views/pm/ProductPlanningCenter.vue — 列表列增加更多信息展示"
      ],
      "dependencies": ["p1-t3", "p1-t4"]
    },
    {
      "id": "p1-t8",
      "title": "前端PMWorkspace瘦身",
      "domain_tags": ["vue3", "typescript", "element-plus"],
      "risk_level": "medium",
      "estimated_complexity": 3,
      "description": "PMWorkspace.vue(2863行)拆分子组件: ①移除产品立项书Drawer(5个子Tab已迁移到ProductPlanDetail) ②提案列表抽为独立组件 ③项目看板抽为MyProjectBoard组件。目标: PMWorkspace聚焦仪表盘+路由导航, 核心录入转到ProductPlanDetail",
      "files_to_create": [
        "frontend/src/views/pm/MyProjectBoard.vue — 我的项目看板组件"
      ],
      "files_to_modify": [
        "frontend/src/views/pm/PMWorkspace.vue — 简化至~800行,抽出Drawer和项目看板"
      ],
      "dependencies": ["p1-t7"]
    },
    {
      "id": "p1-t9",
      "title": "前端审批统一化",
      "domain_tags": ["vue3", "typescript", "element-plus"],
      "risk_level": "medium",
      "estimated_complexity": 2,
      "description": "ApprovalsView.vue移除对request_type='proposal'的特殊跳转分支,直接原生处理ProductPlan审批。ProposalApprovals.vue标记为DEPRECATED,保留只读查看旧记录。新增ApprovalRequest的chain_id查询页面区分审批类型",
      "files_to_modify": [
        "frontend/src/views/approvals/ApprovalsView.vue — 移除proposal特殊分支,统一审批渲染",
        "frontend/src/views/approvals/ProposalApprovals.vue — 加DEPRECATED标记,只读模式"
      ],
      "dependencies": ["p1-t5"]
    },
    {
      "id": "p1-t10",
      "title": "统一业务事件+清理",
      "domain_tags": ["python", "events", "cleanup"],
      "risk_level": "low",
      "estimated_complexity": 2,
      "description": "按P1目标只保留PLAN_APPROVED一个核心业务事件。明确废弃PROPOSAL_APPROVED事件,将相关handler迁移到PLAN_APPROVED。清理旧ProposalApproval的双向同步逻辑,加TODO标记后续彻底移除。迁移脚本完成后更新migrate_proposal_approvals.py引用",
      "files_to_modify": [
        "backend/app/services/events.py — 标记废弃事件类型,文档化迁移",
        "backend/app/api/proposal_utils.py — 加DEPRECATED标记,_sync_approval_request只保留读兼容",
        "backend/app/services/product_plan_workflow.py — 确保只发射PLAN_APPROVED"
      ],
      "dependencies": ["p1-t5", "p1-t6"]
    }
  ],
  "data_model_design": {
    "principle": "ProductPlan作为立项数据中枢,Project仅保留执行字段。通过product_plan_id FK连接两表,形成 策划层(Planning) → 执行层(Execution) 双层架构",
    "product_plan_main_table": {
      "existing_columns": "id, name, series, market, competitor_id, cost_target(JSON), performance_target(JSON), status(enum), project_id(FK), org_id, created_by, timestamps",
      "new_direct_columns": "product_type, target_market, climate_zone, refrigerant, capacity_range, voltage_freq, series_name, energy_rating, dev_category, project_origin, project_duration, ip_ownership (约12列)",
      "reason": "这些字段是项目的基本标识属性,频繁展示在列表和筛选中,直接放主表避免JOIN。字段值从Project旧表直接映射"
    },
    "new_sub_tables": [
      {
        "table": "product_plan_initiations",
        "cardinality": "1:1",
        "description": "项目概述 — 背景/目标/交付物/进度目标",
        "columns": "id(PK), product_plan_id(FK,unique), background_basis(Text), overall_goal(Text), tech_goal(Text), cost_goal(Text), sales_goal(Text), cert_goal(Text), schedule_goal(Text), patent_goal(Text), other_goals(Text), deliverables(Text), sample_qty(Integer), required_date(Date), org_id, created_at, updated_at",
        "source": "Project.Sheet1对应字段"
      },
      {
        "table": "product_plan_markets",
        "cardinality": "1:1",
        "description": "市场与客户需求",
        "columns": "id(PK), product_plan_id(FK,unique), main_capacity(String), energy_efficiency_req(String), cert_requirements(Text), target_price(String), customer_requirements(Text), customer_name(String), other_requirements(Text), fob_price(String), bom_cost_target(String), bom_cost_ratio(String), manufacturing_cost(String), gross_margin(String), annual_sales_forecast(String), product_lifecycle(String), org_id, created_at, updated_at",
        "source": "Project.Sheet2+部分业务字段"
      },
      {
        "table": "product_plan_tech_specs",
        "cardinality": "1:1",
        "description": "技术要求 — 核心性能/安全合规/附件配置",
        "columns": "id(PK), product_plan_id(FK,unique), core_performance(JSON), safety_compliance(JSON), optional_config(Text), accessory_config(Text), feature_config(Text), org_id, created_at, updated_at",
        "source": "Project.Sheet3+accessory/feature_config"
      },
      {
        "table": "product_plan_teams",
        "cardinality": "1:N",
        "description": "团队与职责 — 角色行明细",
        "columns": "id(PK), product_plan_id(FK), role(String), user_id(Integer,FK), username(String), headcount(Integer,default=1), org_id, created_at",
        "source": "Project.team_members(JSON)展开为多行"
      }
    ],
    "existing_sub_table": {
      "table": "costs",
      "cardinality": "1:N",
      "description": "成本明细(已存在)—扩展cost_category枚举支持Sheet4的各类费用标记",
      "modifications": "cost_category列(Enum: dev_cost/economic/mold/prototype/test/cert/labor) — 从Project.Sheet4 JSON展开为Cost行"
    },
    "project_slimmed": {
      "description": "Project移除~120列,保留~25列执行字段+product_plan_id FK",
      "retained_columns": "id, code, name, program_id, product_code, org_id, project_class, source, source_category, dev_modules(JSON), change_impacts(JSON), status, start_date, target_end_date, actual_end_date, critical_path, owner, leader_id, description, market_policy, annual_planning_ref, budget, is_draft, is_deleted, product_plan_id(NEW), created_at, updated_at",
      "removed_sheets": "Sheet1(全部~25列), Sheet2(全部~6列), Sheet3(全部~6列), Sheet4(全部~7列), Sheet5(全部~1列), extra_fields(customer_name~product_lifecycle全部~12列)"
    }
  },
  "api_design": {
    "new_endpoints": [
      {
        "method": "GET",
        "path": "/api/product-plans/{id}",
        "change": "扩展响应体包含所有子表嵌套数据(initiation/market/tech_spec/team/costs)",
        "risk": "low"
      },
      {
        "method": "PATCH",
        "path": "/api/product-plans/{id}",
        "change": "扩展支持新12个直接字段更新",
        "risk": "low"
      },
      {
        "method": "PUT",
        "path": "/api/product-plans/{id}/initiation",
        "change": "创建/更新项目概述子表(Upsert语义)",
        "risk": "low"
      },
      {
        "method": "PUT",
        "path": "/api/product-plans/{id}/market",
        "change": "创建/更新市场子表(Upsert语义)",
        "risk": "low"
      },
      {
        "method": "PUT",
        "path": "/api/product-plans/{id}/tech-spec",
        "change": "创建/更新技术要求子表(Upsert语义)",
        "risk": "low"
      },
      {
        "method": "GET",
        "path": "/api/product-plans/{id}/team",
        "change": "获取团队列表",
        "risk": "low"
      },
      {
        "method": "POST",
        "path": "/api/product-plans/{id}/team",
        "change": "添加团队成员行",
        "risk": "low"
      },
      {
        "method": "DELETE",
        "path": "/api/product-plans/{id}/team/{member_id}",
        "change": "删除团队成员",
        "risk": "low"
      },
      {
        "method": "POST",
        "path": "/api/product-plans/{id}/submit-approval",
        "change": "提交立项审批(创建ApprovalRequest+推进到PROJECT_INIT)",
        "risk": "medium"
      }
    ],
    "modified_endpoints": [
      {
        "method": "POST",
        "path": "/api/product-plans/{id}/advance",
        "change": "APPROVED阶段改为触发ApprovalRequest创建(不再自动创建Project)。审批通过后才推进+创建Project",
        "risk": "high"
      },
      {
        "method": "POST",
        "path": "/api/pm/proposals/submit",
        "change": "标记为DEPRECATED, 引导使用ProductPlan submit-approval",
        "risk": "medium"
      },
      {
        "method": "GET",
        "path": "/api/projects/{id}",
        "change": "移除已迁移的Sheet字段, 输出schema精简",
        "risk": "high"
      },
      {
        "method": "GET",
        "path": "/api/approvals",
        "change": "扩展filter支持chain_id筛选, 原生展示proposal类型",
        "risk": "medium"
      }
    ],
    "removed_endpoints": [],
    "note": "API文件≤600行约束: 若product_plan.py超限则抽子表CRUD到product_plan_subs.py"
  },
  "frontend_design": {
    "new_pages": [
      "frontend/src/views/pm/PlanInitiationTab.vue — 项目概述Tab(复用ProposalOverview逻辑改绑ProductPlan API)",
      "frontend/src/views/pm/PlanMarketTab.vue — 市场与客户需求Tab(新开发)",
      "frontend/src/views/pm/PlanTechSpecTab.vue — 技术要求Tab(从ProposalTechSpec改造)",
      "frontend/src/views/pm/PlanTeamTab.vue — 团队Tab(从ProposalTeam改造)",
      "frontend/src/views/pm/MyProjectBoard.vue — 我的项目看板(从PMWorkspace抽出)"
    ],
    "modified_pages": [
      "ProductPlanDetail.vue — 重构Tab布局:合并原有6Tab为精简Tab+新增5个立项Tab",
      "ProductPlanningCenter.vue — 列表增加initiation状态指示,支持更深筛选",
      "PMWorkspace.vue — 大幅瘦身:移除产品立项书Drawer(移至ProductPlanDetail),抽项目看板",
      "ApprovalsView.vue — 统一渲染proposal类型审批,移除特殊跳转分支",
      "ProposalApprovals.vue — 加DEPRECATED标记,只读模式保留兼容"
    ],
    "removed_pages": [],
    "routing_changes": {
      "new_routes": [
        "/product-plans/:id/initiation — 直接跳转到ProductPlan详情Tab(备用路由)"
      ],
      "modified_routes": [
        "/pm-workspace → 简化版工作台",
        "/approvals → 统一审批(含ProductPlan审批)"
      ]
    },
    "state_management": "扩展现有Pinia productPlanStore, 增加子表状态管理"
  },
  "migration_strategy": {
    "phase": "P1-T2 独立迁移脚本 + P1-T6 Project瘦身迁移",
    "script": "backend/app/migrate_p1_sheet_data.py",
    "steps": [
      {
        "step": 1,
        "action": "创建新表(通过Alembic或SQL DDL)",
        "description": "执行4个子表的CREATE TABLE + ProductPlan主表ALTER ADD COLUMN ~12个新字段",
        "rollback": "DROP新表 + ALTER DROP新字段"
      },
      {
        "step": 2,
        "action": "遍历Project,按sheet提取数据写入ProductPlan",
        "description": "对每个Project(包含is_draft=True/False): ①查找或创建对应的ProductPlan(按project.name匹配或新建) ②Sheet1→product_plan_initiations ③Sheet2→product_plan_markets ④Sheet3→product_plan_tech_specs ⑤Sheet4→扩展Cost行(标记cost_category) ⑥Sheet5→product_plan_teams多行",
        "rollback": "DELETE FROM新表 WHERE migrated_at > script_start"
      },
      {
        "step": 3,
        "action": "设置product_plan_id回链",
        "description": "UPDATE projects SET product_plan_id = 对应ProductPlan.id WHERE 已匹配",
        "rollback": "UPDATE projects SET product_plan_id = NULL"
      },
      {
        "step": 4,
        "action": "迁移ProposalApproval存量审批记录",
        "description": "遍历ProposalApproval表: ①检查对应的ApprovalRequest是否存在 ②若不存在则创建 ③关联snapshot数据到ProductPlan",
        "rollback": "DELETE从ApprovalRequest WHERE 来源标记='p1_migration'"
      },
      {
        "step": 5,
        "action": "Project瘦身ALTER TABLE",
        "description": "ALTER TABLE projects DROP COLUMN ~120列 + ADD COLUMN product_plan_id (FK)。或分两步:先加列迁移数据,再择机DROP旧列(保留兼容期)",
        "rollback": "ALTER TABLE projects ADD COLUMN恢复 + INSERT SELECT从备份"
      }
    ],
    "data_volume": "存量Project~200条(估),每个展开~5个子表行。总迁移量~1000行,脚本运行<30秒",
    "validation": "迁移后对比验证: COUNT(*)一致性检查 + 抽样对比5条Project的Sheet1-5值与新子表值",
    "idempotent": "每个步骤通过ON CONFLICT或IF NOT EXISTS保证可重复执行"
  },
  "risk_assessment": {
    "high_risks": [
      {
        "risk": "Project瘦身导致现有API/frontend大面积报错",
        "mitigation": "先做数据迁移+新API就绪,Project列标记deprecated保留兼容期,前端逐步切换到ProductPlan API。两步走:①加列不删列(兼容期2周)②验证无误后DROP",
        "contingency": "保留旧列JSON snapshot,前端降级读取旧列"
      },
      {
        "risk": "现有使用Project Sheet字段的API(972行projects.py)未全部覆盖",
        "mitigation": "审计所有projects.py端点引用字段,用search_files全库搜索Sheet字段名",
        "contingency": "对无法确定的字段保留旧列至下个Phase"
      },
      {
        "risk": "PMWorkspace前端(2863行)过度耦合,修改可能破坏现有功能",
        "mitigation": "逐步重构:①新ProductPlanDetail加Tab且可用 ②PMWorkspace只移除Drawer,其余不动 ③测试通过后再拆组件",
        "contingency": "保持两套UI并行(旧PMWorkspace只读,新ProductPlanDetail编辑)"
      },
      {
        "risk": "审批流程切换(ProposalApproval→ApprovalRequest)影响存量审批",
        "mitigation": "存量审批继续走旧路径完成。新ProductPlan审批直接走ApprovalRequest。两套并行至存量全部完成",
        "contingency": "ProposalApproval保留只读+兼容模式6个月"
      }
    ],
    "medium_risks": [
      {
        "risk": "数据迁移脚本异常导致数据丢失",
        "mitigation": "事务包裹每步操作+先备份PROJECT表+支持dry-run",
        "contingency": "从备份恢复+修复脚本后重跑"
      },
      {
        "risk": "ProductPlan API文件超600行限制",
        "mitigation": "提前规划拆分子路由product_plan_subs.py",
        "contingency": "超过后立即拆分"
      }
    ]
  },
  "execution_order": {
    "recommended_sequence": [
      "p1-t1 (ProductPlan子表模型) — 无依赖,必须先做",
      "p1-t2 (数据迁移脚本) — 依赖p1-t1,尽早验证数据映射正确性",
      "p1-t3 (API扩展) — 依赖p1-t1+p1-t2,子表CRUD是前端基础",
      "p1-t4 (Workflow升级) — 依赖p1-t1+p1-t3,增强校验+准备审批接入",
      "p1-t5 (审批接入) — 依赖p1-t4,改造核心审批流程",
      "p1-t7 (前端扩展) — 依赖p1-t3+p1-t4,用户可见的最大变更",
      "p1-t8 (PMWorkspace瘦身) — 依赖p1-t7,重构而非功能新增",
      "p1-t6 (Project瘦身) — 依赖p1-t2,可延迟到前端迁移完成后执行",
      "p1-t9 (前端审批统一) — 依赖p1-t5",
      "p1-t10 (事件清理) — 依赖p1-t5+p1-t6,最终清理"
    ],
    "parallel_tracks": [
      {
        "track": "后端核心(高优先级)",
        "tasks": ["p1-t1", "p1-t2", "p1-t3", "p1-t4", "p1-t5"]
      },
      {
        "track": "前端重构(中优先级)",
        "tasks": ["p1-t7", "p1-t8", "p1-t9"],
        "depends_on": ["p1-t3", "p1-t4", "p1-t5"]
      },
      {
        "track": "清理优化(低优先级)",
        "tasks": ["p1-t6", "p1-t10"],
        "depends_on": ["p1-t2", "p1-t5"]
      }
    ],
    "estimated_timeline": "后端核心4-5天 + 前端重构3-4天 + 清理测试2天 = 总计约9-11工作日"
  }
}
```

---

## 关键决策说明

### 为什么子表是1:1而非1:N?
Sheet1-3(项目概述/市场/技术)在立项阶段每产品策划只应有一条记录。1:1设计减少UI复杂度,前端Upsert语义明确。Sheet4(Cost)和Sheet5(Team)是1:N(多成本项+多团队成员),与现有Cost模型一致。

### 为什么不直接用JSON列?
JSON列失去SQL查询能力(WHERE/INDEX/JOIN),审计追踪困难,ORM不支持类型安全。子表设计兼顾查询效率+类型安全+ORM原生支持,且每表较小(<30列,远低于500行约束)。

### 为什么ApprovalRequest不改模型?
现有ApprovalRequest模型已支持proposal类型(request_type字段)。只需在ApprovalChain创建PLAN_APPROVAL链定义(并行4人+研发总监→与旧ProposalApproval一致),无需改表结构。

### 为什么保留旧ProposalApproval只读?
存量可能有进行中的审批记录。保留只读模式确保业务连续性,待全部完成后彻底移除。
