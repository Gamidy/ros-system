# D2-1: Event Identity Standard

> **ROS Event Identity Standard — 所有 Capability 的事件命名规范与版本策略**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-1 | Status: DRAFT

---

## 1. Event Naming Convention

### 1.1 命名格式

```
{capability}.{action}.v{version}

示例:
plan.created.v1
plan.stage_advanced.v1
plan.approved.v1
```

### 1.2 命名规则

| 规则 | 说明 | 示例 |
|:-----|:------|:------|
| **Capability** | 全小写，匹配 Capability ID | `plan`, `verification`, `cert` |
| **Action** | 过去时态动词，snake_case | `created`, `stage_advanced`, `cost_updated` |
| **Version** | 正整数 `v1`/`v2`/`v3` | `v1` |
| **分隔符** | `.` 连接 | `plan.created.v1` |

### 1.3 禁止格式

- ❌ 驼峰命名：`planCreated` / `PlanCreated`
- ❌ 下划线分隔：`plan_created_v1`
- ❌ 无版本：`plan.created`
- ❌ 大版本号：`plan.created.v1.0`

---

## 2. Event Classification（Board Requirement A）

### 2.1 分类字段

每个事件必须附带以下分类属性：

| 字段 | 值 | 说明 |
|:-----|:----|:------|
| **Category** | `Domain` / `Integration` / `System` / `Audit` | 事件类别 |
| **Criticality** | `Critical` / `High` / `Medium` / `Low` | 重要性 |
| **Replay Required** | `Yes` / `No` | Replay 是否需要 |
| **Persistent** | `Yes` / `No` | 是否持久化到 Event Store |

### 2.2 分类定义

| Category | 定义 | 示例 |
|:---------|:------|:------|
| **Domain** | 核心业务事件，反映领域状态变更 | `plan.created`, `plan.approved` |
| **Integration** | 跨 Capability 集成事件 | `project.status_changed` |
| **System** | 系统级事件（通知/告警） | `notification.sent`, `alert.triggered` |
| **Audit** | 审计追踪事件 | `audit.logged`, `decision.recorded` |

### 2.3 Criticality 定义

| Criticality | 定义 | Replay | Persistent |
|:------------|:------|:------:|:----------:|
| **Critical** | 影响核心业务连续性 | Yes | Yes |
| **High** | 影响功能完整性 | Yes | Yes |
| **Medium** | 影响用户体验 | No | Configurable |
| **Low** | 日志/追踪级别 | No | No |

---

## 3. Event Lifecycle（Board Requirement B）

### 3.1 生命周期

```
Draft
  ↓  [Owner submits]
Reviewed
  ↓  [Architecture Board reviews]
Certified
  ↓  [All checks pass]
Released
  ↓  [Time / Deprecation notice]
Deprecated
  ↓  [Replacement event active]
Retired
```

### 3.2 状态定义

| 状态 | 含义 | 可消费 |
|:-----|:------|:-------|
| **Draft** | 创建中，未发布 | ❌ |
| **Reviewed** | 已评审，待发布 | ❌ |
| **Certified** | 已认证，可上线 | ✅ |
| **Released** | 正式发布 | ✅ |
| **Deprecated** | 即将废弃，仍有消费者 | ✅（有警告） |
| **Retired** | 已废弃，不再发布 | ❌ |

### 3.3 版本升级触发条件

| 变更类型 | 版本变动 | 示例 |
|:---------|:---------|:------|
| 新增 Optional 字段 | PATCH（不升级） | v1 仍兼容 |
| 新增 Mandatory 字段 | MINOR → v2 | 消费者需更新 |
| 删除/重命名字段 | MAJOR → v2 | 消费者必须更新 |
| Payload 结构重构 | MAJOR → v2 | Migration Guide 必须 |

---

## 4. Event Version Policy

### 4.1 版本兼容性规则

| 兼容性级别 | 说明 | 消费者影响 |
|:-----------|:------|:-----------|
| **Backward Compatible** | 新增字段（Optional） | 无影响 |
| **Forward Compatible** | 忽略未知字段 | 无影响 |
| **Breaking Change** | 删除/重命名字段 | 消费者必须升级 |

### 4.2 版本升级流程

```
Need for change identified
  ↓
Classify change type (backward / breaking)
  ↓  [Breaking →]
Migration Plan → Architecture Board Review → Approval
  ↓
Dual-write period (90 days for breaking)
  ↓
New version released
  ↓
Consumers migrate
  ↓
Old version deprecated → retired
```

---

## 5. Consumer Compatibility Matrix（Board Requirement C）

### 5.1 矩阵格式

| Event | Version | Producer | Consumer(s) | Category | Status |
|:------|:-------:|:---------|:------------|:---------|:-------|
| `plan.created` | v1 | Planning | Audit, Notification, Verification | Domain | Released |
| `plan.stage_advanced` | v1 | Planning | Digital Thread, Dashboard | Domain | Released |
| `plan.approved` | v1 | Planning | Project Management | Domain | Released |
| `plan.released` | v1 | Planning | Project Mgmt, Review, Knowledge | Domain | Released |
| `plan.cost_updated` | v1 | Planning | Dashboard, BI Analytics, Finance | Domain | Released |

### 5.2 新增 Consumer 流程

```
New consumer identified
  ↓
Add to Consumer Matrix (RFC)
  ↓
Architecture Board Approval
  ↓
Subscribe to Event
  ↓
Verify compatibility
```

---

## 6. Event Quality Metrics

| 指标 | 目标 | 测量方式 |
|:-----|:-----|:---------|
| Schema Coverage | 100% | 所有 Released Event 有 JSON Schema |
| Producer Validation | 100% | 所有 Producer 发布前校验 Schema |
| Consumer Validation | 100% | 所有 Consumer 消费前校验 Schema |
| Replay Success | 100% | Replay 测试通过率 |
| Version Compatibility | 100% | 无 Breaking Change 未通知 |
| Deprecated Events | 0 | 无过期事件未清理 |

---

## 7. Planning Capability — Event Inventory

| Event | Version | Category | Criticality | Replay | Persistent | Status |
|:------|:-------:|:---------|:-----------:|:------:|:----------:|:-------|
| `plan.created` | v1 | Domain | High | Yes | Yes | Certified |
| `plan.stage_advanced` | v1 | Domain | High | Yes | Yes | Certified |
| `plan.approved` | v1 | Domain | Critical | Yes | Yes | Certified |
| `plan.released` | v1 | Domain | Critical | Yes | Yes | Certified |
| `plan.cost_updated` | v1 | Domain | Medium | No | Yes | Certified |

---

*D2-1: Event Identity Standard V1.0 — DRAFT*
*Capability: Planning | Baseline: PC-1.0-BL1*
*Architecture Board Conditions: A ✓ B ✓ C ✓*
