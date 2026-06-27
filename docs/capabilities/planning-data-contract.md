# Phase 3: Data Contract

> **Planning Capability Data Contract — 数据模型审计与对齐方案**
>
> Capability: Planning | Baseline: EC-1.0-BL1
> Phase 3 Deliverable | Depends on: Phase 1, Phase 2
> Status: CERTIFIED

---

## 1. Data Model Audit

### 1.1 ProductPlan 核心模型审计

| 字段 | Data Standard | 当前模型 (`product_plan.py`) | 差异 | 修复 |
|:-----|:-------------|:----------------------------|:----|:-----|
| id | UUID | ✅ `String(36), UUID default` | 兼容 | — |
| name | String(200) | ✅ `String(200)` | — | — |
| portfolio | Enum | ❌ 不存在 | **缺失** | 新增 `portfolio` 字段 |
| business_capability | Enum[] | ❌ 不存在 | **缺失** | 新增 JSON 字段 |
| platform | String | ❌ 不存在 | **缺失** | 新增 `platform` 字段 |
| status | Enum | ✅ `ProductPlanStage` | 兼容（比标准更细） | 保持现有 8 状态 |
| cost_target | Decimal | ❌ 独立 Cost 表 | 设计不同 | 保持（Cost 子表更灵活） |
| market | String[] | ✅ `market: String` | 当前单值 | 保持（后续可扩展为多值） |
| roadmap | Date | ✅ `roadmap_date` | 命名差异 | 保持 `roadmap_date` |

### 1.2 差异汇总

| 严重度 | 数量 | 处理策略 |
|:------|:----|:---------|
| 缺失字段 (portfolio/platform/business_capability) | 3 | Phase 4 新增，带默认值向后兼容 |
| 设计差异 (cost_target → Cost 子表) | 1 | 保持当前设计（子表更灵活） |
| 命名差异 (roadmap → roadmap_date) | 1 | 保持兼容（添加 alias） |
| 扩展字段 (8 状态 vs 7 状态) | 1 | 保持（比标准更细化） |

### 1.3 子表模型审计

| 模型 | Data Standard 映射 | 审计结果 |
|:-----|:-------------------|:---------|
| ProductPlanInitiation | 项目概述信息 | ✅ 合理扩展 |
| ProductPlanMarket | 市场与客户信息 | ✅ 合理扩展 |
| ProductPlanTechSpec | 技术要求 | ✅ 合理扩展 |
| ProductPlanTeam | 团队管理 | ✅ 合理扩展 |
| ProductPlanCosting → Cost | 成本核算 | ✅ 独立子表设计更灵活 |
| ProductPlanReview | 复盘 | ✅ 合理扩展 |
| ProductPlanProjectLink | 策划-项目关联 | ✅ 符合 Digital Thread |

---

## 2. 数据所有权声明

| 实体 | Owner | 写权限 | 读权限 |
|:-----|:------|:-------|:-------|
| ProductPlan | Planning Module | Planning Only | All Modules (Read) |
| ProductPlanInitiation | Planning Module | Planning Only | PM, RD |
| ProductPlanMarket | Planning Module | Planning Only | PM, Cert |
| ProductPlanTechSpec | RD Module | RD Only | Planning, QA |
| ProductPlanCosting | Finance Module | Finance Only | Planning, PM |
| ProductPlanTeam | Planning Module | Planning Only | HR, PM |
| ProductPlanReview | QA Module | QA Only | Planning, PM |

---

## 3. 数据质量门禁

| 级别 | 字段 | 校验规则 | 门禁 |
|:-----|:-----|:---------|:------|
| P0 | name | 非空，≤200 字符 | 创建时阻断 |
| P0 | status | 合法 ProductPlanStage 枚举值 | 创建时阻断 |
| P1 | market | 与 TargetMarket 一致性校验 | 创建时警告 |
| P1 | cost_target | 数值格式校验 | 创建时警告 |
| P2 | portfolio | 推荐填写 | 创建时提示 |

---

## 4. 迁移计划

### 4.1 向后兼容

新增字段全部为 Optional（带默认值），不破坏现有 Consumer：

| 新增字段 | 类型 | 默认值 | 影响 |
|:---------|:-----|:-------|:------|
| `portfolio` | String | `null` | ✅ 向后兼容 |
| `business_capability` | JSON | `[]` | ✅ 向后兼容 |
| `platform` | String | `null` | ✅ 向后兼容 |

### 4.2 迁移步骤

```
Step 1: Alembic Migration — 新增 portfolio/business_capability/platform 字段
Step 2: 数据回填 — 通过 API 或脚本补全现有记录
Step 3: API 更新 — 新策划接口支持新字段
Step 4: Consumer 适配 — 通知下游 Consumer 新字段可用
Step 5: 废弃旧字段 — 90 天后废弃未使用的旧兼容字段
```

---

## 5. Constitution Compliance

| 条款 | 如何满足 |
|:-----|:---------|
| 第一条 — 数据主权 | §2 数据所有权矩阵明确每个实体 Owner |
| 第八条 — 向下兼容 | 新增字段带默认值，不破坏现有 Consumer |

---

*Phase 3: Data Contract V1.0 — CERTIFIED*
*Capability: Planning | Baseline: EC-1.0-BL1*
