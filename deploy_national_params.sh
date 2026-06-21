#!/bin/bash
# Deploy national market params feature
set -e

SERVER="root@139.196.15.52"
BACKEND_DIR="/opt/ros-system/backend"
FRONTEND_DIR="/opt/ros-system/frontend"

echo "=== Extracting backend on server ==="
ssh $SERVER "cd $BACKEND_DIR && tar xzf /tmp/ros_backend.tar.gz && chown -R root:root ."

echo "=== Running DB migration ==="
ssh $SERVER "cd $BACKEND_DIR && source /opt/miniconda3/bin/activate && python -m alembic upgrade head 2>&1"

echo "=== Restarting backend ==="
ssh $SERVER "pkill -f 'uvicorn app.main:app' 2>/dev/null; sleep 1; cd $BACKEND_DIR && nohup /opt/miniconda3/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/uvicorn.log 2>&1 &"

echo "=== Verifying API ==="
sleep 3
curl -s http://139.196.15.52/api/pm/markets/all | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Markets: {len(d)} countries')" 2>/dev/null || echo "API not ready yet"

echo "=== Done ==="
