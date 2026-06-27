# D2-4: Event Validation Framework

> **ROS Event Validation Framework — Schema 验证框架与集成规范**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-4 | Depends on: D2-1, D2-2, D2-3
> Status: DRAFT

---

## 1. Validation Architecture

```
Producer ──→ Pre-publish Validation ──→ Event Bus ──→ Pre-consume Validation ──→ Consumer
                    │                                               │
                    ↓                                               ↓
              Reject on Error                                 Warn/Reject on Error
                    │                                               │
                    ↓                                               ↓
              Audit Log                                         Dead Letter Queue
```

**双端验证原则**：Producer 端保证"发布即合规"，Consumer 端保证"消费即安全"。

---

## 2. Producer-Side Validation

### 2.1 验证时机

| 触发点 | 验证类型 | 阻断级别 |
|:-------|:---------|:---------|
| Schema 变更提交（PR） | 兼容性检测 | 🔴 阻断 CI |
| 事件发布前（运行时） | Schema 合法校验 | 🔴 阻断发布 |
| 预发布（Staging） | 集成验证 | 🟠 告警 |

### 2.2 验证清单

Publisher 必须在 `emit()` 前完成：

| # | 检查项 | 工具 | 失败处理 |
|:-:|:-------|:-----|:---------|
| 1 | metadata 完整性（10 字段） | JSON Schema `event-header.schema.json` | Reject + log |
| 2 | event_type 命名合规 | regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` | Reject + log |
| 3 | version 类型 | integer ≥ 1 | Reject + log |
| 4 | payload Schema 合法 | Capability Event Schema | Reject + log |
| 5 | trace_id 格式 | regex `^[0-9a-f]{32}$` | Warn + auto-gen |
| 6 | tenant_id 非空 | length ≥ 1 | Reject + log |
| 7 | correlation_id（Domain 事件） | non-null | Warn + auto-gen |

### 2.3 Producer SDK 接口

```python
class EventPublisher:
    def emit(self, event_type: str, payload: dict, **metadata) -> str:
        """
        发布事件，自动完成 Producer-side Validation。
        
        Args:
            event_type: '{capability}.{action}'
            payload: 业务数据 dict
            metadata: 可选覆盖 metadata 字段
        
        Returns:
            event_id: 发布成功的事件 ID
        
        Raises:
            SchemaValidationError: 验证失败
        """
        
    def validate(self, event: dict) -> ValidationResult:
        """独立验证方法，不发布事件。用于测试或预检。"""
```

---

## 3. Consumer-Side Validation

### 3.1 验证时机

| 触发点 | 验证类型 | 失败处理 |
|:-------|:---------|:---------|
| 事件到达（同步） | Schema 合法校验 | 入 Dead Letter Queue |
| 事件处理前 | M 字段非空校验 | 抛出 ConsumerException |
| 事件处理后 | 回调验证 | 审计日志 |

### 3.2 Consumer SDK 接口

```python
class EventConsumer:
    def consume(self, event: dict, handler: Callable) -> ConsumeResult:
        """
        消费事件，自动完成 Consumer-side Validation。
        
        Args:
            event: 完整 Event Envelope
            handler: 业务处理函数
        
        Returns:
            ConsumeResult(success, event_id, error)
        """
        
    def pre_validate(self, event: dict) -> ValidationResult:
        """消费前验证：metadata + M 字段完整性"""
```

---

## 4. Validation Pipeline（CI/CD）

### 4.1 Pipeline 阶段

```
┌─ PR Created ────────────────────────────────────────────────┐
│ Step 1: Schema Syntax Check                                 │
│   - JSON Schema 合法性（ajv / jsonschema 校验）              │
│   - event_type 命名合规                                     │
│                                                             │
│ Step 2: Breaking Change Detection (D2-3)                    │
│   - git diff old-schema ↔ new-schema                        │
│   - 运行 7 项 Breaking Change Check                         │
│   - 生成兼容性报告                                          │
│                                                             │
│ Step 3: Consumer Simulation                                 │
│   - 用 old Consumer 消费 new Event                          │
│   - 检查 Consumer 不崩溃                                     │
│                                                             │
│ Step 4: Schema Registration                                 │
│   - 注册到 Event Registry (D2-5)                            │
│   - 更新 Consumer Matrix (D2-6)                             │
│                                                             │
│ Step 5: Architecture Board Review（仅 MAJOR 变更）           │
│   - Breaking Change 走 RFC 流程                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 CI 配置模板

```yaml
# .github/workflows/event-validation.yml
name: Event Schema Validation
on:
  pull_request:
    paths:
      - 'docs/events/**'
      - 'docs/events/schemas/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Schema Syntax Check
        run: |
          for f in docs/events/schemas/*.json; do
            python3 -c "import json; json.load(open('$f'))" || exit 1
          done
      - name: Breaking Change Detection
        run: |
          python3 scripts/check_breaking_changes.py
      - name: Consumer Simulation
        run: |
          python3 -m pytest docs/events/tests/ -v
```

---

## 5. Error Handling

### 5.1 验证失败处理矩阵

