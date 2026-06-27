# Contributing to ROS

> **ROS Foundation 已进入 LTS（冻结）状态。** 所有贡献必须遵守 Constitution。

## 贡献类型

### 1. Capability Proposal

新增 Capability（Supplier / Manufacturing / Simulation 等）的流程：

```
Idea → RFC → Architecture Review → Prototype → Implementation → Review → Release
```

参见 [FOUNDATION.md](./FOUNDATION.md) 中的 RFC 流程。

### 2. Bug Fix / Improvement

直接提交 PR，但必须：

- 遵守 **Constitution** 十二条原则
- 通过 **Compliance Check**（Constitution / Architecture / Security / Data / AI Review）
- Review Agent 评分 ≥ 7

### 3. Architecture Change

任何影响架构的变更必须经过 **Architecture Board** 评审。

## 前置阅读

进入 ROS 仓库后，请按顺序阅读：

1. **CONSTITUTION.md** — 十二条规定什么绝对不能做
2. **FOUNDATION.md** — 治理体系全貌
3. **AGENTS.md** — 项目契约

## PR 规范

- 遵守 Conventional Commits（`feat:` / `fix:` / `refactor:` / `test:` / `docs:`）
- 单次提交 ≤ 200 行（新文件除外）
- 提交前必须通过合规审计
- 所有 PR 必须关联 RFC ID（重大变更）或 Issue ID

## 架构委员会

所有重大决策由 **ROS Architecture Board** 做出。Board 成员见 CONSTITUTION.md 签署页。

---

*CONTRIBUTING.md V1.0*
*生效日期：2026-06-30*
