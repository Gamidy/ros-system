# ROS 研发运营系统 — 项目契约

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
