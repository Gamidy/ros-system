#!/bin/bash
echo '=== FRONTEND DIST ==='
ls -la /opt/frontend/dist/ 2>/dev/null | head -10
echo '=== DIST DIR CHECK ==='
ls -ld /opt/ros-system/frontend/dist/ 2>&1
echo '=== ENV ==='
cat /opt/ros-system/.env.production 2>/dev/null || echo "NO ENV FILE"
echo ''
echo '=== DOCKER ENV ==='
docker inspect ros-backend --format '{{json .Config.Env}}' 2>/dev/null | tr ',' '\n' | head -20
echo ''
echo '=== NGINX ERROR LOG ==='
tail -30 /var/log/nginx/ros-http-error.log 2>/dev/null || echo "NO ERROR LOG"
echo ''
echo '=== NGINX ACCESS LOG (last 5) ==='
tail -5 /var/log/nginx/ros-http-access.log 2>/dev/null || echo "NO ACCESS LOG"
