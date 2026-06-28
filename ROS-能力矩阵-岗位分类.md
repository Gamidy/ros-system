# ROS 系统能力矩阵 — 按岗位分类

> 扫描时间：2026-06-29  
> 系统路径：/Users/gamidy/ros-source/ros-system/  
> 数据来源：后端 API（46个路由模块）、前端视图（约150个组件）、数据模型（70+个模型表）

---

## 📊 系统总览

| 维度 | 数量 |
|------|------|
| 后端 API 路由模块 | 46 个 .py 文件 |
| 前端视图组件 | ~167 个 .vue 文件 |
| 数据库模型 | ~70 个 SQLAlchemy ORM 类 |
| 系统角色 | 21 种（含 2 个超级角色） |
| 全部菜单项 | ~50 个独立功能入口 |

---

## 一、总经理 (general_manager)

**超级角色 — 拥有全部菜单权限**

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱总览 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version, Market |
| BOM物料 | bom | BOMView | BOM, BOMItem, Part, PartAVL |
| 项目管理 | projects | ProjectsView, ProjectDetailView, ProjectGanttView | Program, Project, ProjectGate, Milestone, Task |
| 项目统计 | projects | ProjectStatsView | — |
| 项目对比 | projects | ProjectCompareView | — |
| 知识库 | knowledge_base | KnowledgeBaseView | knowledge |
| 实验测试 | tests | TestsView | TestRequest, TestResult, MQVerification |
| 验证需求 | verification_requirements | VerificationRequirementView | VerificationRequirement |
| Gate规则 | gate_rules | GateRuleView | GateRule |
| 目标市场 | target_markets | TargetMarketView | TargetMarket |
| 测试执行 | test_executions | TestExecutionPanel | TestExecution |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 认证管理(S2) | s2_cert_* | CertHub, S2DashboardView, S2RequirementView, S2CertProjectView, S2CertSampleView, S2CertExecutionView, S2CertResultView, S2CertificateView, S2GateRulesView, S2ImpactView | CertificationRequirement, CertificationProject, CertificationSample, CertificationExecution, CertificationResult, Certificate |
| ECR变更 | ecr | ECRListView, ECRDetailView | ECRRequest |
| ECO变更 | eco | ECOListView, ECOListView, ECOChDashboard | ECO, ECOItem |
| 变更智能评估 | ci_v2 | — | CI v2 models |
| 预警体系 | alerts | AlertsView | AlertRule, Alert |
| 质量管理 | — | QualityIssuesView | QualityIssue |
| 审批管理 | approvals | ApprovalsView | ApprovalChain, ApprovalStep, ApprovalRequest |
| 采购管理 | purchases | PurchasesView, SupplierListView, ReceivingListView, QualityDashboardView, PurchaseReturnView | PurchaseOrder, Supplier |
| 库存管理 | inventory | InventoryListView, WarehouseListView, InventoryTransactionView, InventoryCountListView, StorageLocationView, InventoryAlertView, ReplenishmentView | inventory models |
| 产品策划 | product_plan, pm_* | ProductPlanningCenter, ProductPlanDetail, PMWorkspace, ProposalsView | ProductPlan, Cost, ProductPlanStage |
| 竞品对标 | competitor, competitor_bench | CompetitorStandalone, CompetitorBench | CompetitorModel, CompetitorVersion |
| 市场管理 | markets | MarketMgmt, EnergyLevelManager | Market models |
| 事件时间线 | event_timeline | EventTimelineView, EventTimelineDetail | EventStore, EventLog |
| 智能决策看板 | risk_dashboard | RiskDashboard, MRCReadinessPanel, MQScorecardPanel, CDFTimelinePanel | CI v2 risk |
| 系统设置 | admin_config | AdminConfig, StandardManage | SystemConfig |
| 多租户管理 | admin_tenant | TenantManagement, MyOrgInfo | Organization |
| 角色模板 | admin_role_templates | — | TeamRoleTemplate |
| Role-Mapping | admin_role_mappings | — | RolePositionMapping |
| 安规管理 | safety | SafetyHub, SafetyStandardTab, SafetyInspectionTab, SupplierSafetyTab, SafetyAlertTab | SafetyStandard, SafetyInspectionItem, SupplierSafetyQualification |
| DFM可制造性 | manufacturability | DFMChecklistTab, DFMReportTab | DFMChecklist, DFMReport |
| 外协管理 | outsource | OutsourcePartnerTab, OutsourceOrderTab, OutsourceQualityTab | OutsourcePartner, OutsourceOrder |
| 成本核算 | cost_accounting | CostSheetList, CostSheetDetail, LaborRateConfig, OverheadRuleConfig, CostPeriodManage, CostOverview, CostAnalysisView, CapacityCostConfig, CostEfficiencyView, CostDashboardView | CostAccountingPeriod, CostAccountingSheet, LaborRateConfig |
| 成本预警 | cost_alert_api | — | CostAlertRule |
| BI分析 | bi_analytics | BIAnalyticsView, PlanningAnalytics, CostAnalytics, CostEfficiencyTrend | — |
| 标准监控 | standard_query_api | StandardsView, StandardDetail | Standard, StandardRegion, StandardCategory |
| 标准管理 | standard_admin_api | StandardManage (admin) | StandardCrawl |
| 知识库 | knowledge, knowledge_base | KnowledgeView | Knowledge |
| 事件监控 | event_graph | EventMonitorView | EventStore |
| Webhooks | webhooks | — | WebhookSubscription |
| 通知管理 | user_notification_api | NotificationSettings, NotificationsView | UserNotificationPref, NotificationChannel |
| 个人中心 | — | ProfileView | User |
| 密码重置 | password_reset_api | ForgotPassword, ResetPassword | PasswordResetToken |
| 审计日志 | audit_logs | — | AuditLog |
| 复盘看板 | review_templates, improvement_task_api | ReviewDashboard | ReviewTemplate, ImprovementTask |
| 研发总监面板 | rd_panel | RDDashboard | — |
| 模块管理 | — | ModuleManagerView | — |
| Saga事务 | — | SagaChainViewer | — |
| AI辅助策划 | ai_plan_api | AiSettings | AIConfig |

