# ROS Phase 6 S1 — 实验中心增量任务分解

> 文档版本: 1.0  
> 生成时间: 2026-06-24  
> 基于代码审计: 现有 `backend/app/models/test.py`, `backend/app/api/tests.py`, `backend/app/api/certifications.py`, `frontend/src/views/tests/TestsView.vue`, `frontend/src/views/prototypes/PrototypesView.vue`, `frontend/src/router/index.ts`, `backend/app/core/permissions.py`

---

## 一、现有代码审计结果

| 序号 | 实体 | 后端 Model | 后端 Schema | 后端 API | 前端页面 | 状态 |
|:---:|:-----|:-----------|:-----------|:---------|:---------|:-----|
| 1 | TestRequest | ✅ `test.py:18-44` | ✅ schemas:665-687 | ✅ `tests.py:38-116` | ✅ `TestsView.vue` | **需增强** |
| 2 | TestResult | ✅ `test.py:47-63` | ✅ schemas:649-662 | ✅ `tests.py:118-137` | (内嵌在TestsView) | **需增强** |
| 3 | Prototype | ✅ `test.py:118-138` | ✅ schemas:734-752 | ✅ `certifications.py:88-126` | ✅ `PrototypesView.vue` | **需增强** |
| 4 | VerificationRequirement | ❌ | ❌ | ❌ | ❌ | **新建** |
| 5 | TestExecution | ❌ | ❌ | ❌ | ❌ | **新建** |
| 6 | GateRule | ❌ | ❌ | ❌ | ❌ | **新建** |
| 7 | TestStandard(实验库) | ❌ | ❌ | ❌ | ❌ | **新建** |
| 8 | TargetMarket→Tests→Certs | ❌ | ❌ | ❌ | ❌ | **新建** |

### 关键发现

1. **TestRequest 现有字段**：`request_no`, `title`, `project_code`, `product_code`, `test_type`, `test_standard`, `trigger_mode`, `requester`, `requirement`, `sample_info`, `priority`, `status`, `target_date`, `completed_date`, `ng_count`, `result_summary`, `org_id`
   - 缺少：`vr_id`, `prototype_id`, `test_category`
   - `test_type` 目前是自由文本 → 需改造成规范化 `test_category` 枚举

2. **TestResult 现有字段**：`test_request_id`, `item_name`, `standard_value`, `actual_value`, `is_pass`, `remark`, `tested_by`, `tested_at`, `org_id`
   - 缺少：`prototype_id`, `execution_id`
   - `is_pass` (Boolean) → 需改为 `result` (PASS/FAIL/WAIVER) 三态
   - 缺少 `judgment_data` JSON 判定数据

3. **Prototype 现有字段**：`proto_no`, `product_code`, `project_code`, `proto_type`, `stage`, `status`, `quantity`, `material_status`, `produced_date`, `test_date`, `result`, `remark`, `org_id`
   - `proto_type` 当前是 hand_sample/模具首样/工程样机/小批样机/认证样机 → 需要标准化为 P0/P1/P2/P3 版本序列
   - 缺少：`project_id` FK, `version` (P0/P1/P2/P3), `test_request_ids` 关系

4. **Prototype 路由** 挂载在 `/certifications/prototypes` 前缀下 → 建议迁移到独立 `/prototypes` 路由或专用 test_center 路由

5. **认证/Certification** 已有 `target_market` 字段和认证类型枚举 → TargetMarket→RequiredTests→RequiredCertifications 可作为认证子模块扩展

---

## 二、任务清单（按实施顺序排列）

### 阶段 1: 后端模型层（新建 + 增强）

---

### Task M1: 新建 VerificationRequirement 模型
- **文件路径**: `backend/app/models/verification_requirement.py` (新建)
- **改动类型**: 新建
- **关键字段**:
  ```python
  id: int (PK)
  vr_code: str (唯一, 如 VR-20260624-0001)
  title: str (标题, 如 "APF ≥ 5.20")
  category: str (enum: performance/energy/noise/condensation/damp_heat/
                     high_temp_cool/low_temp_heat/frost_defrost/
                     long_run/elec_safety_pre)
  source: str (enum: product_plan/customer/standard/certification)
  source_id: str (关联源ID, 如 ProductPlan.id 或文本)
  target_value: str (目标值, 如 "≥5.20")
  unit: str (单位, 如 "W/W", "dB")
  status: str (enum: pending/verified/failed/waived)
  project_id: int (FK→projects.id, nullable)
  product_plan_id: str (FK→product_plans.id, nullable)
  gate_code: str (关联Gate, 如 "M4")
  remark: Text
  org_id: int (FK→organizations.id, nullable)
  created_at, updated_at: DateTime
  ```
