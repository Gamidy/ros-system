# ROS 系统 30天沙盒商业模拟方案

## 1. 概述

本沙盒模拟方案用于验证 ROS 系统核心流程的完整性和健壮性，覆盖 **ProductPlan（产品策划）→ ApprovalRequest（审批流）→ Project（项目执行）** 三大模块的端到端协作。模拟周期为 **30 个工作日**，使用 Faker 库生成逼真的测试数据集，包含正常业务和异常场景。

### 1.1 目标

- 验证 ProductPlan 8 阶段推进（DRAFT → COMPETITOR → DEFINITION → COSTING → TECH_INPUT → PROJECT_INIT → APPROVED → RELEASED）各阶段的转换逻辑
- 验证 ApprovalRequest 并行审批流（多角色总监审批）和退回重审机制
- 验证 ProductPlan APPROVED 后自动生成 Project 的联动逻辑
- 验证 Project 执行层（M1-M9 Gate、Task、Milestone、Risk）的配套数据完整性
- 覆盖异常场景（驳回、成本超限、技术变更、取消、Gate 阻塞）下的系统行为

### 1.2 技术栈

| 组件 | 版本/技术 |
|------|----------|
| 后端 | FastAPI + SQLAlchemy ORM |
| 数据库 | MariaDB (ros_db) |
| 数据生成 | Python 3.11 + Faker |
| 前端（仅展示） | Vue3 + Element Plus |

### 1.3 核心流程数据流

```
ProductPlan (策划层)
  │  DRAFT → COMPETITOR → DEFINITION → COSTING → TECH_INPUT → PROJECT_INIT
  │  (8 阶段推进，每阶段可包含子表扩展数据)
  │
  ▼  APPROVED
ApprovalRequest (审批层)
  │  并行审批（总监级 + 总经理）
  │  step_meta 记录各审批人决策
  │
  ▼  approved
Project (执行层)
  │  28 列业务字段 + M1-M9 Gate + Task + Milestone + Risk
  │  planning → running → completed / paused / cancelled
  ▼
Gate & Task 执行
  │  M1~M9 逐级/并行审核
  │  里程碑 + 任务 + 风险追踪
  ▼
完成/结项
```

---

## 2. 场景清单

### 2.1 正常场景（Happy Path）

| 编号 | 场景名称 | 涉及模块 | 说明 |
|------|---------|---------|------|
| N-01 | 全新产品开发全流程 | ProductPlan → Approval → Project | 海外市场新品（目标市场 EU），30天内完成策划→审批→立项→Gate M1~M4 |
| N-02 | 老产品升级迭代 | ProductPlan → Approval → Project | 现有产品能效升级，市场 CN，周期较短 |
| N-03 | 多市场同步上市 | ProductPlan → Approval → Project | 同一策划覆盖 EU+AU+SA 多市场认证要求 |
| N-04 | 成本优化项目 | ProductPlan(COSTING) → Approval → Project | 研发降本项目，source=研发降本，source_category=product_optimization |
| N-05 | 供应链二供导入 | ProductPlan → Approval → Project | 新增备用供应商，source=供应链二供 |
| N-06 | 年度规划常规项目 | ProductPlan → Approval → Project | 从年度规划中产生的标准化项目 |

### 2.2 异常场景（Exception Path）

| 编号 | 场景名称 | 异常类型 | 预期系统行为 |
|------|---------|---------|-------------|
| E-01 | 审批驳回——总监不同意立项 | 审批拒绝 | ApprovalRequest status=rejected，ProductPlan 退回 DRAFT，可修改后重新提交 |
| E-02 | 成本目标超限告警 | 数据校验 | 当 cost_target 超出预算 20% 时，系统应触发告警/阻止推进 |
| E-03 | 技术指标中途变更 | 流程回退 | 在 DEFINITION→COSTING 阶段发现技术指标需调整，回退到 DEFINITION |
| E-04 | 竞品分析缺失导致阻塞 | 数据完整性 | COMPETITOR 阶段未关联 competitor_id 无法进入下一阶段 |
| E-05 | 项目执行中 Gate M4 阻塞 | Gate 审核不通过 | M4 (设计验证) 不通过，项目进入 paused 状态，需整改后重新评审 |
| E-06 | 项目经理主动取消项目 | 流程终止 | 项目从 running 变为 cancelled，关联任务全部标记 cancelled |
| E-07 | 并行审批中部分审批人拒绝 | 多角色不一致 | 并行审批中一人拒绝即整体 rejected |
| E-08 | 项目进度严重延期 | 里程碑预警 | 里程碑 planned_date 超过 5 天未达成，系统标记 delayed |

