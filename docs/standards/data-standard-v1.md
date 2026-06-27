# ROS Data Standard V1.0

> 定义 ProductPlan、Verification、Prototype、Test、Certification 等核心对象的
> 数据模型、命名规范、版本管理、唯一编码、血缘关系。
>
> **稳定性：中高** — 模型定义应长期稳定，实例可扩展。

---

## 1. 数据治理总则

| 原则 | 说明 |
|:-----|:------|
| **唯一编码** | 每个实体 ID 全局唯一，统一编码规则 |
| **主数据单源** | 每类主数据只有一个权威来源 |
| **数据质量** | Completeness / Accuracy / Timeliness 可度量 |
| **统一字典** | 全局数据字典，命名规范统一（禁止 Prototype / P2 / Certification Sample 混用） |
| **元数据管理** | 关键字段有统一定义 |

---

## 2. 核心对象数据模型

### 2.1 ProductPlan（产品策划）

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

### 2.2 Verification（验证需求）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| product_plan_id | UUID | 关联 ProductPlan |
| requirement | String | 验证需求描述 |
| priority | Enum | Critical / Major / Minor |
| coverage_target | Float | 预期覆盖率 |
| actual_coverage | Float | 实际覆盖率 |
| status | Enum | 生命周期状态 |

### 2.3 Prototype（样机）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| product_plan_id | UUID | 关联 ProductPlan |
| stage | Enum | P0 / P1 / P2 / P3 |
| configuration_baseline | JSON | BOM + Firmware + PCB + Supplier + Software + Parameter |
| snapshot | JSON | 样机快照 |
| digital_twin_ref | String | 数字孪生引用 |

### 2.4 Test（实验）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| verification_id | UUID | 关联 Verification |
| result | Enum | PASS / FAIL / INCONCLUSIVE |
| evidence | JSON | Raw Data + Curve + Image + Video + Log |
| kpi | JSON | 质量指标 |

### 2.5 Certification（认证）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| market | String | 目标市场 |
| cert_type | Enum | CE / UL / CB / SAA / ... |
| accreditation_body | String | 发证实验室 |
| status | Enum | 生命周期状态 |
| valid_until | Date | 有效期 |
| market_policy_ref | String | 关联法规版本 |

### 2.6 ECO（工程变更）

| 字段 | 类型 | 说明 |
|:-----|:-----|:------|
| id | UUID | 全局唯一编码 |
| source | Enum | Supplier / Test / Certification / Customer / Manufacturing |
| root_cause | String | 根因分析 |
| impact | Enum[] | 影响范围 |
| status | Enum | 生命周期状态 |

---

## 3. 唯一编码规范

```
{EntityType}-{YYYYMMDD}-{Sequence}

示例：
PP-20260629-0001    (ProductPlan)
VR-20260629-0001    (Verification)
PT-20260629-0001    (Prototype)
CT-20260629-0001    (Certification)
EC-20260629-0001    (ECO)
```

---

## 4. 命名规范

| 类别 | 规范 | 示例 |
|:-----|:-----|:------|
| 枚举值 | PascalCase | StageP2 / PriorityCritical |
| 字段名 | snake_case | cost_target / product_plan_id |
| 事件名 | {Domain}.{Action} | ProductPlan.Created |
| API 路由 | RESTful | /api/pm/plans/{id} |

---

## 5. 血缘关系

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

---

## 6. 数据质量门禁

| 级别 | 要求 | 门禁 |
|:-----|:-----|:------|
| P0 | 核心字段完整、唯一编码合法 | 创建时校验，不通过阻塞 |
| P1 | 关联引用有效、枚举值合法 | 提交时校验，不通过警告 |
| P2 | 覆盖率达标、元数据完整 | 定期巡检，不通过记录 |

---

*标准版本：V1.0*
*稳定性：中高*
*维护者：Data Governance Team*