- **预估复杂度**: 3
- **依赖**: 无
- **说明**:
  - 使用独立文件避免 `test.py` 超 500 行
  - category 使用 `SQLAlchemy Enum` 或 String+校验
  - source=product_plan 时支持自动生成（从 ProductPlan.performance_target JSON 提取）
  - 注册到 `backend/app/models/__init__.py`

---

### Task M2: 新建 TestExecution 模型
- **文件路径**: `backend/app/models/test_execution.py` (新建)
- **改动类型**: 新建
- **关键字段**:
  ```python
  id: int (PK)
  test_request_id: int (FK→test_requests.id)
  lab: str (实验室名称)
  equipment: str (设备编号/名称)
  operator: str (操作人员)
  start_time: DateTime
  end_time: DateTime (nullable)
  duration_minutes: int (计算字段, 自动)
  status: str (enum: running/completed/aborted)
  notes: Text (执行备注)
  org_id: int (FK→organizations.id, nullable)
  created_at: DateTime
  ```
- **预估复杂度**: 2
- **依赖**: 无（依赖 TestRequest，但 TestRequest 已存在）
- **说明**:
  - 与 TestRequest 一对多关系
  - 每个 TestRequest 可以有多次执行记录（重测/复测场景）
  - 注册到 `__init__.py`

---

### Task M3: 新建 GateRule 模型
- **文件路径**: `backend/app/models/gate_rule.py` (新建)
- **改动类型**: 新建
- **关键字段**:
  ```python
  id: int (PK)
  name: str (规则名称)
  product_line: str (产品线, nullable→通配)
  customer: str (客户, nullable→通配)
  gate_code: str (Gate编号, 如 "M4", "G1")
  required_vr_categories: Text (JSON数组, 如 ["performance","noise","condensation","damp_heat"])
  all_pass: bool (默认True: 必须全部通过)
  auto_block: bool (默认False: 自动阻塞Gate)
  priority: int (匹配优先级, 数字越小越优先)
  status: str (enum: active/inactive)
  description: Text
  created_by: str
  org_id: int (FK, nullable)
  created_at, updated_at: DateTime
  ```
- **预估复杂度**: 3
- **依赖**: M1 (VerificationRequirement)
- **说明**:
  - 匹配逻辑：`product_line` + `customer` 精确匹配 → product_line匹配+客户通配 → 全通配
  - `required_vr_categories` 存储 JSON 字符串
  - 内置 `evaluate()` 方法：给定 project + gate_code → 检查 VR 是否全部通过
  - 注册到 `__init__.py`

---

### Task M4: 新建 TargetMarket 模型（含 RequiredTests / RequiredCertifications）
- **文件路径**: `backend/app/models/target_market.py` (新建)
- **改动类型**: 新建
- **关键字段**:
  ```python
  # --- TargetMarket ---
  id: int (PK)
  market_code: str (如 "EU", "US", "AU", "SA", "CN")
  market_name: str (如 "欧盟", "美国")
  description: Text

  # --- RequiredTest (子表) ---
  target_market_id: int (FK)
  test_category: str (enum, 同VerificationRequirement.category)
  test_standard: str (如 "EN 14511", "AHRI 210/240")
  is_required: bool (默认True)

  # --- RequiredCertification (子表) ---
  target_market_id: int (FK)
  cert_type: str (如 "CE", "UL", "AHRI", "SAA", "CCC")
  cert_body: str (认证机构)
  is_mandatory: bool (默认True)
  ```
- **预估复杂度**: 2
- **依赖**: 无
- **说明**:
  - 使用组合模式：一个 TargetMarket → 多个 RequiredTest + 多个 RequiredCertification
  - 不绑定 CCC — 只在 target_market=CN 时出现
  - 设计为配置驱动，启动时 DB seed 初始数据
  - 注册到 `__init__.py`

---

