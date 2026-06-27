# D2-2: Event Metadata Standard

> **ROS Event Metadata Standard — 所有 Capability 事件的统一 Header 规范**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-2 | Depends on: D2-1
> Status: DRAFT

---

## 1. Event Envelope 结构

所有 ROS Event 必须遵守统一封装格式：

```
{
  "metadata": { ... },     ← D2-2 标准定义 (Header)
  "payload":   { ... }     ← 各 Capability 的业务数据 (Event Schema)
}
```

**metadata** 包含 10 个字段（本标准定义），所有 Capability 必须一致。
**payload** 由各 Capability 的 Event Schema 独立定义（不受本标准约束）。

### 1.1 分层关系

```
Event Envelope
├── metadata (D2-2 标准)
│   ├── identity         ← 事件身份（检索与路由）
│   └── context          ← 事件上下文（追踪与隔离）
└── payload (D2-1 Event Schema)
    └── 业务数据
```

---

## 2. Metadata 字段定义

### 2.1 字段级别

| 级别 | 标识 | 含义 |
|:-----|:----|:------|
| **M (Mandatory)** | 必须 | Producer 必须生成，Consumer 可依赖 |
| **M\*** | 条件必须 | Domain/Integration 事件必须，System/Audit 可选 |
| **O (Optional)** | 可选 | Producer 可省略，Consumer 不得依赖 |
| **R (Reserved)** | 保留 | 当前不可用，为未来扩展预留 |

### 2.2 字段清单

| # | 字段名 | 所属组 | 类型 | 级别 | 说明 |
|:--|:-------|:-------|:----|:----|:------|
| 1 | `event_id` | identity | UUID v4 | **M** | 全局唯一事件 ID |
| 2 | `event_type` | identity | string | **M** | `{capability}.{action}` |
| 3 | `version` | identity | integer | **M** | 事件 Schema 版本号 |
| 4 | `timestamp` | context | ISO 8601 | **M** | 事件产生时间（含时区） |
| 5 | `source` | context | string | **M** | 产生事件的 Capability ID |
| 6 | `producer` | context | string | **M** | 具体产生模块名称 |
| 7 | `correlation_id` | context | UUID / null | **M\*** | 关联请求 ID（分布式追踪） |
| 8 | `causation_id` | context | UUID / null | **O** | 起因事件 ID（事件溯源） |
| 9 | `user_id` | context | string | **O** | 操作用户标识（审计用） |
| 10 | `trace_id` | context | string(32) | **M** | OpenTelemetry trace ID |
| 11 | `tenant_id` | context | string | **M** | 多租户 ID |

### 2.3 字段详解

#### ① `event_id` — 事件唯一标识

| 属性 | 值 |
|:-----|:----|
| 类型 | UUID v4 |
| 级别 | Mandatory |
| 生产者 | 事件产生者负责生成 |
| 示例 | `550e8400-e29b-41d4-a716-446655440000` |

全局唯一，碰撞概率 < 10^-36。所有 Consumer 依赖此字段进行去重和追踪。

#### ② `event_type` — 事件类型

| 属性 | 值 |
|:-----|:----|
| 格式 | `{capability}.{action}` |
| 级别 | Mandatory |
| 规则 | 全小写，snake_case，`.` 分隔 |
| 示例 | `plan.created` |

遵循 D2-1 Event Identity Standard 命名规范。event_type 永远不变，版本号通过 `version` 字段区分。

#### ③ `version` — Schema 版本号

| 属性 | 值 |
|:-----|:----|
| 类型 | integer |
| 级别 | Mandatory |
| 起始值 | 1 |
| 升级 | 遵循 D2-1 §3.3 版本升级策略 |

event_type 不变，仅 version 递增。Consumer 可通过 `event_type + version` 过滤特定版本。

#### ④ `timestamp` — 事件产生时间

| 属性 | 值 |
|:-----|:----|
| 格式 | ISO 8601（必须包含时区） |
| 级别 | Mandatory |
| 精度 | 秒级（建议毫秒级） |
| 示例 | `2026-06-30T14:30:00+08:00` |

#### ⑤ `source` — Capability ID

| 属性 | 值 |
|:-----|:----|
| 级别 | Mandatory |
| 值 | 与 Capability Registry 的 `capability.id` 一致 |
| 示例 | `planning`, `verification`, `certification` |

#### ⑥ `producer` — 具体模块名称

| 属性 | 值 |
|:-----|:----|
| 级别 | Mandatory |
| 格式 | `{capability}.{module}` |
| 示例 | `planning.product_plan_workflow` |

比 source 更细粒度，用于故障定位和运维。

#### ⑦ `correlation_id` — 关联请求 ID

| 属性 | 值 |
|:-----|:----|
| 类型 | UUID / null |
| 级别 | **M\*** — Domain/Integration 事件必须，System/Audit 可选 |
| 用途 | 同一用户请求触发的事件链共享同一个 correlation_id |

