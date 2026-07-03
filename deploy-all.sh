#!/bin/bash
# =============================================================================
# ROS System 统一部署脚本
# =============================================================================
# 用法:
#   ./deploy-all.sh              # 全量部署（前端+后端）
#   ./deploy-all.sh --frontend   # 仅部署前端
#   ./deploy-all.sh --backend    # 仅部署后端
#   ./deploy-all.sh --rollback   # 回滚到上一个备份版本
#
# 说明:
#   - 使用 expect 处理 SSH 密码认证（root/NingBo2026*）
#   - 自动备份旧版本，保留最近 5 个备份
#   - 部署后自动验证，失败则自动回滚
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
HOST="139.196.15.52"
SSH_USER="root"
SSH_PASS="NingBo2026*"
SSH_HOST="${SSH_USER}@${HOST}"

PROJECT_ROOT="/Users/gamidy/ros-source/ros-system"
BACKEND_SRC="${PROJECT_ROOT}/backend"
FRONTEND_SRC="${PROJECT_ROOT}/frontend"

REMOTE_BASE="/opt/ros-system"
REMOTE_FRONTEND_DIST="${REMOTE_BASE}/frontend/dist"
REMOTE_BACKEND_APP="${REMOTE_BASE}/backend/app"

BACKUP_DIR="${PROJECT_ROOT}/.backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_NAME="deploy_${TIMESTAMP}"
LOCAL_BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

KEEP_BACKUPS=5

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Expect 辅助函数（SSH 与 SCP 密码认证）
# ---------------------------------------------------------------------------
# 使用 expect 而非 sshpass，因为 expect 更稳定且通常预装

_expect_ssh_script() {
  local cmd="$1"
  cat <<EXPECT
#!/usr/bin/expect -f
set timeout 30
log_user 0
spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${SSH_HOST} "${cmd}"
expect {
  "password:" {
    send "${SSH_PASS}\r"
    exp_continue
  }
  "YES" {
    send "yes\r"
    exp_continue
  }
  eof {
    catch wait result
    set exitcode [lindex \$result 3]
    if { \$exitcode == 0 } {
      puts "SUCCESS"
    }
    exit \$exitcode
  }
  timeout {
    puts "TIMEOUT"
    exit 1
  }
}
EXPECT
}

_expect_scp_script() {
  local src="$1"
  local dst="$2"
  cat <<EXPECT
#!/usr/bin/expect -f
set timeout 60
log_user 0
spawn scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r "${src}" "${SSH_HOST}:${dst}"
expect {
  "password:" {
    send "${SSH_PASS}\r"
    exp_continue
  }
  "YES" {
    send "yes\r"
    exp_continue
  }
  eof {
    catch wait result
    set exitcode [lindex \$result 3]
    if { \$exitcode == 0 } {
      puts "SUCCESS"
    }
    exit \$exitcode
  }
  timeout {
    puts "TIMEOUT"
    exit 1
  }
}
EXPECT
}

_expect_scp_from_remote_script() {
  local src="$1"
  local dst="$2"
  cat <<EXPECT
#!/usr/bin/expect -f
set timeout 60
log_user 0
spawn scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r "${SSH_HOST}:${src}" "${dst}"
expect {
  "password:" {
    send "${SSH_PASS}\r"
    exp_continue
  }
  "YES" {
    send "yes\r"
    exp_continue
  }
  eof {
    catch wait result
    set exitcode [lindex \$result 3]
    if { \$exitcode == 0 } {
      puts "SUCCESS"
    }
    exit \$exitcode
  }
  timeout {
    puts "TIMEOUT"
    exit 1
  }
}
EXPECT
}

# 远程执行命令（通过 expect+ssh）
remote_exec() {
  local cmd="$1"
  local script
  script=$(_expect_ssh_script "$cmd")
  expect -c "$script" 2>&1 | tail -1
  return ${PIPESTATUS[0]}
}

# 远程执行命令并返回所有输出
remote_exec_full() {
  local cmd="$1"
  local script
  script=$(_expect_ssh_script "$cmd")
  # 修改 expect 脚本以输出所有内容
  script="${script//log_user 0/log_user 1}"
  expect -c "$script" 2>&1
  return $?
}

# 复制文件到远程
remote_scp() {
  local src="$1"
  local dst="$2"
  local script
  script=$(_expect_scp_script "$src" "$dst")
  expect -c "$script" 2>&1 | tail -1
  return ${PIPESTATUS[0]}
}

