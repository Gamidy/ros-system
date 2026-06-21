# ROS - 研发运营系统 (R&D Operations System)

海外分体机研发全生命周期管理平台

## 技术栈
- **前端**: Vue3 + Element Plus + TypeScript
- **后端**: FastAPI (Python 3.14)
- **数据库**: MySQL
- **缓存**: Redis
- **Web服务器**: Nginx
- **鉴权**: JWT + RBAC

## 开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 项目结构
```
ros-system/
├── backend/
│   ├── app/
│   │   ├── api/       # API路由
│   │   ├── core/      # 配置/安全/数据库
│   │   ├── models/    # SQLAlchemy模型
│   │   ├── schemas/   # Pydantic验证
│   │   └── main.py    # 应用入口
|   ├── tests/         # 测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/     # 页面组件
│   │   ├── api/       # API调用
│   │   ├── router/    # 路由
│   │   ├── stores/    # Pinia状态管理
│   │   ├── types/     # TypeScript类型
│   │   ├── layout/    # 布局组件
│   │   └── components/# 通用组件
│   ├── dist/          # 构建产物
│   └── package.json
├── config/
│   └── nginx.conf     # Nginx配置
└── docs/              # 文档
```

## 部署

### 生产环境（阿里云 139.196.15.52）

```bash
# 1. 构建前端
cd frontend && npm run build

# 2. 上传到服务器
scp -r dist/* root@139.196.15.52:/opt/ros-system/frontend/dist/

# 3. 重新部署后端
scp -r backend/* root@139.196.15.52:/opt/ros-system/backend/
ssh root@139.196.15.52 "docker cp /opt/ros-system/backend ros-backend:/app && docker restart ros-backend"

# Nginx配置
scp config/nginx.conf root@139.196.15.52:/etc/nginx/conf.d/ros.conf
ssh root@139.196.15.52 "nginx -t && nginx -s reload"
```

### 开发环境

```bash
# 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install
npm run dev
```

## 技术栈
- **前端**: Vue3 + Element Plus + TypeScript (Vite)
- **后端**: FastAPI (Python 3.11) + SQLAlchemy
- **数据库**: MySQL/MariaDB
- **鉴权**: JWT + RBAC (13种角色 + 超级角色)
- **部署**: Docker + Nginx (阿里云)
