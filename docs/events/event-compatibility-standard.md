# D2-3: Event Compatibility Rules

> **ROS Event Compatibility Rules — 事件兼容性规则与 Schema 演进规范**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-3 | Depends on: D2-1, D2-2
> Status: DRAFT

---

## 1. Consumer Contract（消费者契约）

### 1.1 消费者可以信赖什么

| 可依赖字段 | 级别 | 来源 | 说明 |
|:-----------|:----|:-----|:------|
| `metadata.identity.event_id` | M | D2-2 | 永远存在，UUID v4 |
| `metadata.identity.event_type` | M | D2-1/D2-2 | 永远存在，`{capability}.{action}` |
| `metadata.identity.version` | M | D2-2 | integer ≥1 |
| `metadata.context.timestamp` | M | D2-2 | ISO 8601 |
| `metadata.context.source` | M | D2-2 | Capability ID |
| `metadata.context.trace_id` | M | D2-2 | 32 hex |
| `metadata.context.tenant_id` | M | D2-2 | 多租户 ID |
| `payload` 中的 M 字段 | M | Event Schema | 存在直到 MAJOR 版本升级 |

### 1.2 消费者不能信赖什么

| 不可依赖 | 原因 |
|:---------|:------|
| `metadata.context.causation_id` | 独立事件为 null（级别 O） |
| `metadata.context.user_id` | 系统事件可能无用户上下文（级别 O） |
| `metadata.context.correlation_id` | System/Audit 事件可为 null（级别 M*） |
| `payload` 中的 O 字段 | Producer 可省略 |
| 字段的**顺序** | JSON 对象无顺序保证 |
| 字段缺失与 `null` 值的区分 | 需分别处理 |

### 1.3 Consumer 实现规范

**Consumer 必须：**
1. 忽略未知字段 — Forward Compatibility
2. M 字段做非空校验 — 启动时验证
3. O 字段做防御性编程 — `get(field, default)`
4. 不依赖字段顺序 — 用字段名访问
5. 不硬编码版本号 — 支持 `version >= 1` 而非 `version == 1`

**Consumer 禁止：**
6. 禁止在生产代码中断言 M 字段之外的字段存在
7. 禁止基于 event_type 做字符串精确匹配 — 用前缀匹配 `plan.*`

---

## 2. Schema Evolution Rules（Schema 演进规则）

### 2.1 操作分类矩阵

| 操作 | 版本影响 | 兼容性 | 要求 |
|:-----|:---------|:-------|:-----|
| 新增 Optional 字段 | **不升级** | 完全兼容 | Release Notes |
| 新增 Mandatory 字段 | **MINOR (+1)** | Forward Only | Migration Guide |
| 修改字段描述/示例 | **不升级** | 完全兼容 | Release Notes |
| 新增 enum 值 | **不升级** | 完全兼容 | Consumer 需支持 |
| 删除 enum 值 | **MAJOR (+n)** | Breaking | Breaking Process |
| 删除 Optional 字段 | **MAJOR (+n)** | Breaking | Breaking Process |
| 删除 Mandatory 字段 | **MAJOR (+n)** | Breaking | Breaking Process |
| 重命名字段 | **MAJOR (+n)** | Breaking | Breaking Process |
| 字段类型变窄 | **MAJOR (+n)** | Breaking | 例: string→enum |
| 字段类型变宽 | **不升级** | 兼容 | 例: enum→string |
| 新增 metadata 字段 | **不升级** | Forward Compatible | Consumer 忽略 |
| 升级 M→M* | **不升级** | 兼容 | D2-2 规则 |
| 删除 metadata M 字段 | **MAJOR (禁止)** | Breaking | 平台级变更，Board 批准 |

### 2.2 版本号规则

```
version = integer, 起点为 1

不升级: 新增 Optional | 修改描述 | 新增 enum 值 | 类型变宽 | 新增 metadata 字段
MINOR:  新增 Mandatory 字段 (+1)
MAJOR:  删除字段 | 重命名 | 类型变窄 | 删除 enum 值 | 删除 metadata M 字段

event_type 永远不变。版本号通过 metadata.identity.version 字段区分。
```

