# Event Graph + BOM Impact Propagation — 20步流程推演

## 功能概述
为 ECR/ECO 的每个状态变更记录事件链（correlation_id/causation_id），
当 ECO 生效影响 BOM 时，自动传播影响到 Certification / Prototype / Manufacturing。

## 用户操作链

| # | 节点 | 模块 | 数据/UI要求 | 风险 |
|:-:|:-----|:-----|:----------|:----:|
| 1 | ECR提交 → emit ecr.submitted | EventBus | correlation_id=ecr.id, causation_id=null | 🟢 |
| 2 | ECR审批通过 → emit ecr.approved | EventBus | causation_id=上一步event.id | 🟢 |
| 3 | ECR转ECO → emit ecr.converted | EventBus | causation_id=ecr.approved event.id | 🟢 |
| 4 | ECO创建 → emit eco.created | EventBus | causation_id=ecr.converted event.id | 🟢 |
| 5 | ECO实施 → emit eco.implementing | EventBus | causation_id=eco.created | 🟢 |
| 6 | ECO验证通过 → emit eco.verified | EventBus | causation_id=eco.implementing | 🟢 |
| 7 | ECO生效 → emit eco.effective | EventBus | causation_id=eco.verified | 🟢 |
| 8 | BOM更新触发 → eco_bom_service | EventBus | 读取ECOItem → 查询哪些cert受影响 | 🟡 需要BOM-Cert映射 |
| 9 | BOM更新成功 → emit bom.updated | EventBus | affected_items, causation_id=eco.effective | 🟢 |
| 10 | BOM更新失败 → emit bom.update_failed | EventBus | 错误信息, causation_id=eco.effective | 🟢 |
| 11 | 查找受影响的Certification | ImpactService | BOM item → certification 映射表 | 🟡 映射表可能不全 |
| 12 | 标记Cert为"需重新评估" | ImpactService | cert.status = impact_pending | 🟢 |
| 13 | 标记受影响的Prototype | ImpactService | prototype.impacted_by = eco_id | 🟢 |
| 14 | 前端查询事件链 | EventGraph API | GET /api/v2/event-graph/{ecr_id} | 🟢 |
| 15 | 前端展示事件链图 | ECharts | 时序图/流程图 | 🟡 需要新组件 |
| 16 | 前端展示BOM影响传播 | Frontend | 树形传播图 | 🟡 |
| 17 | EC/ECO完整链路追溯 | 审计 | 从ECR追溯到BOM/Cert/Proto | 🟢 |
| 18 | BOM更新触发Feedback | M4 | bom_success/bom_failure | 🟢 已有 |
| 19 | 合规审计 | Stage 8 | vibe-code 38条 | 🟢 |
| 20 | Git提交+部署 | CI/CD | 服务器200 | 🟢 |

## 模块拆分

| 模块 | 内容 | 行数 | 依赖 |
|:-----|:------|:----:|:-----|
| EG-1 | EventStore 模型 + EventGraph API | 200 | 现有 EventBus |
| EG-2 | BOM-Cert-Prototype 影响映射表 | 150 | 现有 BOM/Cert/Proto 模型 |
| EG-3 | ImpactPropagationService | 300 | EG-1 + EG-2 |
| EG-4 | 前端事件链组件 EventChainView.vue | 200 | EG-1 API |
| EG-5 | 测试+审计+部署 | 200 | 全部 |

## 关键设计决策
1. EventStore 使用独立表，不混入现有业务表
2. causation_id 形成链表 → 完整事件链可追溯
3. BOM→Cert 映射基于现有 ChangeImpactRule 数据
4. 前端用 ECharts 时序图展示事件链
