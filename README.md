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
│   ├── tests/         # 测试
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/     # 页面组件
│   │   ├── api/       # API调用
│   │   ├── router/    # 路由
│   │   └── store/     # 状态管理
│   └── package.json
└── config/
    └── nginx.conf     # Nginx配置
```
