# ROS Foundation

> **ROS Foundation 是 ROS 平台不可变的核心治理体系。**
>
> 状态：**LTS（Long Term Support）— 已冻结 ✅**
> 版本：**1.1**（绑定 Constitution 版本号）
>
> 以后：Foundation 不再频繁修改，只允许增补附录。
> Architecture 可以升级，Capability 可以增加，Agent 可以变化，AI 可以变化——
> 但是 Foundation 保持稳定。

---

## Preamble

**ROS exists to ensure that engineering knowledge, product data, and AI collaboration remain trustworthy, traceable, evolvable, and governed throughout the entire product lifecycle.**

**ROS 存在的使命，是保证产品研发全过程中的知识、数据、AI 与决策始终可信、可追溯、可演进、可治理。**

---

## 五层治理体系

```
  ┌─────────────────────────────────────────────────────┐
  │            ROS Foundation（最高层 — 已冻结）           │
  │   Constitution · Change Policy · LTS Versioning     │
  ├─────────────────────────────────────────────────────┤
  │              Architecture Standards                   │
  │   分层 · 边界 · 事件 · 数字主线 · AI架构 · 数字孪生    │
  ├─────────────────────────────────────────────────────┤
  │              Engineering Standards                    │
  │   Data · Engineering · AI · Governance · Operation   │
  ├─────────────────────────────────────────────────────┤
  │              Capability Specifications                │
  │   每个 Capability 的输入/输出/依赖/Owner 定义         │
  ├─────────────────────────────────────────────────────┤
  │              Implementation（代码）                    │
  │   具体的 API、前端、Agent、部署                       │
  └─────────────────────────────────────────────────────┘
```

**任何 Capability 不得违反 Foundation。** 这是红线。

---

## Foundation 组成

ROS Foundation 包含两个文件：

| 文件 | 位置 | 内容 |
|:-----|:------|:------|
| **CONSTITUTION.md** | 项目根目录 | 十二条根本原则 + Change Policy |
| **FOUNDATION.md** | 项目根目录 | 五层治理 + Board + RFC + Registry + Roadmap |

所有其它标准（Architecture / Data / Engineering / AI / Governance / Operation）位于 `docs/standards/`，
作为 Foundation 的支撑体系。

---

## 版本策略

```
Foundation 1.0  → 初始发布（LTS）
Foundation 1.x  → 附录增补、勘误、非实质性澄清
Foundation 2.0  → 仅当 Constitution 条款发生变化时
```

**Foundation 版本号与 Constitution 版本号绑定。**
Constitution 不变 → Foundation 不升 2.0。

---

## Foundation Change Policy

ROS Foundation 已进入 **LTS 状态**。原则上不再修改，只允许增补附录。

### 允许修改的唯一条件（必须全部满足）

| # | 条件 | 说明 |
|:-:|:-----|:------|
| 1 | **违反 Constitution** | 现有条款与 Constitution 冲突 |
| 2 | **影响 Platform Evolution** | 不修改则平台无法演进 |
| 3 | **影响 Digital Thread** | Digital Thread 出现不可修复的断点 |
| 4 | **影响 Data Ownership** | 数据所有权模型需要调整 |
| 5 | **Architecture Board 全票通过** | 全体 Board 成员一致同意 |

### 修改流程

```
Proposal → Architecture Board 预审 → RFC → 全体讨论
→ 全票投票 → Chair 签署 → 发布新版本 + 变更日志
```

---

## ROS Architecture Board

ROS 的最高技术治理机构。

### 组成

| 角色 | 职责 |
|:-----|:------|
| **Chief Architect** | Board Chair，最终决策 |
| **Business Architect** | 业务架构 / Capability 治理 |
| **Data Architect** | 数据架构 / Data Standard 维护 |
| **AI Architect** | AI 架构 / AI Standard 维护 |
| **QA Architect** | 质量架构 / 合规门禁 |
| **Security Architect** | 安全架构 / 权限治理 |

### 决策权限

| 决策类型 | 方式 |
|:---------|:------|
| Foundation 修改 | 全票通过 |
| 新 Capability 批准 | 共识制，Chair 1 票否决 |
| Architecture Review | RFC 评审 |
| 紧急决策 | Chair 裁定，事后通报 |

---

## RFC 流程

所有重大 Capability（Supplier / MES / CRM / Robot / Digital Twin 等）必须通过 RFC。

### RFC 生命周期

```
Idea
  ↓  [PM / Architect 提出]
RFC Draft
  ↓  [2 工作日预审]
Architecture Review
  ↓  [Board 评审：批准 / 拒绝 / 待补充]
Prototype（可选，高风险变更必须）
  ↓
Implementation
  ↓
Review（Post-Implementation Review）
  ↓
Release（进入 Capability Registry）
```

### RFC 元数据

```json
{
  "rfc_id": "RFC-2026-001",
  "title": "Supplier Capability",
  "status": "Approved",
  "author": "Chief Architect",
  "review_date": "2026-07-15",
  "board_decision": "Approved (unanimous)",
  "capability_ref": "CAP-SUPPLIER-001"
}
```

---

## Capability Registry

所有 Capability 的全局注册表。

