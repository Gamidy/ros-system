# ROS Phase 6 架构修正变更说明

> **日期**：2026-06-24
> **评审人**：系统架构师
> **执行人**：AI-A（资深PLM架构师）
> **原版本**：v1.0（待评审）
> **修正版本**：v2.0（架构修正版）

---

## 修正概览

| # | 修正内容 | 严重程度 | 影响范围 |
|---|---------|---------|---------|
| 1 | Test Center 以 Verification Requirement（验证需求）为核心 | **最高** | 架构、数据模型、API、前端、集成点 |
| 2 | 标准库分层设计（国际→国家→客户三层） | 高 | 数据模型、API、前端 |
| 3 | 增加 Prototype（样机）主线实体 | **最高** | 架构、数据模型、API、前端、集成点 |
| 4 | 增加 Gate Rule Engine（可配置规则引擎） | 高 | 数据模型、API、前端、集成点 |

---

## 修正 1：Test Center 以 Verification Requirement 为核心

### 变更前（v1.0 — 错误）
- 以 `test_libraries`（实验项目库）为中心设计
- ProductPlan 直接绑定实验项目库
- LIMS 思维，不符合空调研发流程

### 变更后（v2.0 — 正确）
- 以 `verification_requirements`（验证需求）为中心
- 数字主线：`ProductPlan → Verification Requirement → Test Plan/Request → Test Schedule → Judgment`
- ProductPlan 方案评审触发验证需求，验证需求驱动实验

### 新增/变更内容

| 项目 | 变更 |
|------|------|
| **新增表** | `verification_requirements` |
| **新增 API** | `GET/POST/PUT/PATCH/DELETE /api/v1/verification-requirements/*` |
| **新增前端页面** | `VerificationRequirementView.vue` |
| **新增组件** | `VerificationReqForm.vue`, `VerificationReqTimeline.vue` |
| **新增路由** | `tests/verification-requirements` |
| **新增服务** | `vr_compliance_service.py` |
| **增强关联** | `test_plan_items` 增加 `verification_requirement_id FK` |
| **增强关联** | `product_plan_test_bindings` 增加 `verification_requirement_id FK` |
| **增强 API** | `test_plan_items` 创建时支持关联 VR |
| **增强 API** | `tests` 创建时支持 `verification_requirement_id` |

### 向后兼容
- 原有 `product_plan_test_bindings` 逻辑保留
- 旧数据通过 source/source_id 字段关联到 VR

---

## 修正 2：标准库分层设计

### 变更前（v1.0 — 平铺）
- 单表 `test_standards` 平铺所有标准
- `issuing_body` 字段标记发布机构（小米/格力/国标/IEC/UL）
- `test_library_standards` 作为实验-标准关联表

### 变更后（v2.0 — 三层体系）
- **三层结构**：`standard_systems` → `standards` → `test_standard_mappings`
- 国际标准层：IEC, ISO, UL, EN
- 国家标准层：GB, EN(欧盟), AHRI(美国), AS/NZS(澳洲), JIS(日本)
- 客户标准层：小米, 格力, 海外客户

### 新增/变更内容

| 项目 | 变更 |
|------|------|
| **新增表** | `standard_systems`, `standards`, `test_standard_mappings` |
| **删除表(替代)** | 旧 `test_standards` 保留但不再使用；旧 `test_library_standards` 不再使用 |
| **新增 API** | `GET/POST/PUT /api/v1/standard-systems/*`, `/api/v1/standards/*` |
| **新增前端页面** | `StandardSystemView.vue`（三层树展开） |
| **新增组件** | `StandardSystemTree.vue`, `StandardSelector.vue`（按体系/层级筛选） |
| **新增路由** | `tests/standards` |

### 向后兼容
- 旧 `test_standards` 表保留，数据迁移脚本可将旧数据导入 `standard_systems` + `standards`
- `test_plan_items.standard_id` 仍可引用旧 `test_standards` 数据（渐进迁移）

---

## 修正 3：增加 Prototype（样机）主线实体

### 变更前（v1.0 — 缺失）
- Project → Test，实验判定直接挂在项目上
- 没有样机版本管理概念
- 无法追踪「手板→首样→认证样机→量产样机」的迭代

### 变更后（v2.0 — 新增样机主线）
- 数字主线：`Project → Prototype → Test Request → Judgment`
- 实验判定结果附着在 `prototype` 上而非 `project` 上
- 样机版本升级（V1.0→V2.0），旧实验结果自动失效/归档

### 新增/变更内容

| 项目 | 变更 |
|------|------|
| **新增表** | `prototypes` |
| **新增 API** | `GET/POST/PUT/PATCH/DELETE /api/v1/prototypes/*` |
| **新增前端页面** | `PrototypeListView.vue`, `PrototypeDetailView.vue` |
| **新增组件** | `PrototypeTimeline.vue`, `PrototypeJudgmentSummary.vue` |
| **新增路由** | `tests/prototypes`, `tests/prototypes/:id` |
| **增强关联** | `test_requests` 增加 `prototype_id FK`（可选） |
| **增强关联** | `test_judgments` 增加 `prototype_id FK`（可选，判定跟随样机版本） |
| **增强 API** | `tests` 创建时支持 `prototype_id` |
| **增强 API** | 新增 `GET /api/v1/prototypes/{pid}/judgments`（样机判定总览） |
| **增强 API** | 新增 `POST /api/v1/prototypes/{pid}/archive-judgments`（版本升级归档） |
| **新增事件** | `PROTOTYPE_CREATED`, `PROTOTYPE_COMPLETED`, `PROTOTYPE_VERSION_UPGRADED` |
| **新增 Dashboard 卡片** | "样机判定异常" |

