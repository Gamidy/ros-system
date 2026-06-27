# ROS 后端 API 返回类型注解 — 执行计划

> **目标**: 为 ~386 个未标注返回类型的 API 函数补充精确类型注解（使用 Pydantic schema），使前端 API 层获得自动类型推断。

---

## 一、现状分析

| 指标 | 数值 |
|------|------|
| API endpoint 文件 | **50** 个（`backend/app/api/*.py`） |
| 总计 API 函数 | **553** 个 |
| 已有返回类型 | **167** (30%) |
| 缺少返回类型 | **386** (70%) |
| 其中 `-> dict` 标注 | ~53 个 |
| 其中 `-> list` 标注 | ~25 个 |
| 其中 `-> SchemaOut` 标注 | ~89 个 |
| Schema 文件 | **20** 个（`backend/app/schemas/*.py`） |

### 当前代码风格（三档成熟度）

| 等级 | 示例 | 占比 |
|------|------|------|
| **A级** ✅ 已完整 | `@router.get(...)` + `response_model=SchemaOut` + `-> SchemaOut` | ~30% |
| **B级** ⚠️ 半完整 | `@router.get(...)` + `response_model=SchemaOut` **但缺返回类型** | ~25% |
| **C级** ❌ 未注解 | `@router.get(...)` **无** `response_model` **且无** `->` 返回类型 | ~45% |

### 关键发现

1. **`safety.py` 已有优秀模式**: `SafetyStandardListOut(items: list[T], total: int)` — 分页结果模式值得推广
2. **内联 Schema 常见**: `product_plan.py`、`cost_accounting.py`、`competitor.py` 等文件内部定义 Pydantic schema
3. **返回 ORM 模型**: 多个 endpoint 返回 SQLAlchemy 对象而未转换为 Pydantic schema（但 FastAPI 通过 `response_model` 自动转换）
4. **无通用 PaginatedResult**: 各模块独立实现分页结果 schema
5. **部分 endpoint 返回纯 dict**: 通过 `_plan_to_dict()` 等辅助函数手工构造

---

## 二、类型补充策略

### 核心原则

| 原则 | 说明 |
|------|------|
| **已有 schema → 直接用** | 对 `response_model` 已设 schema 的 endpoint，在函数签名加上相同返回类型 |
| **已有类型不动** | 已有 `-> SchemaOut` 的函数不修改，避免回归 |
| **内联 schema 优先** | 对没有对应 schema 的输出，优先在 API 文件顶部补充内联 schema |
| **先小后大** | 从依赖少、改动小的模块开始，逐步推进到复杂模块 |
| **分页统一化** | 逐步为分页 endpoint 补充 `*ListOut(items, total)` schema |
| **ORM 返回 → schema 转换** | `return db.query(...).all()` → 确认 `response_model` 能正确序列化 |
| **dict 返回 → 优先 schema** | 手工 `return {...}` 的 endpoint，优先创建对应 out schema |

### 三种处理模式

#### 模式 A: 已有 `response_model` ∧ 缺返回类型 ✅（最简单，~140 处）
```python
# BEFORE
@router.get("/{id}", response_model=CertificationOut)
def get_cert(id: int, db: Session = Depends(get_db)):
    ...

# AFTER — 函数签名加返回类型
@router.get("/{id}", response_model=CertificationOut)
def get_cert(id: int, db: Session = Depends(get_db)) -> CertificationOut:
    ...
```

#### 模式 B: 无 `response_model` ∧ 缺返回类型 — 简单 CRUD（~80 处）
```python
# BEFORE
@router.get("")
def list_things(...):
    return db.query(Thing).all()

# AFTER — 加 response_model + 返回类型
@router.get("", response_model=list[ThingOut])
def list_things(...) -> list[ThingOut]:
    return db.query(Thing).all()
```

#### 模式 C: 无 `response_model` ∧ 分页输出（~60 处）
```python
# BEFORE
@router.get("")
def list_things(...) -> dict:
    ...
    return {"items": [...], "total": total}

# AFTER — 定义 PaginatedThingOut + 若缺则创建
@router.get("", response_model=PaginatedThingOut)
def list_things(...) -> PaginatedThingOut:
    ...
    return PaginatedThingOut(items=[ThingOut.model_validate(t) for t in items], total=total)
```

