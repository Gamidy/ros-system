# ROS — AI-native R&D Operating System

> **正式定义**：ROS（R&D Operating System）是一个 AI-native、事件驱动、数据驱动、
> 数字主线驱动的研发操作系统。它以统一的业务架构、数据架构和治理体系为基础，
> 通过可扩展的 Capability 机制，支撑产品全生命周期研发，并能够持续演进，
> 而无需重构核心平台。
>
> **架构阶段：已关闭 ✅** — Foundation 已冻结（LTS / Production Ready）
> **版本管理**：**ROS Foundation**（7 套标准永久维护） + **Capability Library**
>
> **ROS Constitution**（十二条 + Scope + Interpretation + Compliance + Architecture Principles）已建立，见根目录 `CONSTITUTION.md`
> **ROS Foundation**（LTS 状态 — 不可变），见 `FOUNDATION.md`

> 本项目遵循 **vibe-coding 38条通用编程原则**。
> 每次代码任务完成后必须运行 **compliance-auditor** 合规审计。
> 类型注解：全代码 typed（参数类型、返回类型、数据类字段）。
> 禁止使用 `any` 类型（特殊豁免需在本文件记录）。

## 一句话描述

空调(AC)产品研发公司全生命周期管理平台。管理产品从立项、研发、测试、认证到上市的完整流程。

## 技术架构

| 层 | 技术 | 说明 |
|:--|:-----|:-----|
| 前端 | Vue3 + Element Plus + TypeScript | Vite构建，Pinia状态管理 |
| 后端 | FastAPI (Python 3.11) | SQLAlchemy ORM，Pydantic验证 |
| 数据库 | MariaDB (MySQL兼容) | 数据库名: ros_db |
| 鉴权 | JWT + OAuth2 | 13种角色，RBAC权限模型 |
| Web服务器 | Nginx | 反向代理到Docker后端 |
| 部署 | Docker | ros-backend容器，端口8000 |
| 云服务器 | 阿里云 139.196.15.52 | 30GB系统盘 |

## 重要开发约定

### 前端
- 所有Vue组件用 `<script setup>` + TypeScript
- 状态管理用 Pinia (stores/ 目录)
- 路由在 router/index.ts，守卫含权限检查
- 侧边栏菜单在 types/roles.ts 定义
- 登录流程: LoginView → authStore.login() → router.push('/dashboard')
- 构建: `npm run build` → dist/

### 后端
- API路由在 api/ 目录，按模块拆分
- 所有API响应用 Pydantic schema | SQLAlchemy模型
- 权限控制: `require_role()` 或 `require_menu()`
- 部署: docker cp + docker restart

### 关键模块文件大小限制
- 单个API文件 ≤ 600行
- 单个模型文件 ≤ 500行
- 超过上限必须拆分子模块

## 部署流程（三步走）
1. `git commit` 当前改动
2. 构建 + `scp` 到服务器
3. 测试 → 修bug（如需要）

## 角色权限
- admin / general_manager: 超级角色，全部菜单
- 其他11个工程角色: 按角色分配菜单
- 权限定义在 backend/app/core/permissions.py

## 代码规范
- Python: 类型注解（至少API路由函数要有返回类型）
- 错误处理: 使用 `except Exception as e:` 而非裸 `except:`
- Git: 小提交，单次commit说明改了什么及为什么
- 测试: 新功能需配套测试

## 安全
- 无 exec()/eval() 在生产代码中
- SECRET_KEY 通过 .env 注入
- Token黑名单机制支持登出

## 变更记录

### 2026-06-29（持续修复）
- **后端重构**: 拆分 competitor.py (1215→951行)，Market CRUD + 能效等级API 迁移至独立 `backend/app/api/markets.py`（含 Pydantic schema: MarketCreate/MarketUpdate/EnergyLevelCreate/EnergyLevelUpdate）
- **前端修复**: 3个Hub组件(ChangesHub/SafetyHub/CertHub) 动态 `import(rel)` → 静态 `defineAsyncComponent` 映射，修复Vite编译失败导致的路由500错误
- **组件拆分**: MarketMgmt.vue 标准配置弹窗提取为独立 StandardConfigDialog.vue (327行), MarketMgmt.vue 从1059行降至774行
- **前端测试框架**: 搭建 Vitest + jsdom, 4个 EnergyLevelManager 组件测试通过
- **测试组织**: test_market_energy_levels.py 移入子包 backend/tests/market/
- **全量测试**: 102 passed, 1 legacy fail (不变)
- 全站主题色回退: #2563eb(深蓝)→#d97757(橙红)，按钮文字白色(#ffffff)
- 导航选中态、logo-mini、collapse-btn-hover、role-tag全部回退至橙红色系
- **菜单整合**: 侧边栏3项合并: 变更/ECR/ECO→「变更管理」(ChangesHub)
- **菜单整合**: 认证11项合并→「认证管理」(CertHub)
- **菜单整合**: 安规4项合并→「安规管理」(SafetyHub)
- **新增功能**: 市场中新增"最低电压要求(V)"字段（表单+表格显示）
- **新增功能**: 标准配置弹窗新增「能效等级」tab，支持多等级CRUD（SEER/EER/CSPF门槛值）
- 后端: Market模型新增min_voltage列 + MarketEnergyLevel表 + 4个CRUD端点
- **合规修复**: MarketItem接口补充min_voltage/refrigerant_charge字段
- **合规修复**: SafetyHub.vue路径统一（TAB_MAP文件路径整改）
- **合规修复**: EnergyLevelManager.vue bare catch加(e: unknown)参数
- **合规修复**: 能效等级API增加市场存在性验证（404友好）
- **合规修复**: structure_type机型恢复6个选项（分体壁挂/天花/风管/柜机/窗机/移动空调）

### 2026-06-28
- AI-Z合规修复: catch参数补齐、AGENTS.md变更记录更新

### 2026-06-27
- MarketMgmt.vue: 新增筛选栏(区域/状态/搜索) + 标准配置弹窗(测试要求+标准要求)
- 目标市场配置(TargetMarketView)合并入市场管理，移除独立路由
- 新增市场弹窗: 取消market_code输入(自动用名称生成)、取消refrigerant_charge字段
- "压缩机"→"关键元器件的特殊要求" 全局文案替换
- 全局主题色: #d97757(橙红)→#2563eb(深蓝)，导航选中态保留橙红点缀 (后于2026-06-29回退)
- 类型约束: ref<any>全部替换为具体类型接口(MarketForm/CertForm/CompressorForm/TestForm/StandardForm)
- 错误处理: 所有catch块加(e: unknown)参数
- backend: target_markets.py 新增GET/PUT端点 for tests+standards
