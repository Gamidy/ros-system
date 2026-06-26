// ── 阶段映射常量 ──
// 产品策划模块各阶段的标签与 Tag 类型定义

export const STAGE_LABELS: Record<string, string> = {
  draft: '草稿',
  competitor: '竞品分析',
  definition: '产品定义',
  costing: '成本目标',
  tech_input: '技术方案',
  project_init: '立项审批',
  approved: '已批准',
  released: '已发布',
}

export const STAGE_TAGS: Record<string, string> = {
  draft: 'info',
  competitor: 'primary',
  definition: 'primary',
  costing: 'warning',
  tech_input: 'primary',
  project_init: 'warning',
  approved: 'success',
  released: 'success',
}
