# ROS Phase 6 v2.0 — 架构修正说明

> **评审人**：系统架构师
> **执行人**：AI-A
> **日期**：2026-06-24

---

## 一、综合评分

| 项目 | 评分 |
|:-----|:----:|
| 架构方向 | 9.5/10 |
| 模块边界 | 9/10 |
| 集成设计 | 9.5/10 |
| 数据模型 | 8/10 |
| 可扩展性 | 8.5/10 |
| 空调行业适配度 | 8/10 |
| **综合** | **92/100** |

---

## 二、4 项架构修正

### 修正 1（最高）：Verification Requirement 核心化

**之前（v1.0）**：以 `test_libraries`（实验项目库）为中心设计，ProductPlan 直接绑定实验项目库，是 LIMS（实验室管理系统）思路 ❌

**之后（v2.0）**：以 `verification_requirements`（验证需求）为中心 ✅

数字主线变为：
```
ProductPlan（APF ≥ 5.20，噪音 ≤ 38dB）
    ↓
Verification Requirement（系统自动生成验证需求）
    ↓
Test Plan / Test Request（实验方案）
    ↓
Test Schedule（排期）
    ↓
Judgment（判定）
```

**新增实体**：`verification_requirements` 表
- `category`: 性能/能效/噪音风量/凝露/潮态/安全
- `source`: product_plan / project / cert / eco
- `acceptance_criteria`: 允收准则（如 "APF ≥ 5.20"）

---

### 修正 2：标准库分层设计

**之前（v1.0）**：平铺的 `test_standards` 单表

**之后（v2.0）**：三层标准体系 ✅

```
国际标准层: IEC, ISO, UL, EN
国家标准层: GB (中国), EN (欧盟), AHRI (美国), AS/NZS (澳洲), JIS (日本)
客户标准层: 小米, 格力, 海外客户
```

**新增表**：`standard_systems` → `standards` → `test_standard_mappings`
- 一个实验可对应多个标准（如同时满足 IEC + GB + 小米）
- 标准按体系级联管理

---

### 修正 3（最高）：增加 Prototype 样机主线

**之前（v1.0）**：`Project → Test`，实验判定直接挂在项目上，无样机版本管理 ❌

**之后（v2.0）**：`Project → Prototype → Test Request → Judgment` ✅

**研发实际流程**：
```
手板（手工样板）→ 首样（工程样机）→ 认证样机 → 量产样机
```

**设计原则**：
- 实验结果永远跟着样机版本走，而不是项目
- 样机版本升级（V1.0→V2.0），旧实验结果自动失效/归档
- 判定结果附着在 `prototype` 上

**新增实体**：`prototypes` 表
- `prototype_type`: hand_sample / first_sample / cert_sample / mass_production
- `version`: V1.0 / V2.0
- `result`: pass / fail / conditional
- 关联 BOM 版本

**增强**：`test_requests` 和 `test_judgments` 增加可选 FK `prototype_id`

---

### 修正 4：增加 Gate Rule Engine

**之前（v1.0）**：Gate 条件在 `ProjectGate.pass_conditions` 中硬编码 ❌

**之后（v2.0）**：可配置规则引擎 ✅

```json
{
  "gate_code": "M5",
  "product_line": "split_ac",
  "customer": "xiaomi",
  "required_verification_requirements": ["PERFORMANCE", "NOISE", "CONDENSATION"],
  "required_prototype_types": ["cert_sample"],
  "all_pass": true,
  "auto_block": true
}
```

**新增实体**：`gate_rules` 表
- 按 `product_line` + `customer` + `gate_code` 动态匹配
- 支持 `all_pass` 和 `auto_block` 开关
- 不匹配规则时 fallback 到原 `pass_conditions` 逻辑

---

## 三、修正后的数字主线

```
ProductPlan
    ↓
Verification Requirement（验证需求）⭐ 核心新增
    ↓
Gate Rule Engine ←── Project → Prototype（样机）⭐ 关键新增
    │                           ↓
    │                       Test Center（以VR驱动）
    │                           ↓
    ├── Certification Center
    │         ↓
    ├── ECR/ECO
    │         ↓
    └── Mass Production

CDF 关键元器件清单贯穿全程
```

---

## 四、结论

Phase 6 方向认可，**S1 可启动编码**，但 S1 范围扩展为包含：

| S1 子模块 | 说明 |
|:----------|:-----|
| Verification Requirement | 验证需求管理（CRUD + ProductPlan 绑定） |
| Prototype | 样机主线（手板→首样→认证样机→量产样机） |
| Gate Rule Engine | 可配置规则引擎 |
| 分层标准库 | 国际→国家→客户三层 |
| 原实验中心 | 实验项目库、排期、判定 |

S2（认证中心）、S3（变更控制）设计保持不变。
