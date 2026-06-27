# ROS AI-native R&D Operating System — Architecture Governance Standard V3.0

> **ROS ≠ PLM**
> ROS = **AI-native R&D Operating System**
>
> 所有模块（ProductPlan / Verification / Prototype / Test / Certification / Manufacturing / ECO）
> 遵循统一的**数据治理（Data Governance）**、**事件治理（Event Governance）**和
> **AI 治理（AI Governance）**标准。

---

## 总体评分

| 维度 | 评分 |
|:----|:----:|
| 架构治理 | **9.9/10** |
| 工业 PLM | **9.8/10** |
| AI Ready | **9.6/10** |
| 长期演进 | **9.8/10** |
| 可落地性 | **9.5/10** |
| **综合** | **98 / 100** |

> 已可作为 ROS V1 正式架构标准。以下 V3.0 为未来五到十年长期标准。

---

## 架构治理目录（16 层）

### 第 -1 层 ★★★★★ — Business Architecture（业务架构）

> 为什么放在最前面？因为系统越来越大后，Supplier 到底属于 SCM、BOM 还是 Cost？
> 没有 Business Architecture，模块归属会越来越乱。

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

所有模块挂在 Capability 下。

| 检查项 | 说明 |
|:------|:-----|
| **Capability Map** | 业务能力地图是否覆盖全链路 |
| **模块归属** | 每个模块明确属于哪个 Business Capability |
| **职责边界** | 跨 Capability 的接口与依赖定义 |
| **演进路径** | Capability 的成熟度与未来扩展方向 |

---

### 第 0 层 ★★★★★ — Architecture Layer（架构与边界）

| 检查项 | 说明 |
|:------|:-----|
| **数据所有权（Owner）** | 每个核心对象的所属模块必须唯一。例如：ProductPlan 永远属于 Product Planning，而非 Project |
| **修改权限（Who can modify）** | 谁可以修改哪些字段。例如：Cost Target 只能由 Product Planning 修改，不能由 Project 修改 |
| **生命周期归属** | 每个对象的生命周期由谁控制。例如：Prototype 到底属于 Verification、Project 还是 Certification？必须明确定义 |
| **跨模块共享** | 数据跨模块引用时如何处理一致性 |

---

### 第 1 层 ★★★★★ — Data Governance（数据治理）

> 与 Architecture Layer 不同：Architecture Layer 讨论"谁拥有数据"，Data Governance 讨论"数据质量"。

| 检查项 | 说明 |
|:------|:-----|
| **唯一编码** | 每个实体 ID 是否全局唯一，统一编码规则 |
| **主数据** | 是否存在多个来源？主数据版本是否一致 |
| **数据质量** | Completeness / Accuracy / Timeliness |
| **元数据** | 关键字段是否有统一定义（例如：Prototype 是 P2 / Prototype2 / Certification Sample？必须统一） |
| **数据字典** | 全局数据字典是否建立，命名规范是否统一 |

---

### 第 2 层 ★★★★★ — Digital Thread Review（数字主线）

**数字主线链路**：

```
Market Requirement
       ↓
  ProductPlan
       ↓
  Verification
       ↓
   Prototype
       ↓
     Test
       ↓
Certification
       ↓
Mass Production
       ↓
Customer Feedback
       ↓
  Next ProductPlan
```

| 检查项 | 说明 |
|:------|:-----|
| **断点检测** | 链路中是否存在信息断裂 |
| **人工录入** | 是否存在非必要的人工数据录入 |
| **重复录入** | 同一数据是否在多个环节重复录入 |
| **信息丢失** | 数据在传递过程中是否丢失精度或语义 |
| **血缘追溯** | 能否从任意节点追溯至源头 |

---

### 第 3 层 ★★★★★ — Product Planning（产品策划中心）

| 检查项 | 说明 |
|:------|:-----|
| 数据模型 | 核心实体设计是否合理 |
| 生命周期 | 状态机与状态转换设计 |
| Workflow | 工作流编排与审批 |
| Event | 事件驱动与消息契约 |
| Cost | 成本核算与分摊模型 |
| Competitor | 竞品对标与目标设定 |
| Roadmap | 路线图规划与版本管理 |
| Gate | 门禁评审与阶段控制 |
| ProductDefinition | 产品定义与配置管理 |
| **Business Capability** | 产品具备的能力（Cooling / Heating / AI Energy Saving / Voice Control...），而非 Feature |
| **Platform Reuse** | 产品是否从共用平台派生（如 Outdoor Unit A 派生 15 个产品），Product Platform 管理 |
| **Portfolio** | ProductPlan 属于哪个 Portfolio（Residential AC / Commercial AC / Heat Pump / Portable AC），战略分析使用 |
| 数据边界 | 与下游模块的接口契约 |

