# 🏭 CIE v2.0 实施方案（AI-A 规划）

> 基于 `docs/change-intelligence-engine-v2.md` 规范  
> 执行引擎: Ralph Loop v2.0 (AI-A → AI-X → AI-Z → fix → commit → deploy)

---

## 📊 总体数据

| 指标 | 值 |
|:----|:---|
| 模块数 | 6 个 |
| 新文件 | 22 个 |
| 新增代码 | ~3,100 行 |
| 修改代码 | ~700 行 |
| 执行周期 | 3 Phases |

---

## 🔗 模块依赖图

```
Phase 1 (独立可测)
  M1: Risk Engine (AI-B, ~550行)
    ↓
  M2: Impact Graph (AI-C, ~500行) ← 复用 ChangeImpactRule
    ↓
  M3: Approval Advisor (AI-D, ~400行) ← 复用 ai_chat()

Phase 2 (端到端)
  M5: API 集成 (AI-F, ~550行) ← 依赖 M1+M2+M3
  M4: Feedback Loop (AI-E, ~430行) ← 依赖 M1

Phase 3 (用户可见)
  M6: 前端展示 (AI-G, ~500行) ← 依赖 M5
```

---

## 📦 模块详情

### Phase 1: 核心引擎（本周可交付可测 ✅）

| # | 模块 | 负责人 | 行数 | 核心文件 | 验收标准 |
|:-:|:----|:------|:----|:---------|:---------|
| **M1** | **Risk Engine** | AI-B | 550 | `services/ai/risk_engine.py`, `models/ci_v2_risk.py` | 5信号正确加权，pytest覆盖边界 |
| **M2** | **Impact Graph** | AI-C | 500 | `services/ai/impact_graph.py` | BFS遍历，图输出正确，环检测 |
| **M3** | **Approval Advisor** | AI-D | 400 | `services/ai/approval_advisor.py` | 4区间推荐逻辑，LLM降级 |

### Phase 2: 集成层

| # | 模块 | 负责人 | 行数 | 核心文件 | 验收标准 |
|:-:|:----|:------|:----|:---------|:---------|
| **M4** | **Feedback Loop** | AI-E | 430 | `services/ai/feedback_loop.py` | 反馈收集+权重调整+版本管理 |
| **M5** | **API 集成** | AI-F | 550 | `api/ci_v2.py` + ECR/ECO增强 | 7个新端点，现有回归通过 |

### Phase 3: 前端

| # | 模块 | 负责人 | 行数 | 核心文件 | 验收标准 |
|:-:|:----|:------|:----|:---------|:---------|
| **M6** | **前端展示** | AI-G | 500 | `RiskScoreCard.vue`, `ImpactGraphView.vue`, `ApprovalRecommendation.vue` | 3组件集成到ECR详情页 |

---

## 🗺️ 执行建议顺序

### Phase 1（并行+串行混合，Day 1-3）

```
Day 1: M1 (AI-B) + M2 (AI-C) 并行独立开发
Day 2: M1 和 M2 完成后 → M3 (AI-D) 依赖M1结果
Day 3: AI-Z 审核 M1+M2+M3 → 修复 → 全pytest通过
```

### Phase 2（Day 4-5）

```
Day 4: M4 (AI-E) + M5 (AI-F) 并行
Day 5: AI-Z 审核 → 修复 → 端到端测试 → 部署
```

### Phase 3（Day 6-7）

```
Day 6: M6 (AI-G) 前端组件
Day 7: 构建 → 部署 → ECR详情页集成验证
```

---

## 🛡️ 关键设计原则

1. **AI 不直接执行，只做建议** — 所有输出写入 `ci_v2_*` 表，不修改 ECR/ECO 状态
2. **LLM 容错降级** — Approval Advisor 的 LLM 失败时自动降级到规则路径
3. **向后兼容** — 现有 API 格式不变，v2.0 通过独立端点或可选扩展字段提供
4. **可追溯** — 每次 AI 评估生成唯一 ID 持久化，支持全链路审计

---

> 确认后按 **Phase 1：M1 Risk Engine** → AI-B 开始执行
