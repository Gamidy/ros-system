# ROS Operation Standard V1.0

> **定义 ROS 的运营体系**：每天系统怎么运行、谁负责响应、怎么处理故障、怎么变更、怎么保障可用性。
>
> 借鉴 ITIL 框架，适配研发数字化平台场景。
>
> **稳定性：中** — 随系统规模升级而演进。

---

## 1. Incident Management（事件管理）

### 1.1 事件定义

| 级别 | 定义 | 响应时间 | 恢复时间 | 示例 |
|:-----|:-----|:---------|:---------|:------|
| P0 | 系统完全不可用 | ≤ 15 分钟 | ≤ 2 小时 | 登录失败、API 全部 500 |
| P1 | 核心功能不可用 | ≤ 30 分钟 | ≤ 4 小时 | ProductPlan 无法创建 |
| P2 | 非核心功能异常 | ≤ 4 小时 | ≤ 24 小时 | 报表加载慢 |
| P3 | 体验问题 | ≤ 24 小时 | ≤ 72 小时 | UI 显示问题 |

### 1.2 事件处理流程

```
Detection (自动/人工)
  ↓
Classification & Prioritization
  ↓  [P0/P1: 自动通知 Ops Team]
Diagnosis
  ↓
  ├─ Known Error → Apply Workaround
  └─ Unknown → Root Cause Analysis
  ↓
Resolution
  ↓
Verification
  ↓
Closure
  ↓
Postmortem (P0/P1 必须)
```

### 1.3 事件文档要求

每个事件必须记录：

| 字段 | 说明 |
|:-----|:------|
| incident_id | 唯一编号（格式：INC-YYYYMMDD-XXX） |
| severity | P0/P1/P2/P3 |
| detected_at | 发现时间 |
| detected_by | 谁发现的（监控/用户/测试） |
| summary | 一句话描述 |
| root_cause | 根因（P0/P1 必须） |
| resolution | 解决方案 |
| workaround | 临时规避方案 |
| resolved_at | 恢复时间 |
| affected_users | 影响范围 |
| trace_id | 关联分布式追踪 ID |

---

## 2. Problem Management（问题管理）

### 2.1 问题与事件的关系

```
多个相似 Incident
  ↓
Problem Record 创建
  ↓
Root Cause Analysis（5 Whys / Fishbone）
  ↓
Known Error 入库
  ↓
永久修复（Change Request）
  ↓
验证关闭
```

### 2.2 问题优先级

| 优先级 | 条件 | SLA |
|:-------|:-----|:----|
| Critical | 导致同一 P0 事件重复发生 | 7 天出方案 |
| High | 导致 P1 事件重复 ≥ 3 次 | 14 天出方案 |
| Medium | 已知错误但影响可控 | 30 天出方案 |
| Low | 轻微问题，影响有限 | 下一迭代 |

### 2.3 已知错误库

| 字段 | 说明 |
|:-----|:------|
| KE_ID | 唯一编号 |
| error_code | 系统错误码（如有） |
| description | 错误描述 |
| root_cause | 根因 |
| workaround | 临时方案 |
| affected_components | 影响组件 |
| created_at | 创建时间 |
| resolved | 是否已修复 |

---

## 3. Change Management（变更管理）

### 3.1 变更类型

| 类型 | 说明 | 审批 | 窗口 |
|:-----|:------|:-----|:------|
| Standard | 预授权低风险变更 | 无需审批 | 任意时间 |
| Normal | 常规变更 | Tech Lead 审批 | 维护窗口 |
| Emergency | 紧急修复（P0 事件） | 事后审批 | 立即执行 |

### 3.2 变更流程

```
Change Request 创建
  ↓
Impact Assessment
  ↓
  ├─ Standard → Execute
  ├─ Normal → Tech Lead Review → Approve → Execute
  └─ Emergency → Execute → Post-approval
  ↓
Test & Verify
  ↓
Deploy
  ↓
Post-change Review（Normal/Emergency 必须）
```

### 3.3 变更文档

| 字段 | 说明 |
|:-----|:------|
| change_id | CHG-YYYYMMDD-XXX |
| type | Standard / Normal / Emergency |
| summary | 变更描述 |
| justification | 变更理由 |
| risk_assessment | 风险评估（High/Medium/Low） |
| rollback_plan | 回滚方案（Normal 必须） |
| test_results | 测试结果 |
| approver | 审批人 |
| deployed_at | 部署时间 |
| reviewer | 变更后评审人 |