### Task M5: 增强 TestRequest 模型
- **文件路径**: `backend/app/models/test.py`
- **改动类型**: 增强（修改已有模型）
- **新增关键字段**:
  ```python
  vr_id: int (FK→verification_requirements.id, nullable, comment="关联验证需求")
  prototype_id: int (FK→prototypes.id, nullable, comment="关联样机")
  test_category: str (nullable, comment="实验分类: performance/energy/noise/...")
  ```
- **预估复杂度**: 2
- **依赖**: M1, M2 (需要 VerificationRequirement 和 Prototype 先存在)
- **说明**:
  - 所有字段设为 `nullable=True` 保证向后兼容
  - `test_category` 将逐步取代现有的 `test_type` 自由文本
  - 添加 `relationship("VerificationRequirement")` 和 `relationship("Prototype")`

---

### Task M6: 增强 TestResult 模型
- **文件路径**: `backend/app/models/test.py`
- **改动类型**: 增强（修改已有模型）
- **新增/修改关键字段**:
  ```python
  # 新增字段
  prototype_id: int (FK→prototypes.id, nullable, comment="关联样机版本")
  execution_id: int (FK→test_executions.id, nullable, comment="关联执行记录")
  judgment_data: Text (nullable, comment="判定数据JSON, 如{合格偏差:0.5, 结论:'OK'}")

  # 修改字段（向后兼容）
  # is_pass: Boolean → 保留 is_pass 兼容旧数据, 新增 result: str
  result: str (nullable, comment="判定结果: PASS/FAIL/WAIVER")
  ```
- **预估复杂度**: 3
- **依赖**: M2, M5
- **说明**:
  - `result` (PASS/FAIL/WAIVER) 三态，取代 `is_pass` Boolean（保留旧字段兼容）
  - `judgment_data` 支持存储复杂判定参数（JSON）
  - 添加 relationship 到 TestExecution 和 Prototype

---

### Task M7: 增强 Prototype 模型（版本标准化）
- **文件路径**: `backend/app/models/test.py`
- **改动类型**: 增强（修改已有模型）
- **新增/修改关键字段**:
  ```python
  # 修改 proto_type 定义
  proto_type: str → 标准化为: "P0手板"/"P1首样"/"P2认证样机"/"P3量产样机"

  # 新增字段
  version: str (comment: "版本标识: P0/P1/P2/P3")
  project_id: int (FK→projects.id, nullable, comment="关联项目")
  ```
- **预估复杂度**: 2
- **依赖**: 无（但建议与 M5 一起实施）
- **说明**:
  - `proto_type` 保留旧值，`version` 新增标准化字段
  - 添加 `project_id` FK 直接关联 Project（现有 `project_code` 保留为冗余字段）
  - TestResult 的 `prototype_id` 实现"所有实验结果挂在样机上"
  - 版本升级时归档逻辑：旧 TestResult 的 prototype_id 指向旧版本

---

### 阶段 2: 后端 Schema 层

---

### Task S1: 新建 VerificationRequirement Schemas
- **文件路径**: `backend/app/schemas/__init__.py` (追加)
- **改动类型**: 新增
- **关键类**: `VerificationRequirementCreate`, `VerificationRequirementOut`, `VerificationRequirementListParams`
- **预估复杂度**: 2
- **依赖**: M1
- **说明**:
  - `VerificationRequirementOut` 继承自 Create + 包含 id/timestamps
  - 提供 `VR自动生成结果` schema: `VerificationRequirementGenerateResult(items: list)`

---

### Task S2: 新建 TestExecution Schemas
- **文件路径**: `backend/app/schemas/__init__.py` (追加)
- **改动类型**: 新增
- **关键类**: `TestExecutionCreate`, `TestExecutionOut`, `TestExecutionUpdate`
- **预估复杂度**: 1
- **依赖**: M2
- **说明**:
  - `TestExecutionOut` 包含 `test_request_id` 和实验室信息

---

### Task S3: 新建 GateRule Schemas
- **文件路径**: `backend/app/schemas/__init__.py` (追加)
- **改动类型**: 新增
- **关键类**: `GateRuleCreate`, `GateRuleOut`, `GateRuleEvalRequest`, `GateRuleEvalResult`
- **预估复杂度**: 2
- **依赖**: M3
- **说明**:
  - `GateRuleEvalRequest`: `{project_id, gate_code}`
  - `GateRuleEvalResult`: `{passed: bool, details: [{category, status}]}`

