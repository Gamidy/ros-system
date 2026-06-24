# ROS - 研发运营系统 (R&D Operations System)

海外分体机研发全生命周期管理平台

## 技术栈

| 层 | 技术 | 说明 |
|:--|:-----|:-----|
| 前端 | Vue3 + Element Plus + TypeScript | Vite构建，Pinia状态管理 |
| 后端 | FastAPI (Python 3.11) | SQLAlchemy ORM，Pydantic验证 |
| 数据库 | MySQL/MariaDB | 数据库名: ros_db (docker-compose + network_mode=host) |
| 鉴权 | JWT + RBAC | 13种角色，权限矩阵驱动 |
| 部署 | Docker (ros-backend) + Nginx | 阿里云 139.196.15.52 |

## 项目结构

```
ros-system/
├── backend/
│   ├── app/
│   │   ├── api/       # API路由（按模块拆分）
│   │   ├── core/      # 配置/安全/数据库
│   │   ├── models/    # SQLAlchemy模型
│   │   ├── schemas/   # Pydantic验证
│   │   ├── middleware/# 审计/限流/XSS中间件
│   │   └── main.py    # 应用入口
│   ├── tests/         # pytest测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/     # 页面组件（按角色分组）
│   │   ├── api/       # Axios API调用
│   │   ├── router/    # Vue Router + 权限守卫
│   │   ├── stores/    # Pinia状态管理
│   │   ├── types/     # TypeScript类型定义
│   │   ├── layout/    # 布局组件（侧边栏/顶部栏）
│   │   └── components/# 通用组件
│   ├── dist/          # 构建产物（git ignored）
│   └── package.json
└── docs/              # 文档
```

## 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
# 修改 backend/.env DB_TYPE=sqlite 使用本地SQLite
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 生产部署（阿里云）

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 上传前端
scp -r dist/* root@139.196.15.52:/opt/ros-system/frontend/dist/

# 3. 上传修改的后端文件到服务器
scp backend/app/api/*.py root@139.196.15.52:/tmp/
ssh root@139.196.15.52 "docker cp /tmp/xxx.py ros-backend:/app/app/api/xxx.py"

# 4. 重启容器（env_file: .env.production 自动加载新配置）
ssh root@139.196.15.52 "docker restart ros-backend"

# 5. Nginx（通常不需要重启）
# ssh root@139.196.15.52 "nginx -s reload"
```

## 关键约定

- 单个API路由文件 ≤ 600行，超出拆子模块
- 所有API端点使用 `response_model` + `from_attributes = True`
- 新功能需配套 pytest 测试
- Redis 暂未接入（所有 import 已注释）