| 失败类型 | Producer | Consumer | 恢复方式 |
|:---------|:---------|:---------|:---------|
| Schema 语法错误 | ❌ 阻断发布 | ❌ 入 DLQ | 修复 Schema + 重发 |
| M 字段缺失 | ❌ 阻断发布 | ❌ 入 DLQ | 补齐字段 |
| O 字段缺失 | ✅ 允许（Warn） | ✅ 默认值处理 | 不改 |
| event_type 未知 | — | ⚠️ 跳过 + Warn | 检查 Registry |
| trace_id 无效 | ✅ 自动生成替代 | ✅ 忽略 | 无需处理 |
| 版本不兼容 | ❌ 阻断升级 | ⚠️ 回退到旧版本 | Consumer 升级 |

### 5.2 Dead Letter Queue（死信队列）

验证失败的事件入 DLQ：

```json
{
  "dlq_entry": {
    "original_event": { },
    "failure_reason": "M field 'plan_id' missing in payload",
    "failed_at": "2026-06-30T23:00:00Z",
    "source": "consumer-validation",
    "retry_count": 0,
    "status": "pending_review"
  }
}
```

DLQ 管理：
- 自动重试 3 次（指数退避）
- 超过 3 次 → 标记 `failed`，人工介入
- 人工处理后 → 标记 `resolved`，可重新入队列

---

## 6. Test Strategy

### 6.1 测试覆盖要求

| 测试类型 | 覆盖目标 | 框架 |
|:---------|:---------|:-----|
| Schema 单元测试 | 每个 Schema 文件 ≥ 1 测试 | `pytest + jsonschema` |
| Validation 单元测试 | Producer/Consumer SDK 全覆盖 | `pytest` |
| 兼容性测试 | 每对 P×C 版本组合 | `pytest + parametrize` |
| DLQ 集成测试 | DLQ 入/出/重试/人工 | `pytest + TestClient` |
| CI Pipeline 测试 | 完整 Pipeline 端到端 | `act` (本地 CI 模拟) |

### 6.2 测试示例

```python
import json, pytest
from jsonschema import validate, ValidationError

# 分层验证：Envelope → Header → Payload
ENVELOPE_SCHEMA = json.load(open("docs/events/schemas/event-envelope.schema.json"))
HEADER_SCHEMA   = json.load(open("docs/events/schemas/event-header.schema.json"))
PLAN_SCHEMAS = {
    "plan.created": json.load(open("docs/events/plan.created.v1.schema.json")),
}

class TestEventValidation:
    def _build_event(self, **overrides) -> dict:
        """构造一个兼容 D2-2 Envelope 格式的测试事件"""
        event = {
            "metadata": {
                "identity": {
                    "event_id": "550e8400-e29b-41d4-a716-446655440000",
                    "event_type": "plan.created",
                    "version": 1
                },
                "context": {
                    "timestamp": "2026-06-30T23:00:00+08:00",
                    "source": "planning",
                    "producer": "planning.product_plan_workflow",
                    "correlation_id": "abc12345-...",
                    "causation_id": None,
                    "trace_id": "0af7651916cd43dd8448eb211c80319c",
                    "tenant_id": "default"
                }
            },
            "payload": {"plan_id": "PP-20260630-0001", "name": "test", "created_by": "pm"}
        }
        # 应用覆盖
        import copy
        result = copy.deepcopy(event)
        for key, val in overrides.items():
            keys = key.split(".")
            target = result
            for k in keys[:-1]:
                target = target[k]
            target[keys[-1]] = val
        return result

    def _validate_event(self, event: dict) -> None:
        """分层验证：Envelope → Header → Payload"""
        # 第 1 层：Envelope 格式（metadata + payload）
        validate(instance=event, schema=ENVELOPE_SCHEMA)
        # 第 2 层：Header 字段（metadata 下所有字段）
        validate(instance=event["metadata"], schema=HEADER_SCHEMA)
        # 第 3 层：Payload 业务 Schema
        event_type = event["metadata"]["identity"]["event_type"]
        if event_type in PLAN_SCHEMAS:
            validate(instance=event["payload"], schema=PLAN_SCHEMAS[event_type])

    def test_valid_plan_created(self):
        event = self._build_event()
        self._validate_event(event)           # 三层验证

    def test_invalid_empty_event_id(self):
        event = self._build_event(**{"metadata.identity.event_id": ""})
        with pytest.raises(ValidationError):
            self._validate_event(event)

    def test_invalid_empty_tenant_id(self):
        event = self._build_event(**{"metadata.context.tenant_id": ""})
        with pytest.raises(ValidationError):
            self._validate_event(event)
```

---

## 7. Constitution Compliance

| 条款 | 如何满足 |
|:-----|:---------|
| 第四条 — 事件驱动 | 双端验证保证 Event Bus 消息质量 |
| 第六条 — 决策可追溯 | DLQ 记录所有验证失败事件 |
| 第八条 — 向下兼容 | Breaking Change Detection 自动阻止不兼容变更 |
| 第十条 — 架构优先 | MAJOR 变更需 Board 批准 |

---

*D2-4: Event Validation Framework V1.0 — DRAFT*
*Capability: Planning | Baseline: PC-1.0-BL1*
*Depends on: D2-1, D2-2, D2-3*
