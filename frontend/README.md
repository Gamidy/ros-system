# PLM系统前端

## 技术栈
- Vue 3 (Composition API)
- Element Plus UI组件库
- Vue Router 4
- Pinia状态管理
- Axios HTTP请求
- Vite构建工具

## 快速开始

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 启动开发服务器
```bash
npm run dev
```

### 3. 构建生产版本
```bash
npm run build
```

## 功能模块
- **工作台** - 数据看板、待办任务、快捷入口
- **物料管理** - 物料分类、物料主数据、版本控制、生命周期管理
- **BOM管理** - 多级BOM、版本管理、BOM比较、多级展开
- **变更管理** - ECR/ECO流程、审批工作流
- **项目管理** - 项目立项、WBS任务分解、进度跟踪

## 目录结构
```
src/
  api/          # API接口
  components/   # 公共组件
  router/       # 路由配置
  stores/       # Pinia状态管理
  utils/        # 工具函数
  views/        # 页面视图
    materials/  # 物料管理
    boms/       # BOM管理
    changes/    # 变更管理
    projects/   # 项目管理
```

## 默认账号
- 用户名: admin
- 密码: admin123