---

### 第 4 层 — Verification（验证管理）

| 检查项 | 说明 |
|:------|:-----|
| VR 设计 | 验证需求（Verification Requirement）模型是否合理 |
| Requirement Traceability | 需求追溯链路是否完整 |
| Prototype 绑定 | VR 与样机的关联是否正确 |
| Coverage | 需求覆盖率：100条需求中测试覆盖98条，剩余2条研发需解释理由 |
| **Requirement Priority** | 需求优先级（Critical / Major / Minor），Gate 可自动判断是否允许 Waiver |

---

### 第 5 层 — Prototype（样机管理）

| 检查项 | 说明 |
|:------|:-----|
| P0/P1/P2/P3 分级 | 样机阶段划分是否合理 |
| Snapshot | 样机快照与基线管理 |
| BOM 版本 | 物料清单版本控制 |
| Firmware 版本 | 固件版本管理 |
| Digital Twin | 不仅是 BOM，还包括 Firmware / PCB / Tooling / Mold / Supplier |
| **Configuration Baseline** | 一个 Prototype = BOM + Firmware + PCB + Supplier + Software + Parameter，数字孪生依赖 |

---

### 第 6 层 — Test Center（实验中心）

| 检查项 | 说明 |
|:------|:-----|
| 实验设计 | 测试方案与用例设计 |
| 实验执行 | 执行流程与资源调度 |
| 实验结果 | 数据采集与判定标准 |
| KPI | 质量指标与统计 |
| 标准化 | 测试数据是否标准化（AI 可读） |
| **Evidence** | TestResult 不仅是 PASS/FAIL，还包括 Raw Data / Curve / Image / Video / Log，供 AI 直接分析 |

---

### 第 7 层 — Certification（认证管理）

| 检查项 | 说明 |
|:------|:-----|
| CE / UL / CB / SAA | 各目标市场认证 |
| 生命周期 | 认证证书的到期/续证/变更管理 |
| Market Policy | 法规变化跟踪：EU 法规何时更新？是否影响历史产品？ |
| **Accreditation Body** | UL 是哪一家实验室发证？证书可信度追踪 |

---

### 第 8 层 — Manufacturing Readiness（制造准备）

| 检查项 | 说明 |
|:------|:-----|
| 可制造性评审（DFM） | 设计是否满足制造要求 |
| 工装模具 | Tooling & Mold 管理 |
| 供应商 | Supplier Qualification |
| 量产条件 | Mass Production Readiness |
| 工艺文件 | Process documentation |
| **Pilot Run** | MP 之前应经过 Pilot Run，建议作为独立 Gate |

---

### 第 9 层 — ECO（工程变更管理）

| 检查项 | 说明 |
|:------|:-----|
| Change | 变更模型与分类 |
| Impact | 变更影响分析 |
| Re-validation | 变更后的重新验证 |
| Re-certification | 变更后的重新认证 |
| **Root Cause** | ECO 的根因来源：Supplier / Test / Certification / Customer / Manufacturing，AI 可分析返工趋势 |

---

### 第 10 层 ★★★ — Knowledge Graph（知识体系）

| 检查项 | 说明 |
|:------|:-----|
| Event 结构化 | 事件是否 Machine Readable |
| 结构化数据 | 所有核心对象是否结构化存储 |
| 规则化 | Certification 是否规则化（AI 可自动判断） |
| 向量化 | Competitor 数据是否已向量化（AI 可语义检索） |
| 知识图谱 | 跨模块的知识关联 |
| **Ontology** | 统一本体定义：Requirement / Specification / Capability / Feature 必须统一定义 |

---

### 第 11 层 ★★★★★ — AI Readiness Review（AI 就绪度）

| 检查项 | 说明 |
|:------|:-----|
| AI 可理解 | ProductPlan 是否 AI 可直接理解（结构化程度） |
| Requirement 结构化 | 需求是否结构化而非自然语言段落 |
| Competitor 向量化 | 竞品数据是否可向量化检索 |
| Test 标准化 | 实验数据是否标准化（AI 可横向对比） |
| Certification 规则化 | 认证要求是否规则化（AI 可自动推导） |
| Event Machine Readable | 事件是否被机器可消费的格式承载 |
| AI 协作接口 | 每个核心对象是否暴露 AI 可调用的推理接口 |

---

### 第 12 层 ★★★★★ — AI Governance（AI 治理）

> **AI Ready ≠ AI Governance**
> 未来 AI 可以自动创建 ProductPlan、VR、Test、判断 Gate，
> 必须回答：谁批准？谁负责？谁追溯？