### ❌ 明显缺失
1. **企业战略管理** — 无年度经营目标设定、战略地图、OKR/KPI 跟踪功能
2. **经营报表中心** — 缺乏自动生成的月度/季度经营分析报告
3. **组织绩效看板** — 各岗位KPI完成情况、部门效能对比
4. **公司级公告/制度发布** — 无内部公告管理功能
5. **产品线损益总览** — 各产品线的收入/成本/利润汇总看板
6. **移动审批** — 无手机端快捷审批入口

---

## 二、产品经理 (product_manager)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version |
| BOM物料 | bom | BOMView | Part, BOM |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Program, Project |
| 认证管理 | certifications, s2_cert_* | CertHub, S2相关全部视图 | Certification全套 |
| 工作台 | pm_workspace | PMWorkspace, QuickLinks | — |
| 产品策划 | product_plan, product_plan_* | ProductPlanningCenter, ProductPlanDetail, PlanningCalendarView | ProductPlan, Cost, ProductPlanStage |
| 提案管理 | pm_proposal_api | ProposalsView, ProductProposalForm, ProductInitiation | ProductPlanInitiation |
| 竞品对标 | competitor, competitor_bench | CompetitorStandalone, CompetitorBench | CompetitorModel |
| 市场管理 | markets | MarketMgmt, EnergyLevelManager, StandardConfigDialog | Market models |
| 目标市场 | target_markets | TargetMarketView | TargetMarket, RequiredTest, RequiredCertification |
| 验证需求 | verification_requirements | VerificationRequirementView | VerificationRequirement |
| Gate规则 | gate_rules | GateRuleView | GateRule |
| 测试执行 | test_executions | TestExecutionPanel | TestExecution |
| 需求录入 | — | RequirementSubmit, RequirementList | ProductRequirement |
| 路线图 | pm_roadmap | RoadmapPanel | — |
| 年度规划 | — | AnnualPlanList | AnnualPlan |
| 成本概览 | cost_accounting | CostOverview, CostAnalysisView | CostAccounting |
| BI分析 | bi_analytics | BIAnalyticsView, PlanningAnalytics | — |
| 复盘看板 | review_templates, improvement_task_api | ReviewDashboard | ReviewTemplate, ImprovementTask |
| 事件时间线 | event_timeline | EventTimelineView | EventStore |
| AI辅助策划 | ai_plan_api | AiSettings | AIConfig |
| PM配置 | pm_config, pm_accessory | — | CertStandard, PerfDefault, MarketCertification, AccessoryDefault |
| 策划工作流 | product_plan_workflow_api | — | WorkflowTransitionSpec |
| 策划版本 | product_plan_versions | — | ProductPlanHistory |
| 策划模板 | plan_templates | — | PlanTemplate |
| 审批管理 | approvals | ApprovalsView | ApprovalChain |
| 预警 | alerts | AlertsView | AlertRule |