### 向后兼容
- `test_requests` 增加可选 FK `prototype_id`，不影响现有数据
- `test_judgments` 增加可选 FK `prototype_id`，不影响现有判定流程
- 旧数据（无 prototype_id 的判定）仍正常显示

---

## 修正 4：增加 Gate Rule Engine

### 变更前（v1.0 — 硬编码）
- Gate 条件在 `ProjectGate.pass_conditions` 中硬编码引用实验判定
- 无法按产品线/客户差异化配置
- 门禁逻辑固死在代码中，每次调整需发版

### 变更后（v2.0 — 可配置引擎）
- `gate_rules` 表支持配置规则
- 按 `product_line` + `customer` + `gate_code` 动态匹配
- 支持检查必需的验证需求类型、样机类型
- 支持 `all_pass` 和 `auto_block` 开关
- 不匹配规则时 fallback 到原 `pass_conditions` 逻辑

### 新增/变更内容

| 项目 | 变更 |
|------|------|
| **新增表** | `gate_rules` |
| **新增 API** | `GET/POST/PUT/PATCH/DELETE /api/v1/gate-rules/*` |
| **新增 API** | `POST /api/v1/gate-rules/evaluate`（规则评估核心API） |
| **新增 API** | `GET /api/v1/projects/{id}/gate-rules-status` |
| **新增前端页面** | `GateRuleView.vue` |
| **新增组件** | `GateRuleForm.vue`, `GateRuleEvalResult.vue` |
| **新增路由** | `tests/gate-rules` |
| **新增服务** | `gate_rule_engine.py` |
| **新增事件** | `GATE_RULE_EVALUATED`, `GATE_BLOCKED` |
| **新增 Dashboard 卡片** | "Gate 阻塞（规则未满足）" |
| **增强项目逻辑** | `Project._can_light_gate()` 优先使用 Gate Rule Engine |

### 向后兼容
- 原有 `ProjectGate.pass_conditions` 逻辑保留作为 fallback
- Gate Rule Engine 匹配不到规则时自动走回原逻辑
- 旧 Gate 数据不受影响

---

## 文件变更汇总

### 修改文件
| 文件路径 | 变更说明 |
|---------|---------|
| `phase6-plan.md` | 架构修正 v1.0→v2.0（本文件） |

### 新增文件（修正版引入）
| 文件路径 | 说明 |
|---------|------|
| `phase6-changelog.md` | **本文件** — 架构修正变更说明 |

### 原 v1.0 中已有的新增文件清单（修正版中保留）
参见 `phase6-plan.md` 附录 A 完整文件变更清单。

---

## 数据迁移注意事项

### 1. test_standards → standard_systems + standards
```sql
-- 迁移脚本示例：将平铺标准导入分层体系
INSERT INTO standard_systems (code, name, level, org_id)
SELECT DISTINCT 
    LOWER(issuing_body) AS code,
    issuing_body AS name,
    CASE 
        WHEN issuing_body IN ('IEC','ISO','UL','EN') THEN 'international'
        WHEN issuing_body IN ('GB','AHRI','AS/NZS','JIS') THEN 'national'
        ELSE 'customer'
    END AS level,
    org_id
FROM test_standards;

INSERT INTO standards (standard_code, standard_name, system_id, issuing_body, region, version, effective_date, status, org_id)
SELECT 
    ts.standard_code,
    ts.standard_name,
    ss.id AS system_id,
    ts.issuing_body,
    ts.region,
    ts.version,
    ts.effective_date,
    ts.status,
    ts.org_id
FROM test_standards ts
JOIN standard_systems ss ON LOWER(ts.issuing_body) = ss.code;
```

### 2. prototype_id 字段新增
```sql
-- TestRequest 表新增可选 FK
ALTER TABLE test_requests ADD COLUMN prototype_id INT NULL;
ALTER TABLE test_requests ADD CONSTRAINT fk_tr_prototype FOREIGN KEY (prototype_id) REFERENCES prototypes(id);

-- TestJudgment 表新增可选 FK
ALTER TABLE test_judgments ADD COLUMN prototype_id INT NULL;
ALTER TABLE test_judgments ADD CONSTRAINT fk_tj_prototype FOREIGN KEY (prototype_id) REFERENCES prototypes(id);
```

---

## 数字主线对比

### v1.0（原设计）
```
ProductPlan → Project → Test Center → Certification Center → ECR/ECO → Mass Production
                  ↑ (判定结果挂项目)
```

### v2.0（修正后）
```
ProductPlan → Verification Requirement → Project → Prototype → Test Center
                  ↓ (VR驱动)                ↑ (样机判定)     ↓
             Gate Rule Engine ←─────────── 样机版本迭代 ←── Judgment
                                                                  ↓
                                           Certification Center → ECR/ECO → Mass Production
```

---

> **说明**：本变更文档记录了 v1.0 → v2.0 的所有架构修正。修正范围仅限于：① 验证需求核心化 ② 标准库分层 ③ 样机实体新增 ④ Gate规则引擎。原有 S2（认证中心）、S3（变更控制）的设计保持不变。所有修正均考虑了向后兼容，不破坏现有表结构。
