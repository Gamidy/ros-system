# Phase 2 — 20步流程推演

## 用户操作链

| # | 节点 | 模块 | 数据/状态要求 | 风险 |
|:-:|:----|:-----|:------------|:----:|
| 1 | 部署Phase 2到服务器 | M5 | Docker容器重启 | 🟡 需验证API存活 |
| 2 | 前端调用 `/api/v2/risk/{ecr_id}` | M5 | ECR必须有 `ci_risk_assessments` 记录 | 🟢 M1已实现 |
| 3 | 前端调用 `/api/v2/impact-graph/{ecr_id}` | M5 | ECR必须有 `ci_impact_graphs` 快照 | 🟢 M2已实现 |
| 4 | 前端调用 `/api/v2/approval-recommendation/{ecr_id}` | M5 | 需M1+M2输出 | 🟢 |
| 5 | ECR提交 → 事件触发自动风险评估 | M5+M1 | Event Hook → 调用RiskEngine | 🔴 事件不触发则静默失败 |
| 6 | 用户审批ECR通过 | M4 | 记录 `actual_outcome=approved` | 🟢 |
| 7 | 用户驳回ECR | M4 | 记录 `actual_outcome=rejected` | 🟢 |
| 8 | BOM更新成功→ECO CLOSED | M4 | 记录 `actual_outcome=bom_success` | 🟢 |
| 9 | BOM更新失败→ROLLBACK_REQUIRED | M4 | 记录 `actual_outcome=bom_failure` | 🟢 |
| 10 | 反馈数据达到N条→触发权重重算 | M4 | 最小样本数(默认10) | 🟡 权重突变 |
| 11 | 用户查看 `/api/v2/model-params` | M5+M4 | 参数版本信息 | 🟢 |
| 12 | 用户回滚参数到历史版本 | M5+M4 | 支持版本ID | 🟡 回滚后需重新累积 |
| 13 | ECR详情页扩展字段回归测试 | M5 | 现有API格式不变 | 🔴 破坏向后兼容 |
| 14 | 批量风险评分 `/api/v2/risk/batch` | M5 | 单次最多20个ECR | 🟡 性能 |
| 15 | 反馈数据提交 `/api/v2/feedback` | M5+M4 | 外部系统也可写入 | 🟡 数据验证 |
| 16 | 参数版本无限增长 | M4 | 保留最近20个版本 | 🟡 清理策略 |
| 17 | Celery离线时BOM更新不触发 | M5 | 同步降级 | 🟢 已有log降级 |
| 18 | 前端集成到ECR详情页(Phase 3) | — | 等待Phase 3 | 🟢 预留API格式 |
| 19 | 合规审计→多级AI协作 | 全 | Stage 8 | 🟢 |
| 20 | Git提交+部署验证 | 全 | 服务器200 OK | 🟢 |

## 堵点与依赖

| # | 堵点 | 缓解 |
|:-:|:-----|:-----|
| 5 | ECR提交事件钩子需要修改 `submit_ecr()` | 在 ecr.py submit 末尾加 `risk_engine.assess_for_ecr()` 调用 |
| 10 | 权重突变影响评分稳定性 | 保留旧参数快照，支持回滚 |
| 13 | ECRDetailOut 扩展破坏现有前端 | 用 Optional 字段，不改变必填字段 |
| 16 | 参数版本膨胀 | 保留最多20个版本，自动清理最旧的 |
