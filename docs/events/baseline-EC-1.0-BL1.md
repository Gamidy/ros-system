# Baseline: EC-1.0-BL1

> **Planning Capability — Event Contract Baseline**
>
> 本 Baseline 标记 Planning Capability Phase 2 完成时的冻结状态。
> 以后任何事件契约修改必须从这个 Baseline 演进。

---

## Baseline 元数据

| 字段 | 值 |
|:-----|:-----|
| **Baseline ID** | **EC-1.0-BL1** |
| **Parent Baseline** | PC-1.0-BL1 |
| **Capability** | Planning (Product Planning) |
| **Phase** | 2 — Event Contract |
| **Status** | FROZEN |
| **RFC** | RFC-2026-001 V2.0 |
| **Board Score** | 98.6/100 |
| **Board Decision** | ✅ PASS |

## Phase 2 交付物清单

| # | Deliverable | File | Status |
|:-:|:------------|:-----|:-------|
| D2-1 | Event Identity Standard | `docs/events/event-identity-standard.md` | ✅ Certified |
| D2-2 | Event Metadata Standard | `docs/events/event-metadata-standard.md` | ✅ Certified |
| D2-3 | Event Compatibility Rules | `docs/events/event-compatibility-standard.md` | ✅ Certified |
| D2-4 | Event Validation Framework | `docs/events/event-validation-framework.md` | ✅ Certified |
| D2-5 | Event Registry | `docs/events/event-registry.yaml` | ✅ Certified |
| D2-6 | Consumer Matrix | `docs/events/consumer-matrix.yaml` | ✅ Certified |
| D2-7 | Replay Certification Report | `docs/events/replay-certification-template.md` | ✅ Template |

## 文件清单

| 文件 | Git Commit | 说明 |
|:-----|:-----------|:------|
| `docs/events/event-identity-standard.md` | `321f9f4` | 命名/分类/生命周期/版本策略 |
| `docs/events/event-metadata-standard.md` | `aba94f3` | 10 字段 Header (identity+context) |
| `docs/events/event-compatibility-standard.md` | `e0d92b8` | Consumer Contract / Schema Evolution |
| `docs/events/event-validation-framework.md` | `d416880` | 双端验证/CI Pipeline/DLQ |
| `docs/events/event-registry.yaml` | `3882c3a` | 5 事件 (Category/Criticality/Lifecycle) |
| `docs/events/consumer-matrix.yaml` | `3882c3a` | 11 Consumer 记录 |
| `docs/events/replay-certification-template.md` | `TBD` | Replay 验证模板 |
| `docs/events/schemas/event-header.schema.json` | `aba94f3` | Header JSON Schema |
| `docs/events/schemas/event-envelope.schema.json` | `aba94f3` | Envelope JSON Schema |
| `docs/events/schemas/compatibility-rules.schema.json` | `e0d92b8` | 兼容性规则 (13 op × 11 trans) |

## Board 三项强制要求

| 要求 | 状态 | 实现位置 |
|:-----|:------|:---------|
| A — Event Classification | ✅ | D2-1 §2 + D2-5 Registry |
| B — Event Lifecycle | ✅ | D2-1 §3 + D2-5 Registry Lifecycle |
| C — Consumer Matrix | ✅ | D2-6 consumer-matrix.yaml |

## 演进规则

1. **本 Baseline 已冻结。** 事件契约文件不可直接修改。
2. 任何修改必须：
   - 从 EC-1.0-BL1 创建分支
   - 通过 Breaking Change Detection (D2-3)
   - Architecture Board 评审
   - 创建新的 Baseline (EC-1.0-BL2 或 EC-2.0-BL1)
3. Constitution 第八条（向下兼容）：Breaking Change 必须有 90 天过渡期

---

*Baseline: EC-1.0-BL1*
*Parent: PC-1.0-BL1*
*冻结日期: 2026-06-30*
*创建者: ROS Architecture Board*