### 2.3 混合场景（Composite）

| 编号 | 场景名称 | 组合说明 |
|------|---------|---------|
| C-01 | 正常产品 + 并行审批通过 | 多个 ProductPlan 同时提交审批，所有审批人批准 |
| C-02 | 正常产品 + 审批驳回 + 重提交 | 先驳回，修改后重新提交并通过 |
| C-03 | 高等级项目(T级)全流程 | T级项目需要总经理审批+额外 M0 评估 |
| C-04 | 多个项目执行叠加，部分挂起 | 3个项目 running，1个 paused，1个 cancelled |

---

## 3. 验证标准

### 3.1 数据层验证

| 验证项 | 预期 | 检查方式 |
|--------|------|---------|
| ProductPlan 数量 | ≥ 15 条（含正常和异常） | `SELECT COUNT(*) FROM product_plans` |
| ApprovalRequest 数量 | 与提交审批的 ProductPlan 数一致 | `SELECT COUNT(*) FROM approval_requests` |
| ApprovalRecord 数量 | 每条审批请求至少 2 条记录 | `SELECT request_id, COUNT(*) FROM approval_records GROUP BY request_id` |
| Project 数量 | 成功审批的 ProductPlan 对应生成 Project | `SELECT COUNT(*) FROM projects WHERE product_plan_id IS NOT NULL` |
| Gate 数量 | 每个 Project 至少 4 个 Gate (M1-M4) | `SELECT project_id, COUNT(*) FROM project_gates GROUP BY project_id` |
| 子表数据完整性 | ProductPlanInitiation/Market/TechSpec/Team 非空 | 检查各子表是否与 ProductPlan 一一关联 |
| 异常数据 | 至少 5 条 status=cancelled/paused/rejected 的记录 | `SELECT status, COUNT(*) FROM projects GROUP BY status` |

### 3.2 流程层验证

| 验证项 | 预期 | 检查方式 |
|--------|------|---------|
| 阶段转换 | ProductPlan 完整走完 8 阶段路径 | 检查 status 字段的时间戳变化 |
| 审批流转 | ApprovalRequest.step_meta 包含所有审批人决策 | 解析 JSON 确认 step_meta 结构完整 |
| 自动联动 | ProductPlan.approved → Project.product_plan_id 非空 | 确认所有 approved 的 ProductPlan 有对应 Project |
| 驳回回退 | rejected 的 ProductPlan status 为 DRAFT | `SELECT id, status FROM product_plans WHERE id IN (rejected 的请求)` |
| Gate 状态机 | Gate M1-M4 的 status 合理流转 | `SELECT gate_code, status FROM project_gates ORDER BY project_id, seq` |

### 3.3 时间轴验证

| 天数 | 预期状态 |
|------|---------|
| Day 1-5 | 多个 ProductPlan 创建、进入 DRAFT/COMPETITOR 阶段 |
| Day 6-10 | 推进到 DEFINITION/COSTING，部分进入 PROJECT_INIT |
| Day 11-15 | 提交审批（ApprovalRequest），部分获批，部分驳回 |
| Day 16-20 | 获批的生成 Project，进入 planning/running |
| Day 21-25 | Project 执行，Gate 评审，部分出现异常 |
| Day 26-30 | 部分完成，部分 paused/cancelled，混合状态 |

---

## 4. 数据准备说明

