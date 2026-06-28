# 🏛️ ROS Change Control Engine v1.0
> 工业级 PLM 变更控制系统最终实现规范（Architecture Board Approved）

---

## 1. 系统定位

ROS Change Control Engine（CCE）是 ROS 平台中负责设计变更、工程变更与制造影响控制的核心子系统。
它覆盖：ECR / ECO / BOM 变更控制 / Prototype 影响分析 / Certification 影响评估 / Event 驱动变更传播

## 2. 核心设计原则（Constitution Level）

| 原则 | 说明 |
|:----|:------|
| **单向不可逆** | CONVERTED / CLOSED = TERMINAL STATE（不可回退） |
| **变更必须生成新实体** | REJECTED / MODIFIED = NEW ECR / ECO（禁止原地修改） |
| **Event 驱动优先** | 任何状态变化必须 emit Event |
| **Saga 保证一致性** | 跨模块变更 = Saga Transaction |

## 3. 状态机设计

### 3.1 ECR 状态机

```
DRAFT → SUBMITTED → REVIEWING → APPROVED → CONVERTED (TERMINAL)
                                     ↓
                                REJECTED (TERMINAL)
```

**规则：**
- REJECTED → ❌ 不允许重新提交，✔ 必须创建新 ECR（ECR v2）
- CONVERTED → ❌ 不可逆，✔ 已映射到 ECO

### 3.2 ECO 状态机

```
DRAFT → IMPLEMENTING → VERIFIED → EFFECTIVE → CLOSED
                                          ↓
                                    ROLLBACK_REQUIRED (COMPENSATION STATE)
```

**BOM 更新规则：**
```
ECO EFFECTIVE → Trigger BOM Update
  → SUCCESS → CLOSED
  → FAILURE → Retry (3 times) → FAIL → ROLLBACK_REQUIRED
```

**Retry 机制：** Celery Queue, max_retries=3, exponential backoff

## 4. 审批流设计

**标准审批链（Board 统一）：**
```
模块经理 → 研发总监 → 品质工程师
```

**规则：**
- ALL APPROVED → AUTO ADVANCE STATE
- ANY REJECTED → TERMINAL REJECTED
- ECO 必须全链通过才能 EFFECTIVE
- QA（品质工程师）为强制 Gate

## 5. Event 驱动机制

### ECR Events

| Event | 说明 |
|:------|:-----|
| `ecr.submitted` | 提交 |
| `ecr.reviewing` | 评审 |
| `ecr.approved` | 通过 |
| `ecr.converted` | 转 ECO |
| `ecr.rejected` | 终止 |

### ECO Events

| Event | 说明 |
|:------|:-----|
| `eco.implementing` | 执行中 |
| `eco.verified` | 验证 |
| `eco.effective` | 生效 |
| `eco.closed` | 完成 |
| `eco.rollback_required` | 补偿 |

## 6. BOM 变更控制机制

**工业级要求：**
```
ECO EFFECTIVE → BOM PATCH → Validation
```

**失败处理（强制）：**
```
FAIL → retry 3 times → ROLLBACK_REQUIRED → Saga compensation
```

## 7. Saga 事务模型

**ECO EFFECTIVE SAGA:**
1. Update BOM
2. Update Prototype
3. Update Certification Impact
4. Emit Event
> FAIL → rollback all steps

## 8. 前端架构规范

| 页面 | 状态 |
|:----|:-----|
| `/ecr` | ✅ 主入口 |
| `/eco` | ✅ 主入口 |
| `ChangesView.vue` | ❌ **deprecated** → redirect → `/ecr` |

## 9. Event Contract 标准

**Event Header（统一）：**
```
event_id | event_type | event_version | aggregate_id
aggregate_type | timestamp | producer | correlation_id
causation_id | tenant_id
```

**Compatibility:** Mandatory / Optional / Deprecated / Reserved, Backward compatible versioning required

## 10. System Boundary

| 模块 | 归属 |
|:----|:-----|
| Product Planning | ❌ 上游 |
| ECR | ✔ |
| ECO | ✔ |
| BOM | ✔ |
| Prototype | ✔ |
| Certification Impact | ✔ |

## 11. Architecture Level Summary

**ROS Change Control Engine** 是一个 Event-driven + Saga-based + BOM-aware + Approval-controlled 工业级变更系统。

## 12. 系统核心价值

| 能力 | 实现方式 |
|:----|:---------|
| **可追溯性（Traceability）** | 每个变更 = Event Chain |
| **可回滚性（Recoverability）** | ECO rollback_required + Saga |
| **可审计性（Auditability）** | Event Store + Registry + Versioning |

---

> **Final Verdict:** ROS Change Control Engine v1.0 已达到工业 PLM 级变更控制标准
> **下一步建议：** ECR/ECO Event Graph + BOM Impact Propagation Model
