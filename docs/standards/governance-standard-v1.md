# ROS Governance Standard V1.0

> **定义 ROS 的治理体系**：谁决定、谁批准、谁负责、谁可以修改、什么时候修改、什么时候废弃。
>
> 这是 ROS V5 新增的核心标准。如果说 Architecture / Data / Engineering / AI Standard 定义了
> "如何开发系统"，Governance Standard 定义的是"如何运营系统"。
>
> **稳定性：中高** — 治理结构应长期稳定，角色和权限可演进。

---

## 1. Product Governance（产品治理）

### 1.1 ProductPlan 生命周期

```
Idea
  ↓  [Gate: Concept Review — PM approves]
Concept
  ↓  [Gate: Feasibility Review — Architecture Board approves]
Planning
  ↓  [Gate: Planning Review — GM approves]
Development
  ↓  [Gate: Verification Review — QA approves]
Launch
  ↓  [Gate: Launch Review — PM + Cert approves]
Maintenance
  ↓  [Gate: Retirement Review — GM approves]
Retirement
```

### 1.2 Gate 决策权矩阵

| Gate | 决策者 | 所需输入 | 决策类型 |
|:-----|:-------|:---------|:---------|
| Concept Review | Product Manager | Market Research, Business Case | Go / No-Go |
| Feasibility Review | Architecture Board | Technical Assessment, Cost Estimate | Go / No-Go |
| Planning Review | General Manager | Full ProductPlan, Resource Plan | Go / No-Go |
| Verification Review | QA Lead | Test Report, Coverage Report | PASS / FAIL |
| Launch Review | PM + Cert Lead | Certification Status, Maturity Report | Go / No-Go |
| Retirement Review | General Manager | EOL Analysis, Service Impact | Approve / Reject |

### 1.3 生命周期状态定义

| 状态 | 说明 | 可操作 |
|:-----|:------|:-------|
| Idea | 初始想法 | 编辑、删除 |
| Concept | 概念验证中 | 编辑、推进 |
| Planning | 策划阶段 | 编辑、推进 |
| Development | 开发中 | 只读（变更需 ECO） |
| Launch | 上市阶段 | 只读 |
| Maintenance | 维护期 | 只读 |
| Retirement | 退市 | 只读，不可逆 |

---

## 2. Standard Governance（标准治理）

### 2.1 标准生命周期

```
Draft
  ↓  [Author submits]
Review
  ↓  [Architecture Board reviews]
Approved
  ↓  [Chair signs off]
Published
  ↓  [Time / Deprecation notice]
Deprecated
  ↓  [Replacement standard active]
Archived
```

### 2.2 标准版本管理

| 字段 | 说明 |
|:-----|:------|
| 版本号 | SemVer（MAJOR.MINOR.PATCH） |
| MAJOR 变更 | 不兼容的架构变更（需 Board 批准） |
| MINOR 变更 | 向后兼容的新增（需标准 Owner 批准） |
| PATCH 变更 | 勘误/排版（直接发布） |
| 生效日期 | Published 后自动生效，可设过渡期 |
| 废弃通知期 | 至少 90 天 |

### 2.3 标准维护者

| 标准 | Owner | 审批者 | 评审周期 |
|:-----|:------|:-------|:---------|
| Architecture Standard | Architecture Team | Architecture Board | 季度 |
| Data Standard | Data Governance Team | Data Steward | 月度 |
| Engineering Standard | Engineering Team | Tech Lead | 持续 |
| AI Standard | AI Governance Team | AI Steward | 持续 |
| **Governance Standard（本文件）** | **Architecture Board** | **Board Chair** | **半年度** |
| Operation Standard | Ops Team | Ops Lead | 月度 |

---

## 3. Rule Governance（规则治理）

### 3.1 规则类型

| 规则类型 | 说明 | 示例 |
|:---------|:------|:------|
| GateRule | 阶段门禁规则 | 覆盖率 ≥ 80% 通过 |
| CertificationRule | 认证判定规则 | CE 需 EMC + LVD 报告 |
| MarketRule | 市场准入规则 | 欧盟需 ERP 标签 |
| CostRule | 成本控制规则 | 目标成本 ±5% 阈值 |
| QualityRule | 质量判定规则 | P0 缺陷零容忍 |

### 3.2 规则生命周期

```
Draft
  ↓  [Author creates]
Review
  ↓  [Domain expert reviews]
Approved
  ↓  [Rule Owner signs off]
Published
  ↓  [Auto-enforced by system]
Deprecated
  ↓  [Replacement rule active]
Archived
```

### 3.3 规则元数据

每个规则必须包含：

```json
{
  "rule_id": "GATE-2026-001",
  "rule_type": "GateRule",
  "name": "Verification Coverage Gate",
  "version": 1,
  "status": "Published",
  "effective_date": "2026-07-01",
  "owner": "QA Lead",
  "condition": "coverage >= 80%",
  "action": "PASS: allow next stage / FAIL: block",
  "depends_on": ["VR-2026-*"]
}
```