### 2.3 event_type 永远不变

| 变更场景 | event_type | version |
|:---------|:-----------|:--------|
| 发布 v1 | `plan.created` | 1 |
| 新增 Optional 字段 | `plan.created` | 1 (不变) |
| 新增 Mandatory 字段 | `plan.created` | 2 |
| Payload 结构重构 | `plan.created` | 3 |

---

## 3. Forward / Backward Compatibility

### 3.1 定义

```
Forward Compatibility (向前兼容):
  旧 Producer → 新 Consumer
  实现: Consumer 忽略未知字段、O 字段防御性处理

Backward Compatibility (向后兼容):
  新 Producer → 旧 Consumer
  实现: Producer 不删除 M 字段、新增字段只加 O 字段

Full Compatibility = Forward + Backward
```

### 3.2 兼容性矩阵

| Producer | Consumer | 兼容? | 条件 |
|:--------:|:--------:|:-----:|:------|
| v1 | v1 | ✅ Full | 默认 |
| v1 | v2 | ✅ Forward | Consumer v2 忽略 v2 新增字段 |
| v2 (+O) | v1 | ✅ Backward | v1 Consumer 忽略 v2 新增 O 字段 |
| v2 (+M) | v1 | ❌ Breaking | v1 Consumer 缺少 M 字段 |
| v2 (del) | v1 | ❌ Breaking | v1 Consumer 依赖已删除字段 |

### 3.3 兼容性测试要求

每对 (Producer V, Consumer W) 组合必须通过：
1. Consumer 消费事件不崩溃
2. Consumer 正确提取所有 M 字段
3. Consumer 默认处理缺失 O 字段
4. Consumer 不因新增 metadata 字段失败

---

## 4. Breaking Change Detection（破坏性变更检测）

### 4.1 自动检测清单

| # | 检查 | 判定 | 严重度 |
|:-:|:-----|:-----|:------:|
| 1 | M 字段删除 | payload.required 字段移除 → Breaking | 🔴 Critical |
| 2 | M 字段重命名 | 字段名变更但语义相同 → Breaking | 🔴 Critical |
| 3 | O 字段删除 | properties 中移除 → Breaking | 🟠 High |
| 4 | 类型变窄 | string→enum, number→integer → Breaking | 🟠 High |
| 5 | enum 值删除 | enum 数组元素移除 → Breaking | 🔴 Critical |
| 6 | metadata M 字段变更 | 删除 M 字段 → 禁止（平台级） | 🔴 Critical |
| 7 | $ref 断裂 | 引用文件不存在 → 编译错误 | 🔴 Critical |

### 4.2 CI/CD 集成

```yaml
compatibility-checks:
  - breaking-change-detection   # Check 1-7
  - schema-validation           # JSON Schema 合法性
  - consumer-compatibility-test # 旧 Consumer 消费新 Event
```

---

## 5. Field Classification（字段分类规则）

### 5.1 分类决策树

```
新字段 → 是否需要 Consumer 据此做决策?
  ├── 是 → Consumer 不处理是否会出错?
  │   ├── 是 → M (Mandatory)
  │   └── 否 → 默认值有合理语义?
  │       ├── 是 → O (Optional, 附带 default)
  │       └── 否 → M* (条件必须)
  └── 否 → O (Optional)
```

### 5.2 分类转换边界

| 从→到 | M | M* | O | R |
|:------|:--|:---|:--|:--|
| **M** | — | ❌ | MAJOR | ❌ |
| **M*** | ❌ | — | ❌ | ❌ |
| **O** | MINOR | MINOR | — | MAJOR |
| **R** | ❌ | ❌ | ARCH | — |

> ❌ = 禁止 | ARCH = Architecture Board 批准 | MAJOR/MINOR = 版本递增

### 5.3 Default Value 策略

