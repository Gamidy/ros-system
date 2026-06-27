# D2-7: Replay Certification Report

> **ROS Event Replay Certification — Replay 一致性验证报告**
>
> Capability: Planning | Baseline: PC-1.0-BL1
> Phase 2 Deliverable: D2-7 | Status: TEMPLATE

---

## 1. Replay 验证目标

验证从 Event Store 重放事件是否能完全恢复系统状态。

### 验证公式：

```
Replay(Event Store) → State = Snapshot = Current State
  三者完全一致 → ✅ Certified
  任一不一致 → ❌ 不可发布
```

---

## 2. Replay 流程

```
Event Store (所有持久化事件)
    │
    ▼
Replay Engine (按时间顺序重放)
    │
    ▼
State Reconstruction (逐事件恢复状态)
    │
    ├── Checkpoint Snapshot (定期快照)
    └── Current State (最新状态)
    │
    ▼
Comparison (三路比对)
    │
    ├── Replay State = Snapshot → PASS
    └── Replay State = Current State → PASS
```

### 2.1 Replay 引擎要求

| 能力 | 要求 |
|:-----|:------|
| 事件排序 | 按 `timestamp ASC` + `event_id ASC`（处理时间戳相同） |
| 幂等重放 | 相同事件重复消费不影响最终状态 |
| 检查点跳过 | 从最近的 Checkpoint Snapshot 开始，跳过其包含的事件 |
| 错误恢复 | 单个事件失败 → 跳过 + 记录日志，不中断整体 Replay |
| 进度报告 | 每 1000 事件报告一次进度 |

### 2.2 涉及事件

| Event | Replay Required | 重放时影响 |
|:------|:---------------:|:-----------|
| `plan.created` | Yes | 重建策划记录 |
| `plan.stage_advanced` | Yes | 重建阶段历史 |
| `plan.approved` | Yes | 重建审批链状态 |
| `plan.released` | Yes | 重建发布状态 + 级联触发 |
| `plan.cost_updated` | No | 成本可最后对齐 |

---

## 3. 验证测试矩阵

### 3.1 单一事件 Replay

| 测试 | 输入 | 预期输出 | 验证方法 |
|:-----|:-----|:---------|:---------|
| `plan.created` replay | 1 × create event | 策划存在于 DB | DB 查询 |
| `plan.stage_advanced` x3 | 3 × advance events | 策划状态 = 第 3 阶段 | 状态校验 |
| `plan.approved` + `plan.released` | 2 events | 策划 = Released + Project 创建 | DB + API |
| `plan.cost_updated` x5 | 5 × cost changes | 成本 = 最后一次更新值 | 成本校验 |

### 3.2 全链路 Replay

```
Full Chain Test:
  事件序列: create → advance(×3) → approved → released → cost_updated(×2)
  
  预期最终状态:
    - ProductPlan: id=PP-20260630-0001, status=released
    - StageHistory: 3 次推进记录
    - CostRecords: 2 次成本更新
    - Project: 1 个关联项目（由 plan.released 触发）
  
  验证:
    1. Replay 后的 DB 状态 = 原始 DB 状态
    2. Replay 后的 API 查询 = 原始 API 响应
```

### 3.3 边界条件

| 测试 | 场景 | 预期 |
|:-----|:------|:------|
| 空 Event Store | 无事件 | Replay 后状态为空 |
| 重复事件 | event_id 重复 | 幂等：第二次被忽略 |
| 时间戳乱序 | 旧时间戳在新时间戳之后 | 按 event_id 排序修正 |
| 检查点恢复 | 从中间检查点开始 | 只重放检查点之后的事件 |
| 事件不完整 | plan.created 缺失 | 记录错误，继续处理其余事件 |

---

## 4. 验证报告模板

```json
{
  "replay_certification": {
    "capability": "planning",
    "baseline": "PC-1.0-BL1",
    "certified_at": "2026-06-30",
    "status": "PASS / FAIL",

    "summary": {
      "total_events_replayed": 1000,
      "failed_events": 0,
      "duration_seconds": 45,
      "throughput": "22 events/sec",

      "state_comparison": {
        "replay_vs_snapshot": "IDENTICAL",
        "replay_vs_current": "IDENTICAL",
        "snapshot_vs_current": "IDENTICAL"
      }
    },

    "test_results": [
      {
        "test": "plan.created replay",
        "status": "PASS",
        "input": "1 × plan.created event",
        "output": "ProductPlan PP-20260630-0001 exists in DB"
      },
      {
        "test": "full chain replay",
        "status": "PASS",
        "input": "8 events (create+advance×3+approved+released+cost×2)",
        "output": "All states match original"
      }
    ],

    "issues": [],
    "certified_by": "ROS Architecture Board"
  }
}
```

---

## 5. Replay SLA

| 指标 | 目标 |
|:-----|:-----|
| 10,000 events Replay | < 5 分钟 |
| 100,000 events Replay | < 30 分钟 |
| 1,000,000 events Replay | < 3 小时 |
| 数据零丢失 | 100% |
| 状态一致性 | 100% |

---

*D2-7: Replay Certification Report V1.0 — TEMPLATE*
*Capability: Planning | Baseline: PC-1.0-BL1*
