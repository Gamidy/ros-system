/* ===== PMWorkspace 纯工具函数 ===== */

/**
 * 金额格式化（千位分隔符）
 */
export function formatMoney(val: number | null | undefined): string {
  if (val == null) return '0'
  return Number(val).toLocaleString('zh-CN')
}

/**
 * 项目状态 → Element Plus Tag 类型映射
 */
export function statusTagType(status: string): string {
  const map: Record<string, string> = {
    planning: 'info',
    running: '',
    completed: 'success',
    paused: 'warning',
    cancelled: 'danger',
    draft: 'info',
    overdue: 'danger',
    submitted: 'primary',
  }
  return map[status] || 'info'
}

/**
 * 项目状态 → 中文标签映射
 */
export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    planning: '规划中',
    running: '进行中',
    completed: '已完成',
    paused: '暂停',
    cancelled: '已取消',
    draft: '草稿',
    overdue: '超期',
    submitted: '已提交',
  }
  return map[status] || status
}

/**
 * 审批状态 → Element Plus Tag 类型映射
 */
export function approvalTagType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }
  return map[status] || 'info'
}

/**
 * 审批状态 → 中文标签映射
 */
export function approvalLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '审批中',
    approved: '审批通过',
    rejected: '审批驳回',
  }
  return map[status] || status
}

/**
 * 项目进度 → 颜色值映射
 */
export function progressColor(progress: number): string {
  if (progress >= 80) return '#67c23a'
  if (progress >= 40) return '#409eff'
  return '#e6a23c'
}