---

### Task S4: 新建 TargetMarket Schemas
- **文件路径**: `backend/app/schemas/__init__.py` (追加)
- **改动类型**: 新增
- **关键类**: `TargetMarketCreate`, `TargetMarketOut`, `RequiredTestCreate`, `RequiredTestOut`, `RequiredCertificationCreate`, `RequiredCertificationOut`
- **预估复杂度**: 2
- **依赖**: M4
- **说明**:
  - 组合输出：`TargetMarketDetailOut( TargetMarketOut + tests: list[RequiredTestOut] + certs: list[RequiredCertificationOut] )`

---

### Task S5: 增强 TestRequest + TestResult Schemas
- **文件路径**: `backend/app/schemas/__init__.py`
- **改动类型**: 修改
- **关键改动**:
  - `TestRequestCreate` 新增: `vr_id`, `prototype_id`, `test_category`
  - `TestRequestOut` 新增: `vr_id`, `prototype_id`, `test_category`, `executions: list[TestExecutionOut]`
  - `TestResultCreate` 新增: `prototype_id`, `execution_id`, `result`, `judgment_data`
  - `TestResultOut` 新增: `prototype_id`, `execution_id`, `result`, `judgment_data`
- **预估复杂度**: 2
- **依赖**: M5, M6, S1, S2
- **说明**:
  - 所有新增字段为 `Optional` 保证向后兼容

---

### 阶段 3: 后端 API 层

---

### Task A1: 新建 VerificationRequirement API
- **文件路径**: `backend/app/api/verification_requirements.py` (新建)
- **改动类型**: 新建
- **路由前缀**: `/verification-requirements`
- **端点**:
  - `GET /` — 列表（支持 project_code, category, status, source 筛选）
  - `POST /` — 创建 VR
  - `GET /{id}` — 详情
  - `PATCH /{id}` — 更新
  - `DELETE /{id}` — 删除（软删除或硬删除）
  - `POST /generate-from-plan/{plan_id}` — 从 ProductPlan 自动生成 VR
  - `GET /by-project/{project_id}` — 按项目获取 VR（含 Gate 评估）
- **预估复杂度**: 4
- **依赖**: M1, S1
- **说明**:
  - `generate-from-plan` 从 `ProductPlan.performance_target` JSON 解析
  - 自动生成的 VR `source='product_plan'`, `status='pending'`
  - 注册 API 路由到 main.py
  - 注册 API_MENU_MAP 权限

---

### Task A2: 新建 / 迁移 Prototype API（独立路由）
- **文件路径**: `backend/app/api/prototypes.py` (新建)
- **改动类型**: 新建 + 迁移
- **路由前缀**: `/prototypes`（独立于 certifications）
- **端点**:
  - `GET /` — 列表（增强筛选: version, project_id, stage）
  - `POST /` — 创建（含 version 标准化）
  - `GET /{id}` — 详情（含关联 VR + TestResult）
  - `PATCH /{id}` — 更新（含版本升级逻辑）
  - `POST /{id}/upgrade` — 版本升级（P0→P1→P2→P3，旧判定归档）
- **预估复杂度**: 3
- **依赖**: M7, S5
- **说明**:
  - 保留 `certifications.py` 中原有 `/prototypes` 端点作为向后兼容（返回兼容数据）
  - 新路由提供完整功能
  - 注册 API_MENU_MAP: `"prototypes": "prototypes"`

---

### Task A3: 新建 TestExecution API
- **文件路径**: `backend/app/api/test_executions.py` (新建)
- **改动类型**: 新建
- **路由前缀**: `/test-requests/{rid}/executions`
- **端点**:
  - `GET /` — 按 TestRequest 获取执行记录列表
  - `POST /` — 创建执行记录（开始实验）
  - `PATCH /{exec_id}` — 更新执行记录（结束时间/状态/备注）
  - `GET /{exec_id}` — 执行详情
- **预估复杂度**: 2
- **依赖**: M2, S2
- **说明**:
  - 嵌套路由以 TestRequest 为父资源
  - 状态机：创建时 `status=running` → 更新时可设为 `completed/aborted`

---