# 从远程复制文件到本地
remote_scp_from() {
  local src="$1"
  local dst="$2"
  local script
  script=$(_expect_scp_from_remote_script "$src" "$dst")
  expect -c "$script" 2>&1 | tail -1
  return ${PIPESTATUS[0]}
}

# ---------------------------------------------------------------------------
# 备份与回滚
# ---------------------------------------------------------------------------

# 远程备份：备份服务器上的前端 dist 和后端 app
backup_remote() {
  log_info "创建远程备份: ${BACKUP_NAME} ..."

  mkdir -p "${LOCAL_BACKUP_PATH}"

  # 备份远程前端 dist
  log_info "备份远程前端 dist ..."
  if remote_exec "test -d ${REMOTE_FRONTEND_DIST}"; then
    remote_scp_from "${REMOTE_FRONTEND_DIST}/" "${LOCAL_BACKUP_PATH}/frontend-dist/" || \
      log_warn "前端 dist 备份不完整（可能为空目录）"
  else
    log_warn "远程前端 dist 目录不存在，跳过备份"
    mkdir -p "${LOCAL_BACKUP_PATH}/frontend-dist"
  fi

  # 备份远程后端 app（从 Docker 容器中拷贝）
  log_info "备份远程后端 app（从容器 ros-backend）..."
  local tmp_backup="/tmp/ros-backend-app-backup-${TIMESTAMP}.tar.gz"
  if remote_exec "docker exec ros-backend sh -c 'tar czf ${tmp_backup} -C /app/app . 2>/dev/null'"; then
    remote_scp_from "${tmp_backup}" "${LOCAL_BACKUP_PATH}/backend-app.tar.gz" || \
      log_warn "后端 app 备份失败"
    remote_exec "rm -f ${tmp_backup}"
  else
    log_warn "容器 ros-backend 中的 /app/app 不可用，尝试直接备份远程目录"
    if remote_exec "test -d ${REMOTE_BACKEND_APP}"; then
      remote_exec "tar czf ${tmp_backup} -C ${REMOTE_BACKEND_APP} . 2>/dev/null"
      remote_scp_from "${tmp_backup}" "${LOCAL_BACKUP_PATH}/backend-app.tar.gz" || \
        log_warn "后端 app 备份失败"
      remote_exec "rm -f ${tmp_backup}"
    else
      log_warn "远程后端 app 目录也不存在"
      touch "${LOCAL_BACKUP_PATH}/backend-app.tar.gz"
    fi
  fi

  # 保存备份元数据
  cat > "${LOCAL_BACKUP_PATH}/meta.txt" <<EOF
backup_name=${BACKUP_NAME}
timestamp=${TIMESTAMP}
date=$(date '+%Y-%m-%d %H:%M:%S')
type=${DEPLOY_TYPE:-full}
EOF

  log_ok "远程备份完成: ${LOCAL_BACKUP_PATH}"
}

# 回滚到指定备份
rollback_to_backup() {
  local backup_path="$1"
  log_info "正在回滚到备份: ${backup_path} ..."

  if [ ! -d "${backup_path}" ]; then
    log_error "备份目录不存在: ${backup_path}"
    return 1
  fi

  # 回滚前端 dist
  if [ -d "${backup_path}/frontend-dist" ]; then
    log_info "回滚前端 dist ..."
    # 在远程上创建临时目录
    local tmp_rollback="/tmp/ros-rollback-frontend-${TIMESTAMP}.tar.gz"
    # 在本地打包备份的前端 dist
    cd "${backup_path}/frontend-dist"
    tar czf "/tmp/ros-rollback-frontend-local.tar.gz" .
    cd "${PROJECT_ROOT}"
    # 上传到远程并解压
    remote_scp "/tmp/ros-rollback-frontend-local.tar.gz" "${tmp_rollback}"
    remote_exec "rm -rf ${REMOTE_FRONTEND_DIST} && mkdir -p ${REMOTE_FRONTEND_DIST} && tar xzf ${tmp_rollback} -C ${REMOTE_FRONTEND_DIST}/ && rm -f ${tmp_rollback}"
    rm -f "/tmp/ros-rollback-frontend-local.tar.gz"
    log_ok "前端 dist 回滚完成"
  else
    log_warn "备份中无可用的前端 dist"
  fi

  # 回滚后端 app
  if [ -f "${backup_path}/backend-app.tar.gz" ] && [ -s "${backup_path}/backend-app.tar.gz" ]; then
    log_info "回滚后端 app ..."
    local tmp_rollback_bak="/tmp/ros-rollback-backend-${TIMESTAMP}.tar.gz"
    remote_scp "${backup_path}/backend-app.tar.gz" "${tmp_rollback_bak}"
    remote_exec "docker exec ros-backend sh -c 'rm -rf /app/app && mkdir /app/app && cd /app/app && tar xzf ${tmp_rollback_bak} && rm -f ${tmp_rollback_bak}'"
    remote_exec "docker restart ros-backend"
    log_ok "后端 app 回滚完成"
  else
    log_warn "备份中无可用的后端 app"
  fi

  # Nginx reload
  log_info "重新加载 Nginx ..."
  remote_exec "nginx -s reload" || log_warn "Nginx reload 失败"

  log_ok "回滚操作完成"
}

