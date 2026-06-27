# ROS Engineering Standard V1.0

> 定义编码规范、API 规范、事件规范、Saga 事务、可观测性（Observability）、
> 韧性工程（Resilience）、安全架构（Security）、多租户等工程实践。
>
> **稳定性：中** — 随技术栈升级而演进。

---

## 1. Observability（可观测性）

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

---

## 2. Resilience（韧性工程）

| 模式 | 说明 | 实现 |
|:-----|:------|:------|
| **Retry** | 临时故障自动重试 | 指数退避 + 抖动 |
| **Circuit Breaker** | 防止级联故障 | 熔断后快速失败 |
| **Rate Limit** | 防止过载 | 令牌桶 / 漏桶 |
| **Dead Letter Queue** | 失败消息不丢失 | 持久化后人工处理 |
| **Replay** | Event Store 回溯重放 | 事件溯源模式 |
| **Compensation** | Saga 失败时回滚 | 补偿事务 |
| **Recovery** | 系统崩溃后自动恢复 | 健康检查 + 自愈 |

### Saga 事务规范

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

---

## 3. Security Architecture（安全架构）

| 层次 | 控制 | 说明 |
|:-----|:-----|:------|
| **认证** | JWT + OAuth2 | 用户身份认证 |
| **授权** | RBAC + ABAC | 角色 + 属性级权限 |
| **数据权限** | Field Level Security | 敏感字段（成本/客户）权限控制 |
| **AI 权限** | Prompt Permission | AI 能访问的数据范围控制 |
| **API 安全** | Rate Limit + CSRF + XSS | API 防护 |
| **审计** | Audit Log | 所有写操作记录 |
| **多租户** | Tenant Isolation | 租户数据隔离 |

### ABAC 属性定义

| 属性 | 示例 | 用途 |
|:-----|:------|:------|
| user.role | admin / pm / rd | 角色判断 |
| user.dept | planning / test / cert | 部门隔离 |
| resource.type | cost / customer / spec | 资源分类 |
| resource.tenant | tenant_id | 多租户 |
| environment | prod / staging | 环境控制 |
| ai.permission | read / write / decide | AI 操作权限 |

---

## 4. Event Specification（事件规范）

### 事件格式

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

### 事件类型命名

| 域 | 事件示例 |
|:---|:---------|
| ProductPlan | `ProductPlan.Created`, `ProductPlan.StatusChanged`, `ProductPlan.CostTargetUpdated` |
| Verification | `Verification.Created`, `Verification.CoverageUpdated` |
| Prototype | `Prototype.StageChanged`, `Prototype.SnapshotCreated` |
| Test | `Test.Completed`, `Test.EvidenceUploaded` |
| Certification | `Certification.Granted`, `Certification.Expiring` |
| ECO | `ECO.Created`, `ECO.ImpactAnalyzed` |
| AI | `AI.DecisionMade`, `AI.ActionApproved`, `AI.ActionRejected` |

---

## 5. API 规范

| 规则 | 说明 |
|:-----|:------|
| **RESTful** | 资源 + HTTP 动词 |
| **版本** | URL 路径版本（`/api/v1/`）或 Header |
| **分页** | `?page=1&page_size=20` |
| **错误格式** | `{ "code": "ERROR_CODE", "detail": "描述", "trace_id": "uuid" }` |
| **幂等** | POST 创建返回 201，PUT 更新幂等 |
| **异步** | 长任务返回 202 + Location Header |

---

## 6. 编码规范

| 语言 | 规范 | 检查 |
|:-----|:-----|:------|
| Python | PEP8 + Type Hints（全代码 typed） | ruff / mypy |
| TypeScript | ESLint + Prettier | vue-tsc |
| API | 所有函数有返回类型注解 | 审计 |
| 测试 | 新功能配套测试，异常路径全覆盖 | pytest / vitest |

### 提交规范

- Conventional Commits（`feat:` / `fix:` / `refactor:` / `test:` / `docs:`）
- 单次提交 ≤ 200 行（新文件除外）
- 提交前必须通过合规审计

---

## 7. 多租户

| 能力 | 说明 |
|:-----|:------|
| **数据隔离** | 租户级行级隔离（org_id 字段） |
| **配置隔离** | 每个租户独立配置 |
| **资源隔离** | 可选独立数据库或共享 |
| **租户感知** | API 自动从 Token 提取 tenant_id |

---

*标准版本：V1.0*
*稳定性：中*
*维护者：Engineering Team*
