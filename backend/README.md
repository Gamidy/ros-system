# PLM系统后端

## 技术栈
- FastAPI 0.109+
- SQLAlchemy 2.0+
- PostgreSQL 14+
- JWT认证
- RBAC权限控制

## 快速开始

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置数据库
```bash
# 创建数据库
createdb plm_system

# 或者使用Docker
docker run -d --name plm-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=plm_system \
  -p 5432:5432 postgres:14
```

### 3. 配置环境变量
```bash
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/plm_system"
```

### 4. 启动服务
```bash
python run.py
```

### 5. 初始化系统
```bash
curl -X POST http://localhost:8000/api/v1/auth/init
```

默认管理员账号：`admin` / `admin123`

## API文档
启动后访问：http://localhost:8000/docs

## 核心模块
- 物料管理 `/api/v1/materials`
- BOM管理 `/api/v1/boms`
- 变更管理 `/api/v1/changes`
- 项目管理 `/api/v1/projects`
- 认证 `/api/v1/auth`

## 数据模型
- 物料分类：支持多级树形结构
- 物料主数据：版本控制、生命周期管理
- BOM：多级展开、版本比较
- 变更：ECR/ECO流程、审批工作流
- 项目：WBS任务分解、进度跟踪
