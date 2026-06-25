import type { Component } from 'vue'
import {
  Monitor, Goods, List, Folder, Document, WarningFilled,
  Stamp, Cpu, WarnTriangleFilled, Refresh, Select,
  ShoppingCart, DataAnalysis, Setting, Checked,
  OfficeBuilding, User,
} from '@element-plus/icons-vue'

/** 系统支持的全部角色（与后端 permissions.py ALL_ROLES 对齐） */
export type RoleName =
  | 'admin'
  | 'general_manager'
  | 'rd_director'
  | 'product_manager'
  | 'systems_engineer'
  | 'structural_engineer'
  | 'electrical_control_engineer'
  | 'electrical_engineer'
  | 'procurement'
  | 'quality_engineer'
  | 'process_engineer'
  | 'project_admin'
  | 'production'
  | 'module_manager'
  | 'module_manager_struct'
  | 'module_manager_sys'
  | 'finance_manager'
  | 'process_manager'
  | 'procurement_director'
  | 'security_officer'
  | 'engineer'  // 向后兼容：原系统默认角色

/** 角色中文名称映射 */
export const ROLE_LABELS: Record<RoleName, string> = {
  admin:                      '系统管理员',
  general_manager:            '总经理',
  rd_director:                '研发总监',
  product_manager:            '产品经理',
  systems_engineer:           '系统工程师',
  structural_engineer:        '结构工程师',
  electrical_control_engineer:'电控工程师',
  electrical_engineer:        '电气工程师',
  procurement:                '采购',
  quality_engineer:           '品质工程师',
  process_engineer:           '工艺工程师',
  project_admin:              '项目管理员',
  production:                 '生产',
  module_manager:             '模块经理',
  module_manager_struct:      '结构模块经理',
  module_manager_sys:         '系统模块经理',
  finance_manager:            '财务经理',
  process_manager:            '工艺经理',
  procurement_director:       '采购总监',
  security_officer:           'IT安全员',
  engineer:                   '工程师',
}

/** 菜单项定义 */
export interface MenuItem {
  path: string      // 路由路径 (同时也是 el-menu 的 index)
  title: string     // 菜单标题
  icon: Component   // Element Plus 图标组件
}

/** 全部菜单 */
export const ALL_MENUS: MenuItem[] = [
  { path: '/dashboard',      title: '驾驶舱',        icon: Monitor },
  { path: '/products',       title: '产品主线',       icon: Goods },
  { path: '/bom',            title: 'BOM物料管理',    icon: List },
  { path: '/projects',       title: '项目管理',       icon: Folder },
  { path: '/tests',          title: '实验与测试',     icon: Document },
  { path: '/alerts',         title: '预警体系',       icon: WarningFilled },
  { path: '/certifications', title: '认证管理',       icon: Stamp },
  { path: '/prototypes',     title: '样机管理',       icon: Cpu },
  { path: '/quality',        title: '质量问题',       icon: WarnTriangleFilled },
  { path: '/changes',        title: '变更管理',       icon: Refresh },
  { path: '/approvals',      title: '审批管理',       icon: Select },
  { path: '/approvals/proposals', title: '产品立项审批', icon: Checked },
  { path: '/purchases',      title: '采购管理',       icon: ShoppingCart },
  { path: '/mm',            title: '模块管理',       icon: DataAnalysis },
  { path: '/pm-workspace',   title: '工作台',         icon: Monitor },
  { path: '/competitor-bench',   title: '竞品对标',     icon: DataAnalysis },
  { path: '/market-mgmt',        title: '市场管理',     icon: Stamp },
  { path: '/product-plans',      title: '产品策划',     icon: DataAnalysis },
  { path: '/event-timeline',    title: '事件时间线',    icon: DataAnalysis },
  { path: '/saga-viewer',      title: 'Saga事务',      icon: Select },
  { path: '/risk-dashboard',  title: '智能决策看板',  icon: DataAnalysis },
  { path: '/rd-dashboard',   title: '研发总监',       icon: DataAnalysis },
  { path: '/admin-config',   title: '系统设置',       icon: Setting },
  { path: '/admin/tenants',   title: '多租户管理',     icon: OfficeBuilding },
  { path: '/admin/my-org',    title: '我的组织',       icon: User },
  // P0-6 安规管理
  { path: '/safety/standards',  title: '安全标准库',       icon: Document },
  { path: '/safety/inspection-items', title: '安规检测项', icon: Document },
  { path: '/safety/supplier-qualifications', title: '供应商安规', icon: ShoppingCart },
  { path: '/safety/alerts',     title: '安规预警',         icon: WarningFilled },
  // P0-8 DFM可制造性分析
  { path: '/dfm/checklist',   title: 'DFM检查项',        icon: Document },
  { path: '/dfm/reports',     title: 'DFM分析报告',      icon: DataAnalysis },
  // P0-7 外协管理
  { path: '/outsource/partners',  title: '外协厂商',        icon: ShoppingCart },
  { path: '/outsource/orders',    title: '外协订单',        icon: List },
  { path: '/outsource/quality-records', title: '外协质检',  icon: Document },
]

/**
 * 注意: 角色→路由路径映射表 (ROLE_ROUTES) 已从前端移除。
 * 权限数据现由后端 GET /api/auth/me 的 allowed_paths 字段动态下发，
 * 前端仅保存当前登录用户的允许路径，不再暴露全局角色权限表。
 */