### Task A4: 新建 GateRule API
- **文件路径**: `backend/app/api/gate_rules.py` (新建)
- **改动类型**: 新建
- **路由前缀**: `/gate-rules`
- **端点**:
  - `GET /` — 规则列表（支持 product_line, gate_code, status 筛选）
  - `POST /` — 创建规则
  - `GET /{id}` — 规则详情
  - `PATCH /{id}` — 更新规则
  - `DELETE /{id}` — 删除规则
  - `POST /evaluate` — 评估 API（通过 project_id + gate_code → 返回通过/阻塞）
  - `GET /check-gate/{project_id}/{gate_code}` — 快速检查 Gate 是否可通过
- **预估复杂度**: 4
- **依赖**: M3, S3, A1
- **说明**:
  - 评估 API 核心逻辑：
    1. 根据 project 的 product_line + customer 找到匹配规则
    2. 按 priority 排序取最精确匹配
    3. 提取 required_vr_categories
    4. 查询该 project 下所有对应 category 的 VR
    5. 如 all_pass=True → 全部 PASS 才返回通过
    6. 如 auto_block=True → 任一 FAIL 触发自动阻塞

---

### Task A5: 新建 TargetMarket API
- **文件路径**: `backend/app/api/target_markets.py` (新建)
- **改动类型**: 新建
- **路由前缀**: `/target-markets`
- **端点**:
  - `GET /` — 市场列表
  - `POST /` — 创建市场
  - `GET /{id}/requirements` — 某市场的完整要求（测试项+认证项）
  - `PATCH /{id}` — 更新
- **预估复杂度**: 2
- **依赖**: M4, S4
- **说明**:
  - 配置驱动，初始数据通过 DB Seed 或迁移脚本填充

---

### Task A6: 增强 Tests API（现有 tests.py）
- **文件路径**: `backend/app/api/tests.py`
- **改动类型**: 增强
- **关键改动**:
  - `POST /` — TestRequestCreate 支持新增 `vr_id`, `prototype_id`, `test_category`
  - `GET /{rid}` — 返回增加 `executions`, `vr`, `prototype` 关联数据
  - `POST /{rid}/results` — TestResultCreate 支持新增 `prototype_id`, `execution_id`, `result`, `judgment_data`
  - 新增 `GET /categories` — 返回标准 test_category 枚举列表
- **预估复杂度**: 2
- **依赖**: S5, A3
- **说明**:
  - 保持向后兼容：旧字段依然有效
  - 新增字段在原 schema 基础上扩展

---

### 阶段 4: 前端页面

---

### Task F1: 新建 VerificationRequirement 管理页面
- **文件路径**: `frontend/src/views/tests/VerificationRequirementView.vue` (新建)
- **改动类型**: 新建
- **页面内容**:
  - 表格列表：VR编码、标题、分类、来源、目标值、状态、操作
  - 筛选栏：分类、来源、状态、项目
  - 新建/编辑对话框（含来源选择器：产品策划/客户要求/标准要求/认证要求）
  - 从 ProductPlan 一键生成按钮
  - 关联样机和实验结果的时间线展示
- **预估复杂度**: 4
- **依赖**: A1
- **说明**:
  - 使用 `<script setup>` + TypeScript
  - 调用 `/api/verification-requirements/*` 接口
  - 配合 `VerificationReqForm.vue` 和 `VerificationReqTimeline.vue` 子组件

---

### Task F2: 新建 TestExecution 执行记录面板
- **文件路径**: `frontend/src/views/tests/TestExecutionPanel.vue` (新建, 组件级)
- **改动类型**: 新建
- **组件内容**:
  - 嵌入在 TestRequest 详情页
  - 展示执行记录列表：实验室、设备、人员、时间范围、状态
  - 新建执行记录表单
  - 结束执行、填写备注
- **预估复杂度**: 3
- **依赖**: A3
- **说明**:
  - 作为 TestsView 的增强组件，或独立页面
  - 建议作为 TestRequest 详情页的子组件

---

### Task F3: 新建 GateRule 管理页面
- **文件路径**: `frontend/src/views/tests/GateRuleView.vue` (新建)
- **改动类型**: 新建
- **页面内容**:
  - 规则列表：规则名、产品线、客户、Gate、必检项、开关状态
  - 新建/编辑表单（含 product_line/customer/gate_code 选择器）
  - required_vr_categories 多选 Tag 编辑器
  - all_pass 和 auto_block 开关
  - 评估测试面板：选择项目 + Gate → 执行评估 → 显示结果