| 级别 | Default 策略 |
|:-----|:-------------|
| **M** | 无默认值 — Producer 必须提供 |
| **M*** | 无默认值 — 条件满足时必须提供 |
| **O** | 必须有默认值 — Consumer 使用 default |
| **R** | 不可用 |

---

## 6. Deprecation Policy（废弃策略）

### 6.1 时间线

```
ANNOUNCED (Day 0) → DEPRECATED (Day 30) → RETIRED (Day 90) → REMOVED (Day 180)
```

| 阶段 | 时间 | Producer | Consumer | Registry |
|:-----|:-----|:---------|:---------|:---------|
| **ANNOUNCED** | Day 0 | 继续发送 + 通知 | 开始评估 | status→Deprecated |
| **DEPRECATED** | Day 30 | 继续发送 + `deprecated: true` header | 启动迁移 | 更新通知 |
| **RETIRED** | Day 90 | 停止发送 | 必须完成迁移 | status→Retired |
| **REMOVED** | Day 180 | 删除代码 | 验证不再消费 | status→Archived |

**最短总时间：90 天（Constitution 第八条）**

### 6.2 紧急废弃

安全漏洞或数据泄露等情况：
- Board Chair 直接批准
- 时间线缩短至 **7 天**
- 事后补全文档

---

## 7. Compatibility Validation（兼容性验证）

### 7.1 自动验证方法

| 验证 | 工具 | 检查内容 |
|:-----|:-----|:---------|
| Schema Diff | `json-schema-diff` | Breaking Change 报告 |
| Consumer Simulation | `pytest` + TestClient | Consumer 不崩溃 |
| Event Replay | Event Store replay | 正确处理旧事件 |
| Schema Registration | CI Pipeline | 命名/Header/分类正确 |

### 7.2 验证脚本接口

```python
def check_breaking_changes(old_schema: dict, new_schema: dict) -> list[str]:
    """返回 Breaking Change 列表"""

def check_consumer_compatibility(
    consumer_fn, old_event: dict, new_event: dict
) -> bool:
    """Consumer 兼容性验证"""

def check_full_compatibility_matrix(
    schemas: list[dict], consumers: list
) -> dict:
    """完整 P×C 兼容性矩阵"""
```

---

## 8. 与 D2-1 / D2-2 的对齐

| D2-1 §3.3 | D2-3 细化 |
|:-----------|:-----------|
| "新增 Optional → 不升级" | §2.1: 7 种不升级操作精确列表 |
| "新增 Mandatory → MINOR" | §2.2: version +1, Migration Guide |
| "删除/重命名 → MAJOR" | §2.1: 11 种操作×3 种影响 |
| "90 天过渡期" | §6: 4 阶段时间线 |

| D2-2 §2.1 | D2-3 细化 |
|:-----------|:-----------|
| "M/M*/O/R" | §5.1: 分类决策树 |
| 级别定义 | §5.2: 互转边界表 |
| 无 Default 策略 | §5.3: Default Value 策略 |

---

## 9. Constitution Compliance

| 条款 | 如何满足 |
|:-----|:---------|
| 第四条 — 事件驱动 | Consumer Contract 保证事件可信赖 |
| 第八条 — 向下兼容 | Forward/Backward 矩阵 + 90 天 Deprecation |
| 第十条 — 架构优先 | Breaking Change 必须 Board 批准 |
| 第一条 — 数据主权 | M 字段属于 Producer Capability |

---

## 10. 引用

| 引用 | 位置 |
|:-----|:------|
| D2-1 Event Identity Standard | `docs/events/event-identity-standard.md` |
| D2-2 Event Metadata Standard | `docs/events/event-metadata-standard.md` |
| Engineering Standard V1.0 | `docs/standards/engineering-standard-v1.md` |
| ROS Constitution | `CONSTITUTION.md` |

---

*D2-3: Event Compatibility Rules V1.0 — DRAFT*
*Capability: Planning | Baseline: PC-1.0-BL1*
*Depends on: D2-1 (Certified), D2-2 (Certified)*