# 查找最新的备份
find_latest_backup() {
  local backups
  backups=$(ls -1dt "${BACKUP_DIR}"/deploy_* 2>/dev/null || true)
  if [ -z "${backups}" ]; then
    echo ""
    return
  fi
  echo "${backups}" | head -1
}

# 清理旧备份（保留最近 KEEP_BACKUPS 个）
cleanup_old_backups() {
  log_info "清理旧备份（保留最近 ${KEEP_BACKUPS} 个）..."
  local all_backups
  all_backups=$(ls -1dt "${BACKUP_DIR}"/deploy_* 2>/dev/null || true)
  if [ -z "${all_backups}" ]; then
    return
  fi
  local count
  count=$(echo "${all_backups}" | wc -l | tr -d ' ')
  if [ "$count" -le "${KEEP_BACKUPS}" ]; then
    log_info "备份数量 ${count}，无需清理"
    return
  fi
  local to_delete
  to_delete=$(echo "${all_backups}" | tail -n +$((KEEP_BACKUPS + 1)))
  echo "${to_delete}" | while read -r bak; do
    if [ -n "${bak}" ]; then
      log_info "删除旧备份: ${bak}"
      rm -rf "${bak}"
    fi
  done
  log_ok "清理完成"
}

# ---------------------------------------------------------------------------
# 部署函数
# ---------------------------------------------------------------------------

deploy_frontend() {
  log_info "====== 开始部署前端 ======"

  # 1. 构建前端
  log_info "构建前端 (npm run build) ..."
  cd "${FRONTEND_SRC}"
  if npm run build; then
    log_ok "前端构建成功"
  else
    log_error "前端构建失败"
    return 1
  fi

  # 2. 确认 dist 目录存在
  if [ ! -d "${FRONTEND_SRC}/dist" ]; then
    log_error "构建后 dist 目录不存在"
    return 1
  fi

  # 3. 打包 dist 并上传到远程
  log_info "打包并上传前端 dist ..."
  local dist_tar="/tmp/ros-frontend-dist-${TIMESTAMP}.tar.gz"
  cd "${FRONTEND_SRC}"
  tar czf "${dist_tar}" -C dist .

  # 远程：备份当前 dist（在 backup_remote 中已完成），然后部署新版本
  local remote_tar="/tmp/ros-frontend-dist-${TIMESTAMP}.tar.gz"
  if remote_scp "${dist_tar}" "${remote_tar}"; then
    # 在远程上解压到目标目录
    log_info "在远程服务器上解压前端 dist ..."
    if remote_exec "rm -rf ${REMOTE_FRONTEND_DIST}_new && mkdir -p ${REMOTE_FRONTEND_DIST}_new && tar xzf ${remote_tar} -C ${REMOTE_FRONTEND_DIST}_new/ && rm -f ${remote_tar}"; then
      # 原子替换：用新版本替换旧版本
      remote_exec "mv ${REMOTE_FRONTEND_DIST} ${REMOTE_FRONTEND_DIST}_old 2>/dev/null; mv ${REMOTE_FRONTEND_DIST}_new ${REMOTE_FRONTEND_DIST}; rm -rf ${REMOTE_FRONTEND_DIST}_old"
      log_ok "前端 dist 部署完成"
    else
      log_error "远程解压前端 dist 失败"
      rm -f "${dist_tar}"
      return 1
    fi
  else
    log_error "SCP 上传前端 dist 失败"
    rm -f "${dist_tar}"
    return 1
  fi

  rm -f "${dist_tar}"

  # 4. 重新加载 Nginx
  log_info "重新加载 Nginx ..."
  if remote_exec "nginx -t && nginx -s reload"; then
    log_ok "Nginx 重新加载成功"
  else
    log_warn "Nginx reload 失败，请手动检查"
  fi

  log_ok "====== 前端部署完成 ======"
  return 0
}