### 4.1 生成方式

使用 Python 脚本 `tests/sandbox/generate_sandbox_data.py` 执行：
```
cd /Users/gamidy/ros-source/ros-system
python tests/sandbox/generate_sandbox_data.py
```

### 4.2 环境要求

- Python 3.11+
- 依赖：`pip install faker sqlalchemy pymysql`
- 可访问 ROS 数据库（配置在 `app.core.config` 或通过环境变量）

### 4.3 输出数据量

| 表名 | 预计行数 | 备注 |
|------|---------|------|
| product_plans | 18-22 条 | 含正常+异常场景 |
| product_plan_initiations | 18-22 条 | 1:1 关联 |
| product_plan_markets | 18-22 条 | 1:1 关联 |
| product_plan_tech_specs | 18-22 条 | 1:1 关联 |
| product_plan_teams | 50-80 条 | 1:N 关联 |
| costs | 50-80 条 | 1:N 关联 |
| approval_chains | 2-3 条 | 预定义审批链 |
| approval_steps | 6-10 条 | 预定义审批步骤 |
| approval_requests | 10-15 条 | 提交审批的策划案 |
| approval_records | 25-50 条 | 审批记录 |
| projects | 8-12 条 | 审批通过的策划自动生成 |
| project_gates | 40-60 条 | 每个 Project 4-6 个 Gate |
| tasks | 60-120 条 | 每个 Project 5-10 个 Task |
| milestones | 30-50 条 | 每个 Project 3-5 个 Milestone |
| risks | 15-30 条 | 异常场景配置 |

### 4.4 种子数据依赖

脚本执行前需确保数据库已有以下种子数据：
- 用户表（users）：至少 10 个用户，涵盖 admin、rd_director、product_manager、systems_engineer、procurement、quality_engineer 等角色
- 组织表（organizations）：至少 1 个组织
- 竞品模型表（competitor_models）：至少 5 条竞品记录

如上述数据不存在，脚本将自动创建基础种子用户和数据。

### 4.5 数据清理

若要重置沙盒数据，可执行：
```sql
DELETE FROM approval_records;
DELETE FROM approval_requests;
DELETE FROM approval_steps;
DELETE FROM approval_chains;
DELETE FROM tasks;
DELETE FROM risks;
DELETE FROM milestones;
DELETE FROM project_gates;
DELETE FROM projects;
DELETE FROM product_plan_teams;
DELETE FROM product_plan_tech_specs;
DELETE FROM product_plan_markets;
DELETE FROM product_plan_initiations;
DELETE FROM costs;
DELETE FROM product_plans;
```

---

## 5. 模拟时间轴

### Day 1-5: 策划启动阶段
```
Day 1: 创建 2 个全新品策划（DRAFT），目标市场 EU
Day 2: 创建 1 个升级品策划（DRAFT），目标市场 CN
Day 3: 创建 1 个多市场策划（DRAFT），目标市场 EU+AU
Day 4: 创建 1 个降本项目（DRAFT），source=研发降本
Day 5: 推进 3 个策划到 COMPETITOR 阶段，关联竞品分析
```

### Day 6-10: 策划细化阶段
```
Day 6: 2 个策划推进到 DEFINITION，填写技术指标
Day 7: 1 个策划进入 COSTING，录入成本目标
Day 8: 1 个策划进入 TECH_INPUT，补充项目周期信息
Day 9: 1 个策划试图跳过 COMPETITOR → 被系统阻止（异常 E-04）
Day 10: 所有正常策划推进到 PROJECT_INIT
```

### Day 11-15: 审批阶段
```
Day 11: 3 个正常策划提交审批（ApprovalRequest created）
Day 12: 总监审批——2 个 approved，1 个 rejected（异常 E-01）
Day 13: 被驳回的策划修改后重新提交
Day 14: 再次审批通过（C-02 混合场景）
Day 15: 总经理终审，所有 approved
```

