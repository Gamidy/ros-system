# ROS Capability Engineering Methodology

> **所有 Capability 统一遵循的 7 阶段治理与交付流程。**
>
> 这是 ROS 与传统 PLM 平台最本质的区别之一——统一的 Capability Engineering Methodology。

---

## 生命周期全景

```
Capability Proposal (RFC)
        │
        ▼
Phase 1 ─── Capability Contract ─── FROZEN
        │
        ▼
Phase 2 ─── Event Contract ─────── CERTIFIED
        │
        ▼
Phase 3 ─── Data Contract ──────── CERTIFIED
        │
        ▼
Phase 4 ─── Implementation ─────── COMPLETED
        │
        ▼
Phase 5 ─── Compliance Review ──── PASS
        │
        ▼
Phase 6 ─── Architecture Validation ─── PASS
        │
        ▼
Phase 7 ─── Registry & Release ─── BASELINE
```

---

## Phase 1 — Capability Contract（合约冻结）

**目标**：冻结 Capability 的 Interface、Owner、Dependencies、数据所有权。

| 产出 | 说明 |
|:-----|:------|
| `capability.yaml` | 合约主文件（Interface / Provides / Consumes / Produces / Owner / Dependencies） |
| `registry.yaml` | Registry 注册信息 |
| Baseline | 冻结基线标记 |

**验收标准**：
- [ ] Capability Contract YAML 已冻结
- [ ] Registry 已建立
- [ ] Constitution 12 条全部通过
- [ ] Architecture Principles 6 条全部通过
- [ ] AI-Z Review 评分 ≥ 7
- [ ] Board 审核通过

---

## Phase 2 — Event Contract（事件契约认证）

**目标**：建立完整的事件契约平台，包括 Identity、Metadata、Compatibility、Validation、Registry、Replay Certification。

| 子阶段 | 说明 |
|:-------|:------|
| 2.1 Event Identity | 统一事件命名规范 |
| 2.2 Event Metadata | 统一 Header（10 个必填字段） |
| 2.3 Event Compatibility | Mandatory / Optional / Deprecated / Reserved 字段定义 |
| 2.4 Event Validation | Schema Validation（Producer + Consumer 双端） |
| 2.5 Event Registry | 事件注册表（Event / Version / Producer / Consumer / Status） |
| 2.6 Event Replay Certification | Replay → State → Snapshot → Current State 一致性验证 |

**验收标准**：
- [ ] Event Naming 100% 符合规范
- [ ] Event Metadata 统一 Header
- [ ] Schema Validation Producer + Consumer 全覆盖
- [ ] Event Registry 已建立
- [ ] Replay Test 100% 通过
- [ ] Version Policy 已验证
- [ ] Constitution Compliance PASS

**Gate**：Event Certification 通过后才能进入 Phase 3。

---

## Phase 3 — Data Contract（数据契约认证）

**目标**：冻结数据模型，确保与 Data Standard 对齐。

| 产出 | 说明 |
|:-----|:------|
| Data Model Audit | 模型字段与 Data Standard 一致性检查 |
| Migration Plan | 数据迁移方案（如需） |
| Schema Versioning | 数据模型版本策略 |

**验收标准**：
- [ ] Data Model 100% 对齐 Data Standard
- [ ] Migration Plan 就绪
- [ ] Backward Compatibility 验证通过

---

## Phase 4 — Implementation（实现）

**目标**：基于已冻结的 Contract / Event / Data 实现代码。

| 内容 | 说明 |
|:-----|:------|
| API 实现 | 按 Capability Contract Interface |
| Event Bus 接入 | 按 Event Contract |
| Gate 规则实现 | 按 Governance Standard |
| 测试覆盖 | 按 Engineering Standard |

**约束**：
- ❌ 禁止边写代码边改 Event Schema
- ❌ 禁止绕过 Contract 新增 API
- ✅ Contract 冻结期间不修改合约文件

---

## Phase 5 — Compliance Review（合规审查）

**目标**：全面的 Constitution + Standards 合规检查。

| 审查项 | 说明 |
|:-------|:------|
| Constitution Review | 12 条原则逐条检查 |
| Architecture Review | Architecture Standard 对齐 |
| Security Review | 安全审计 |
| Data Review | Data Standard 对齐 |
| AI Review | AI Standard 对齐（如涉及 AI） |

---

## Phase 6 — Architecture Validation（架构验证）

**目标**：Architecture Board 最终验证。

| 验证项 | 说明 |
|:-------|:------|
| Architecture Board 评审 | 完整性 + 一致性 + 可演进性 |
| Downstream Compatibility | 下游消费者集成验证 |
| Performance SLA | 延迟/吞吐量验证 |

---

## Phase 7 — Registry & Release（注册发布）

**目标**：正式注册到 Capability Registry，标记就绪状态。

| 产出 | 说明 |
|:-----|:------|
| `registry.yaml` 更新 | status = implemented |
| Baseline 创建 | `{Capability}-{Version}-BL{Sequence}` |
| Release Notes | 变更日志 |

---

## 附录：Capability 状态定义

| 状态 | 含义 |
|:-----|:------|
| `proposal` | RFC 起草中 |
| `frozen` | Phase 1 完成，合约冻结 |
| `implementing` | Phase 2-4 进行中 |
| `certified` | Phase 5-6 完成，合规通过 |
| `released` | Phase 7 完成，可投产 |
| `deprecated` | 已废弃，不再维护 |

---

*ROS Capability Engineering Methodology V1.0*
*生效日期：2026-06-30*
*维护者：ROS Architecture Board*
