# D2-1: Event Identity Standard

> **ROS Event Identity Standard — 所有 Capability 的事件命名规范与版本策略**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-1 | Status: DRAFT

---

## 1. Event Naming Convention

### 1.1 命名格式

```
{capability}.{action}

示例:
plan.created
plan.stage_advanced
plan.approved
plan.released
plan.cost_updated
```

**格式说明：**

| 规则 | 说明 | 示例 |
|:-----|:------|:------|
| **Capability** | 全小写，匹配 Capability ID | `plan`, `verification`, `cert` |
| **Action** | 过去时态动词，snake_case | `created`, `stage_advanced` |
| **分隔符** | `.` 连接两部分 | `plan.created` |
| **版本号** | 独立字段 `version: integer`，不在 event_type 字符串中 | `"version": 1` |

### 1.2 Legacy Compat

> ROS V1 时代使用 `{Domain}.{Entity}.{Action}` （PascalCase）格式，
> 如 `ProductPlan.Created`。该格式仍受支持但已废弃（Deprecated）。
> 所有新事件使用本标准的 `{capability}.{action}` 格式。

### 1.3 禁止格式

- ❌ 驼峰命名：`planCreated` / `PlanCreated`
- ❌ 版本后缀嵌入 event_type：`plan.created.v1`
- ❌ 无 capability 前缀：`created` / `approved`

---

## 2. Event Classification（Board Requirement A）

### 2.1 分类字段

每个事件必须附带以下分类属性：

| 字段 | 值 | 说明 | 默认值 |
|:-----|:----|:------|:-------|
| **Category** | `Domain` / `Integration` / `System` / `Audit` | 事件类别 | —（必需） |
| **Criticality** | `Critical` / `High` / `Medium` / `Low` | 重要性 | `Medium` |
| **Replay Required** | `Yes` / `No` | Replay 是否需要 | `No` |
| **Persistent** | `Yes` / `No` | 是否持久化到 Event Store | `Yes`（Critical/High） |

### 2.2 分类定义

| Category | 定义 | 示例 |
|:---------|:------|:------|
| **Domain** | 核心业务事件，反映领域状态变更 | `plan.created`, `plan.approved` |
| **Integration** | 跨 Capability 集成事件 | `project.status_changed` |
| **System** | 系统级事件（通知/告警） | `notification.sent` |
| **Audit** | 审计追踪事件 | `audit.logged` |

### 2.3 Criticality 与持久化

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
 [Draft]
    │  [Owner submits for review]
    ▼
 [Reviewed]
    │  [Architecture Board certifies]
    ▼
 [Certified] ◄── 可消费
    │  [Released to production]
    ▼
 [Released]  ◄── 可消费
    │  [Deprecation notice (90d min)]
    ▼
 [Deprecated] ◄── 可消费（带警告）
    │  [All consumers migrated]
    ▼
 [Retired]   ◄── 不可消费
```

### 3.2 状态定义

| 状态 | 含义 | 可消费 | 最大停留时间 |
|:-----|:------|:-------|:------------|
| **Draft** | 创建中，未发布 | ❌ | 无限制 |
| **Reviewed** | 已评审，待发布 | ❌ | 30 天 |
| **Certified** | 已认证，可上线 | ✅ | 无限制（预发布） |
| **Released** | 正式发布 | ✅ | 无限制 |
| **Deprecated** | 即将废弃 | ✅（带警告） | 90 天（最短） |
| **Retired** | 已废弃 | ❌ | 永久 |

### 3.3 版本升级触发

| 变更类型 | 版本变动 | event_type | version 字段 | 消费者影响 |
|:---------|:---------|:-----------|:-------------|:-----------|
| 新增 Optional 字段 | **不升级** | 不变 | 不变 | 无 |
| 新增 Mandatory 字段 | **MINOR** → v2 | 不变 | 2 | 需更新 consumer |
| 删除/重命名字段 | **MAJOR** → v2 | 不变 | 2 | 必须更新 |
| Payload 结构重构 | **MAJOR** → v2 | 不变 | 2 | Migration Guide 必须 |

> **注意**：`event_type` 永远不变。版本号通过 `version` 字段区分。
> Consumer 可以订阅 `event_type = "plan.created"` 接收所有版本，
> 或 `event_type + version = 1` 只接收特定版本。

---

## 4. Event Version Policy

### 4.1 版本兼容性

| 兼容性级别 | 说明 | version 字段 |
|:-----------|:------|:-------------|
| **Backward Compatible** | 新增 Optional 字段 | 不变 |
| **Forward Compatible** | Consumer 忽略未知字段 | 不变 |
| **Breaking Change** | 删除/重命名字段 | +1 |

### 4.2 版本升级流程

```
Need for change identified
  ↓
