# CIE v2.0 Phase 2 — 精确执行计划

> AI-A 规划, vibe-code 38条强制, ralph-loop 执行
> 基线: Phase 1 完成 (69 tests, 100% Stage 8)

---

## 📊 总览

| 模块 | 子任务 | 负责人 | 行数 | 测试 |
|:----|:-------|:------|:----:|:----:|
| **M4 Feedback Loop** | 6 | AI-E | ~530 | ~18 |
| **M5 API 集成** | 5 | AI-F | ~480 | ~23 |
| **Phase 2 合计** | **11** | **AI-E + AI-F** | **~1,010** | **~41** |

---

## 🗺️ 执行拓扑

```
Day 1 (并行启动):
  M4-T1 反馈模型 (AI-E) ───────┐
  M4-T2 反馈Schema (AI-E) ─────┤
  M5-T2 ECR风险钩子 (AI-F) ────┤   ← 无依赖, 立即启动
  M5-T3 ECRDetail扩展 (AI-F) ──┘
          ↓
Day 2 (核心业务):
  M4-T3 FeedbackLoop服务 (AI-E) ──── 依赖 M4-T1+M4-T2
  M5-T1 7个API端点 (AI-F) ────────── 依赖 M4-T2
          ↓
Day 3 (收尾+测试):
  M4-T4 事件钩子 (AI-E)
  M4-T5 单元测试 (AI-E)
  M4-T6 Alembic迁移 (AI-E)
  M5-T4 单元测试 (AI-F)
  M5-T5 Schema导出 (AI-F)
          ↓
AI-Z 审核 → 修复 → 合规审计 Stage 8
```

---

## 📦 M4: Feedback Loop (AI-E)

| # | 子任务 | 文件 | 行数 | 依赖 |
|:-:|:-------|:----|:----:|:----:|
| T1 | 反馈模型 | `models/ci_v2_feedback.py` | 60 | — |
| T2 | Schema追加 | `schemas/ci_v2.py` | 50 | T1 |
| T3 | 核心服务 | `services/ai/feedback_loop.py` | 180 | T1+T2 |
| T4 | 事件钩子 | `feedback_loop.py` + `events.py` | 30 | T3 |
| T5 | 单元测试 | `tests/test_ci_v2_feedback.py` | 180 | T3+T4 |
| T6 | 迁移脚本 | `migrations/` | 30 | T1 |

## 📦 M5: API 集成 (AI-F)

| # | 子任务 | 文件 | 行数 | 依赖 |
|:-:|:-------|:----|:----:|:----:|
| T1 | 7个API端点 | `api/ci_v2.py` | 250 | M4-T2 |
| T2 | ECR提交风险钩子 | `ecr.py` (修改) | 15 | — |
| T3 | ECRDetail扩展 | `schemas/ecr_eco.py` (修改) | 10 | — |
| T4 | 单元测试 | `tests/test_ci_v2_api.py` | 200 | T1+T2+T3 |
| T5 | Schema导出 | `schemas/__init__.py` | 5 | M4-T2 |

---

## 🏛️ 架构约束

1. **向后兼容** — 现有 ECR/ECO API 响应格式不变，新字段全是 `Optional`
2. **非阻断** — RiskEngine 异常不阻断 ECR 审批流程
3. **全类型注解** — 所有新代码 `Any` 零容忍
4. **无裸 except** — 每个 `except` 必须 `except Exception as e:`

---

> 确认后启动：**M4-T1 + M5-T2 + M5-T3** 三路并行 🚀
