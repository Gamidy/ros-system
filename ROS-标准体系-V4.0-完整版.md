# ROS 研发运营系统 — R&D Operations System

> **定位：AI-native Digital Engineering Platform**
>
> 海外分体机研发全生命周期管理平台
>
> 标准体系版本：**V4.0**（四套独立标准合并版）

---

## 第一部分：项目总览

### 技术栈

| 层 | 技术 | 说明 |
|:--|:-----|:-----|
| 前端 | Vue3 + Element Plus + TypeScript | Vite构建，Pinia状态管理 |
| 后端 | FastAPI (Python 3.11) | SQLAlchemy ORM，Pydantic验证 |
| 数据库 | MySQL/MariaDB | 数据库名: ros_db (docker-compose + network_mode=host) |
| 鉴权 | JWT + RBAC | 13种角色，权限矩阵驱动 |
| 部署 | Docker (ros-backend) + Nginx | 阿里云 139.196.15.52 |

### 项目结构

```
ros-system/
├── backend/
│   ├── app/
│   │   ├── api/       # API路由（按模块拆分）
│   │   ├── core/      # 配置/安全/数据库
│   │   ├── models/    # SQLAlchemy模型
│   │   ├── schemas/   # Pydantic验证
│   │   ├── middleware/# 审计/限流/XSS中间件
│   │   └── main.py    # 应用入口
│   ├── tests/         # pytest测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/     # 页面组件（按角色分组）
│   │   ├── api/       # Axios API调用
│   │   ├── router/    # Vue Router + 权限守卫
│   │   ├── stores/    # Pinia状态管理
│   │   ├── types/     # TypeScript类型定义
│   │   ├── layout/    # 布局组件（侧边栏/顶部栏）
│   │   └── components/# 通用组件
│   ├── dist/          # 构建产物（git ignored）
│   └── package.json
└── docs/              # 文档
```

