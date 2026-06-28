# 🏛️ ECR / ECO 模块 — Architecture Board 正式裁决

> 审查标准：工业 PLM / Siemens Teamcenter / Windchill  
> 审查日期：2026-07-01  
> 审批状态：**APPROVED**（含 P0 强制性修复要求）

---

## 1️⃣ ECR 状态机

### 当前设计
```
DRAFT → SUBMITTED → REVIEWING → APPROVED → CONVERTED
                                              → REJECTED
```

### Board 裁决

| 状态 | 决策 | 说明 |
|:----|:-----|:-----|
| DRAFT | ✅ 保留 | — |
| SUBMITTED | ✅ 保留 | — |
| REVIEWING | ✅ 保留 | — |
| APPROVED | ✅ **必须保留** | 关键状态 |
| **CONVERTED** | ✅ **不可逆终端状态（Immutable Terminal State）** | ECR→ECO是工业标准"单向映射"，避免回滚污染BOM/ECO链，保证Digital Thread完整性 |
| **REJECTED** | ✅ **终端状态** | 禁止从REJECTED修改后重新提交 |

### ⚠️ 重新提交规则

```
REJECTED → 修改 → 再 SUBMITTED   ❌ 不允许
REJECTED → 新建 ECR v2 → SUBMITTED ✅ 允许
```

### ✅ 最终状态机（Board版）

```
DRAFT
  → SUBMITTED
    → REVIEWING
      → APPROVED
        → CONVERTED  (TERMINAL)
        → REJECTED   (TERMINAL)
```

---

## 2️⃣ ECO 状态机

### 当前设计
```
DRAFT → IMPLEMENTING → VERIFIED → EFFECTIVE → CLOSED
```

### Board 裁决

| 状态 | 决策 | 说明 |
|:----|:-----|:-----|
| DRAFT | ✅ 保留 | — |
| IMPLEMENTING | ✅ 保留 | — |
| VERIFIED | ✅ 保留 | — |
| EFFECTIVE | ✅ **必须保留** | 关键生产状态 |
| CLOSED | ✅ 保留 | — |
| **ROLLBACK_REQUIRED** | 🔧 **必须新增** | BOM更新失败后的补偿状态 |

### ⚠️ BOM 更新失败机制（必须实现）

**正确设计流程：**

```
ECO → EFFECTIVE
        ↓
   Trigger BOM Update
        ↓
   ┌─ SUCCESS → CLOSED
   └─ FAILURE → COMPENSATION
```

**推荐方案 A（3次重试队列）：**

```
BOM Update FAILED
  → Retry #1 FAILED
    → Retry #2 FAILED
      → Retry #3 FAILED
        → STATE: ROLLBACK_REQUIRED
```

**高级方案 B（Saga Compensation）：**
- revert BOM
- revert ECO state
- notify engineering

### ✅ 最终状态机（Board版）

```
DRAFT
  → IMPLEMENTING
    → VERIFIED
      → EFFECTIVE
        → CLOSED
        → ROLLBACK_REQUIRED (BOM失败补偿)
```

---

## 3️⃣ 审批流设计

### 当前设计（待修正顺序）
```
研发总监 → 品质工程师 → 模块经理
```

### Board 裁决

| 项目 | 决策 | 说明 |
|:----|:-----|:-----|
| 审批模式 | ✅ **顺序审批（Sequential Approval）** | 符合 PLM 标准 |
| 批准后自动推进 | ✅ **必须实现 Event Driven** | All Approved → 自动推进到 APPROVED |
| 拒即终端 | ✅ **Any Rejected → 立即 REJECTED** | — |
| **审批顺序** | 🔧 **修正为：模块经理 → 研发总监** | 用户明确要求的两级审批 |

### 自动推进机制

```
Approve Step Completed
  → Check all approvers done
    → ALL ✅ → ECR.APPROVED
    → ANY ❌ → ECR.REJECTED (immediate)
```

### ✅ 最终审批链（用户确认）

```
模块经理（第一级审批）
  → 研发总监（第二级审批）
```

---

## 4️⃣ 前端设计

### 当前问题
`ChangesView.vue` 仍作为旧入口存在。

### Board 裁决

| 页面 | 策略 |
|:----|:-----|
| `ChangesView.vue` | ❌ **deprecated** — 废弃，不再作为主入口 |
| `/ecr` | ✅ **新主入口** — 已就绪 |
| `/eco` | ✅ **新主入口** — 已就绪 |

### ✅ 推荐新架构

```
/ecr
  ├── ECR List          — 列表视图
  ├── ECR Detail        — 详情页
  ├── Approval Flow     — 审批流展示
  └── Convert Action    — 转ECO操作

/eco
  ├── ECO List           — 列表视图
  ├── ECO Execution Timeline — 执行时间线
  ├── BOM Impact View    — BOM影响分析
  └── Effectivity Control — 生效控制
```

---

## 5️⃣ 强制性修复清单（P0）

| # | 模块 | 修复项 | 优先级 |
|:-:|:----|:-------|:------:|
| 1 | ECR | REJECTED 改为不可逆终端状态，禁止重新提交 | **P0** |
| 2 | ECO | 新增 `ROLLBACK_REQUIRED` 状态 | **P0** |
| 3 | ECO | BOM更新失败重试队列（Retry 3次 → 补偿状态） | **P0** |
| 4 | 审批链 | 审批顺序修正为：模块经理 → 研发总监 | **P0** |
| 5 | 前端 | `ChangesView.vue` 标记废弃 | **P0** |

---

## 📊 Final Verdict

| 模块 | 裁决 |
|:----|:-----|
| ECR 状态机 | ✅ **APPROVED** — CONVERTED=TERMINAL, REJECTED=不可重新提交 |
| ECO 状态机 | ✅ **APPROVED** — 需补充ROLLBACK_REQUIRED和BOM重试队列 |
| 审批流 | ✅ **APPROVED** — Sequential OK, 顺序需修正 |
| 前端 | ✅ **APPROVED** — ChangesView废弃, /ecr /eco 为主入口 |
| **总评** | ✅ **APPROVED with P0 fixes** |

> *Board Chair：Architecture Board  
> 下一步建议：ECR/ECO Event Contract Phase（强状态机+强事务链+强BOM影响+强Saga依赖）*
