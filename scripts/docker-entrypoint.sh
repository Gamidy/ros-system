#!/bin/bash
# =============================================================================
# ROS 后端 Docker 入口脚本
# 功能: 等待数据库就绪 → 运行数据库迁移 → 启动 uvicorn
# =============================================================================
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 1. 等待数据库就绪 ──
# =============================================================================
wait_for_db() {
    local host="${DB_HOST:-mariadb}"
    local port="${DB_PORT:-3306}"
    local retries=30
    local wait_seconds=3

    log_info "等待数据库 $host:$port 就绪..."
    for i in $(seq 1 $retries); do
        if mysqladmin ping -h "$host" -P "$port" --silent 2>/dev/null; then
            log_info "数据库已就绪！"
            return 0
        fi
        log_info "等待数据库... ($i/$retries)"
        sleep "$wait_seconds"
    done

    log_error "数据库连接超时，请检查 MariaDB 服务状态"
    exit 1
}

# ── 2. 等待 Redis 就绪 ──
# =============================================================================
wait_for_redis() {
    local host="${REDIS_HOST:-redis}"
    local port="${REDIS_PORT:-6379}"
    local password="${REDIS_PASSWORD:-}"
    local retries=15
    local wait_seconds=2

    log_info "等待 Redis $host:$port 就绪..."
    for i in $(seq 1 $retries); do
        if redis-cli -h "$host" -p "$port" -a "$password" ping 2>/dev/null | grep -q "PONG"; then
            log_info "Redis 已就绪！"
            return 0
        fi
        log_info "等待 Redis... ($i/$retries)"
        sleep "$wait_seconds"
    done

    log_warn "Redis 连接超时，将继续启动（Celery 可能不可用）"
    return 0
}

# ── 3. 运行数据库迁移 ──
# =============================================================================
run_migrations() {
    log_info "开始运行数据库迁移..."

    # 创建所有表（如果尚未创建）
    python -c "
from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)
print('[OK] 数据库表结构创建/校验完成')
" || {
        log_warn "表结构创建遇到警告（可能已存在），继续执行..."
    }

    # 运行 Alembic 迁移（如果有）
    if [ -d "alembic" ] || [ -f "alembic.ini" ]; then
        log_info "检测到 Alembic 配置，运行迁移..."
        alembic upgrade head 2>/dev/null || log_warn "Alembic 迁移跳过（可能尚无迁移脚本）"
    else
        log_info "未检测到 Alembic 配置，跳过迁移"
    fi

    log_info "数据库迁移完成！"
}

# ── 4. 首次初始化（创建默认组织和管理员） ──
# =============================================================================
run_init_admin() {
    log_info "检查是否需要首次初始化..."

    # 使用 Python 脚本进行首次初始化（幂等操作）
    if [ -f "scripts/init_admin.py" ]; then
        python scripts/init_admin.py || log_warn "首次初始化遇到问题，跳过（可能已初始化）"
    fi

    log_info "初始化检查完成"
}

# ── 5. 启动主服务 ──
# =============================================================================
start_uvicorn() {
    log_info "启动 Uvicorn API 服务器..."

    # 使用 exec 让 uvicorn 接管进程（信号正确处理）
    exec uvicorn app.main:app \
        --host "${HOST:-0.0.0.0}" \
        --port "${PORT:-8000}" \
        --workers "${UVICORN_WORKERS:-4}" \
        --log-level "${LOG_LEVEL:-info}" \
        --proxy-headers \
        --forwarded-allow-ips '*'
}

# ── 主流程 ──
# =============================================================================
main() {
    log_info "========================================"
    log_info " ROS 后端服务启动"
    log_info " 环境: ${ENV:-production}"
    log_info "========================================"

    # 等待依赖服务
    wait_for_db
    wait_for_redis

    # 数据库初始化
    run_migrations
    run_init_admin

    # 如果传入了自定义命令，则执行它（用于 docker-compose 覆盖）
    if [ $# -gt 0 ]; then
        log_info "执行自定义启动命令: $*"
        exec "$@"
    fi

    # 默认启动 uvicorn
    start_uvicorn
}

main "$@"
