#!/bin/bash
# ROS系统云端部署脚本
# 用法: ./deploy.sh [frontend|backend|all]

set -e

HOST="root@139.196.15.52"
BACKEND_SRC="/Users/gamidy/ros-source/ros-system/backend"
FRONTEND_SRC="/Users/gamidy/ros-source/ros-system/frontend"

deploy_frontend() {
  echo ">>> 部署前端..."
  cd "$FRONTEND_SRC"
  tar czf /tmp/ros-frontend-dist.tar.gz -C dist .
  ssh "$HOST" "rm -rf /opt/ros-system/frontend/dist_old && mv /opt/ros-system/frontend/dist /opt/ros-system/frontend/dist_old && mkdir -p /opt/ros-system/frontend/dist && tar xzf /dev/stdin -C /opt/ros-system/frontend/dist/" < /tmp/ros-frontend-dist.tar.gz
  echo "前端 ✅"
}

deploy_backend() {
  echo ">>> 部署后端..."

  # 在宿主机上打包backend/app/目录（不含__pycache__）
  cd "$BACKEND_SRC"
  tar czf /tmp/ros-backend-app.tar.gz \
    --exclude='__pycache__' --exclude='*.pyc' \
    -C app .

  # 复制到服务器
  scp /tmp/ros-backend-app.tar.gz "$HOST":/tmp/

  # 服务器上：先清空容器内/app/app/，再解压进去
  ssh "$HOST" '
    docker exec ros-backend sh -c "rm -rf /app/app_old && mv /app/app /app/app_old && mkdir /app/app"
    docker cp /tmp/ros-backend-app.tar.gz ros-backend:/tmp/
    docker exec ros-backend sh -c "cd /app/app && tar xzf /tmp/ros-backend-app.tar.gz && rm /tmp/ros-backend-app.tar.gz"
    docker restart ros-backend
  '
  echo "后端 ✅"
  sleep 3
  curl -s http://139.196.15.52/health
}

deploy_nginx() {
  echo ">>> 部署Nginx配置..."
  scp /tmp/ros-http-ip.conf "$HOST":/etc/nginx/conf.d/ros-http-ip.conf
  ssh "$HOST" "nginx -t && nginx -s reload"
  echo "Nginx ✅"
}

case "${1:-all}" in
  frontend) deploy_frontend ;;
  backend)  deploy_backend ;;
  nginx)    deploy_nginx ;;
  all)
    deploy_frontend
    deploy_backend
    deploy_nginx
    echo "=== 全部部署完成 ==="
    ;;
  *)
    echo "用法: ./deploy.sh [frontend|backend|nginx|all]"
    exit 1
    ;;
esac