### ❌ 明显缺失
1. **用户调研/需求采集** — 无用户反馈录入、需求池管理、优先级排序（RICE/WSJF）
2. **竞品周报自动生成** — 竞品动态摘要无自动化推送
3. **产品路线图可视化** — 现有路线图较简单，缺少时间轴拖拽交互
4. **PRD在线协作** — 需求文档在线编辑/评注/版本对比
5. **发布管理** — 产品发布 checklist、发布审批、发布后复盘
6. **客户反馈闭环** — 从售后到产品改进的反馈跟踪

---

## 三、项目经理 / 项目管理员 (project_admin)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Program, Project, ProjectGate, Milestone, Task |
| 项目甘特图 | projects | ProjectGanttView | — |
| 项目统计 | projects | ProjectStatsView | — |
| 项目对比 | projects | ProjectCompareView | — |
| 任务依赖 | task_deps | TaskDepTab | Task (依赖关系) |
| 任务评论 | task_comments | TaskCommentsTab | — |
| 工时管理 | time_entries | TimeLogTab | — |
| 项目模板 | project_templates | ProjectTemplatesView | PlanTemplate |
| 项目评审 | project_reviews | ProjectReviewTab, ReviewCompare | ProjectReview |
| 产品 | products | ProductsView | Product |
| BOM | bom | BOMView | BOM |
| 测试 | tests | TestsView | TestRequest |
| 验证需求 | verification_requirements | VerificationRequirementView | VerificationRequirement |
| 测试执行 | test_executions | TestExecutionPanel | TestExecution |
| 样机 | prototypes | PrototypesView | Prototype |
| 预警 | alerts | AlertsView | Alert |
| 变更管理(ECR/ECO) | ecr, eco | ECRListView, ECOListView, ChangesHub, ChangesView | ECRRequest, ECO |
| 审批管理 | approvals | ApprovalsView | ApprovalRequest |
| Gate报告 | — | GateReportTab | GateEvalRecord |
| 预算管理 | — | BudgetTab (in ProjectsView) | — |
| 跨模块联动 | — | CrossModuleTab | — |
| 日历视图 | — | TaskCalendarTab | — |
| Kanban看板 | — | TaskKanbanTab | — |
| WBS分解 | — | WBSTreeTab | — |
| BI分析 | bi_analytics | BIAnalyticsView | — |
| 知识库 | knowledge_base | KnowledgeBaseView | Knowledge |

### ❌ 明显缺失
1. **资源负载管理** — 无人员资源日历、资源冲突检测、负载均衡建议
2. **项目基线管理** — 进度基线、成本基线、范围基线及变更对比
3. **风险登记册** — 仅基础Risk模型，缺少风险概率/影响矩阵、应对措施跟踪
4. **项目周报自动生成** — 无自动汇总进度/工时/问题的周报
5. **里程碑预警** — 关键里程碑延迟自动通知
6. **挣值管理(EVM)** — PV/EV/AC 挣值分析、CPI/SPI指标
7. **项目结项管理** — 结项检查表、项目归档、经验教训库

---

## 四、结构工程师 (structural_engineer)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version |
| BOM物料 | bom | BOMView | PartCategory, Part, PartAVL, BOM, BOMItem |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Project, Task |
| 测试管理 | tests | TestsView, VerificationRequirementView, TestExecutionPanel | TestRequest, TestResult, VerificationRequirement |
| 目标市场 | target_markets | TargetMarketView | TargetMarket |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 工程变更(ECR/ECO) | ecr, eco | ECRListView, ECOListView | ECRRequest, ECO, ECOItem |
| 认证中心(S2) | s2_cert_* | S2全套视图 | Certification全套 |
| 安规标准库 | safety | SafetyStandardTab | SafetyStandard |
| 安规检测项 | safety | SafetyInspectionTab | SafetyInspectionItem |
| DFM可制造性 | manufacturability | DFMChecklistTab, DFMReportTab | DFMChecklist, DFMReport, DFMScoreWeight |
| 知识库 | knowledge_base | KnowledgeBaseView | Knowledge |