#### 模式 D: 复杂聚合/stats 输出（~30 处）
```python
# BEFORE
@router.get("/stats")
def get_stats(...) -> dict:
    ...
    return {"total_rules": n, "by_level": {...}, ...}

# AFTER — 内联 StatsOut schema
class StatsOut(BaseModel):
    total_rules: int
    active_rules: int
    ...

@router.get("/stats", response_model=StatsOut)
def get_stats(...) -> StatsOut:
    ...
    return StatsOut(total_rules=n, ...)
```

---

## 三、分步执行计划

### 第 0 步（前置，1 个 PR）: 准备通用 PaginatedResult 基类

**文件**: `backend/app/schemas/__init__.py` (或新建 `backend/app/schemas/common.py`)

创建通用分页包装器：

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
```

> **为什么额外加 `page`/`page_size`**: 多数分页 endpoint 的前端 expects 这些字段（参考 `product_plan.py` 第 280-284 行、`projects.py` 第 250-269 行）。

**风险评级**: ⭐ 低
**预估改动**: ~20 行

---

### 第 1 步（低风险）: S2 认证模块 — 已部分类型化

| 文件 | 函数总数 | 缺类型 | 类型化方案 |
|------|---------|--------|-----------|
| `s2_certificates.py` | 7 | 7 | ✅ 全部已有 `response_model=CertificateOut`，直接补 `-> CertificateOut`；`suspend`/`revoke` 补内联 `ActionResponse(BaseModel)` |
| `s2_cert_projects.py` | 6 | 5 | ✅ 已有 `response_model=`，补对应返回类型；`/{cp_id}/status` 缺 schema |
| `s2_cert_executions.py` | 3 | 3 | ✅ 全部已有 `response_model`，直接补 |
| `s2_cert_requirements.py` | 3 | 3 | ✅ 同上 |
| `s2_cert_results.py` | 4 | 4 | ✅ 同上 |
| `s2_cert_samples.py` | 4 | 3 | ✅ 同上，`{sample_id}/upload` 需单独处理 |
| `s2_change_impact.py` | 7 | 7 | `/rules` + `/records` 分页 → 用 `PaginatedResult[ChangeImpactRuleOut]`；stats 补 `ImpactStatsOut` |
| `s2_gate_rules.py` | 5 | 5 | 全部缺 `response_model` → 补 |
| **小计** | **39** | **37** | |

**风险评级**: ⭐ 低 — S2 模块 CRUD 模式统一，schema 完备
**预估改动**: ~120 行

---

### 第 2 步（低风险）: 验证需求与目标市场

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `verification_requirements.py` | 7 | 6 | 主要缺分页返回类型；`/generate-from-plan` 需内联 schema |
| `target_markets.py` | 12 | 12 | 全部缺类型 — 简单 CRUD，需先检查 schemas/ 是否有对应 schema |
| `gate_rules.py` | 7 | 7 | 分页列表 + 简单 CRUD |
| `test_executions.py` | 4 | 4 | 已有 schemas `TestExecutionOut` |
| **小计** | **30** | **29** | |

**风险评级**: ⭐ 低 — 与主业务解耦，schema 多数已存在
**预估改动**: ~80 行

---

### 第 3 步（中等风险）: 产品策划与 BOM

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `product_plan.py` | 18 | 14 | ⚠️ 内联 schema 多（`PlanOut`, `PlanStatusOut` 等），复杂拼接返回（`_plan_to_dict`）→ 需为每个 endpoint 验证是否有 schema 对应 |
| `product_plan_subs.py` | 15 | 14 | 同上，子表模块 |
| `products.py` | 19 | 4 | 已有 Schema 较全，仅少量缺 |
| `bom.py` | 25 | 6 | BOM 树返回类型复杂（`BOMTreeOut`），需特别处理 |
| `product_plan_link.py` | — | — | 已由 `ProductPlanLinkOut` 覆盖 |
| **小计** | **77** | **38** | |

**⚠️ 注意**: `product_plan.py` 的 `_plan_to_dict()` 返回手工构造 dict，不能直接用 `PlanOut`（多了 initiation 子表字段）。最佳方案：将现有 `PlanOut` 扩展为完整 dict key 包含所有子表字段，或新建 `PlanFullOut`。

**风险评级**: ⭐⭐ 中等 — 内联 schema 复杂，需仔细匹配字段
**预估改动**: ~180 行

---

### 第 4 步（中等风险）: 项目管理

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `projects.py` | 27 | 16 | 复杂嵌套返回（`get_program` 拼字段、`get_project_detail` 拼 gates/milestones/risks 数组）→ 需创建 `ProgramDetailOut`/`ProjectDetailOut` |
| `pm_workspace.py` | 19 | 14 | 工作台聚合数据，返回结构不固定 |
| `pm_proposal_api.py` | 5 | 4 | 提案审批流程 |
| `pm_proposal_utils.py` | 11 | 4 | 工具函数 |
| `pm_config.py` | 4 | 3 | 配置查询 |
| `pm_roadmap.py` | 2 | 1 | 路线图 |
| `pm_statistics.py` | 1 | 1 | 统计 |
| `pm_accessory.py` | 2 | 1 | 配件管理 |
| **小计** | **71** | **44** | |

**⚠️ 注意**: `projects.py` 的 `get_project_detail` 手工构造深度嵌套 dict（含 gates/milestones/risks 三个子列表），需对应 `ProjectDetailOut` schema。

**风险评级**: ⭐⭐ 中等 — 数据结构复杂，需谨慎定义 schema
**预估改动**: ~200 行

---

### 第 5 步（中等风险）: 认证/安规/测试

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `certifications.py` | 20 | 13 | 部分已类型化 |
| `safety.py` | 20 | 20 | ✅ 已有完整 schema（含 `*ListOut`），仅缺函数返回类型注解 → 纯机械补 |
| `tests.py` | 10 | 7 | 测试管理 |
| `prototypes.py` | 8 | 7 | 样机管理 |
| `manufacturability.py` | 21 | 19 | DFM — 已有 schema 但函数缺注解 |
| **小计** | **79** | **66** | |

> `safety.py` 是最佳起点 — schema 已完善，只需在函数签名加 `-> Type`。

**风险评级**: ⭐ 低~中 — safety 几乎纯机械；manufacturability schema 需检查完整性
**预估改动**: ~160 行

---

### 第 6 步（中等风险）: 财务与采购

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `cost_accounting.py` | 35 | 5 | ✅ 已高度类型化，仅 5 处缺 |
| `cost_alert_api.py` | 6 | 6 | 成本预警 |
| `purchases.py` | 13 | 5 | 采购管理 |
| `outsource.py` | 16 | 14 | 外协管理 |
| **小计** | **70** | **30** | |

**风险评级**: ⭐ 低 — schema 完备（`purchase.py`/`outsource.py` 均已定义），函数签名补加即可
**预估改动**: ~80 行

---

### 第 7 步（中等风险）: 认证与工程变更

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `ecr.py` | 18 | 12 | ECR — 已有 `ECROut`/`ECRDetailOut` 等 |
| `eco.py` | 21 | 15 | ECO — 同上 |
| `competitor.py` | 28 | 21 | 竞品库 — 内联 schema 多 |
| `competitor_bench.py` | 2 | 1 | 对标分析 |
| **小计** | **69** | **49** | |

**风险评级**: ⭐⭐ 中等 — ECR/ECO 状态机流转、competitor 批量操作需特殊处理
**预估改动**: ~160 行

---

### 第 8 步（较高风险）: 认证与管理后台

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `auth.py` | 12 | 7 | 认证 — `Token`/`UserOut` 等 schema 完备，但 login/logout 返回特别 |
| `admin_*.py` (5 个) | 30 | 25 | 后台管理 — 配置 CRUD，schema 可能不完整 |
| `password_reset_api.py` | 3 | 1 | 密码重置 |
| `user_notification_api.py` | 2 | 2 | 用户通知 |
| `alerts.py` | 5 | 5 | 预警 — 已有 schema |
| `approvals.py` | 16 | 11 | 审批流 — 已有 schema |
| `bi_analytics.py` | 4 | 4 | BI 分析 |
| **小计** | **72** | **55** | |

**风险评级**: ⭐⭐⭐ 较高 — auth 涉及安全；admin 配置 schema 可能缺失需补充
**预估改动**: ~150 行

---

### 第 9 步（较高风险）: 剩余零散模块

| 文件 | 函数总数 | 缺类型 | 说明 |
|------|---------|--------|------|
| `dashboard.py` | 6 | 5 | 仪表盘 — 聚合查询，需 `DashboardResponse` |
| `risk_dashboard.py` | 7 | 7 | 风险仪表盘 |
| `knowledge.py` | 7 | 5 | 知识库 |
| `event_logs.py` | 7 | 5 | 事件日志 |
| `event_timeline.py` | 5 | 5 | 事件时间线 |
| `webhooks.py` | 8 | 7 | Webhook |
| `state_machine_api.py` | 2 | 1 | 状态机 |
| `audit_logs.py` | 2 | 2 | 审计日志 |
| `rd_panel.py` | 2 | 1 | 研发面板 |
| **小计** | **46** | **38** | |

**风险评级**: ⭐⭐⭐ 较高 — schema 可能不完备，部分需要先定义 schema
**预估改动**: ~120 行

---

## 四、汇总

| 步骤 | 模块 | 函数数 | 缺类型数 | 风险 | 预估行数 |
|------|------|--------|---------|------|---------|
| 0 | 通用 PaginatedResult | — | — | ⭐ | 20 |
| 1 | S2 认证模块 | 39 | 37 | ⭐ | 120 |
| 2 | 验证需求/目标市场 | 30 | 29 | ⭐ | 80 |
| 3 | 产品策划 & BOM | 77 | 38 | ⭐⭐ | 180 |
| 4 | 项目管理 | 71 | 44 | ⭐⭐ | 200 |
| 5 | 认证/安规/测试 | 79 | 66 | ⭐~⭐⭐ | 160 |
| 6 | 财务与采购 | 70 | 30 | ⭐ | 80 |
| 7 | 认证变更/竞品 | 69 | 49 | ⭐⭐ | 160 |
| 8 | 认证与后台管理 | 72 | 55 | ⭐⭐⭐ | 150 |
| 9 | 剩余零散模块 | 46 | 38 | ⭐⭐⭐ | 120 |
| **总计** | **50 文件** | **553** | **386** | — | **~1270** |

---

## 五、执行建议

### 推荐执行顺序
1. **Step 0** → **Step 1** (Quick wins, 快速见效) → **Step 2** → **Step 6**
2. **Step 5** (safety.py 纯机械) → **Step 3** (核心业务，需仔细) → **Step 4**
3. **Step 7** → **Step 8** → **Step 9** (复杂度高)

### 每个文件的标准操作流程
```
1. 查: 检查 app/schemas/*.py 已有哪些 out-schema
2. 定: 确认每个 endpoint 的 response 应该用什么 schema
3. 补: 若缺 schema，在对应 schemas/*.py 文件补充
4. 标: 在函数签名加返回类型注解
5. 验: python -c "compile(open('file.py').read(), 'file.py', 'exec')" 确保语法正确
```

### 风险规避
- **每个文件作为一个独立 PR/commit**，不要跨文件
- **先跑 `pytest` 确认当前 OK**，改完再跑一次
- **对 inline dict 构建的 endpoint**（如 `_plan_to_dict`），不要急着改构造逻辑，先确认现有 schema 覆盖所有 key，再补 `response_model` + 返回类型
- **ORM 直返的 endpoint**（`return db.query(...).all()`）已有 `response_model` 转换，补返回类型时注意用 `list[SchemaOut]` 而非 `list[Model]`
- **避免引入 `from typing import Any`** 除非万不得已

### 文件修改限制
- 每个文件 ≤ 200 行改动（符合项目契约）
- 超过 200 行的文件分两次 PR（例如 `projects.py`、`competitor.py`、`cost_accounting.py`）
- 超过 600 行的 API 文件考虑拆分子模块（如 `projects.py` 1012 行）