### Day 16-20: 项目生成与启动
```
Day 16: 3 个 ProductPlan → Project 自动生成（planning）
Day 17: 创建 M1-M4 Gate 节点，分配项目经理
Day 18: Project 转为 running 状态，创建 Task
Day 19: 创建里程碑和初始风险
Day 20: 追加 1 个高等级 T 级项目（异常 E-05 潜伏）
```

### Day 21-25: 项目执行与异常
```
Day 21: M1 Gate 通过，M2 进行中
Day 22: 1 个项目的 M4 Gate 阻塞（异常 E-05）
Day 23: 1 个项目主动取消（异常 E-06）
Day 24: 1 个正常项目推进中，里程碑 1 延期（异常 E-08）
Day 25: 风险升级 —— 2 个项目出现 A 级风险
```

### Day 26-30: 收尾与混合状态
```
Day 26: 1 个项目 M3 通过，进度正常
Day 27: T 级项目因预算超限触发预警（异常 E-02）
Day 28: 2 个正常项目进入 completed，1 个仍 running
Day 29: 1 个优化项目推进到 M4，降本目标达成
Day 30: 最终状态验证 —— 4 running, 2 completed, 1 paused, 1 cancelled
```

---

## 6. 异常场景详细说明

### E-01: 审批驳回
```
触发条件: 审批人（如研发总监）选择"拒绝"，comment 填写"技术方案不成熟，需重新评审"
系统预期:
  1. ApprovalRequest.status = "rejected"
  2. 关联 ProductPlan.status 回退到 "draft"
  3. 记录 ApprovalRecord 含 approver + decision + comment
  4. 用户可修改后重新提交
验证: SELECT * FROM approval_records WHERE decision='rejected'
```

### E-02: 成本超限告警
```
触发条件: 成本目标 target_value 超过预算基准的 1.2 倍
系统预期:
  1. 系统应显示成本告警标记（或阻止推进）
  2. 需总经理特批才能继续
验证: costs 表中 target_value > budget*1.2 的记录需有特殊标记
```

### E-03: 技术指标变更
```
触发条件: 在 COSTING 阶段修改 core_performance 参数
系统预期:
  1. ProductPlan 回退到 DEFINITION 阶段
  2. 需重新进行技术评审
验证: status 变化记录和 updated_at 时间戳
```

### E-04: 竞品数据缺失阻塞
```
触发条件: 尝试从 DRAFT 推进到 COMPETITOR 但 competitor_id 为空
系统预期:
  1. 系统返回验证错误
  2. 阻止阶段推进
  3. 提示"请先完成竞品关联"
验证: 脚本中该 ProductPlan 的状态应留在 DRAFT
```

### E-05: Gate M4 阻塞
```
触发条件: M4 (设计验证) 的 pass_conditions 未完全满足
系统预期:
  1. Gate.status = "failed"
  2. Project.status = "paused"
  3. 创建整改任务，assignee=项目负责人
  4. 整改完成后可重新评审
验证: SELECT * FROM project_gates WHERE gate_code='M4' AND status='failed'
```

### E-06: 项目取消
```
触发条件: 项目经理调用取消接口
系统预期:
  1. Project.status = "cancelled"
  2. 关联 Tasks 全部标记 cancelled
  3. 关联里程碑标记 cancelled
验证: Project 及子表状态一致性
```

### E-07: 并行审批不一致
```
触发条件: 并行审批步骤中，部分审批人批准，部分拒绝
系统预期:
  1. 拒绝者 > 0 → 整体 rejected
  2. step_meta JSON 记录每个审批人的决策
验证: step_meta 字段 JSON 结构完整
```

### E-08: 里程碑延期预警
```
触发条件: 里程碑 planned_date 已过但 status 仍为 pending
系统预期:
  1. 超期 >= 5 天 → status 自动标记 "delayed"
  2. 关联任务优先级提升为 high/urgent
验证: milestones WHERE status='delayed'
```

---

## 7. 数据验证脚本

以下 SQL 查询可用于验证沙盒数据的完整性：