### ❌ 明显缺失
1. **CAD图纸管理** — 无3D模型上传/预览、图纸版本管理、图号编码规则
2. **结构评审** — 结构设计评审流程、DFM评审、CAE仿真结果关联
3. **模具管理** — 模具台账、模具寿命追踪、模具维修记录
4. **物料优选库** — 结构件优选物料清单、替代料推荐
5. **结构DFMEA** — 结构设计失效模式分析模板
6. **尺寸链计算** — 公差分析、尺寸链计算工具
7. **样机制作跟踪** — 样机BOM对比、样机问题反馈闭环

---

## 五、系统工程师 (systems_engineer)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version, ManufacturingVariant |
| BOM物料 | bom | BOMView | BOM全套 |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Project, Task |
| 测试管理 | tests | TestsView, VerificationRequirementView, TestExecutionPanel | TestRequest, TestResult, MQVerification |
| 目标市场 | target_markets | TargetMarketView | TargetMarket |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 工程变更(ECR/ECO) | ecr, eco | ECRListView, ECOListView | ECRRequest, ECO |
| 认证中心(S2) | s2_cert_* | S2全套视图 | Certification全套 |
| 安规标准库 | safety | SafetyStandardTab | SafetyStandard |
| 安规检测项 | safety | SafetyInspectionTab | SafetyInspectionItem |
| DFM可制造性 | manufacturability | DFMChecklistTab, DFMReportTab | DFMReport |
| BOM对比 | — | BOMView (对比功能) | — |
| 变更影响分析 | ci_v2 | CertImpactView | CI v2 models |

### ❌ 明显缺失
1. **系统需求管理** — 系统级需求分解（如QFD）、需求追溯矩阵、需求变更影响链
2. **性能仿真** — 制冷/制热性能仿真数据管理、能效计算工具
3. **系统架构图** — 产品系统架构图、制冷系统原理图在线编辑
4. **技术参数管理** — 关键性能参数(KP)台账、参数对标、参数变更审批
5. **系统DFMEA** — 系统级失效模式分析、RPN评级
6. **匹配计算** — 压缩机/换热器/节流元件匹配计算工具
7. **噪音/振动管理** — 噪音测试数据管理、振动分析报告关联

---

## 六、电控工程师 (electrical_control_engineer)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version |
| BOM物料 | bom | BOMView | BOM, Part (电子料) |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Project, Task |
| 测试管理 | tests | TestsView, VerificationRequirementView, TestExecutionPanel | TestRequest, TestResult |
| 目标市场 | target_markets | TargetMarketView | TargetMarket |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 认证管理 | certifications, s2_cert_* | CertHub, S2全套 | Certification全套 |
| 工程变更(ECR/ECO) | ecr, eco | ECRListView, ECOListView | ECRRequest, ECO |
| 安规标准库 | safety | SafetyStandardTab | SafetyStandard |
| 安规检测项 | safety | SafetyInspectionTab | SafetyInspectionItem |
| 供应商安规 | safety | SupplierSafetyTab | SupplierSafetyQualification |
| DFM可制造性 | manufacturability | DFMChecklistTab, DFMReportTab | DFMReport |

### ❌ 明显缺失
1. **电气原理图管理** — 电路图上传/版本管理、电气原理图在线查看
2. **PCB/EDA管理** — PCB设计文件管理、BOM比对、元器件库
3. **电控件物料管理** — 电控专用料号规则、替代料认证状态
4. **电控测试用例** — 电控测试用例库、自动化测试结果导入
5. **EMC管理** — EMC测试数据管理、整改措施跟踪
6. **软件版本管理** — 嵌入式软件版本、固件发布记录、变更日志
7. **电控DFMEA** — 电控系统失效模式分析
8. **控制器参数管理** — 不同机型的控制器参数配置表

---

## 七、测试工程师

> 注：系统中无独立「测试工程师」角色，实际测试功能分散在 systems_engineer / structural_engineer / quality_engineer 等角色中。以下按功能聚合。

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 测试管理 | tests | TestsView | TestRequest, TestResult, MQVerification |
| 验证需求 | verification_requirements | VerificationRequirementView | VerificationRequirement |
| 测试执行 | test_executions | TestExecutionPanel | TestExecution |
| Gate规则 | gate_rules | GateRuleView, S2GateRulesView | GateRule, CertificationGateRule |
| 目标市场(测试要求) | target_markets | TargetMarketView | RequiredTest |
| 样机测试 | prototypes | PrototypesView | Prototype |
| 质量看板(采购侧) | — | QualityDashboardView | — |
| 质量问题 | — | QualityIssuesView | QualityIssue |
| 安规检测 | safety | SafetyInspectionTab | SafetyInspectionItem |
| DFM检查 | manufacturability | DFMChecklistTab | DFMChecklist |
| 认证执行 | s2_cert_executions | S2CertExecutionView | CertificationExecution |
| 认证结果 | s2_cert_results | S2CertResultView | CertificationResult |

