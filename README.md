# 吉德（Jide）家用变频空调 PLM 系统

> Product Lifecycle Management — 基于 IPD 结构化流程的空调产品研发全生命周期管理

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / PostgreSQL 16
- **前端**: Vue 3.4+ / TypeScript / Element Plus / Vite 5
- **部署**: Docker Compose

## 快速启动

```bash
git clone <repo-url>
cd plm-system

# 1. 配置环境变量
cp .env.example .env
# 编辑 .env → 设置 SECRET_KEY

# 2. 启动服务
docker compose up -d

# 3. 数据库迁移
make migrate

# 4. 种子数据
make seed

# 5. 访问
# 前端: http://localhost:5173
# API文档: http://localhost:8000/docs
```

## 项目结构

```
plm-system/
├── docker-compose.yml       # PostgreSQL + FastAPI + Vue3
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── crud/            # 数据访问层
│   │   ├── api/v1/          # REST API v1 路由
│   │   └── core/            # 配置/安全/权限
│   ├── alembic/             # 数据库迁移
│   └── tests/               # pytest 测试
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── api/             # API 封装
│   │   └── router/          # 路由配置
│   └── public/
├── AGENTS.md                # 工程契约
└── Makefile                 # 常用命令
```

## 开发流程

遵循 **TDD → AI-Z 审核 → 合规审计** 的 Loop 工作流。

每个修改必须:
1. 先写测试 (RED)
2. 写实现 (GREEN)
3. 重构 (REFACTOR)
4. AI-Z 审核 ≥ 8分
5. 提交 (≤200行)