| Capability | Owner | Status | Version | Dependencies | API Path |
|:-----------|:------|:-------|:--------|:-------------|:---------|
| Planning | PM | ✅ Released | 1.2 | — | `/api/pm/` |
| Verification | QA | ✅ Released | 1.1 | Planning | `/api/vr/` |
| Prototype | RD | ✅ Released | 1.0 | Planning | `/api/pt/` |
| Test | QA | ✅ Released | 1.0 | Verification | `/api/test/` |
| Certification | Cert | ✅ Released | 1.0 | Test | `/api/cert/` |
| ECO | PM | ✅ Released | 1.0 | Planning | `/api/eco/` |
| **Supplier** | **SCM** | **🔜 2027 Q1** | — | — | — |
| **Manufacturing** | **MFG** | **🔜 2027 Q2** | — | Planning | — |
| **Knowledge** | **AI** | **🔜 2027 Q3** | — | All | — |
| **Simulation** | **RD** | **🔜 2028** | — | Prototype | — |
| **Digital Twin** | **RD** | **🔜 2028** | — | All | — |
| **APS** | **MFG** | **🔜 2028** | — | Manufacturing | — |
| **Robot** | **New** | **🔜 TBD** | — | — | — |
| **Energy Storage** | **New** | **🔜 TBD** | — | — | — |

**规则**：每个 Capability 必须声明 Dependencies。依赖未就绪的 Capability 不可上线。

---

## Agent Registry

所有 Agent 的全局注册表。

| Agent | Owner | Input | Output | Permission | Status |
|:------|:------|:------|:-------|:-----------|:-------|
| Planner | PM | User Requirement | Task Plan | Suggest | ✅ Active |
| Architecture | Architect | Requirement Spec | Architecture Doc | Suggest (human approve) | ✅ Active |
| Coding | Tech | Task + Architecture | Code + Test | Auto | ✅ Active |
| Verifier | QA | Code + Requirement | Verification Report | Suggest | ✅ Active |
| Reviewer | Architect | Code Diff | Review Report + Score | **Block/Veto** | ✅ Active |
| Certification | Cert | Product + Market | Cert Evaluation | Suggest | ✅ Active |
| Knowledge | AI | Query | Knowledge | Suggest | ✅ Active |
| **Supplier** | **SCM** | **🔜 TBD** | | | **Planned** |
| **Simulation** | **RD** | **🔜 TBD** | | | **Planned** |

**规则**：每个 Agent 必须有明确的输入/输出契约。无契约的 Agent 不可上线。
Agent 实现可以替换，契约不可违背（Constitution 第九条）。

---

## Platform Roadmap

### 2026（Foundation 年）

| Capability | 状态 |
|:-----------|:------|
| ✅ Planning | Released |
| ✅ Verification | Released |
| ✅ Prototype | Released |
| ✅ Test | Released |
| ✅ Certification | Released |
| ✅ ECO | Released |
| ✅ **ROS Foundation** | **LTS ✅** |

### 2027（扩展年）

| Capability | 目标 | 依赖 |
|:-----------|:------|:------|
| Supplier Management | 2027 Q1 | Planning, ECO |
| Manufacturing Interface | 2027 Q2 | Planning, Prototype |
| Knowledge System | 2027 Q3 | All Capabilities |
| AI Agent Upgrade (L2) | 2027 Q4 | Knowledge |

### 2028（智能年）

| Capability | 目标 | 依赖 |
|:-----------|:------|:------|
| Simulation | 2028 Q1 | Prototype |
| Digital Twin | 2028 Q2 | All Capabilities |
| APS | 2028 Q3 | Manufacturing |
| AI Agent Upgrade (L3) | 2028 Q4 | Simulation, Twin |

### 2029+（生态年）

| Capability | 说明 |
|:-----------|:------|
| Robot Capability | 新产品线 |
| Energy Storage Capability | 新产品线 |
| Heat Pump Capability | 新产品线 |
| AI Agent Upgrade (L4) | 完全自主 |

---

## Foundation Repository

**ROS Foundation 应与代码仓库分离。**

建议独立仓库结构：

```
ros-foundation/
├── CONSTITUTION.md          # 十二条根本原则（LTS）
├── FOUNDATION.md            # 本文件（LTS）
├── docs/
│   ├── standards/
│   │   ├── architecture-standard-v1.md
│   │   ├── data-standard-v1.md
│   │   ├── engineering-standard-v1.md
│   │   ├── ai-standard-v1.md
│   │   ├── governance-standard-v1.md
│   │   └── operation-standard-v1.md
│   ├── governance/
│   │   ├── architecture-board-charter.md
│   │   ├── rfc-template.md
│   │   └── registry-maintenance.md
│   └── roadmap/
│       └── platform-roadmap.md
└── README.md
```

代码仓库（独立）：

```
ros-system/
├── backend/
├── frontend/
├── docker/
└── ...
```

这样 Foundation 不会和代码混在一起，Agent 和开发者可独立引用。

---

## 总结

```
ROS Foundation（LTS / 不可变）
    │
    ├── Constitution（12条）
    ├── Change Policy
    ├── 五层治理模型
    ├── Architecture Board
    ├── RFC 流程
    ├── Capability Registry
    ├── Agent Registry
    └── Platform Roadmap
        │
        ▼
ROS Platform（持续演进）
    │
    ├── Architecture Standards
    ├── Engineering Standards
    │
    ▼
ROS Capabilities（快速迭代）
    │
    ├── Planning
    ├── Verification
    ├── Certification
    ├── Supplier (2027)
    ├── Manufacturing (2027)
    ├── Simulation (2028)
    └── ...
```

---

*ROS Foundation V1.1 — LTS*
*冻结日期：2026-06-30*
*维护者：ROS Architecture Board*