- **预估复杂度**: 4
- **依赖**: A4
- **说明**:
  - 配合 `GateRuleForm.vue` 和 `GateRuleEvalResult.vue` 子组件
  - 评估结果用绿/黄/红状态标签展示

---

### Task F4: 新建 TargetMarket 配置页面
- **文件路径**: `frontend/src/views/tests/TargetMarketView.vue` (新建)
- **改动类型**: 新建
- **页面内容**:
  - 市场列表：市场编码、名称、操作
  - 点击展开市场详情：必需的测试项 + 必需的认证项
  - 添加/编辑 RequiredTest 和 RequiredCertification
- **预估复杂度**: 3
- **依赖**: A5
- **说明**:
  - 配置维护页面，供管理员使用
  - 可与认证管理页面联动

---

### Task F5: 增强 TestsView 页面
- **文件路径**: `frontend/src/views/tests/TestsView.vue`
- **改动类型**: 增强
- **关键改动**:
  - 表格增加列：VR编码、样机编号、实验分类
  - 筛选增加：实验分类、VR、样机
  - 新建/编辑表单增加：关联VR选择器、关联样机选择器、实验分类下拉
  - 嵌入 TestExecutionPanel 组件（展开行或详情弹窗）
  - 结果录入支持三态判定（PASS/FAIL/WAIVER）
- **预估复杂度**: 3
- **依赖**: A6, F2
- **说明**:
  - 保持页面简洁（现有 103 行 → 预计 250-300 行）
  - 如果超出 600 行限制，拆分子组件

---

### Task F6: 增强 PrototypesView 页面
- **文件路径**: `frontend/src/views/prototypes/PrototypesView.vue`
- **改动类型**: 增强
- **关键改动**:
  - 增加 version 列（P0/P1/P2/P3 标签）
  - 增加"关联VR"和"关联实验结果"展示
  - 增加版本升级操作按钮
  - 新建表单增加：项目选择器、版本选择器
- **预估复杂度**: 3
- **依赖**: A2
- **说明**:
  - 保留现有筛选和表格结构
  - 新增字段在原有 form 基础上扩展

---

### Task F7: 更新前端路由
- **文件路径**: `frontend/src/router/index.ts`
- **改动类型**: 修改
- **新增路由**:
  ```typescript
  {
    path: 'tests/verification-requirements',
    name: 'VerificationRequirements',
    component: () => import('@/views/tests/VerificationRequirementView.vue'),
    meta: { title: '验证需求', menu: 'tests' },
  },
  {
    path: 'tests/gate-rules',
    name: 'GateRules',
    component: () => import('@/views/tests/GateRuleView.vue'),
    meta: { title: 'Gate规则引擎', menu: 'tests' },
  },
  {
    path: 'tests/target-markets',
    name: 'TargetMarkets',
    component: () => import('@/views/tests/TargetMarketView.vue'),
    meta: { title: '目标市场配置', menu: 'tests' },
  },
  ```
- **预估复杂度**: 1
- **依赖**: F1, F3, F4
- **说明**:
  - 所有新页面放在 `tests/` 子路径下，共享 `tests` 菜单权限

---

### 阶段 5: 权限与配置

---

### Task P1: 更新权限菜单
- **文件路径**: `backend/app/core/permissions.py`
- **改动类型**: 修改
- **关键改动**:
  - `ALL_MENUS` 新增（可选）: 如果 VR/Gate/TargetMarket 需要独立菜单权限
  - `API_MENU_MAP` 新增:
    ```python
    "verification-requirements": "tests",
    "prototypes": "prototypes",  # 独立路由
    "gate-rules": "tests",
    "target-markets": "tests",
    "test-requests": "tests",
    ```
  - `MENU_PATH_MAP` 可选新增
- **预估复杂度**: 1
- **依赖**: A1, A2, A4, A5
- **说明**:
  - 如果使用 `tests` 父菜单共享权限，则无需新增 ALL_MENUS 条目
  - 关键是要确保 API_MENU_MAP 正确映射路由前缀

---

