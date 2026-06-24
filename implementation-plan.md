# ROS系统 建议①(事件总线) + 建议②(统一状态机) — 实施计划

> **项目根路径**: `/Users/gamidy/ros-source/ros-system/backend/app/`
> **前端路径**: `/Users/gamidy/ros-source/ros-system/frontend/src/`
> **预计工期**: 10-15人天

---

## 建议②：统一状态机 (services/state_machine.py)

### 当前问题
19个模型的状态都是裸字符串，校验方式五花八门：
| 校验方式 | 模型 |
|---|---|
| 手写 if-check 列表 | Project, Task, Risk, QualityIssue |
| 独立验证函数 | TestRequest (validate_transition) |
| 无任何校验 | BOM, Certification, MQVerification, ECR, ECN, PurchaseOrder |

### 实施步骤

**第1步 — 新建 `services/state_machine.py`** (工作量: 中)
- 定义 `TRANSITIONS` 字典，覆盖所有19个模型的状态转换规则
- 实现 `assert_transition(model, current, target)` 校验函数（不合规则抛 400）
- 实现 `get_valid_transitions(model, current)` → 返回可转换目标列表（供前端调用）
- 内置 `StateMachineRegistry` 支持插入自定义 `before/after` 钩子

**第2步 — 逐个API文件接入** (工作量: 小×12个文件)
- `api/tests.py`: 删掉 `validate_transition()`，统一用 `assert_transition()`
- `api/projects.py`: Project/Program/Task/Risk/Milestone 统一接入
- `api/certifications.py`: Certification/QualityIssue/ECR/ECN 接入
- `api/bom.py`: BOM.status 接入
- `api/purchases.py`: PurchaseOrder/OutsourceRequest 接入
- `api/proposal_utils.py`: ProposalApproval.status 接入
- `models/test.py`: 可删除 `_VALID_TRANSITIONS`（兼容保留也可）

**第3步 — 前端动态下拉** (工作量: 大)
- 新增 `GET /api/v1/state-transitions?model=xxx&current=xxx` 端点
- 逐一改造约10个 Vue 组件中的 `<el-select>` 从硬编码改为 API 调用

---

## 建议①：事件总线 (services/events.py)

### 当前问题
副作用（如测试NG→写Alert）直接在API路由里硬编码调用，耦合度高、难以维护。

### 实施步骤

**第1步 — 新建 `services/events.py`** (工作量: 中)
- `EventTypes` 枚举所有事件类型常量
- `EventBus` 单例：`bus.on()` / `bus.off()` / `bus.emit()`
- 同步调用，纯 Python Observer 模式，不依赖外部消息队列

**第2步 — 新建 `services/event_handlers.py`** (工作量: 中)
- 注册入口 `register_all_handlers(bus)`，在 `main.py` 启动时调用
- 实现以下业务 handler：

| 事件 | 触发点 | Handler 逻辑 |
|---|---|---|
| `proposal.approved` | 审批通过时 emit | 自动设置 Gate planned_date + 创建 TestRequest(占位,draft) |
| `test.done_with_ng` | 测试完成且NG>0 | 写 Alert(level=2) + 累加 ng_count |
| `test.done_with_ng` (条件) | ng_count ≥ 3 | 自动创建 QualityIssue + 升级 Alert 至 level=1 |
| `alert.overdue_found` | 超期扫描发现时 emit | 触发审批催办/升级通知 |

**第3步 — 在现有API中插入 emit()** (工作量: 小×5个文件)
- `api/tests.py`: `bus.emit('test.done_with_ng', ...)`
- `api/proposal_utils.py`: `bus.emit('proposal.approved', ...)`
- `api/alerts.py`: `bus.emit('alert.overdue_found', ...)`
- 只加 emit，不改变现有返回值和业务逻辑

---

## 分期执行计划

```
Phase 1 ─ 基础建设 (1-2天)
  ┣ services/state_machine.py (CREATE)
  ┣ services/events.py (CREATE)
  ┣ services/event_handlers.py (CREATE)
  ┗ 单元测试：状态转换规则 + 事件链路

Phase 2 ─ 状态机接入 (3-5天)
  ┣ 逐个 API 文件接入 assert_transition()
  ┗ 回归测试所有状态变更端点

Phase 3 ─ 前端动态下拉 (2-3天)
  ┣ 新增后端端点
  ┗ 逐个 Vue 组件改造 el-select

Phase 4 ─ 事件发射点注入 (1天)
  ┣ 在现有API路由中插入 bus.emit()
  ┗ 验证事件被触发但不改变API行为

Phase 5 ─ 事件处理器实现 (2-3天)
  ┣ 审批通过→建Gate+测试申请
  ┣ NG≥3→品质整改+升级预警
  ┗ 超期→催办升级

Phase 6 ─ 整合测试+部署 (1-2天)
  ┣ 端到端联调
  ┗ 前端+后端同步上线
```

---

## 核心设计原则

| 决策 | 选择 | 理由 |
|---|---|---|
| 状态机存储 | 纯字典配置(代码)非DB | 规则稳定，变更走部署，减少运行时开销 |
| 事件总线 | 同步单例 Observer | 当前规模无需消息队列，后期可换 |
| 校验 vs 写入 | `assert_transition` 只做校验，不写库 | 保持职责清晰 |
| Handler异常 | 独立 try/except + logging | 不阻断主流程 |

## 风险点 & 缓解措施

1. 🔴 **前端改造范围大** — 约10个Vue组件需要改状态下拉。缓解：分模块渐进交付，先改 tests 和 projects
2. 🟡 **NG≥3自动品质整改防止重复** — 每次 emit 前检查是否有同源未关闭的 QualityIssue
3. 🟡 **事件 handler 长耗时** — 每个 handler 控制在50ms内，超过则需考虑异步化
4. 🟢 **ProposalApproval 多表联动** — 纯校验交给状态机，联动逻辑保留在 proposal_utils.py

---

## 详细JSON文件

完整JSON格式实施计划已输出至:
`/Users/gamidy/ros-source/ros-system/implementation-plan.json`

包含每个文件的精确改动描述、工作量评估、依赖顺序和风险点。