```sql
-- 1. 数据总量检查
SELECT 'product_plans' AS tbl, COUNT(*) AS cnt FROM product_plans
UNION ALL
SELECT 'projects', COUNT(*) FROM projects
UNION ALL
SELECT 'approval_requests', COUNT(*) FROM approval_requests
UNION ALL
SELECT 'project_gates', COUNT(*) FROM project_gates
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks
UNION ALL
SELECT 'milestones', COUNT(*) FROM milestones
UNION ALL
SELECT 'risks', COUNT(*) FROM risks
ORDER BY cnt DESC;

-- 2. 流程状态分布
SELECT status, COUNT(*) AS cnt FROM product_plans GROUP BY status ORDER BY cnt DESC;

-- 3. 审批结果分布
SELECT status, COUNT(*) FROM approval_requests GROUP BY status;

-- 4. 项目状态分布
SELECT status, COUNT(*) FROM projects GROUP BY status;

-- 5. Gate 通过率
SELECT gate_code, status, COUNT(*) FROM project_gates GROUP BY gate_code, status ORDER BY gate_code;

-- 6. 审批记录详情
SELECT ar.id, ar.title, ar.status, ar.current_step,
       ar2.approver, ar2.decision, ar2.comment
FROM approval_requests ar
JOIN approval_records ar2 ON ar2.request_id = ar.id
ORDER BY ar.id, ar2.decided_at;

-- 7. 异常数据检查（rejected/paused/cancelled）
SELECT 'REJECTED PLANS' AS category, id, name, status FROM product_plans WHERE status='draft' AND id IN (
  SELECT request_id FROM approval_requests WHERE status='rejected'
)
UNION ALL
SELECT 'PAUSED PROJECTS', id, name, status FROM projects WHERE status='paused'
UNION ALL
SELECT 'CANCELLED PROJECTS', id, name, status FROM projects WHERE status='cancelled';
```

---

## 8. 附录

### 8.1 ProductPlan 阶段说明

| 阶段 | 代码 | 前置条件 | 产出物 |
|------|------|---------|-------|
| 草稿 | DRAFT | — | 策划基本信息 |
| 竞品分析 | COMPETITOR | 关联 competitor_id | 竞品对标报告 |
| 产品定义 | DEFINITION | 填写市场/技术子表 | 产品需求文档 |
| 成本核算 | COSTING | 至少 1 条 cost 记录 | 成本目标表 |
| 技术输入 | TECH_INPUT | tech_spec 填写完整 | 技术规格书 |
| 立项准备 | PROJECT_INIT | 团队 + 周期数据完整 | 立项申请书 |
| 已批准 | APPROVED | 审批通过 | 触发 Project 生成 |
| 已发布 | RELEASED | Project 启动执行 | 产品发布令 |

### 8.2 ApprovalRequest 审批流定义

| 步骤 | 角色 | 类型 | 说明 |
|------|------|------|------|
| 1 | 产品经理提交 | sequential | 发起审批请求 |
| 2 | 研发总监 | parallel | 技术可行性审核 |
| 3 | 模块经理 | parallel | 资源评估 |
| 4 | 总经理 | sequential | 最终批准 |

### 8.3 M1-M9 Gate 节点

| Gate | 名称 | 决策层 | 正常通过条件 |
|------|------|--------|-------------|
| M1 | 项目启动 | 项目经理 | 需求确认、团队组建完成 |
| M2 | 方案设计 | 研发总监 | 技术方案评审通过 |
| M3 | 详细设计 | 模块经理 | 3D/2D 图档冻结 |
| M4 | 设计验证 | 研发总监 | 手板验证通过 |
| M5 | 小批试产 | 生产经理 | 产线验证通过 |
| M6 | 认证测试 | 质量经理 | 认证报告齐全 |
| M7 | 市场准备 | 产品经理 | 市场物料准备完成 |
| M8 | 量产批准 | 总经理 | 量产条件满足 |
| M9 | 项目结项 | 总经理 | 全部门签收 |
