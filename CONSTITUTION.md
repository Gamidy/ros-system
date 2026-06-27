# ROS Constitution

> **ROS（R&D Operating System）是一个 AI-native、事件驱动、数据驱动、数字主线驱动的研发操作系统。**
>
> 本宪法是 ROS Foundation 的最高层——定义什么绝对不能做。
> 任何代码、任何 Agent、任何架构决策不得违反。
> 修改本宪法需 Architecture Board ≥ 75% 多数通过。

---

## Scope

本宪法适用于：

- **ROS Foundation** — 治理体系的最高层
- **ROS Platform** — 研发平台本身
- **所有 Capability** — Planning / Verification / Certification / Supplier / Manufacturing / Simulation / Digital Twin / Robot / Storage / APS / CRM 等
- **所有 Agent** — Planner / Architect / Coding / Reviewer / Verifier / Knowledge 等
- **所有 API** — 内部与外部接口
- **所有 Data Model** — 核心与扩展数据对象
- **所有 Event** — Event Bus 上流通的所有业务事件
- **所有 AI Decision** — AI 驱动的任何建议或自动决策

**任何新增模块默认适用本宪法。** 不适用需 Architecture Board 特别豁免。

---

## Preamble 序言

**ROS exists to ensure that engineering knowledge, product data, and AI collaboration remain trustworthy, traceable, evolvable, and governed throughout the entire product lifecycle.**

**ROS 存在的使命，是保证产品研发全过程中的知识、数据、AI 与决策始终可信、可追溯、可演进、可治理。**

这一页，是所有进入 ROS 仓库的人第一眼看到的内容。

---

## 第一条 — 数据主权

**所有数据。只有一个 Owner。**

每个核心数据对象必须有一个且唯一的所有者模块。非 Owner 模块只能通过事件订阅或只读接口访问。成本数据由 Product Planning 所有，测试数据由 QA 所有，认证数据由 Certification 所有——没有例外。

数据一致性从源头保证，不依赖事后对账。

---

## 第二条 — 数字主线

**Digital Thread。永远不能断。**

从 Market Requirement 到 Customer Feedback 的完整链路必须可追溯。信息在传递过程中不得丢失精度或语义。任何节点必须能追溯到源头，任何断点必须被自动检测和告警。

所有 Review 的第一项检查：有没有破坏 Digital Thread？如果有，直接 Reject。

---

## 第三条 — AI 真实性

**AI。永远基于事实。不能绕过治理。**

AI 的所有决策必须有可验证的事实依据。AI 不能直接修改成本数据、客户信息或 Gate 门禁结果。AI 的建议必须包含推理链和置信度，人工审批不可被 AI 代理。

AI 应该建议，不能裁决。真正批准的一定是人。

---

## 第四条 — 事件驱动

**任何 Capability。必须事件驱动。**

跨模块通信必须通过 Event Bus。禁止直接跨模块 API 耦合。每个事件必须有 event_id、trace_id 和版本号。Event Store 作为系统核心基础设施，所有事件持久化且支持 Replay。

整个 ROS 通过 Event Bus 统一。Saga、Replay、Event Store 长期存在。

---

## 第五条 — 知识结构化

**所有 Knowledge。必须结构化。**

Lessons Learned、Failure Mode、Engineering Rules 必须按照统一的知识分类体系存储。非结构化的文档不得进入知识库。知识的有效性必须有生命周期管理，过期知识必须自动标记。

Knowledge Graph、Ontology、Taxonomy 全部引用本条。

---

## 第六条 — 决策可追溯

**任何 Decision。必须可追溯。**

每次 Gate 决策、每次 ECO 审批、每次 AI 调用，必须记录决策人、决策依据、决策时间和决策结果。不可追溯的决策等于没有发生。

Gate / AI / Certification / ECO 全部统一 Trace。

---

## 第七条 — 规则配置化

**任何 Rule。必须配置化。**

Gate 门禁规则、认证判定规则、成本控制规则、市场准入规则——所有业务规则必须通过规则引擎配置，不得硬编码在代码中。规则必须有版本、有效期限和 Owner。

ROS 没有 Hard Code。

---

## 第八条 — 向下兼容

**所有 Platform。向下兼容。**

API 版本升级必须向后兼容。数据模型新增字段不得破坏现有消费方。标准废弃必须有至少 90 天过渡期。破坏性变更必须经过 Architecture Board 全体评审。

ROS 十年不会崩。

---

## 第九条 — Agent 可替换

**任何 Agent。必须可替换。**

