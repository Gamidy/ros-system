# Phase 3 — 20步流程推演

## 用户操作链

| # | 节点 | 模块 | 数据/UI要求 | 风险 |
|:-:|:-----|:-----|:----------|:----:|
| 1 | 用户打开 ECR 详情页 | ECRDetailView | 已有页面, 需扩展 | 🟢 |
| 2 | 页面上方显示风险评分卡 | RiskScoreCard | GET /api/v2/risk/{id} | 🟢 |
| 3 | 评分卡显示: 分数(0-100) + 等级颜色 | RiskScoreCard | LOW=绿, MEDIUM=黄, HIGH=橙, CRITICAL=红 | 🟢 |
| 4 | 5维信号雷达图(可选) | RiskScoreCard | bom/cert/proto/cost/hist | 🟡 首次加载数据 |
| 5 | 页面中间显示影响图 | ImpactGraphView | GET /api/v2/impact-graph/{id} | 🟢 |
| 6 | 图显示: 节点+边, 颜色编码 | ImpactGraphView | ECharts 关系图 | 🟡 ECharts配置 |
| 7 | 悬停显示节点详情 | ImpactGraphView | tooltip | 🟢 |
| 8 | 节点可展开/折叠子节点 | ImpactGraphView | 交互 | 🟡 复杂交互 |
| 9 | 页面底部显示审批推荐 | ApprovalRecommendation | GET /api/v2/approval-recommendation/{id} | 🟢 |
| 10 | 推荐: 动作(4选1) + 审批人列表 | ApprovalRecommendation | 标签/进度条/列表 | 🟢 |
| 11 | AI解释文本显示 | ApprovalRecommendation | 置信度进度条 | 🟢 |
| 12 | 无数据时显示空状态 | 全部组件 | 友好提示, 非崩溃 | 🟢 |
| 13 | API失败时显示错误提示 | 全部组件 | loading/error state | 🟢 |
| 14 | 组件在ECR详情页集成后正常 | ECRDetailView | 组件插入到合适位置 | 🟡 布局兼容 |
| 15 | npm build 成功 | 构建 | vue-tsc + vite | 🟢 |
| 16 | 部署到服务器 | SCP | dist/ 替换 | 🟢 |
| 17 | 浏览器验证 | 手动 | 200 OK | 🟢 |
| 18 | API 调用CI v2.0 | 跨域/鉴权 | require_menu("changes") | 🟢 已有权限 |
| 19 | 合规审计 | Stage 8 | vibe-code 38条 | 🟢 |
| 20 | Git提交 | commit | ≤200行/commit | 🟡 3组件~470行 |

## 关键堵点

| # | 堵点 | 缓解 |
|:-:|:-----|:------|
| 6 | ECharts关系图需从 DAG 数据转换 | ImpactGraphView 负责转换 |
| 14 | ECRDetailView 已有布局 | 在侧边信息栏下方追加新section |
| 20 | 470行超200行限制 | M6拆3次提交: ①API+store ②组件 ③集成 |