生产者生成。如无上游请求（如定时任务），生产者自生成 UUID。
Consumer 将此 ID 传递给后续产生的事件。

#### ⑧ `causation_id` — 起因事件 ID

| 属性 | 值 |
|:-----|:----|
| 类型 | UUID / null |
| 级别 | Optional |
| 用途 | 事件溯源：记录直接触发本事件的上一个事件的 event_id |

仅在因果链中存在上游事件时填充。独立事件（如定时任务触发）可为 null。

#### ⑨ `user_id` — 操作用户 ID

| 属性 | 值 |
|:-----|:----|
| 类型 | string |
| 级别 | Optional |
| 用途 | 审计追踪：记录执行操作的用户标识 |
| 来源 | 当前认证上下文 |

Producer 从认证上下文中获取。System 事件（如定时任务）可为空。

#### ⑩ `trace_id` — OpenTelemetry Trace ID

| 属性 | 值 |
|:-----|:----|
| 类型 | 32 位十六进制字符串 |
| 级别 | Mandatory |
| 格式 | `^[0-9a-f]{32}$` |
| 标准 | W3C Trace Context |

如果已有 Active Span，继承其 trace_id；否则生产者自生成。

#### ⑩ `tenant_id` — 多租户 ID

| 属性 | 值 |
|:-----|:----|
| 级别 | Mandatory |
| 默认值 | `default`（单租户部署） |
| 来源 | 当前认证上下文 |

Producer 从当前认证上下文中获取。保证跨租户数据隔离。

---

## 3. Metadata JSON Schema

完整 Schema 位于 `docs/events/schemas/event-header.schema.json`。

```json
{
  "metadata": {
    "identity": {
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "plan.approved",
      "version": 1
    },
    "context": {
      "timestamp": "2026-06-30T14:30:00+08:00",
      "source": "planning",
      "producer": "planning.product_plan_workflow",
      "correlation_id": "abc12345-...",
      "causation_id": "def67890-...",
      "trace_id": "0af7651916cd43dd8448eb211c80319c",
      "tenant_id": "acme-corp"
    }
  }
}
```

---

## 4. 与现有 Schema 的对齐

### 4.1 对齐策略：Wrapper 模式

**不对现有 Payload Schema 做 Breaking Change。** 采用 Wrapper 模式：将现有顶层字段移入 metadata，新增字段（producer, tenant_id, causation_id, correlation_id）。

### 4.2 对齐映射

| Phase 1（扁平） | Phase 2（Wrapper） |
|:----------------|:--------------------|
| `event_id` | → `metadata.identity.event_id` |
| `event_type` | → `metadata.identity.event_type`（值不变） |
| — | → `metadata.identity.version`（新增） |
| `timestamp` | → `metadata.context.timestamp` |
| `source` | → `metadata.context.source` |
| — | → `context.user_id`（新增，来自原 `metadata.user_id`） |
| — | → `context.producer`（新增） |
| — | → `metadata.context.correlation_id`（新增） |
| — | → `metadata.context.causation_id`（新增） |
| `trace_id` | → `metadata.context.trace_id` |
| — | → `metadata.context.tenant_id`（新增） |
| `payload` | → `payload`（不变） |

### 4.3 Consumer 兼容性

| 变更 | 影响 | 策略 |
|:-----|:-----|:------|
| 新增字段 | 无 | Forward Compatible |
| 字段位置变化 | 有 | Adapter 层适配，90 天过渡期 |
| Payload 不变 | 无 | 完全兼容 |
| 旧格式 schema | 标记 deprecated | 90 天后退役 |

---

## 5. Constitution Compliance

| 条款 | 本标准如何满足 |
|:-----|:---------------|
| 第四条 — 事件驱动 | `correlation_id` + `trace_id` 提供完整分布式追踪链路 |
| 第一条 — 数据主权 | `tenant_id` 保证跨租户隔离 |
| 第六条 — 决策可追溯 | `causation_id` + `correlation_id` 完整因果链 |
| 第八条 — 向下兼容 | Wrapper 模式，不破坏现有 Payload Schema |
| 第九条 — Agent 可替换 | 统一 Header 允许任何 Agent 消费任何 Event |

---

## 6. 引用

| 引用 | 位置 |
|:-----|:------|
| D2-1 Event Identity Standard | `docs/events/event-identity-standard.md` |
| Engineering Standard V1.0 | `docs/standards/engineering-standard-v1.md` |
| Header Schema | `docs/events/schemas/event-header.schema.json` |
| Envelope Schema | `docs/events/schemas/event-envelope.schema.json` |

---

*D2-2: Event Metadata Standard V1.0 — DRAFT*
*Capability: Planning | Baseline: PC-1.0-BL1*
*Depends on: D2-1 (Certified)*
*JSON Schema: event-header.schema.json (validated)*