---

## 4. Release Management（发布管理）

### 4.1 发布类型

| 类型 | 频率 | 包含内容 | 审批 |
|:-----|:------|:---------|:-----|
| Major Release | 月度 | 新功能 + 架构变更 | Architecture Board |
| Minor Release | 双周 | 功能迭代 + 修复 | Tech Lead |
| Patch Release | 按需 | Bug 修复 + 安全补丁 | Ops Lead |
| Emergency Release | 按需 | P0/P1 修复 | 事后审批 |

### 4.2 发布流程

```
Release Planning → 确定范围
  ↓
Code Freeze（Major: T-3 天 / Minor: T-1 天）
  ↓
Regression Test（Major: 全量 / Minor: Smoke）
  ↓
Staging Deployment
  ↓
UAT / Verification
  ↓
Production Deployment
  ↓
Smoke Test（生产环境）
  ↓
Release Notes 发布
```

### 4.3 发布版本规范

```
ROS-{MAJOR}.{MINOR}.{PATCH}

Major: 架构/不兼容变更
Minor: 功能迭代
Patch: 修复

示例：ROS-4.2.1
```

---

## 5. Configuration Management（配置管理）

### 5.1 配置项（CI）类型

| CI 类型 | 说明 | 存储位置 |
|:--------|:------|:---------|
| 服务器 | 物理/云服务器 | CMDB |
| 容器 | Docker 容器 | Docker Registry |
| 数据库 | 数据库实例 | CMDB |
| 配置 | 环境变量/配置文件 | Git + .env |
| 证书 | SSL/API 证书 | Secret Store |
| 第三方服务 | 外部 API 依赖 | CMDB |

### 5.2 配置管理要求

| 要求 | 说明 |
|:-----|:------|
| **代码化** | 所有配置存储在 Git，环境和密钥用 .env |
| **版本化** | 配置文件有版本历史 |
| **可追溯** | 每次配置变更关联 Change ID |
| **自动化** | 配置变更通过 CI/CD 而非手动修改 |
| **备份** | 关键配置有自动备份 |

---

## 6. Capacity Management（容量管理）

### 6.1 容量指标

| 指标 | 监控阈值 | 告警阈值 | 扩容触发 |
|:-----|:---------|:---------|:---------|
| CPU 使用率 | < 70% | > 80% > 5 分钟 | > 85% |
| 内存使用率 | < 75% | > 85% > 5 分钟 | > 90% |
| 磁盘使用率 | < 70% | > 80% | > 85% |
| API QPS | < 80% 峰值 | > 90% 峰值 | > 95% 峰值 |
| 数据库连接数 | < 60% 上限 | > 75% 上限 | > 85% 上限 |

### 6.2 容量规划

- **月度**：资源使用率趋势报告
- **季度**：基于业务增长的容量预测
- **年度**：基础设施扩容计划

---

## 7. Availability Management（可用性管理）

### 7.1 可用性目标

| 服务等级 | 目标可用性 | 允许月停机时间 |
|:---------|:-----------|:--------------|
| 核心服务（登录/API） | 99.9% | ≤ 43 分钟/月 |
| 非核心服务（报表/导出） | 99.5% | ≤ 3.6 小时/月 |
| 内部工具 | 99% | ≤ 7.2 小时/月 |

### 7.2 可用性指标

| 指标 | 定义 | 目标 |
|:-----|:-----|:-----|
| MTBF | 平均无故障时间 | ≥ 720 小时 |
| MTTR | 平均恢复时间 | ≤ 1 小时（P0） |
| MTTD | 平均发现时间 | ≤ 15 分钟（P0） |
| 可用性% | (1 - 停机时间/总时间) × 100 | ≥ 99.9% |

### 7.3 维护窗口

| 窗口 | 时间 | 允许操作 |
|:-----|:-----|:---------|
| 常规维护 | 每周三 02:00-04:00 | Normal Change |
| 紧急窗口 | 每天 02:00-06:00 | Emergency Only |
| 静默期 | 每月最后 3 天 | 禁止变更 |

---

*标准版本：V1.0*
*稳定性：中*
*维护者：Ops Team*
*生效日期：2026-06-30*
