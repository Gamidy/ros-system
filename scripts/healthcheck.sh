#!/bin/bash
# =============================================================================
# ROS 系统健康检查脚本
# 功能: 同时检查后端 API、Redis 和 MariaDB 的运行状态
# 返回: 0 = 全部正常, 1 = 至少一项异常
# =============================================================================
set +e  # 不因单个检查失败而退出，需收集所有状态

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC}     $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC}   $1"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC}  $1"; }

# 配置（可通过环境变量覆盖）
API_URL="${API_URL:-http://localhost:8000/health}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"

# 整体状态（0=正常，1=异常）
OVERALL_STATUS=0

# ── 开始检查 ──
echo "=============================================="
echo " ROS 系统健康检查"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ── 1. 后端 API 健康检查 ──
echo ""
echo "▶ 后端 API 检查 ($API_URL)"
if curl -sf "$API_URL" > /dev/null 2>&1; then
    log_ok "API 服务正常"
else
    log_fail "API 服务无响应"
    OVERALL_STATUS=1
fi

# ── 2. Redis 检查 ──
echo ""
echo "▶ Redis 检查 ($REDIS_HOST:$REDIS_PORT)"
if command -v redis-cli &> /dev/null; then
    if [ -n "$REDIS_PASSWORD" ]; then
        RESULT=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping 2>/dev/null)
    else
        RESULT=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null)
    fi

    if [ "$RESULT" = "PONG" ]; then
        log_ok "Redis 正常响应 PONG"
    else
        log_fail "Redis 无响应"
        OVERALL_STATUS=1
    fi
else
    log_skip "redis-cli 未安装，跳过 Redis 检查"
fi

# ── 3. MariaDB 检查 ──
echo ""
echo "▶ MariaDB 检查 ($DB_HOST:$DB_PORT)"
if command -v mysqladmin &> /dev/null; then
    if mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" --silent 2>/dev/null; then
        log_ok "MariaDB 正常响应"
    else
        log_fail "MariaDB 无响应"
        OVERALL_STATUS=1
    fi
else
    log_skip "mysqladmin 未安装，跳过 MariaDB 检查"
fi

# ── 汇总 ──
echo ""
echo "=============================================="
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e " ${GREEN}✓ 所有服务运行正常${NC}"
else
    echo -e " ${RED}✗ 存在服务异常，请检查上方日志${NC}"
fi
echo "=============================================="
exit $OVERALL_STATUS