### Task P2: 注册 API 路由到 FastAPI
- **文件路径**: `backend/app/main.py`
- **改动类型**: 修改
- **关键改动**:
  ```python
  from app.api.verification_requirements import router as vr_router
  from app.api.prototypes import router as proto_router
  from app.api.test_executions import router as exec_router
  from app.api.gate_rules import router as gate_router
  from app.api.target_markets import router as market_router

  app.include_router(vr_router, prefix="/api")
  app.include_router(proto_router, prefix="/api")
  app.include_router(exec_router, prefix="/api")
  app.include_router(gate_router, prefix="/api")
  app.include_router(market_router, prefix="/api")
  ```
- **预估复杂度**: 1
- **依赖**: A1-A5
- **说明**:
  - 路由已自带 prefix，在 `app.include_router` 级别不再加 `/api` 前缀
  - 或者统一加：检查现有模式（tests.py 用的是 `prefix="/tests"`）

---

### 阶段 6: 数据库迁移 & 种子数据

---

### Task D1: 新建数据库迁移脚本
- **文件路径**: `backend/migrate_v6_add_test_center.py` (新建)
- **改动类型**: 新建
- **迁移内容**:
  ```sql
  -- 1. 新建表
  CREATE TABLE IF NOT EXISTS verification_requirements (...);
  CREATE TABLE IF NOT EXISTS test_executions (...);
  CREATE TABLE IF NOT EXISTS gate_rules (...);
  CREATE TABLE IF NOT EXISTS target_markets (...);
  CREATE TABLE IF NOT EXISTS required_tests (...);
  CREATE TABLE IF NOT EXISTS required_certifications (...);

  -- 2. 修改已有表
  ALTER TABLE test_requests ADD COLUMN vr_id INT NULL;
  ALTER TABLE test_requests ADD COLUMN prototype_id INT NULL;
  ALTER TABLE test_requests ADD COLUMN test_category VARCHAR(50) NULL;

  ALTER TABLE test_results ADD COLUMN prototype_id INT NULL;
  ALTER TABLE test_results ADD COLUMN execution_id INT NULL;
  ALTER TABLE test_results ADD COLUMN result VARCHAR(10) NULL;
  ALTER TABLE test_results ADD COLUMN judgment_data TEXT NULL;

  ALTER TABLE prototypes ADD COLUMN version VARCHAR(10) NULL;
  ALTER TABLE prototypes ADD COLUMN project_id INT NULL;
  ```
- **预估复杂度**: 3
- **依赖**: M1-M7
- **说明**:
  - 参照 `migrate_v5_add_tenant.py` 的模式
  - 使用原始 SQL + SQLAlchemy 混合方式
  - 所有 ALTER 用 `IF NOT EXISTS` / `IF column not exists` 保护

---

### Task D2: DB 种子数据（标准实验库 + 目标市场初始数据）
- **文件路径**: `backend/seed_data_v6.py` (新建) 或 `backend/app/seed_data/__init__.py` (追加)
- **改动类型**: 新建
- **种子内容**:
  ```python
  # 标准实验库（方案评审阶段）
  STANDARD_TESTS_PHASE1 = [
      {"category": "performance", "name": "性能测试"},
      {"category": "energy", "name": "能效测试"},
      {"category": "noise", "name": "噪音测试"},
      {"category": "condensation", "name": "凝露测试"},
      {"category": "damp_heat", "name": "潮态测试"},
  ]

  # 标准实验库（首样阶段）
  STANDARD_TESTS_PHASE2 = [
      {"category": "high_temp_cool", "name": "高温制冷"},
      {"category": "low_temp_heat", "name": "低温制热"},
      {"category": "frost_defrost", "name": "冻结融霜"},
      {"category": "long_run", "name": "长时间运行"},
      {"category": "elec_safety_pre", "name": "电气安全预验证"},
  ]

  # 目标市场
  TARGET_MARKETS = [
      {"code": "EU", "name": "欧盟", "tests": [...], "certs": [{"type": "CE"}, {"type": "EN"}]},
      {"code": "US", "name": "美国", "tests": [...], "certs": [{"type": "UL"}, {"type": "AHRI"}]},
      {"code": "AU", "name": "澳洲", "tests": [...], "certs": [{"type": "SAA"}]},
  ]
  ```
- **预估复杂度**: 2
- **依赖**: D1
- **说明**:
  - 提供可重复执行的 seed 脚本
  - 使用 `INSERT IGNORE` 或 `ON CONFLICT DO NOTHING`

---

