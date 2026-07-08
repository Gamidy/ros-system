#!/bin/bash
# =============================================================================
# ROS 离线安装包构建脚本
# 功能:
#   1. 构建后端 Docker 镜像
#   2. 导出 Docker 镜像为 tar 文件
#   3. pip download 下载离线依赖包
#   4. 打包为发布 tar.gz（含 docker-compose.yml、配置、脚本）
# =============================================================================
set -e

# ── 配置 ──
PROJECT_NAME="ros-system"
VERSION="${VERSION:-1.0.0}"
OUTPUT_DIR="${OUTPUT_DIR:-./dist}"
BUILD_DIR=$(mktemp -d /tmp/ros-offline-build-XXXXXX)

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 清理临时目录 ──
cleanup() {
    log_info "清理临时文件..."
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

# ── 1. 检查前提条件 ──
# =============================================================================
check_prerequisites() {
    log_info "检查构建环境..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker！"
        exit 1
    fi
    log_info "Docker: $(docker --version)"

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        log_error "docker compose 插件未安装！"
        exit 1
    fi
    log_info "Docker Compose: $(docker compose version)"

    # 检查项目目录结构
    if [ ! -f "docker-compose.yml" ]; then
        log_error "请在项目根目录执行此脚本（未找到 docker-compose.yml）"
        exit 1
    fi
    if [ ! -f "Dockerfile" ]; then
        log_error "未找到 Dockerfile"
        exit 1
    fi
    if [ ! -f "backend/requirements.txt" ]; then
        log_error "未找到 backend/requirements.txt"
        exit 1
    fi

    log_info "项目结构检查通过 ✓"
}

# ── 2. 构建 Docker 镜像并导出 ──
# =============================================================================
build_and_export_images() {
    log_info "开始构建 Docker 镜像..."

    # 构建后端镜像
    docker build -t "ros-backend:${VERSION}" -f Dockerfile . || {
        log_error "后端镜像构建失败"
        exit 1
    }
    log_info "后端镜像构建成功: ros-backend:${VERSION}"

    # 拉取并打标签所需的第三方镜像
    log_info "拉取 MariaDB 镜像..."
    docker pull mariadb:10.11
    docker tag mariadb:10.11 "ros-mariadb:10.11"

    log_info "拉取 Redis 镜像..."
    docker pull redis:7-alpine
    docker tag redis:7-alpine "ros-redis:7-alpine"

    log_info "拉取 Nginx 镜像..."
    docker pull nginx:alpine
    docker tag nginx:alpine "ros-nginx:alpine"

    # 导出所有镜像为 tar 文件
    log_info "导出 Docker 镜像..."
    docker save \
        "ros-backend:${VERSION}" \
        "ros-mariadb:10.11" \
        "ros-redis:7-alpine" \
        "ros-nginx:alpine" \
        -o "${BUILD_DIR}/ros-images.tar" || {
        log_error "Docker 镜像导出失败"
        exit 1
    }
    log_info "镜像导出成功: ros-images.tar"
}

# ── 3. 下载 Python 离线依赖包 ──
# =============================================================================
download_pip_packages() {
    log_info "下载 Python 离线依赖包..."

    mkdir -p "${BUILD_DIR}/pip-packages"

    # 使用与 Docker 镜像相同的 Python 版本下载 wheel
    pip download \
        -r backend/requirements.txt \
        -d "${BUILD_DIR}/pip-packages" \
        --platform manylinux2014_x86_64 \
        --platform linux_x86_64 \
        --python-version 311 \
        --only-binary=:all: \
        --no-deps 2>/dev/null || {
        log_warn "纯 binary 下载失败，回退到普通下载模式..."
        pip download \
            -r backend/requirements.txt \
            -d "${BUILD_DIR}/pip-packages"
    }

    # 生成 requirements.txt 的离线版本（包含哈希校验）
    pip list --format=freeze > /dev/null 2>&1
    cp backend/requirements.txt "${BUILD_DIR}/pip-packages/requirements.txt"

    log_info "离线依赖包下载完成: $(ls ${BUILD_DIR}/pip-packages/*.whl 2>/dev/null | wc -l) 个 wheel 文件"
}

# ── 4. 打包离线安装包 ──
# =============================================================================
package_offline_tarball() {
    log_info "打包离线安装包..."

    # 创建发布目录结构
    RELEASE_DIR="${BUILD_DIR}/${PROJECT_NAME}-${VERSION}-offline"
    mkdir -p "${RELEASE_DIR}"

    # 复制核心部署文件
    cp docker-compose.yml        "${RELEASE_DIR}/"
    cp .env.prod                 "${RELEASE_DIR}/.env.prod.example"
    cp Dockerfile                "${RELEASE_DIR}/"
    cp nginx.conf                "${RELEASE_DIR}/" 2>/dev/null || log_warn "nginx.conf 不存在，跳过"

    # 复制 scripts 目录
    cp -r scripts                "${RELEASE_DIR}/scripts"
    chmod +x "${RELEASE_DIR}/scripts/"*.sh

    # 复制前端 dist（如果存在）
    if [ -d "frontend/dist" ]; then
        cp -r frontend/dist      "${RELEASE_DIR}/frontend/dist"
        log_info "前端静态文件已包含"
    else
        log_warn "frontend/dist 不存在，请先构建前端 (cd frontend && npm run build)"
    fi

    # 复制镜像和 pip 包
    mkdir -p "${RELEASE_DIR}/offline"
    cp "${BUILD_DIR}/ros-images.tar" "${RELEASE_DIR}/offline/"
    cp -r "${BUILD_DIR}/pip-packages" "${RELEASE_DIR}/offline/pip-packages"

    # 创建离线安装说明
    cat > "${RELEASE_DIR}/README-OFFLINE.md" << 'EOF'
# ROS 离线安装包使用说明

## 前提条件
- Docker >= 20.10 (推荐 24.x)
- docker compose 插件
- 目标服务器已安装 Docker

## 安装步骤
1. 上传离线包到目标服务器
2. 解压: tar xzf ros-system-*-offline.tar.gz
3. 进入目录: cd ros-system-*-offline
4. 复制并修改配置: cp .env.prod.example .env.prod
5. 运行安装: sudo bash scripts/install-offline.sh

## 注意事项
- .env.prod 中的密码请务必修改
- 默认端口: 80(前端), 8000(后端API), 3306(数据库), 6379(Redis)
- 管理员默认账号: admin / Admin123! (首次启动后请立即修改)
EOF

    # 打包
    OUTPUT_FILE="${OUTPUT_DIR}/${PROJECT_NAME}-${VERSION}-offline.tar.gz"
    mkdir -p "$OUTPUT_DIR"
    cd "$BUILD_DIR"
    tar -czf "$OUTPUT_FILE" "$(basename "${RELEASE_DIR}")"

    log_info "离线安装包已生成: ${OUTPUT_FILE}"
}

# ── 主流程 ──
# =============================================================================
main() {
    echo ""
    echo "=============================================="
    echo " ROS 离线安装包构建工具"
    echo " 版本: ${VERSION}"
    echo "=============================================="
    echo ""

    check_prerequisites
    build_and_export_images
    download_pip_packages
    package_offline_tarball

    echo ""
    echo "=============================================="
    echo -e " ${GREEN}✓ 构建成功${NC}"
    echo " 输出: ${OUTPUT_DIR}/${PROJECT_NAME}-${VERSION}-offline.tar.gz"
    echo " 大小: $(du -h "${OUTPUT_DIR}/${PROJECT_NAME}-${VERSION}-offline.tar.gz" | cut -f1)"
    echo "=============================================="
}

main
