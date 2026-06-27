# ROS Architecture Standard V1.0

> 定义 ROS（AI-native Digital Engineering Platform）的分层架构、系统边界、事件契约、
> 数字主线、AI 架构等长期稳定原则。
>
> **稳定性：高** — 架构原则不应因工程细节频繁变动。

---

## 总体定位

```
ROS = AI-native Digital Engineering Platform

PLM ⊂ ROS  (PLM 只是 ROS 的一个子域)
QMS ⊂ ROS
ALM ⊂ ROS
AI  ⊂ ROS
Digital Twin ⊂ ROS
Knowledge Graph ⊂ ROS
```

---

## 1. 分层架构

### 第 -1 层 — Business Architecture（业务架构）

**Business Capability Map**：

```
Product Strategy
       ↓
Product Planning
       ↓
Product Definition
       ↓
  Verification
       ↓
 Certification
       ↓
Manufacturing
       ↓
   Service
```

- 所有模块挂在 Capability 下
- 每个模块明确属于哪个 Business Capability
- 跨 Capability 的接口与依赖定义

### 第 0 层 — Architecture Layer（架构与边界）

- **数据所有权（Owner）**：每个核心对象的所属模块必须唯一
- **修改权限**：谁可以修改哪些字段（如 Cost Target 只能由 Product Planning）
- **生命周期归属**：每个对象的生命周期由谁控制
- **跨模块共享**：数据跨模块引用时的一致性处理

### 第 1 层 — Runtime Architecture（运行时架构）

```
User
       ↓
  API Gateway
       ↓
Workflow Engine
       ↓
   Event Bus
       ↓
  AI Router
       ↓
  Agent Pool
       ↓
  Knowledge
       ↓
 Event Store
       ↓
  Database
```

- API Gateway：统一入口、认证、限流
- Workflow Engine：业务流程编排
- Event Bus：事件驱动通信
- AI Router：AI 请求分发
- Agent Pool：多 Agent 协作运行时
- Event Store：事件持久化与回溯

### 第 2 层 — Digital Thread（数字主线）

**数据血缘链路**：

```
Market Requirement → ProductPlan → Verification → Prototype
→ Test → Certification → Mass Production → Customer Feedback
→ Next ProductPlan
```

- **断点检测**：链路中是否存在信息断裂
- **人工录入**：是否存在非必要的人工数据录入
- **重复录入**：同一数据是否在多个环节重复录入
- **信息丢失**：数据在传递过程中是否丢失精度或语义
- **血缘追溯**：能否从任意节点追溯至源头

### 第 3~9 层 — 业务模块

参见 Data Standard 中各模块的详细定义。

### 第 10 层 — Knowledge Architecture（知识架构）

- **Ontology**：统一本体定义（Requirement / Specification / Capability / Feature）
- **Taxonomy**：分类体系
- **Standard Library**：标准库
- **Engineering Rules**：工程规则
- **Lessons Learned**：经验教训库
- **Failure Mode**：故障模式库
- **Expert Knowledge**：领域专家知识
- **Best Practice**：最佳实践

### 第 11 层 — AI Agent Architecture（AI 智能体架构）

```
Planner Agent
       ↓
Architecture Agent
       ↓
  Coding Agent
       ↓
Verification Agent
       ↓
  Review Agent
       ↓
Certification Agent
       ↓
Knowledge Agent
```

每个 Agent 定义：
- **职责**（Responsibility）
- **边界**（Scope）
- **输入**（Input Contract）
- **输出**（Output Contract）
- **依赖**（Dependencies）

### 第 12 层 — Digital Twin Architecture（数字孪生架构）

```
Physical Product
       ↓
  Digital Product（BOM + Firmware + PCB + Tooling + Mold + Supplier + Software + Parameter）
       ↓
   Simulation
       ↓
  Verification
       ↓
     Test
       ↓
Manufacturing
       ↓
Customer Feedback
       ↓
  AI Prediction
```

- Configuration Baseline：每个 Prototype = BOM + Firmware + PCB + Supplier + Software + Parameter
- 孪生数据闭环：从物理到数字、从仿真到验证、从生产到反馈

---

## 2. 系统边界

| 域 | 包含 | 不包含 |
|:---|:-----|:-------|
| PLM | ProductPlan / Verification / Prototype / Certification / ECO | MES 执行 / SCM 采购 |
| QMS | Test / Quality / NCR / CAPA | 生产线上质检 |
| ALM | Requirement / Test Case / Defect | CI/CD Pipeline |
| MES 接口 | 工艺参数 / 工装 / 产量数据 | 产线控制 |
| AI | Agent / Knowledge / Prediction | 模型训练平台 |

---

## 3. 事件契约

所有跨模块通信通过 Event Bus，遵循：

- **事件命名**：`{Domain}.{Entity}.{Action}`（如 `ProductPlan.Created`）
- **事件载荷**：必须包含 `event_id`, `timestamp`, `source`, `payload`, `trace_id`
- **事件版本**：向后兼容，重大变更需新版本
- **事件存储**：Event Store 持久化，支持 Replay

---

## 4. 设计原则

| 原则 | 说明 |
|:-----|:------|
| **唯一所有权** | 每个数据对象只有一个 Owner 模块 |
| **单向依赖** | Business Capability 方向自上而下，禁止逆向依赖 |
| **事件驱动** | 跨模块通信优先事件，避免直接 API 耦合 |
| **配置优于编码** | 新市场/新流程应通过配置而非开发 |
| **AI 原生** | 每个核心对象结构化至 AI 可直接消费 |
| **可观测** | 每个组件必须输出 Metrics / Logs / Traces / Events |
| **可演进** | 新增品类不需重构核心架构 |

---

*标准版本：V1.0*
*稳定性：高（长期稳定）*
*维护者：Architecture Team*