### ❌ 明显缺失
1. **测试用例库** — 结构化测试用例管理(用例分类/步骤/预期结果/优先级)
2. **测试计划编制** — 测试计划(Test Plan)编制、资源分配、排期
3. **测试报告自动生成** — 测试报告模板、数据自动汇总、结论推荐
4. **缺陷管理系统** — 独立缺陷管理（严重程度/优先级/复现步骤/截图/指派）
5. **可靠性测试管理** — 寿命测试、环境测试、可靠性增长跟踪
6. **测试设备管理** — 测试设备台账、校准周期、设备利用率
7. **型式试验管理** — 全性能试验/型式试验报告管理
8. **自动化测试集成** — 测试数据自动采集接口

---

## 八、认证工程师

> 注：系统中无独立「认证工程师」角色，认证功能分散在多个角色中。以下按功能聚合。

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 认证需求 | s2_cert_requirements | S2RequirementView | CertificationRequirement |
| 认证项目 | s2_cert_projects | S2CertProjectView, S2CertProjectDetail | CertificationProject |
| 认证样机 | s2_cert_samples | S2CertSampleView | CertificationSample |
| 认证执行 | s2_cert_executions | S2CertExecutionView | CertificationExecution |
| 认证结果 | s2_cert_results | S2CertResultView | CertificationResult |
| 证书管理 | s2_certificates | S2CertificateView, S2CertificateDetail | Certificate, CertificateVersion |
| 认证门禁规则 | s2_gate_rules | S2GateRulesView | CertificationGateRule |
| 变更影响(认证) | s2_change_impact | S2ImpactView, CertImpactView | ChangeImpactRule |
| 规则管理 | — | CertRulesView | ChangeImpactRecord |
| 安规标准 | safety | SafetyStandardTab | SafetyStandard |
| 标准知识库 | standard_query_api | StandardsView, StandardDetail | Standard, StandardRegion, StandardCategory |
| 标准管理 | standard_admin_api | StandardManage | StandardCrawl |
| 市场参数(认证要求) | market_param_config | — | MarketParamConfig |
| 认证配置(PM) | pm_config | — | CertStandard, MarketCertification |
| 自动派发 | cert_auto_gen | — | CertAutoGenLog |

### ❌ 明显缺失
1. **认证费用管理** — 认证费用预算、实际支出追踪、ROI分析
2. **认证进度看板** — 多国认证并行进度总览（中国CCC/欧盟CE/美国UL等）
3. **认证机构管理** — 认证机构档案、合作记录、评价
4. **证书到期预警** — 证书有效期预警、续证提醒
5. **法规更新追踪** — 各目标市场法规变更自动抓取+影响评估
6. **认证方案推荐** — 根据目标市场自动推荐最优认证路径
7. **认证文档管理** — 认证提交资料包管理、多语言文档

---

## 九、采购工程师 (procurement)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 采购订单 | purchases | PurchasesView | PurchaseOrder, PurchaseOrderItem |
| 供应商管理 | purchases | SupplierListView | Supplier |
| 采购收货 | purchases | ReceivingListView | PurchaseOrder (收货状态) |
| 采购退货 | purchase_return | PurchaseReturnView | PurchaseReturn |
| 质检看板 | — | QualityDashboardView | — |
| 外协管理 | outsource | OutsourcePartnerTab, OutsourceOrderTab, OutsourceQualityTab | OutsourcePartner, OutsourceOrder |
| 库存总览 | inventory | InventoryListView | Inventory |
| 仓库管理 | inventory | WarehouseListView | — |
| 库存流水 | inventory | InventoryTransactionView | — |
| 库存盘点 | inventory_count | InventoryCountListView | InventoryCount |
| 库位管理 | inventory_bin | StorageLocationView | — |
| 库存预警 | inventory_alert | InventoryAlertView | — |
| 补货建议 | — | ReplenishmentView | — |
| BOM物料 | bom | BOMView | Part, PartAVL |
| 产品 | products | ProductsView | Product |
| 认证(供应商证书) | certifications | CertHub (供应商标书) | Certification |
| 预警 | alerts | AlertsView | Alert |