deploy_backend() {
  log_info "====== 开始部署后端 ======"

  # 1. 打包后端 app 目录（排除 __pycache__ 和 .pyc）
  log_info "打包后端 app 目录 ..."
  local backend_tar="/tmp/ros-backend-app-${TIMESTAMP}.tar.gz"
  cd "${BACKEND_SRC}"
  tar czf "${backend_tar}" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    -C app .

  if [ ! -f "${backend_tar}" ]; then
    log_error "后端打包失败"
    return 1
  fi

  # 2. 上传到远程服务器
  log_info "上传后端包到远程服务器 ..."
  local remote_tar="/tmp/ros-backend-app-${TIMESTAMP}.tar.gz"
  if remote_scp "${backend_tar}" "${remote_tar}"; then
    # 3. 在 Docker 容器内替换 app 目录
    log_info "在 Docker 容器内更新后端代码 ..."
    if remote_exec "\
      docker exec ros-backend sh -c '\
        rm -rf /app/app_old && \
        mv /app/app /app/app_old && \
        mkdir /app/app' && \
      docker cp ${remote_tar} ros-backend:/tmp/ && \
      docker exec ros-backend sh -c '\
        cd /app/app && \
        tar xzf /tmp/ros-backend-app-${TIMESTAMP}.tar.gz && \
        rm -f /tmp/ros-backend-app-${TIMESTAMP}.tar.gz'"; then
      log_ok "后端代码更新完成"
    else
      log_error "Docker 容器内更新后端代码失败"
      # 尝试恢复
      log_info "尝试恢复旧版本..."
      remote_exec "docker exec ros-backend sh -c 'rm -rf /app/app && mv /app/app_old /app/app'" || true
      rm -f "${backend_tar}"
      return 1
    fi
  else
    log_error "SCP 上传后端包失败"
    rm -f "${backend_tar}"
    return 1
  fi

  rm -f "${backend_tar}"

  # 4. 重启 Docker 容器
  log_info "重启 Docker 容器 ros-backend ..."
  if remote_exec "docker restart ros-backend"; then
    log_ok "Docker 容器重启成功"
  else
    log_error "Docker 容器重启失败"
    return 1
  fi

  # 5. 等待后端启动
  log_info "等待后端服务启动（5 秒）..."
  sleep 5

  log_ok "====== 后端部署完成 ======"
  return 0
}

# ---------------------------------------------------------------------------
# 验证函数
# ---------------------------------------------------------------------------

verify_deployment() {
  log_info "====== 开始部署验证 ======"
  local failed=0

  # 验证 1: 检查远程前端 dist 文件存在
  log_info "验证 1/3: 检查前端 dist/index.html ..."
  if remote_exec "test -f ${REMOTE_FRONTEND_DIST}/index.html"; then
    log_ok "  ✓ ${REMOTE_FRONTEND_DIST}/index.html 存在"
  else
    log_error "  ✗ ${REMOTE_FRONTEND_DIST}/index.html 不存在"
    failed=1
  fi

  # 验证 2: curl 根路径返回 200
  log_info "验证 2/3: curl http://${HOST}/ → 200 ..."
  local http_code_root
  http_code_root=$(remote_exec "curl -s -o /dev/null -w '%{http_code}' http://localhost/") || true
  if [ "${http_code_root}" = "200" ]; then
    log_ok "  ✓ 根路径返回 HTTP 200"
  else
    log_error "  ✗ 根路径返回 HTTP ${http_code_root:-'N/A'}（期望 200）"
    failed=1
  fi

  # 验证 3: curl /api/auth/login 返回 405 (POST only)
  log_info "验证 3/3: curl http://${HOST}/api/auth/login → 405 ..."
  local http_code_login
  http_code_login=$(remote_exec "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/auth/login") || true
  if [ "${http_code_login}" = "405" ]; then
    log_ok "  ✓ /api/auth/login 返回 HTTP 405（正确，仅接受 POST）"
  else
    log_error "  ✗ /api/auth/login 返回 HTTP ${http_code_login:-'N/A'}（期望 405）"
    failed=1
  fi

  if [ "${failed}" -eq 0 ]; then
    log_ok "====== 全部验证通过 ======"
    return 0
  else
    log_error "====== 验证失败 ======"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

# 解析参数
DEPLOY_FRONTEND=false
DEPLOY_BACKEND=false
DEPLOY_ROLLBACK=false

case "${1:-}" in
  --frontend)
    DEPLOY_FRONTEND=true
    DEPLOY_TYPE="frontend"
    ;;
  --backend)
    DEPLOY_BACKEND=true
    DEPLOY_TYPE="backend"
    ;;
  --rollback)
    DEPLOY_ROLLBACK=true
    DEPLOY_TYPE="rollback"
    ;;
  "")
    DEPLOY_FRONTEND=true
    DEPLOY_BACKEND=true
    DEPLOY_TYPE="full"
    ;;
  *)
    echo "用法: $0 [--frontend|--backend|--rollback]"
    echo ""
    echo "  (无参数)   全量部署（前端 + 后端）"
    echo "  --frontend 仅部署前端"
    echo "  --backend  仅部署后端"
    echo "  --rollback 回滚到上一个备份"
    exit 1
    ;;
