# Baseline: PC-1.0-BL1

> **Planning Capability — Baseline 基线**
>
> 本 Baseline 标记 Planning Capability Phase 1 完成时的冻结状态。
> 以后任何修改必须从这个 Baseline 演进，不得直接修改冻结文件。

---

## Baseline 元数据

| 字段 | 值 |
|:-----|:-----|
| **Baseline ID** | `PC-1.0-BL1` |
| **Capability** | Planning (Product Planning) |
| **Phase** | 1 — Capability Contract |
| **Status** | FROZEN |
| **RFC** | RFC-2026-001 V2.0 |
| **Board Score** | 98.6/100 |
| **Board Decision** | ✅ PASS |

## 文件清单

| 文件 | Hash (SHA256) | 说明 |
|:-----|:--------------|:------|
| `docs/capabilities/planning.capability.yaml` | `95ba321` (Git) | Capability 合约主文件 |
| `docs/capabilities/registry.yaml` | `95ba321` (Git) | Capability Registry |
| `docs/events/plan.created.v1.schema.json` | `95ba321` (Git) | 策划创建事件 Schema |
| `docs/events/plan.stage_advanced.v1.schema.json` | `95ba321` (Git) | 阶段推进事件 Schema |
| `docs/events/plan.approved.v1.schema.json` | `95ba321` (Git) | 审批通过事件 Schema |
| `docs/events/plan.released.v1.schema.json` | `95ba321` (Git) | 发布事件 Schema |
| `docs/events/plan.cost_updated.v1.schema.json` | `95ba321` (Git) | 成本更新事件 Schema |

## 审核结果

| 审核项 | 结果 |
|:-------|:------|
| Constitution Compliance (12条) | ✅ 全部通过 |
| Architecture Principles (6条) | ✅ 全部通过 |
| AI-Z Review Score | 8/10 PASS |
| RFC 8项 Board 整改 | ✅ 7 项完全满足，1 项已修复 |
| Medium Issues 关闭 | ✅ 3 项全部关闭 |

## 演进规则

1. **本 Baseline 已冻结。** 合约文件不可直接修改。
2. 任何修改必须：
   - 通过 RFC 流程
   - Architecture Board 评审
   - 创建新的 Baseline（PC-1.0-BL2 / PC-2.0-BL1 等）
3. Baseline 版本号格式：`{Capability}-{Major}.{Minor}-BL{Sequence}`

---

*Baseline: PC-1.0-BL1*
*冻结日期: 2026-06-30*
*创建者: ROS Architecture Board*