### ❌ 明显缺失
1. **询比价管理** — 询价单(RFQ)、比价表、价格谈判历史
2. **采购合同管理** — 合同模板、电子签章、合同执行跟踪
3. **供应商准入/评估** — 供应商资质审核、绩效评分(质量/交付/价格/服务)
4. **采购计划编制** — MRP采购需求计划、安全库存计算
5. **来料检验(IQC)** — 来料检验标准、检验记录、不合格处理
6. **供应商协同门户** — 供应商自助查看订单、发货、对账
7. **采购对账结算** — 采购对账单、发票匹配、付款计划
8. **成本下降追踪** — 年度降本目标、降价达成率、VA/VE提案管理

---

## 十、质量工程师 (quality_engineer)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 质量管理 | — | QualityIssuesView | QualityIssue |
| 测试管理 | tests | TestsView, VerificationRequirementView, TestExecutionPanel | TestRequest, TestResult |
| 目标市场(质量要求) | target_markets | TargetMarketView | RequiredTest |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 工程变更(ECR/ECO) | ecr, eco | ECRListView, ECOListView, ECOChDashboard | ECRRequest, ECO |
| 认证中心 | s2_cert_* | S2全套视图 | Certification全套 |
| 变更影响规则 | — | CertRulesView | ChangeImpactRule |
| 安规标准 | safety | SafetyStandardTab, SafetyInspectionTab | SafetyStandard, SafetyInspectionItem |
| DFM检查 | manufacturability | DFMChecklistTab, DFMReportTab | DFMChecklist, DFMReport |
| 外协质检 | outsource | OutsourceQualityTab | OutsourceQualityRecord |
| 采购质检看板 | — | QualityDashboardView | — |
| 预警体系 | alerts | AlertsView | AlertRule, Alert |
| 事件监控 | event_graph | EventMonitorView | EventStore |

### ❌ 明显缺失
1. **8D报告管理** — 8D问题解决流程、根本原因分析、纠正措施跟踪
2. **质量目标管理** — 质量KPI设定(直通率/返修率/客诉率)、趋势图
3. **来料检验(IQC)** — 检验标准、抽样方案(AQL)、检验记录
4. **过程检验(IPQC)** — 产线巡检、首件确认、过程能力CPK
5. **出货检验(OQC)** — 出货检查标准、不合格品控制
6. **客诉管理** — 客户投诉登记、分析、8D闭环、客诉统计
7. **质量成本(COQ)** — 预防成本/鉴定成本/失败成本统计
8. **SPC统计过程控制** — X̅-R图、P图、过程能力分析
9. **不合格品处理** — 不合格品标识/隔离/评审/处置流程(NCR)
10. **仪器校准管理** — 计量器具台账、校准计划、校准记录

---

## 十一、工艺工程师 (process_engineer)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Platform, Product, Version |
| BOM物料 | bom | BOMView | Part, BOM |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Project, Task |
| 测试管理 | tests | TestsView, VerificationRequirementView, TestExecutionPanel | TestRequest, TestResult |
| 目标市场 | target_markets | TargetMarketView | TargetMarket |
| 样机管理 | prototypes | PrototypesView | Prototype |
| 认证中心 | s2_cert_* | S2全套视图 | Certification全套 |
| 预警体系 | alerts | AlertsView | AlertRule |

### ❌ 明显缺失
1. **工艺路线编制** — 产品装配工艺流程图、工序卡片、工装夹具管理
2. **SOP管理** — 标准作业指导书(SOP)编制/版本/培训
3. **工时定额管理** — 标准工时测定、工时定额表、产能核算
4. **工艺BOM(PBOM)** — 从EBOM到PBOM的转换、工序物料清单
5. **产线平衡分析** — 工序节拍分析、瓶颈识别、平衡率计算
6. **新工艺验证** — 新工艺/新材料导入验证、小批量试产跟踪
7. **工艺变更管理** — 工艺变更申请/评审/验证/切换
8. **工装设备管理** — 工装夹具台账、维护计划、寿命管理
9. **PFMEA** — 过程失效模式分析、控制计划(Control Plan)
10. **直通率管理** — 产线直通率(FPY)统计、不良原因分析

---

## 十二、成本会计 (finance_manager / 财务经理)

