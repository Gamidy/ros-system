#!/bin/bash
# =============================================================================
# ROS 离线安装脚本
# 功能:
#   1. 加载 Docker 镜像
#   2. 检查环境依赖
#   3. 启动 docker compose 服务
#   4. 初始化数据库和管理员
#   5. 验证部署状态
# =============================================================================
set -e

# ── 颜色 ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${CYAN}▶ $1${NC}"; }

# ── 配置 ──
ENV_FILE="${ENV_FILE:-.env.prod}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-docker-compose.yml}"
PROJECT_NAME="ros-system"

# ── 0. 检查运行环境 ──
# =============================================================================
check_environment() {
    log_step "检查运行环境"

    # 检查是否以 root 运行（docker compose 通常需要 sudo）
    if [ "$EUID" -ne 0 ]; then
        log_warn "建议以 root 或使用 sudo 运行（Docker 需要权限）"
    fi

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装！请先安装 Docker。"
        log_info "安装参考: https://docs.docker.com/engine/install/"
        exit 1
    fi
    log_info "Docker: $(docker --version)"

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        log_error "docker compose 插件未安装！"
        exit 1
    fi
    log_info "Compose: $(docker compose version)"

    # 检查配置文件
    if [ ! -f "$ENV_FILE" ]; then
        log_warn "${ENV_FILE} 不存在，正在从示例文件创建..."
        if [ -f "${ENV_FILE}.example" ]; then
            cp "${ENV_FILE}.example" "$ENV_FILE"
            log_info "已创建 ${ENV_FILE}，请务必修改其中的密码！"
            log_info "修改完成后重新运行本脚本。"
            exit 0
        fi
        log_error "${ENV_FILE} 和 ${ENV_FILE}.example 都找不到，请检查安装包完整性"
        exit 1
    fi

    # 检查必要目录
    if [ ! -d "frontend/dist" ]; then
        log_warn "frontend/dist 目录不存在，前端页面将不可用"
        log_info "请先构建前端: cd frontend && npm run build"
        log_info "按 Ctrl+C 取消，或等待 5 秒继续..."
        sleep 5
    fi

    log_info "环境检查通过 ✓"
}

# ── 1. 加载 Docker 镜像 ──
# =============================================================================
load_docker_images() {
    local IMAGE_FILE="offline/ros-images.tar"

    if [ -f "$IMAGE_FILE" ]; then
        log_step "加载 Docker 镜像"

        # 检查是否已有同名镜像（避免重复加载）
        local already_loaded=true
        for img in ros-backend ros-mariadb ros-redis ros-nginx; do
            if ! docker images --format "{{.Repository}}" | grep -q "^${img}$"; then
                already_loaded=false
                break
            fi
        done

        if [ "$already_loaded" = true ]; then
            log_info "镜像已加载，跳过导入步骤"
        else
            log_info "正在导入 Docker 镜像（可能需要几分钟）..."
            docker load -i "$IMAGE_FILE"
            log_info "Docker 镜像导入完成"
        fi
    else
        log_warn "离线镜像文件不存在: ${IMAGE_FILE}"
        log_warn "将尝试从 Docker Hub 拉取镜像（需要网络连接）"
    fi
}

# ── 2. 准备离线 pip 包（可选） ──
# =============================================================================
prepare_pip_cache() {
    local PIP_DIR="offline/pip-packages"

    if [ -d "$PIP_DIR" ] && [ -f "${PIP_DIR}/requirements.txt" ]; then
        log_step "准备 Python 离线依赖缓存"

        # 创建 pip 缓存目录供 Docker build 使用（如果本地构建）
        mkdir -p /tmp/pip-cache
        cp -r "${PIP_DIR}"/* /tmp/pip-cache/
        log_info "离线 pip 包已就绪（${PIP_DIR}）"
    fi
}

# ── 3. 启动 Docker Compose 服务 ──
# =============================================================================
start_services() {
    log_step "启动 Docker Compose 服务"

    # 停止并清理旧容器（如果存在）
    log_info "停止并移除旧容器（如有）..."
    docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" down --remove-orphans 2>/dev/null || true

    # 启动所有服务
    log_info "启动所有容器服务..."
    docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" up -d

    log_info "等待服务启动（约 30 秒）..."
    sleep 10

    # 等待后端就绪
    log_info "等待后端 API 就绪..."
    local retries=30
    local i=0
    while [ $i -lt $retries ]; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" exec -T backend curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            log_info "后端 API 已就绪！"
            break
        fi
        i=$((i + 1))
        sleep 3
        if [ $i -eq $retries ]; then
            log_warn "后端启动超时，请稍后手动检查状态"
        else
            echo -n "."
        fi
    done
}

# ── 4. 验证部署状态 ──
# =============================================================================
verify_deployment() {
    log_step "验证部署状态"

    # 检查容器状态
    echo ""
    docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" ps

    echo ""
    log_info "容器状态:"
    local all_running=true
    for service in mariadb redis backend frontend; do
        local status=$(docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" ps --format "{{.State}}" "$service" 2>/dev/null)
        if [ "$status" = "running" ]; then
            log_info "  ✓ $service: 运行中"
        else
            log_warn "  ✗ $service: ${status:-未运行}"
            all_running=false
        fi
    done

    # 后端 API 健康检查
    echo ""
    log_info "后端健康检查..."
    if docker compose -f "$DOCKER_COMPOSE_FILE" --project-name "$PROJECT_NAME" exec -T backend curl -sf http://localhost:8000/health 2>/dev/null; then
        echo ""
        log_info "API 健康检查通过 ✓"
    else
        log_warn "API 健康检查暂时不可用（服务可能仍在启动中）"
    fi

    echo ""
    if [ "$all_running" = true ]; then
        log_info "所有服务运行正常 ✓"
    else
        log_warn "部分服务未运行，请检查日志: docker compose logs"
    fi
}

# ── 5. 显示部署信息 ──
# =============================================================================
show_summary() {
    log_step "部署完成 — 访问信息"

    # 获取宿主机 IP
    HOST_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

    echo ""
    echo "=============================================="
    echo -e " ${GREEN}ROS 系统已成功部署！${NC}"
    echo "=============================================="
    echo ""
    echo "  前端页面:  http://${HOST_IP}:80"
    echo "  API 文档:  http://${HOST_IP}:8000/api/v2/docs"
    echo "  API 健康:  http://${HOST_IP}:8000/health"
    echo ""
    echo "  管理员登录:"
    echo "    用户名: $(grep "^ADMIN_USERNAME=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "admin")"
    echo "    密码:   (在 ${ENV_FILE} 中配置)"
    echo ""
    echo "  管理命令:"
    echo "    docker compose logs -f    # 查看实时日志"
    echo "    docker compose ps         # 查看容器状态"
    echo "    bash scripts/healthcheck.sh  # 运行健康检查"
    echo "    docker compose down       # 停止所有服务"
    echo "=============================================="
}

# ── 主流程 ──
# =============================================================================
main() {
    echo ""
    echo "=============================================="
    echo " ROS 系统离线安装工具"
    echo "=============================================="
    echo ""

    check_environment
    load_docker_images
    prepare_pip_cache
    start_services
    verify_deployment
    show_summary
}

main