| 检查项 | 说明 |
|:------|:-----|
| **AI Decision** | AI 是否可以直接决策，还是仅辅助建议 |
| **Human Approval** | 哪些 AI 输出必须人工批准后才能生效 |
| **Explainability** | AI 为什么这样判断？推理过程是否可解释 |
| **Traceability** | AI 推理链是否完整保存，可追溯审计 |
| **Model Version** | 使用的 AI 模型名称、版本、训练时间 |
| **Fallback** | AI 无法判断时是否有回退机制 |

---

### 第 13 层 ★★★★★ — Evolution Review（未来演进能力）

| 检查项 | 说明 |
|:------|:-----|
| **品类扩展** | 能否增加机器人 / 冰箱 / 洗衣机 / 储能 / 热泵而**不需重构** |
| 新市场适配 | 增加新目标市场是否只需配置而非开发 |
| 新流程接入 | 新增业务流程是否可插拔 |
| 数据模型扩展 | 核心模型是否可扩展字段而非新建表 |
| AI 能力升级 | 未来 AI 能力升级是否需要动核心架构 |
| 多工厂支持 | 从单工厂到多工厂是否架构级变更 |
| 生态开放 | 对外 API 是否可支撑第三方集成 |
| **AI 主导研发** | **是否支持从 AI 辅助研发演进到 AI 主导研发，而无需重构核心架构** —— 这是 ROS 与传统 PLM 最大的区别 |

> 如果以上答案为"是" → 架构成功 ✅

---

## 评审标准体系

### 三层治理

| 治理层 | 覆盖范围 | 核心问题 |
|:------|:---------|:--------|
| **Data Governance** | 数据质量 / 编码 / 字典 / 元数据 | 数据是否可信、一致 |
| **Event Governance** | 事件契约 / Machine Readable / 血缘 | 事件是否可追踪、可消费 |
| **AI Governance** | 决策权限 / 可解释性 / 追溯 / 模型 | AI 是否可控、可审计 |

### 战略定位

| 维度 | 传统 PLM | ROS V3.0 |
|:----|:---------|:---------|
| 定位 | 研发管理系统 | **AI-native R&D Operating System** |
| 数据 | 应用内存储 | 统一数据治理 + 数字主线 |
| 事件 | 记录日志 | Machine Readable Event Bus |
| AI | 外部集成 | **原生 AI 治理 + AI 主导演进** |
| 扩展 | 定制开发 | Capability Map + 品类扩展无需重构 |

---

## 交付物

### 《ROS AI-native R&D Operating System — Architecture Governance Report V1.0》

| 章节 | 内容 |
|:----|:-----|
| Business Architecture | Capability Map / 模块归属 |
| Architecture Layer | 数据所有权 / 修改权限 / 生命周期归属 |
| Data Governance | 唯一编码 / 主数据 / 数据质量 / 字典 |
| Digital Thread | 数据血缘 / 断点 / 信息丢失分析 |
| 模块评分 | 每个模块独立评分 × 16 层 |
| 问题清单 | P0（阻断）/ P1（重要）/ P2（改进） |
| 改进方案 | 具体修复路径 |
| 优先级路线图 | 短期 / 中期 / 长期实施计划 |
| 对标分析 | 传统 PLM + AI-native 双维度对比 |
| AI 治理审计 | 决策权限 / Explainability / Traceability |
| 演进建议 | 未来 5~10 年架构演进方向 |

---

## 评审启动顺序

```
第 -1 轮：Business Architecture（业务架构 / Capability Map）
第 0 轮：Architecture Layer（架构与边界）
第 1 轮：Data Governance（数据治理 / 编码 / 质量 / 字典）
第 2 轮：Digital Thread（数字主线 / 数据血缘）
第 3+4+5 轮：ProductPlan → Verification → Prototype（核心产品链）
第 6+7 轮：Test → Certification（质量合规链）
第 8+9 轮：Manufacturing → ECO（制造与变更链）
第 10+11+12 轮：Knowledge → AI Readiness → AI Governance（智能链）
最终轮：Evolution Review（演进能力 / AI 主导未来）
```

---

## 最终定位

> **ROS 不应再定位为"研发管理系统"**
>
> 正式定义为：
> **AI-native R&D Operating System（AI 原生研发操作系统）**
>
> 所有模块（ProductPlan / Verification / Prototype / Test / Certification / Manufacturing / ECO）
> 遵循统一的 **数据治理（Data Governance）**、**事件治理（Event Governance）**和
> **AI 治理（AI Governance）**标准。
>
> 这是 ROS V3.0 架构标准正式确立的方向。

---

*标准版本：V3.0*
*更新日期：2026-06-29*
*总体评价：98/100*
*下一步：从 Business Architecture（第 -1 层）开始第一轮评审*