### 阶段 7: 集成 & 验证

---

### Task I1: 端到端集成测试
- **文件路径**: 后端新增 `/backend/tests/test_phase6_s1.py`
- **改动类型**: 新建
- **测试场景**:
  1. 创建 ProductPlan → 自动生成 VR（通过 generate-from-plan API）
  2. 手动创建 VR + CRUD 验证
  3. 创建 Project → 创建 Prototype → 创建 TestRequest（关联 VR + Prototype）
  4. 创建 TestExecution → 添加 TestResult（三态判定）
  5. 配置 GateRule → 调用 evaluate API → 验证 Gate 阻塞逻辑
  6. 查看 TargetMarket 配置 → 验证 RequiredTests + RequiredCerts
- **预估复杂度**: 4
- **依赖**: A1-A6, D1-D2
- **说明**:
  - 使用 pytest + FastAPI TestClient
  - 使用独立测试数据库（SQLite 内存模式）

---

### Task I2: 数据完整性验证（升级后旧数据检查）
- **文件路径**: `backend/scripts/check_data_integrity_v6.py` (新建)
- **改动类型**: 新建
- **检查内容**:
  - 所有旧 TestRequest 数据无 vr_id/prototype_id → 标记为"未关联"
  - 所有旧 TestResult 数据无 prototype_id → 用所在 TestRequest 推算
  - Prototype 版本为空 → 根据 proto_type 自动推断版本
- **预估复杂度**: 2
- **依赖**: D1
- **说明**:
  - 只读不写，生成报告
  - 建议在升级后运行一次

---

### Task I3: 更新 OpenAPI 文档
- **文件路径**: `backend/docs/openapi.yaml`
- **改动类型**: 修改
- **关键改动**: 同步新增/修改的 API 端点
- **预估复杂度**: 2
- **依赖**: A1-A6
- **说明**:
  - 如果有自动生成文档工具，则直接运行
  - 否则手动补充变更部分

---

## 三、实施顺序依赖图

```
M1 → S1 → A1 → F1 ──┐
                     │
M2 → S2 → A3 → F2 ──┤
                     │
M3 → S3 → A4 → F3 ──┤
                     │
M4 → S4 → A5 → F4 ──┤
                     │
M5 ─┐                ├→ P1 → P2 → D1 → D2 → I1 → I2 → I3
    ├→ S5 → A6 → F5 ─┤
M6 ─┘                │
                     │
M7 → ───→ A2 → F6 ──┘
      F7 ────────────┘
```

**关键路径**: M1 → S1 → A1 → F1 + M5 → S5 → A6 → F5
**并行度**: M1~M4 可并行开发，F1~F4 可并行开发

---

## 四、工作量估算

| 阶段 | 任务数 | 预估总复杂度 | 备注 |
|:-----|:------:|:-----------:|:-----|
| 后端模型层 (M1-M7) | 7 | 17 | 含3个新建+4个增强 |
| 后端Schema层 (S1-S5) | 5 | 9 | 含4个新建+1个增强 |
| 后端API层 (A1-A6) | 6 | 17 | 含5个新建+1个增强 |
| 前端页面 (F1-F7) | 7 | 21 | 含4个新建+2个增强+1个路由 |
| 权限与配置 (P1-P2) | 2 | 2 | |
| 数据库迁移 (D1-D2) | 2 | 5 | 含迁移脚本+种子数据 |
| 集成验证 (I1-I3) | 3 | 8 | 含测试+数据检查+文档 |
| **合计** | **32** | **79** | **约 2-3 人周** |

---

## 五、风险与建议

1. **向后兼容风险**: TestRequest/TestResult/Prototype 的字段变更需要确保旧前端仍可用，建议分两阶段部署（先加字段，后改前端）
2. **Prototype 路由迁移**: 现有前端 `PrototypesView.vue` 调用 `/certifications/prototypes`，新版独立路由 `/prototypes` 发布后，前端需同步更新 API 调用路径
3. **gate_code 体系**: 现有 `stage_gate_service.py` 使用 G0-G6，`ProjectGate` 使用 M1-M9，GateRule 的 `gate_code` 需要同时兼容两种体系
4. **VerificationRequirement.performance_target 解析**: ProductPlan 的 `performance_target` 是自由 JSON 文本，需要定义解析协议或使用标准 schema