Change type classified (backward / breaking)
  ↓  [Breaking →]
Migration Plan drafted → Architecture Board Review → Approved
  ↓
Dual-write period (90 days minimum for breaking)
  ↓
New version released (version: 2)
  ↓
Consumers migrate (within 90 days)
  ↓
Old version deprecated → retired
```

---

## 5. Consumer Compatibility Matrix（Board Requirement C）

### 5.1 矩阵格式（通用模板）

| Event | Versions | Producer | Consumer(s) | Category | Status |
|:------|:--------:|:---------|:------------|:---------|:-------|
| `{capability}.{action}` | 1,2,... | Producer | ConsumerA, ConsumerB, ... | Domain | Released |

### 5.2 Planning Capability Consumer Matrix

| Event | Versions | Producer | Consumer(s) | Category | Criticality | Status |
|:------|:--------:|:---------|:------------|:---------|:-----------:|:-------|
| `plan.created` | 1 | Planning | Audit, Notification, Verification | Domain | High | Certified |
| `plan.stage_advanced` | 1 | Planning | Digital Thread, Dashboard | Domain | High | Certified |
| `plan.approved` | 1 | Planning | Project Management | Domain | Critical | Certified |
| `plan.released` | 1 | Planning | Project Mgmt, Review, Knowledge | Domain | Critical | Certified |
| `plan.cost_updated` | 1 | Planning | Dashboard, BI Analytics, Finance | Domain | Medium | Certified |

### 5.3 新增 Consumer 流程

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
| Schema Coverage | 100% | 所有 Certified+Released Event 有 JSON Schema |
| Producer Validation | 100% | 所有 Producer 发布前校验 Schema |
| Consumer Validation | 100% | 所有 Consumer 消费前校验 Schema |
| Replay Success | 100% | Replay 测试通过率 |
| Version Compatibility | 100% | 无 Breaking Change 未通知 |
| Deprecated Events | 0 | 无过期事件未清理 |

---

## 7. Planning Capability — Event Inventory

| Event | Version | Category | Criticality | Replay | Persistent | Status |
|:------|:-------:|:---------|:-----------:|:------:|:----------:|:-------|
| `plan.created` | 1 | Domain | High | Yes | Yes | Certified |
| `plan.stage_advanced` | 1 | Domain | High | Yes | Yes | Certified |
| `plan.approved` | 1 | Domain | Critical | Yes | Yes | Certified |
| `plan.released` | 1 | Domain | Critical | Yes | Yes | Certified |
| `plan.cost_updated` | 1 | Domain | Medium | No | Yes | Certified |

---

## 8. Compliance References

| 引用 | 位置 | 实际文件状态 |
|:-----|:------|:-------------|
| ROS Constitution | `CONSTITUTION.md`（项目根目录） | ✅ 已建立（LTS） |
| ROS Foundation | `FOUNDATION.md`（项目根目录） | ✅ 已建立（LTS） |
| Engineering Standard V1.0 | `docs/standards/engineering-standard-v1.md` | ✅ Section 4 Event Spec |
| RFC-2026-001 | `RFC-2026-001-Planning-Capability.md` | ✅ Architecture Board Approved |

---

*D2-1: Event Identity Standard V1.1 — DRAFT*
*Capability: Planning | Baseline: PC-1.0-BL1*
*Architecture Board Conditions: A ✓ B ✓ C ✓*
*AI-Z Review: 5/10 → 修复后待重新审核*