每个 Agent 的输入输出契约必须明确定义。Agent 的实现可以升级、替换甚至废弃，只要满足契约。没有 Agent 可以成为平台的关键单点依赖。

GPT / Claude / Gemini / DeepSeek 全部可以替换。平台不绑定任何模型。

---

## 第十条 — 架构优先

**Architecture。永远优先于功能。**

任何功能需求如果与架构原则冲突，修改功能而非架构。短期便利不得以长期架构一致性为代价。每一行代码、每一个 Agent、每一次变更都必须通过 Architecture Review。

这一条永远放在最后——因为它代表整个 ROS 的价值观。

---

## 第十一条 — Engineering Truth

**Engineering Truth always overrides opinion. 工程事实永远凌驾于观点之上。**

实验说 Fail，AI 说 Pass——最终是 Fail。任何 Decision 必须基于 Evidence。直觉、地位、权威都不能替代可复现的实验数据。

---

## 第十二条 — Platform First

**任何 Capability 必须能够复用。**

不能为了一个产品写一套代码。新增 Capability 时，必须优先利用平台已有的架构能力、数据模型和基础设施。每个新增 Capability 需证明其在不同产品线间的可复用性。

这样 ROS 才能越来越强。

---

## Architecture Principles

| 原则 | 说明 |
|:-----|:------|
| **Simple over Complex** | 简单方案优先于复杂方案 |
| **Reuse over Rewrite** | 复用优先于重写 |
| **Platform over Project** | 平台思维优先于项目思维 |
| **Configuration over Code** | 配置化优先于硬编码 |
| **Evidence over Opinion** | 事实依据优先于主观判断 |
| **Event over Coupling** | 事件驱动优先于直接耦合 |

---

## Interpretation

本宪法的最终解释权属于 **Architecture Board**。

当不同标准之间发生冲突时，优先级如下：

```
Constitution（最高）
    ↓
Foundation
    ↓
Architecture Standard
    ↓
Engineering Standard
    ↓
Capability Specification
    ↓
Implementation（最低）
```

---

## Compliance

任何 Capability Merge 前必须完成：

| # | Review | 说明 |
|:-:|:-------|:------|
| 1 | ✅ Constitution Review | 是否违反十二条原则 |
| 2 | ✅ Architecture Review | 是否符合 Architecture Standard |
| 3 | ✅ Security Review | 是否有安全风险 |
| 4 | ✅ Data Review | 是否符合 Data Standard |
| 5 | ✅ AI Review（如涉及 AI）| 是否符合 AI Standard |

**Compliance Check 不通过 → Merge 阻塞。**

---

## Foundation Change Policy

ROS Foundation（包括本宪法及 FOUNDATION.md）已进入 **LTS（Long Term Support）** 状态。
原则上不再修改，只允许增补附录。

允许修改的唯一条件（必须全部满足）：

| # | 条件 | 说明 |
|:-:|:-----|:------|
| 1 | **违反 Constitution** | 现有条款与 Constitution 冲突 |
| 2 | **影响 Platform Evolution** | 不修改则平台无法演进 |
| 3 | **影响 Digital Thread** | Digital Thread 出现不可修复的断点 |
| 4 | **影响 Data Ownership** | 数据所有权模型需要调整 |
| 5 | **Architecture Board ≥ 75% 同意** | Board 成员 3/4 以上支持 |

### 版本策略

```
Foundation 1.0  → 初始发布（LTS）
Foundation 1.x  → 附录增补、勘误、非实质性澄清
Foundation 2.0  → 仅当 Constitution 条款发生变化时
```

**Foundation 版本号与 Constitution 版本号绑定。**
Constitution 不变 → Foundation 不升 2.0。

### 修改流程

```
Proposal → Architecture Board 预审 → RFC → 全体讨论
→ ≥ 75% 投票 → Chair 签署 → 发布新版本 + 变更日志
```

---

## 签署

**ROS Architecture Board**

| 角色 | 签名 | 日期 |
|:-----|:-----|:-----|
| Chief System Architect | | 2026-06-30 |
| Architecture Board Chair | | 2026-06-30 |
| Business Architect | | 2026-06-30 |
| Data Architect | | 2026-06-30 |
| AI Architect | | 2026-06-30 |
| QA Architect | | 2026-06-30 |
| Security Architect | | 2026-06-30 |

---

*ROS Constitution V1.2 — LTS (Production Ready)*
*生效日期：2026-06-30*
*修改条件：Architecture Board ≥ 75% 通过 + Foundation Change Policy*