### ✅ 已有功能
| 功能域 | API 模块 | 前端视图 | 数据模型 |
|--------|----------|----------|----------|
| 驾驶舱 | dashboard | DashboardView | — |
| 产品主线 | products | ProductsView | Product |
| BOM物料 | bom | BOMView | Part, BOM (标准成本) |
| 项目管理 | projects | ProjectsView, ProjectDetailView | Project (预算) |
| 采购管理 | purchases | PurchasesView, SupplierListView | PurchaseOrder (价格信息) |
| 预警体系 | alerts | AlertsView | Alert |
| 审批管理 | approvals | ApprovalsView | ApprovalRequest (成本相关) |
| 成本核算 | cost_accounting全套 | CostSheetList, CostSheetDetail, LaborRateConfig, OverheadRuleConfig, CostPeriodManage, CostOverview, CostAnalysisView, CapacityCostConfig, CostEfficiencyView, CostDashboardView | CostAccountingPeriod, CostAccountingSheet, CostAccountingItem, LaborRateConfig, OverheadAllocationRule |
| 成本预警 | cost_alert_api | — | CostAlertRule |
| 成本重算 | cost_recalculation | CapacityRecalcPanel | CostRecalculation |
| BI成本分析 | bi_analytics | CostAnalytics, CostEfficiencyTrend | — |
| 库存管理 | inventory | InventoryListView, InventoryCountListView | Inventory, InventoryCount |

### ❌ 明显缺失
1. **产品标准成本BOM** — 标准成本版本管理、成本BOM维护、成本模拟
2. **成本差异分析** — 实际 vs 标准成本差异(材料/人工/制造费用)、差异归因
3. **预算编制与控制** — 研发费用预算编制、预算执行率、预警
4. **项目成本核算** — 按项目归集研发费用、(料/工/费)分摊
5. **投资回报分析** — 产品线投资回报(ROI)、盈亏平衡分析
6. **成本预测** — 基于BOM+人工+分摊的成本预测模型
7. **费用报销管理** — 差旅/实验/测试费用报销审批流程
8. **月度关账** — 成本关账流程、期间费用预提/摊销
9. **目标成本管理** — 目标成本设定、成本拆解、达成追踪
10. **间接费用分摊** — 更精细的间接费用分摊规则（按产量/工时/机时）

---

## 📌 系统功能覆盖度总结

| 岗位 | 已有功能数（约） | 明显缺失数 | 覆盖度评估 |
|------|:---------:|:-----:|:------:|
| 总经理 | 50+ | 6 | ✅ 高 — 超级角色全功能 |
| 产品经理 | 30+ | 6 | ✅ 中高 — 策划/市场较完整 |
| 项目经理 | 25+ | 7 | ⚠️ 中 — 缺资源/基线/挣值 |
| 结构工程师 | 13+ | 7 | ⚠️ 中低 — 缺CAD/模具/DFMEA |
| 系统工程师 | 14+ | 8 | ⚠️ 中低 — 缺性能仿真/系统需求 |
| 电控工程师 | 13+ | 8 | ❌ 低 — 缺电控专业功能 |
| 测试工程师 | 14+ | 8 | ⚠️ 中低 — 缺用例库/缺陷管理 |
| 认证工程师 | 14+ | 8 | ⚠️ 中 — 有S2体系但缺费用/预警 |
| 采购工程师 | 18+ | 8 | ⚠️ 中 — 有基本采购但缺询比价/合同 |
| 质量工程师 | 14+ | 10 | ❌ 低 — 缺核心质量工具(8D/SPC/COQ) |
| 工艺工程师 | 9+ | 10 | ❌ 低 — 缺工艺核心功能 |
| 成本会计 | 15+ | 10 | ⚠️ 中低 — 有核算但缺预算/差异分析 |

### 总体评估

- **最强领域**：产品策划与项目管理 — 产品经理和项目经理功能相对完整
- **中等领域**：认证管理(S2体系较新)、采购/库存、成本核算(基础架子有)
- **最弱领域**：工艺工程、质量控制、电控工程 — 这三个岗位的专业功能几乎空白
- **当前强项模块**：认证全生命周期(S2)、产品策划工作流、成本核算基础、变更管理(ECR/ECO)
- **最需优先补齐**：质量管理(8D/SPC/COQ)、工艺管理(SOP/PFMEA/PBOM)、采购管理(询比价/合同)
