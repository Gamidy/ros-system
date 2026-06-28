import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/login/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/register/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/forgot-password',
      name: 'ForgotPassword',
      component: () => import('../views/login/ForgotPassword.vue'),
      meta: { public: true },
    },
    {
      path: '/reset-password',
      name: 'ResetPassword',
      component: () => import('../views/login/ResetPassword.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../layout/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('../views/dashboard/DashboardView.vue'),
          meta: { title: '驾驶舱' },
        },
        {
          path: 'products',
          name: 'Products',
          component: () => import('../views/products/ProductsView.vue'),
          meta: { title: '产品主线' },
        },
        {
          path: 'bom',
          name: 'BOM',
          component: () => import('../views/bom/BOMView.vue'),
          meta: { title: 'BOM物料管理' },
        },
        {
          path: 'projects',
          name: 'Projects',
          component: () => import('../views/projects/ProjectsView.vue'),
          meta: { title: '项目管理' },
        },
        {
          path: 'tests',
          name: 'Tests',
          component: () => import('../views/tests/TestsView.vue'),
          meta: { title: '实验与测试', menu: 'tests' },
        },
        {
          path: 'tests/verification-requirements',
          name: 'VerificationRequirements',
          component: () => import('../views/tests/VerificationRequirementView.vue'),
          meta: { title: '验证需求', menu: 'tests' },
        },
        {
          path: 'tests/gate-rules',
          name: 'GateRules',
          component: () => import('../views/tests/GateRuleView.vue'),
          meta: { title: 'Gate规则引擎', menu: 'tests' },
        },
        {
          path: 'alerts',
          name: 'Alerts',
          component: () => import('../views/alerts/AlertsView.vue'),
          meta: { title: '预警体系' },
        },
        {
          path: 'certifications',
          name: 'Certifications',
          component: () => import('../views/certifications/CertHub.vue'),
          meta: { title: '认证管理' },
        },
        // S2 认证中心路由
        {
          path: 's2/dashboard',
          name: 'S2Dashboard',
          component: () => import('../views/s2/S2DashboardView.vue'),
          meta: { title: '认证中心', menu: 'certifications' },
        },
        {
          path: 's2/requirements',
          name: 'S2Requirements',
          component: () => import('../views/s2/S2RequirementView.vue'),
          meta: { title: '认证需求', menu: 'certifications' },
        },
        {
          path: 's2/projects',
          name: 'S2Projects',
          component: () => import('../views/s2/S2CertProjectView.vue'),
          meta: { title: '认证项目', menu: 'certifications' },
        },
        {
          path: 's2/projects/:id',
          name: 'S2ProjectDetail',
          component: () => import('../views/s2/S2CertProjectDetail.vue'),
          meta: { title: '认证项目详情', menu: 'certifications' },
        },
        {
          path: 's2/samples',
          name: 'S2Samples',
          component: () => import('../views/s2/S2CertSampleView.vue'),
          meta: { title: '认证样机', menu: 'certifications' },
        },
        {
          path: 's2/executions',
          name: 'S2Executions',
          component: () => import('../views/s2/S2CertExecutionView.vue'),
          meta: { title: '认证执行', menu: 'certifications' },
        },
        {
          path: 's2/results',
          name: 'S2Results',
          component: () => import('../views/s2/S2CertResultView.vue'),
          meta: { title: '认证结果', menu: 'certifications' },
        },
        {
          path: 's2/certificates',
          name: 'S2Certificates',
          component: () => import('../views/s2/S2CertificateView.vue'),
          meta: { title: '证书管理', menu: 'certifications' },
        },
        {
          path: 's2/certificates/:id',
          name: 'S2CertificateDetail',
          component: () => import('../views/s2/S2CertificateDetail.vue'),
          meta: { title: '证书详情', menu: 'certifications' },
        },
        {
          path: 's2/gate-rules',
          name: 'S2GateRules',
          component: () => import('../views/s2/S2GateRulesView.vue'),
          meta: { title: '认证门禁规则', menu: 'certifications' },
        },
        {
          path: 's2/impact',
          name: 'S2Impact',
          component: () => import('../views/s2/S2ImpactView.vue'),
          meta: { title: '变更影响分析', menu: 'certifications' },
        },
        // P2-T4 影响链可视化（新页面）
        {
          path: 'cert/impact',
          name: 'CertImpact',
          component: () => import('../views/cert/CertImpactView.vue'),
          meta: { title: '影响链可视化', menu: 'certifications' },
        },
        {
          path: 'prototypes',
          name: 'Prototypes',
          component: () => import('../views/prototypes/PrototypesView.vue'),
          meta: { title: '样机管理' },
        },
        {
          path: 'quality',
          name: 'QualityIssues',
          component: () => import('../views/quality/QualityIssuesView.vue'),
          meta: { title: '质量问题' },
        },
        {
          path: 'changes',
          name: 'Changes',
          component: () => import('../views/changes/ChangesHub.vue'),
          meta: { title: '变更管理' },
        },
        {
          path: 'approvals',
          name: 'Approvals',
          component: () => import('../views/approvals/ApprovalsView.vue'),
          meta: { title: '审批管理' },
        },
        {
          path: 'rd-dashboard',
          name: 'RDDashboard',
          component: () => import('../views/rd/RDDashboard.vue'),
          meta: { title: '研发总监仪表盘' },
        },
        {
          path: 'purchases',
          name: 'Purchases',
          component: () => import('../views/purchases/PurchasesView.vue'),
          meta: { title: '采购管理' },
        },
        {
          path: 'mm',
          name: 'ModuleManager',
          component: () => import('../views/mm/ModuleManagerView.vue'),
          meta: { title: '模块管理' },
        },
        {
          path: 'pm-workspace',
          name: 'PMWorkspace',
          component: () => import('../views/pm/PMWorkspace.vue'),
          meta: { title: '工作台', menu: 'pm-workspace' },
        },
        {
          path: 'proposals',
          name: 'Proposals',
          component: () => import('../views/pm/ProposalsView.vue'),
          meta: { title: '提案管理', menu: 'proposals' },
        },
        {
          path: 'planning/calendar',
          name: 'PlanningCalendar',
          component: () => import('../views/pm/PlanningCalendarView.vue'),
          meta: { title: '年度规划日历', menu: 'planning-calendar' },
        },
        {
          path: 'competitor-bench',
          name: 'CompetitorBench',
          component: () => import('../views/pm/CompetitorStandalone.vue'),
          meta: { title: '竞品对标' },
        },
        {
          path: 'market-mgmt',
          name: 'MarketMgmt',
          component: () => import('../views/pm/MarketMgmt.vue'),
          meta: { title: '市场管理' },
        },
        {
          path: 'product-plans',
          name: 'ProductPlanningCenter',
          component: () => import('../views/pm/ProductPlanningCenter.vue'),
          meta: { title: '产品策划', menu: 'product-plans' },
        },
        {
          path: 'product-plans/:id',
          name: 'ProductPlanDetail',
          component: () => import('../views/pm/ProductPlanDetail.vue'),
          meta: { title: '策划详情', menu: 'product-plans' },
        },
        {
          path: 'event-timeline',
          name: 'EventTimeline',
          component: () => import('../views/pm/EventTimelineView.vue'),
          meta: { title: '事件时间线' },
        },
        {
          path: 'event-timeline/detail/:planId',
          name: 'EventTimelineDetail',
          component: () => import('../views/pm/EventTimelineDetail.vue'),
          meta: { title: '事件详情' },
        },
        {
          path: 'saga-viewer',
          name: 'SagaChainViewer',
          component: () => import('../views/pm/SagaChainViewer.vue'),
          meta: { title: 'Saga事务' },
        },
        {
          path: 'risk-dashboard',
          name: 'RiskDashboard',
          component: () => import('../views/risk/RiskDashboard.vue'),
          meta: { title: '智能决策看板' },
        },
        {
          path: 'admin-config',
          name: 'AdminConfig',
          component: () => import('../views/admin/AdminConfig.vue'),
          meta: { title: '系统设置', menu: 'admin-config' },
        },
        {
          path: 'settings/notifications',
          name: 'NotificationSettings',
          component: () => import('../views/settings/NotificationSettings.vue'),
          meta: { title: '通知配置', menu: 'admin-config' },
        },
        {
          path: 'settings/ai',
          name: 'AiSettings',
          component: () => import('../views/settings/AiSettings.vue'),
          meta: { title: 'AI配置管理', menu: 'admin-config' },
        },
        {
          path: 'admin/tenants',
          name: 'TenantManagement',
          component: () => import('../views/admin/TenantManagement.vue'),
          meta: { title: '多租户管理' },
        },
        {
          path: 'admin/my-org',
          name: 'MyOrgInfo',
          component: () => import('../views/admin/MyOrgInfo.vue'),
          meta: { title: '我的组织' },
        },
        // Phase 6 S3 — ECR/ECO 工程变更控制
        {
          path: 'ecr',
          name: 'ECRList',
          component: () => import('../views/changes/ECRListView.vue'),
          meta: { title: 'ECR变更申请', menu: 'changes' },
        },
        {
          path: 'ecr/:id',
          name: 'ECRDetail',
          component: () => import('../views/changes/ECRDetailView.vue'),
          meta: { title: 'ECR详情', menu: 'changes' },
        },
        {
          path: 'eco',
          name: 'ECOList',
          component: () => import('../views/changes/ECOListView.vue'),
          meta: { title: 'ECO变更指令', menu: 'changes' },
        },
        {
          path: 'eco/:id',
          name: 'ECODetail',
          component: () => import('../views/changes/ECODetailView.vue'),
          meta: { title: 'ECO详情', menu: 'changes' },
        },
        {
          path: 'eco/changes',
          name: 'ECOChDashboard',
          component: () => import('../views/changes/ECOChDashboard.vue'),
          meta: { title: '变更看板', menu: 'changes' },
        },
        // P0-6 安规管理
        {
          path: 'safety',
          name: 'SafetyHub',
          component: () => import('../views/safety/SafetyHub.vue'),
          meta: { title: '安规管理', menu: 'safety' },
        },
        {
          path: 'safety/standards',
          name: 'SafetyStandards',
          component: () => import('../views/safety/SafetyStandardTab.vue'),
          meta: { title: '安全标准库', menu: 'safety-standards' },
        },
        {
          path: 'safety/inspection-items',
          name: 'SafetyInspectionItems',
          component: () => import('../views/safety/SafetyInspectionTab.vue'),
          meta: { title: '安规检测项', menu: 'safety-inspection-items' },
        },
        {
          path: 'safety/supplier-qualifications',
          name: 'SupplierSafety',
          component: () => import('../views/safety/SupplierSafetyTab.vue'),
          meta: { title: '供应商安规', menu: 'safety-supplier-qual' },
        },
        {
          path: 'safety/alerts',
          name: 'SafetyAlerts',
          component: () => import('../views/safety/SafetyAlertTab.vue'),
          meta: { title: '安规预警', menu: 'safety-alerts' },
        },
        // P0-8 DFM可制造性分析
        {
          path: 'dfm/checklist',
          name: 'DFMChecklist',
          component: () => import('../views/manufacturability/DFMChecklistTab.vue'),
          meta: { title: 'DFM检查项', menu: 'dfm-checklist' },
        },
        {
          path: 'dfm/reports',
          name: 'DFMReports',
          component: () => import('../views/manufacturability/DFMReportTab.vue'),
          meta: { title: 'DFM分析报告', menu: 'dfm-reports' },
        },
        // P0-7 外协管理
        {
          path: 'outsource/partners',
          name: 'OutsourcePartners',
          component: () => import('../views/outsource/OutsourcePartnerTab.vue'),
          meta: { title: '外协厂商', menu: 'outsource-partners' },
        },
        {
          path: 'outsource/orders',
          name: 'OutsourceOrders',
          component: () => import('../views/outsource/OutsourceOrderTab.vue'),
          meta: { title: '外协订单', menu: 'outsource-orders' },
        },
        {
          path: 'outsource/quality-records',
          name: 'OutsourceQuality',
          component: () => import('../views/outsource/OutsourceQualityTab.vue'),
          meta: { title: '外协质检', menu: 'outsource-quality' },
        },
        // S4 成本核算
        {
          path: 'cost-accounting',
          name: 'CostAccounting',
          component: () => import('../views/cost-accounting/CostSheetList.vue'),
          meta: { title: '成本核算', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/sheets/:id',
          name: 'CostSheetDetail',
          component: () => import('../views/cost-accounting/CostSheetDetail.vue'),
          meta: { title: '核算单详情', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/labor-rates',
          name: 'CostLaborRates',
          component: () => import('../views/cost-accounting/LaborRateConfig.vue'),
          meta: { title: '工时费率', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/overhead-rules',
          name: 'CostOverheadRules',
          component: () => import('../views/cost-accounting/OverheadRuleConfig.vue'),
          meta: { title: '分摊规则', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/periods',
          name: 'CostPeriods',
          component: () => import('../views/cost-accounting/CostPeriodManage.vue'),
          meta: { title: '核算期间', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/overview',
          name: 'CostOverview',
          component: () => import('../views/cost-accounting/CostOverview.vue'),
          meta: { title: '成本概览', menu: 'cost-accounting' },
        },
        {
          path: 'cost-accounting/analysis',
          name: 'CostAnalysis',
          component: () => import('../views/cost-accounting/CostAnalysisView.vue'),
          meta: { title: '成本分析', menu: 'cost-accounting' },
        },
        // D1 — BI 分析看板
        {
          path: 'bi/planning',
          name: 'BiPlanning',
          component: () => import('../views/bi/PlanningAnalytics.vue'),
          meta: { title: 'BI研发规划分析', menu: 'bi' },
        },
        {
          path: 'bi/cost',
          name: 'BiCost',
          component: () => import('../views/bi/CostAnalytics.vue'),
          meta: { title: 'BI成本分析', menu: 'bi' },
        },
        {
          path: 'bi',
          name: 'BiAnalytics',
          component: () => import('../views/bi/BIAnalyticsView.vue'),
          meta: { title: 'BI分析仪表盘', menu: 'bi' },
        },
        // D4-3 复盘看板
        {
          path: 'review/dashboard',
          name: 'ReviewDashboard',
          component: () => import('../views/review/ReviewDashboard.vue'),
          meta: { title: '复盘看板', menu: 'product-plans' },
        },

        // P2-T5 — 规则管理
        {
          path: 'cert/rules',
          name: 'CertRules',
          component: () => import('../views/cert/CertRulesView.vue'),
          meta: { title: '变更影响规则', menu: 'cert-rules' },
        },
        // P1-T5 前端事件监控面板
        {
          path: 'monitor/events',
          name: 'EventMonitor',
          component: () => import('../views/monitor/EventMonitorView.vue'),
          meta: { title: '事件监控面板', menu: 'event-monitor' },
        },
        // P2 需求录入
        {
          path: 'pm/requirements/submit',
          name: 'RequirementSubmit',
          component: () => import('../views/pm/RequirementSubmit.vue'),
          meta: { title: '需求录入', menu: 'pm-requirements' },
        },
        {
          path: 'pm/requirements',
          name: 'RequirementList',
          component: () => import('../views/pm/RequirementList.vue'),
          meta: { title: '需求管理', menu: 'pm-requirements' },
        },
        // D5-5 移动端 Tab 导航目标路由（占位）
        {
          path: 'notifications',
          name: 'Notifications',
          component: () => import('../views/notifications/NotificationsView.vue'),
          meta: { title: '通知中心' },
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('../views/profile/ProfileView.vue'),
          meta: { title: '个人中心' },
        },
        // 标准知识库
        {
          path: 'standards',
          name: 'Standards',
          component: () => import('../views/standards/StandardsView.vue'),
          meta: { title: '标准知识库' },
        },
        {
          path: 'standards/:id',
          name: 'StandardDetail',
          component: () => import('../views/standards/StandardDetail.vue'),
          meta: { title: '标准详情' },
        },
        {
          path: 'admin/standards',
          name: 'StandardManage',
          component: () => import('../views/admin/StandardManage.vue'),
          meta: { title: '标准配置', roles: ['admin'] },
        },
        // 知识库
        {
          path: 'knowledge',
          name: 'KnowledgeView',
          component: () => import('../views/knowledge/KnowledgeView.vue'),
          meta: { title: '知识库' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('token')
  const isPublic = to.meta.public === true
  if (!token) {
    if (isPublic) return next()
    return next('/login')
  }
  if (isPublic) return next()
  const authStore = useAuthStore()
  try {
    if (!authStore.user) await authStore.fetchUser()
  } catch {
    ElMessage.error('会话验证失败，请重新登录')
    authStore.logout()
    return next('/login')
  }
  if (!authStore.hasRouteAccess(to.path)) {
    // 防止死循环：如果目标就是 /dashboard 但无权限，说明权限数据异常
    if (to.path === '/dashboard') {
      ElMessage.error('账户权限数据异常，请重新登录')
      authStore.logout()
      return next('/login')
    }
    ElMessage.warning('没有访问该页面的权限，已跳转到驾驶舱')
    return next('/dashboard')
  }
  next()
})

export default router