esac

echo ""
echo "=============================================="
echo "  ROS System 统一部署脚本"
echo "  类型: ${DEPLOY_TYPE}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo ""

# ----- 回滚模式 -----
if [ "${DEPLOY_ROLLBACK}" = true ]; then
  LATEST_BACKUP=$(find_latest_backup)
  if [ -z "${LATEST_BACKUP}" ]; then
    log_error "没有找到可用的备份，无法回滚"
    exit 1
  fi
  log_info "找到最新备份: ${LATEST_BACKUP}"
  rollback_to_backup "${LATEST_BACKUP}"
  log_info "等待 3 秒后验证..."
  sleep 3
  if verify_deployment; then
    log_ok "回滚后验证通过"
  else
    log_error "回滚后验证失败，请手动检查"
    exit 1
  fi
  exit 0
fi

# ----- 正常部署模式 -----

# 1. 先做备份
log_info "===== 步骤 1: 备份当前版本 ====="
backup_remote

# 2. 部署
DEPLOY_FAILED=false

if [ "${DEPLOY_FRONTEND}" = true ]; then
  echo ""
  log_info "===== 步骤 2a: 部署前端 ====="
  if deploy_frontend; then
    log_ok "前端部署成功"
  else
    log_error "前端部署失败"
    DEPLOY_FAILED=true
  fi
fi

if [ "${DEPLOY_BACKEND}" = true ]; then
  echo ""
  log_info "===== 步骤 2b: 部署后端 ====="
  if deploy_backend; then
    log_ok "后端部署成功"
  else
    log_error "后端部署失败"
    DEPLOY_FAILED=true
  fi
fi

# 3. 如果部署失败，自动回滚
if [ "${DEPLOY_FAILED}" = true ]; then
  echo ""
  log_error "===== 部署失败，开始自动回滚 ====="
  LATEST_BACKUP=$(find_latest_backup)
  if [ -n "${LATEST_BACKUP}" ]; then
    rollback_to_backup "${LATEST_BACKUP}"
    log_info "等待 3 秒后验证..."
    sleep 3
    if verify_deployment; then
      log_ok "回滚成功，服务已恢复"
    else
      log_error "回滚后验证仍然失败，请手动介入检查"
    fi
  else
    log_error "没有备份可回滚，请手动修复"
  fi
  exit 1
fi

# 4. 验证部署
echo ""
log_info "===== 步骤 3: 验证部署 ====="
sleep 2
if verify_deployment; then
  log_ok "部署验证全部通过"
else
  echo ""
  log_error "===== 验证失败，开始自动回滚 ====="
  LATEST_BACKUP=$(find_latest_backup)
  if [ -n "${LATEST_BACKUP}" ]; then
    rollback_to_backup "${LATEST_BACKUP}"
    log_info "等待 3 秒后验证..."
    sleep 3
    verify_deployment || log_error "回滚后验证仍然失败，请手动检查"
  fi
  exit 1
fi

# 5. 清理旧备份
echo ""
log_info "===== 步骤 4: 清理旧备份 ====="
cleanup_old_backups

# 6. 完成
echo ""
echo "=============================================="
echo -e "${GREEN}  🎉 部署成功完成！${NC}"
echo "  类型: ${DEPLOY_TYPE}"
echo "  备份: ${LOCAL_BACKUP_PATH}"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
