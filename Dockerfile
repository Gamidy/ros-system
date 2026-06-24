# =============================================================================
# ROS 后端 Dockerfile — 多阶段构建
# =============================================================================

# ---- 阶段1: 依赖安装 ----
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /build

# 安装编译依赖（某些 Python 包需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmariadb-dev-compat g++ && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖声明并安装
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- 阶段2: 运行镜像 ----
FROM python:3.11-slim

# 安装运行时依赖（mysqlclient 需要 libmariadb）
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmariadb3 curl redis-tools mariadb-client && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 设置工作目录
WORKDIR /app

# 复制后端代码
COPY backend/ .

# 暴露 API 端口
EXPOSE 8000

# 默认启动命令（docker-entrypoint.sh 会覆盖此命令）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