### 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
# 修改 backend/.env DB_TYPE=sqlite 使用本地SQLite
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 生产部署（阿里云）

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 上传前端
scp -r dist/* root@139.196.15.52:/opt/ros-system/frontend/dist/

# 3. 上传修改的后端文件到服务器
scp backend/app/api/*.py root@139.196.15.52:/tmp/
ssh root@139.196.15.52 "docker cp /tmp/xxx.py ros-backend:/app/app/api/xxx.py"

# 4. 重启容器（env_file: .env.production 自动加载新配置）
ssh root@139.196.15.52 "docker restart ros-backend"

# 5. Nginx（通常不需要重启）
# ssh root@139.196.15.52 "nginx -s reload"
```

### 关键约定

- 单个API路由文件 ≤ 600行，超出拆子模块
- 所有API端点使用 `response_model` + `from_attributes = True`
- 新功能需配套 pytest 测试
- Redis 暂未接入（所有 import 已注释）

---

## 第二部分：Architecture Standard V1.0

> 定义 ROS（AI-native Digital Engineering Platform）的分层架构、系统边界、事件契约、
> 数字主线、AI 架构等长期稳定原则。
>
> **稳定性：高** — 架构原则不应因工程细节频繁变动。

### 总体定位

```
ROS = AI-native Digital Engineering Platform

PLM ⊂ ROS  (PLM 只是 ROS 的一个子域)
QMS ⊂ ROS
ALM ⊂ ROS
AI  ⊂ ROS
Digital Twin ⊂ ROS
Knowledge Graph ⊂ ROS
```

### 1. 分层架构

#### 第 -1 层 — Business Architecture（业务架构）

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

#### 第 0 层 — Architecture Layer（架构与边界）

- **数据所有权（Owner）**：每个核心对象的所属模块必须唯一
- **修改权限**：谁可以修改哪些字段（如 Cost Target 只能由 Product Planning）
- **生命周期归属**：每个对象的生命周期由谁控制
- **跨模块共享**：数据跨模块引用时的一致性处理

#### 第 1 层 — Runtime Architecture（运行时架构）

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

#### 第 2 层 — Digital Thread（数字主线）

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

#### 第 3~9 层 — 业务模块

参见 Data Standard 中各模块的详细定义。

#### 第 10 层 — Knowledge Architecture（知识架构）

- **Ontology**：统一本体定义（Requirement / Specification / Capability / Feature）
- **Taxonomy**：分类体系
- **Standard Library**：标准库
- **Engineering Rules**：工程规则
- **Lessons Learned**：经验教训库
- **Failure Mode**：故障模式库
- **Expert Knowledge**：领域专家知识
- **Best Practice**：最佳实践

#### 第 11 层 — AI Agent Architecture（AI 智能体架构）

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

#### 第 12 层 — Digital Twin Architecture（数字孪生架构）

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

### 2. 系统边界

| 域 | 包含 | 不包含 |
|:---|:-----|:-------|
| PLM | ProductPlan / Verification / Prototype / Certification / ECO | MES 执行 / SCM 采购 |
| QMS | Test / Quality / NCR / CAPA | 生产线上质检 |
| ALM | Requirement / Test Case / Defect | CI/CD Pipeline |
| MES 接口 | 工艺参数 / 工装 / 产量数据 | 产线控制 |
| AI | Agent / Knowledge / Prediction | 模型训练平台 |

### 3. 事件契约

所有跨模块通信通过 Event Bus，遵循：

- **事件命名**：`{Domain}.{Entity}.{Action}`（如 `ProductPlan.Created`）
- **事件载荷**：必须包含 `event_id`, `timestamp`, `source`, `payload`, `trace_id`
- **事件版本**：向后兼容，重大变更需新版本
- **事件存储**：Event Store 持久化，支持 Replay

### 4. 设计原则

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

## 第三部分：Data Standard V1.0

> 定义 ProductPlan、Verification、Prototype、Test、Certification 等核心对象的
> 数据模型、命名规范、版本管理、唯一编码、血缘关系。
>
> **稳定性：中高** — 模型定义应长期稳定，实例可扩展。

### 1. 数据治理总则

| 原则 | 说明 |
|:-----|:------|
| **唯一编码** | 每个实体 ID 全局唯一，统一编码规则 |
| **主数据单源** | 每类主数据只有一个权威来源 |
| **数据质量** | Completeness / Accuracy / Timeliness 可度量 |
| **统一字典** | 全局数据字典，命名规范统一（禁止 Prototype / P2 / Certification Sample 混用） |
| **元数据管理** | 关键字段有统一定义 |

### 2. 核心对象数据模型

#### 2.1 ProductPlan（产品策划）

| 字段 | 类型 | 说明 | Owner |
|:-----|:-----|:------|:------|
| id | UUID | 全局唯一编码 | Product Planning |
| name | String | 策划名称 | Product Planning |
| portfolio | Enum | Portfolio（Residential AC / Commercial AC / Heat Pump / Portable AC） | Product Planning |
| business_capability | Enum[] | 产品能力（Cooling / Heating / AI Energy Saving / Voice Control） | Product Planning |
| platform | String | 所属平台（如 Outdoor Unit A） | Product Planning |
| status | Enum | 生命周期状态 | Product Planning |
| cost_target | Decimal | 目标成本 | Product Planning（只读：Project 不可修改） |
| market | String[] | 目标市场 | Product Planning |
| roadmap | Date | 路线图节点 | Product Planning |

#### 2.2 Verification（验证需求）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| product_plan_id | UUID | 关联 ProductPlan |
| requirement | String | 验证需求描述 |
| priority | Enum | Critical / Major / Minor |
| coverage_target | Float | 预期覆盖率 |
| actual_coverage | Float | 实际覆盖率 |
| status | Enum | 生命周期状态 |

#### 2.3 Prototype（样机）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| product_plan_id | UUID | 关联 ProductPlan |
| stage | Enum | P0 / P1 / P2 / P3 |
| configuration_baseline | JSON | BOM + Firmware + PCB + Supplier + Software + Parameter |
| snapshot | JSON | 样机快照 |
| digital_twin_ref | String | 数字孪生引用 |

#### 2.4 Test（实验）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| verification_id | UUID | 关联 Verification |
| result | Enum | PASS / FAIL / INCONCLUSIVE |
| evidence | JSON | Raw Data + Curve + Image + Video + Log |
| kpi | JSON | 质量指标 |

#### 2.5 Certification（认证）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| market | String | 目标市场 |
| cert_type | Enum | CE / UL / CB / SAA / ... |
| accreditation_body | String | 发证实验室 |
| status | Enum | 生命周期状态 |
| valid_until | Date | 有效期 |
| market_policy_ref | String | 关联法规版本 |

#### 2.6 ECO（工程变更）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| source | Enum | Supplier / Test / Certification / Customer / Manufacturing |
| root_cause | String | 根因分析 |
| impact | Enum[] | 影响范围 |
| status | Enum | 生命周期状态 |

### 3. 唯一编码规范

```
{EntityType}-{YYYYMMDD}-{Sequence}

示例：
PP-20260629-0001    (ProductPlan)
VR-20260629-0001    (Verification)
PT-20260629-0001    (Prototype)
CT-20260629-0001    (Certification)
EC-20260629-0001    (ECO)
```

### 4. 命名规范

| 类别 | 规范 | 示例 |
|:-----|:-----|:------|
| 枚举值 | PascalCase | StageP2 / PriorityCritical |
| 字段名 | snake_case | cost_target / product_plan_id |
| 事件名 | {Domain}.{Action} | ProductPlan.Created |
| API 路由 | RESTful | /api/pm/plans/{id} |

### 5. 血缘关系

```
ProductPlan ← Verification ← Prototype ← Test ← Certification
     ↓
    ECO（变更链路）
     ↓
Manufacturing（制造链路）
     ↓
   Service（服务链路）
```

- 每条链路可追溯至源头
- 跨链路交叉引用通过 Event Bus 事件关联
- 禁止直接跨链路 FK 引用（避免循环依赖）

### 6. 数据质量门禁

| 级别 | 要求 | 门禁 |
|:-----|:-----|:------|
| P0 | 核心字段完整、唯一编码合法 | 创建时校验，不通过阻塞 |
| P1 | 关联引用有效、枚举值合法 | 提交时校验，不通过警告 |
| P2 | 覆盖率达标、元数据完整 | 定期巡检，不通过记录 |

---

## 第四部分：Engineering Standard V1.0

> 定义编码规范、API 规范、事件规范、Saga 事务、可观测性（Observability）、
> 韧性工程（Resilience）、安全架构（Security）、多租户等工程实践。
>
> **稳定性：中** — 随技术栈升级而演进。

### 1. Observability（可观测性）

所有服务必须输出以下四个信号：

| 信号 | 要求 | 工具 |
|:-----|:-----|:------|
| **Metrics** | 业务指标（QPS / 延迟 / 错误率 / 覆盖率） | Prometheus |
| **Logs** | 结构化日志（JSON 格式，含 trace_id） | ELK / Loki |
| **Traces** | 分布式追踪（跨模块调用链） | OpenTelemetry |
| **Events** | 业务事件（Event Bus 发布） | Event Store |

**AI 额外可观测**：

| 信号 | 说明 |
|:-----|:------|
| **AI Decision Logs** | AI 每次决策的记录（输入/输出/推理过程） |
| **Prompt Logs** | 发送给 AI 的完整 Prompt |
| **Model Version** | 每次 AI 调用使用的模型版本 |
| **Latency** | AI 调用延迟（P50 / P95 / P99） |

### 2. Resilience（韧性工程）

| 模式 | 说明 | 实现 |
|:-----|:------|:------|
| **Retry** | 临时故障自动重试 | 指数退避 + 抖动 |
| **Circuit Breaker** | 防止级联故障 | 熔断后快速失败 |
| **Rate Limit** | 防止过载 | 令牌桶 / 漏桶 |
| **Dead Letter Queue** | 失败消息不丢失 | 持久化后人工处理 |
| **Replay** | Event Store 回溯重放 | 事件溯源模式 |
| **Compensation** | Saga 失败时回滚 | 补偿事务 |
| **Recovery** | 系统崩溃后自动恢复 | 健康检查 + 自愈 |

#### Saga 事务规范

```
Begin → Step 1 → Step 2 → ... → Step N → Commit
                             ↓ (failure)
                      Compensate Step N-1
                             ↓
                      Compensate Step N-2
                             ↓
                           ...
```

- 每个 Step 必须有对应的补偿动作（Compensation）
- 补偿动作必须幂等
- Saga 状态持久化到 Event Store

### 3. Security Architecture（安全架构）

| 层次 | 控制 | 说明 |
|:-----|:-----|:------|
| **认证** | JWT + OAuth2 | 用户身份认证 |
| **授权** | RBAC + ABAC | 角色 + 属性级权限 |
| **数据权限** | Field Level Security | 敏感字段（成本/客户）权限控制 |
| **AI 权限** | Prompt Permission | AI 能访问的数据范围控制 |
| **API 安全** | Rate Limit + CSRF + XSS | API 防护 |
| **审计** | Audit Log | 所有写操作记录 |
| **多租户** | Tenant Isolation | 租户数据隔离 |

#### ABAC 属性定义

| 属性 | 示例 | 用途 |
|:-----|:------|:------|
| user.role | admin / pm / rd | 角色判断 |
| user.dept | planning / test / cert | 部门隔离 |
| resource.type | cost / customer / spec | 资源分类 |
| resource.tenant | tenant_id | 多租户 |
| environment | prod / staging | 环境控制 |
| ai.permission | read / write / decide | AI 操作权限 |

### 4. Event Specification（事件规范）

#### 事件格式

```json
{
  "event_id": "uuid",
  "event_type": "{Domain}.{Entity}.{Action}",
  "version": 1,
  "timestamp": "2026-06-29T12:00:00Z",
  "source": "service-name",
  "trace_id": "uuid",
  "tenant_id": "tenant-id",
  "payload": { },
  "metadata": {
    "user_id": "user-id",
    "correlation_id": "uuid"
  }
}
```

#### 事件类型命名

| 域 | 事件示例 |
|:---|:---------|
| ProductPlan | `ProductPlan.Created`, `ProductPlan.StatusChanged`, `ProductPlan.CostTargetUpdated` |
| Verification | `Verification.Created`, `Verification.CoverageUpdated` |
| Prototype | `Prototype.StageChanged`, `Prototype.SnapshotCreated` |
| Test | `Test.Completed`, `Test.EvidenceUploaded` |
| Certification | `Certification.Granted`, `Certification.Expiring` |
| ECO | `ECO.Created`, `ECO.ImpactAnalyzed` |
| AI | `AI.DecisionMade`, `AI.ActionApproved`, `AI.ActionRejected` |

### 5. API 规范

| 规则 | 说明 |
|:-----|:------|
| **RESTful** | 资源 + HTTP 动词 |
| **版本** | URL 路径版本（`/api/v1/`）或 Header |
| **分页** | `?page=1&page_size=20` |
| **错误格式** | `{ "code": "ERROR_CODE", "detail": "描述", "trace_id": "uuid" }` |
| **幂等** | POST 创建返回 201，PUT 更新幂等 |
| **异步** | 长任务返回 202 + Location Header |

### 6. 编码规范

| 语言 | 规范 | 检查 |
|:-----|:-----|:------|
| Python | PEP8 + Type Hints（全代码 typed） | ruff / mypy |
| TypeScript | ESLint + Prettier | vue-tsc |
| API | 所有函数有返回类型注解 | 审计 |
| 测试 | 新功能配套测试，异常路径全覆盖 | pytest / vitest |

#### 提交规范

- Conventional Commits（`feat:` / `fix:` / `refactor:` / `test:` / `docs:`）
- 单次提交 ≤ 200 行（新文件除外）
- 提交前必须通过合规审计

### 7. 多租户

| 能力 | 说明 |
|:-----|:------|
| **数据隔离** | 租户级行级隔离（org_id 字段） |
| **配置隔离** | 每个租户独立配置 |
| **资源隔离** | 可选独立数据库或共享 |
| **租户感知** | API 自动从 Token 提取 tenant_id |

---

## 第五部分：AI Standard V1.0

> 定义 AI Agent 职责边界、AI 决策权限、提示词规范、模型治理、
> 知识库接口、AI 审计与追溯。
>
> **稳定性：中低** — 随 AI 能力升级而演进。

### 1. AI Agent Architecture（AI 智能体架构）

#### Agent 拓扑

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

#### 每个 Agent 的定义

| Agent | 职责 | 输入 | 输出 | 决策权限 |
|:------|:-----|:-----|:-----|:---------|
| **Planner** | 项目规划、20步推演、任务拆解 | 用户需求 | 任务分解 + 执行计划 | 建议 |
| **Architecture** | 架构设计、模块边界、数据模型 | 需求规格 | 架构文档 + 模型定义 | 建议（需人工批准） |
| **Coding** | 代码实现、测试编写 | 任务 + 架构 | 代码 + 测试 | **自动** |
| **Verification** | 验证实现是否符合需求 | 代码 + 需求 | 验证报告 | 建议 |
| **Review** | 代码审查、合规审计 | 代码 diff | 审查报告 + 评分 | **阻断/否决** |
| **Certification** | 认证合规检查 | 产品数据 + 市场法规 | 认证评估 | 建议 |
| **Knowledge** | 知识检索、经验匹配 | 查询 | 相关知识 | 建议 |

### 2. AI Governance（AI 治理）

#### 决策权限矩阵

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

#### Explainability（可解释性）

所有 AI 决策必须输出：

1. **推理过程**（Reasoning Chain）
2. **依据来源**（Source References）
3. **置信度**（Confidence Score）
4. **备选方案**（Alternatives Considered）
5. **局限性**（Known Limitations）

#### Traceability（追溯性）

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

### 3. Prompt 规范

#### 通用 Prompt 结构

```
[Context]     → 当前状态、用户信息、项目信息
[Task]        → 具体任务描述
[Constraints] → 约束条件（权限、规则、标准）
[Format]      → 输出格式要求
[Examples]    → 示例（可选）
```

#### 规则

- **Context 优先**：先给背景再给任务
- **约束明确**：AI 应知道什么能做、什么不能做
- **输出结构**：JSON / Markdown 等结构化格式
- **版本标记**：每个 Prompt 模板有版本号

### 4. 知识库接口

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

### 5. 数据权限（AI 感知）

| 数据类别 | AI 可读 | AI 可写 | 示例 |
|:---------|:-------:|:--------:|:-----|
| 产品规格 | ✅ | ✅ | ProductPlan.Spec |
| 成本数据 | ❌ | ❌ | Cost Target |
| 客户信息 | ❌ | ❌ | Customer Name |
| 测试结果 | ✅ | ✅ | Test Result |
| 认证证书 | ✅ | ❌ | Certificate Status |
| 供应商 | ✅ | ❌ | Supplier Info |

### 6. AI 安全

| 控制 | 说明 |
|:-----|:------|
| **Prompt Injection** | 输入清洗，禁止注入指令 |
| **数据泄露** | AI 输出不能包含敏感数据 |
| **权限校验** | AI 调用前检查操作权限 |
| **审计日志** | 所有 AI 操作记录审计 |
| **模型隔离** | 不同租户使用隔离的模型上下文 |
| **Fallback** | AI 无法判断时有回退机制（转人工） |

### 7. 从 AI 辅助到 AI 主导的演进路径

| 阶段 | AI 角色 | 人类角色 | 条件 |
|:-----|:--------|:---------|:------|
| **L1 辅助** | 建议、代码生成 | 决策、审批 | 当前状态 |
| **L2 协作** | 创建 Plan / VR / Test，人工复核 | 复核 + 审批 | AI Governance 就绪 |
| **L3 主导** | 自动判断 Gate、触发 ECO | 抽查 + 例外处理 | Explainability + Audit 成熟 |
| **L4 自主** | AI 驱动完整研发流程 | 战略决策 + 异常处理 | 知识图谱 + 规则库完备 |

> **架构要求**：从 L1 到 L4 的演进不需重构核心架构。
> 这是 ROS 与传统 PLM 最大的区别。

---

## 附录：版本演进

| 版本 | 形态 | 说明 | 评分 |
|:-----|:-----|:------|:----:|
| V1.0 | Review Checklist | 合规审计清单（38条编码原则） | 59%→93% |
| V2.0 | Architecture Review | 6层架构评审方案 | 97/100 |
| V3.0 | Architecture Governance | 16层架构治理标准 | 98/100 |
| **V4.0** | **Enterprise Standard System** | **Architecture / Data / Engineering / AI 四套独立标准** | **99/100** |
