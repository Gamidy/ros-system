# ROS AI Standard V1.0

> 定义 AI Agent 职责边界、AI 决策权限、提示词规范、模型治理、
> 知识库接口、AI 审计与追溯。
>
> **稳定性：中低** — 随 AI 能力升级而演进。

---

## 1. AI Agent Architecture（AI 智能体架构）

### Agent 拓扑

```
Planner Agent（规划）
       ↓
Architecture Agent（架构）
       ↓
  Coding Agent（编码）
       ↓
Verification Agent（验证）
       ↓
  Review Agent（审查）
       ↓
Certification Agent（认证）
       ↓
Knowledge Agent（知识）
```

### 每个 Agent 的定义

| Agent | 职责 | 输入 | 输出 | 决策权限 |
|:------|:-----|:-----|:-----|:---------|
| **Planner** | 项目规划、20步推演、任务拆解 | 用户需求 | 任务分解 + 执行计划 | 建议 |
| **Architecture** | 架构设计、模块边界、数据模型 | 需求规格 | 架构文档 + 模型定义 | 建议（需人工批准） |
| **Coding** | 代码实现、测试编写 | 任务 + 架构 | 代码 + 测试 | **自动** |
| **Verification** | 验证实现是否符合需求 | 代码 + 需求 | 验证报告 | 建议 |
| **Review** | 代码审查、合规审计 | 代码 diff | 审查报告 + 评分 | **阻断绝** |
| **Certification** | 认证合规检查 | 产品数据 + 市场法规 | 认证评估 | 建议 |
| **Knowledge** | 知识检索、经验匹配 | 查询 | 相关知识 | 建议 |

---

## 2. AI Governance（AI 治理）

### 决策权限矩阵

| 决策类型 | AI 自动 | AI 建议 | 人工必须 |
|:---------|:-------:|:--------:|:--------:|
| 代码生成 | ✅ | — | — |
| 测试编写 | ✅ | — | — |
| 代码审查评分 | ✅ | — | — |
| 架构设计 | — | ✅ | ✅ |
| ProductPlan 创建 | — | ✅ | ✅ |
| Gate 门禁判断 | — | ✅ | ✅ |
| ECO 影响分析 | — | ✅ | ✅ |
| 认证评估 | — | ✅ | ✅ |
| 成本变更 | ❌ | ❌ | ✅ |
| 客户数据访问 | ❌ | ❌ | ✅ |

### Explainability（可解释性）

所有 AI 决策必须输出：

1. **推理过程**（Reasoning Chain）
2. **依据来源**（Source References）
3. **置信度**（Confidence Score）
4. **备选方案**（Alternatives Considered）
5. **局限性**（Known Limitations）

### Traceability（追溯性）

每次 AI 调用必须记录：

| 字段 | 说明 |
|:-----|:------|
| `ai_call_id` | 全局唯一 ID |
| `timestamp` | 调用时间 |
| `user_id` | 发起用户 |
| `agent_name` | Agent 名称 |
| `model` | 模型名称 + 版本 |
| `prompt` | 完整 Prompt |
| `response` | AI 输出 |
| `reasoning_chain` | 推理链 |
| `decision_type` | 决策类型 |
| `approved_by` | 批准人（如需） |
| `status` | approved / rejected / pending |

---

## 3. Prompt 规范

### 通用 Prompt 结构

```
[Context]     → 当前状态、用户信息、项目信息
[Task]        → 具体任务描述
[Constraints] → 约束条件（权限、规则、标准）
[Format]      → 输出格式要求
[Examples]    → 示例（可选）
```

### 规则

- **Context 优先**：先给背景再给任务
- **约束明确**：AI 应知道什么能做、什么不能做
- **输出结构**：JSON / Markdown 等结构化格式
- **版本标记**：每个 Prompt 模板有版本号

---

## 4. 知识库接口

所有 Agent 通过统一接口访问知识库：

```
GET /knowledge/search?q={query}&type={ontology_type}&limit={n}
```

| 知识类型 | 说明 | 存储 |
|:---------|:------|:------|
| Ontology | 本体定义 | RDF / Graph DB |
| Taxonomy | 分类体系 | RDF / Graph DB |
| Standard Library | 标准库 | Document Store |
| Engineering Rules | 工程规则 | Rule Engine |
| Lessons Learned | 经验教训 | Vector DB |
| Failure Mode | 故障模式 | Vector DB |
| Expert Knowledge | 专家知识 | Vector DB |
| Best Practice | 最佳实践 | Vector DB |

---

## 5. 数据权限（AI 感知）

| 数据类别 | AI 可读 | AI 可写 | 示例 |
|:---------|:-------:|:--------:|:-----|
| 产品规格 | ✅ | ✅ | ProductPlan.Spec |
| 成本数据 | ❌ | ❌ | Cost Target |
| 客户信息 | ❌ | ❌ | Customer Name |
| 测试结果 | ✅ | ✅ | Test Result |
| 认证证书 | ✅ | ❌ | Certificate Status |
| 供应商 | ✅ | ❌ | Supplier Info |

---

## 6. AI 安全

| 控制 | 说明 |
|:-----|:------|
| **Prompt Injection** | 输入清洗，禁止注入指令 |
| **数据泄露** | AI 输出不能包含敏感数据 |
| **权限校验** | AI 调用前检查操作权限 |
| **审计日志** | 所有 AI 操作记录审计 |
| **模型隔离** | 不同租户使用隔离的模型上下文 |
| **Fallback** | AI 无法判断时有回退机制（转人工） |

---

## 7. 从 AI 辅助到 AI 主导的演进路径

| 阶段 | AI 角色 | 人类角色 | 条件 |
|:-----|:--------|:---------|:------|
| **L1 辅助** | 建议、代码生成 | 决策、审批 | 当前状态 |
| **L2 协作** | 创建 Plan / VR / Test，人工复核 | 复核 + 审批 | AI Governance 就绪 |
| **L3 主导** | 自动判断 Gate、触发 ECO | 抽查 + 例外处理 | Explainability + Audit 成熟 |
| **L4 自主** | AI 驱动完整研发流程 | 战略决策 + 异常处理 | 知识图谱 + 规则库完备 |

> **架构要求**：从 L1 到 L4 的演进不需重构核心架构。
> 这是 ROS 与传统 PLM 最大的区别。

---

*标准版本：V1.0*
*稳定性：中低*
*维护者：AI Governance Team*