---

## 4. AI Governance（AI 运营治理）

### 4.1 Agent 生命周期

| Agent | Owner | 升级审批者 | 下线条件 |
|:------|:------|:----------|:---------|
| Planner Agent | PM Lead | Architecture Board | 连续 3 月准确率 < 70% |
| Architecture Agent | Architect Lead | Architecture Board | 架构变更后需重新验证 |
| Coding Agent | Tech Lead | Tech Lead | 代码审计通过率 < 85% |
| Verification Agent | QA Lead | QA Lead | 漏报率 > 5% |
| Review Agent | Architect Lead | Architecture Board | 评分偏差 > 1σ |
| Certification Agent | Cert Lead | Cert Lead | 法规更新后需重训 |
| Knowledge Agent | Knowledge Steward | Data Governance | 知识召回率 < 60% |

### 4.2 Prompt 治理

| 控制点 | 要求 |
|:-------|:------|
| Prompt 版本管理 | 每个 Prompt 模板有版本号和变更记录 |
| Prompt 审批 | 生产环境 Prompt 变更需 Agent Owner 批准 |
| Prompt 审计 | 所有 Prompt 历史可追溯 |
| Prompt 测试覆盖率 | 每个 Prompt 有 ≥ 3 个测试用例 |
| 回滚机制 | 新 Prompt 上线后保留前版本 7 天 |

### 4.3 模型升级流程

```
New Model Available
  ↓
Offline Evaluation（标准测试集）
  ↓  [Score >= baseline]
Shadow Deployment（流量镜像）
  ↓  [7 days, no regression]
Canary Release（1% 流量）
  ↓  [3 days, no incident]
Full Rollout
```

---

## 5. Knowledge Governance（知识治理）

### 5.1 知识类型与维护

| 知识类型 | 创建者 | 审核者 | 失效周期 | 刷新机制 |
|:---------|:-------|:-------|:---------|:---------|
| Ontology | Data Steward | Architecture Board | 年度 | 版本更新 |
| Taxonomy | Data Steward | Data Governance | 年度 | 版本更新 |
| Standard Library | Cert Team | Cert Lead | 法规变更时 | 自动通知 |
| Engineering Rules | Senior Engineer | Tech Lead | 季度 | 人工评审 |
| Lessons Learned | 任何角色 | Domain Expert | 项目结束后 6 月 | 回顾会议 |
| Failure Mode | QA Team | QA Lead | 持续 | 新故障自动录入 |
| Expert Knowledge | Domain Expert | Knowledge Steward | 年度 | 访谈更新 |
| Best Practice | Tech Lead | Architecture Board | 半年度 | 实践验证 |

### 5.2 知识质量门禁

| 级别 | 要求 | 检查周期 |
|:-----|:-----|:---------|
| P0 | Lessons Learned 必须有根因和解决方案 | 创建时 |
| P1 | 知识引用必须有来源 | 提交时 |
| P2 | 知识必须分类和标签 | 提交时 |
| P3 | 过期知识必须标记 | 月度巡检 |

---

## 6. Organization Governance（组织治理）

### 6.1 Capability Owner 矩阵

| Business Capability | Owner 部门 | 代表角色 | 决策权限 |
|:--------------------|:-----------|:---------|:---------|
| Product Strategy | Executive | GM | 战略级 |
| Product Planning | Product Management | PM | Plan 级 |
| Product Definition | R&D | RD Lead | 规格级 |
| Verification | QA | QA Lead | 验证级 |
| Certification | Certification | Cert Lead | 认证级 |
| Manufacturing | Manufacturing | MFG Lead | 生产级 |
| Service | Service | Service Lead | 服务级 |

### 6.2 跨 Capability 决策

当决策涉及多个 Capability 时：

| 冲突类型 | 升级路径 | 最终决策者 |
|:---------|:---------|:-----------|
| PM vs RD（规格争议） | PM → GM | GM |
| RD vs QA（质量争议） | QA → GM | GM |
| Cost vs Quality | PM + RD → GM | GM |
| Time vs Scope | PM → Architecture Board | Board Chair |

### 6.3 RACI 模板（每 Capability 定义）

| 活动 | R（执行） | A（批准） | C（咨询） | I（知会） |
|:-----|:----------|:----------|:----------|:----------|
| ProductPlan 创建 | PM | PM Lead | RD, QA, Cert | GM |
| Gateway 评审 | PM | Gate Owner | Architecture Board | 相关部门 |
| ECO 发起 | 任意 | PM + RD | QA, Cert | MFG |
| 标准修订 | Standard Owner | Architecture Board | Domain Experts | 全员 |

---

*标准版本：V1.0*
*稳定性：中高*
*维护者：ROS Architecture Board*
*生效日期：2026-06-30*
