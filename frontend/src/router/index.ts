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
          path: 'tests/target-markets',
          name: 'TargetMarkets',
          component: () => import('../views/tests/TargetMarketView.vue'),
          meta: { title: '目标市场配置', menu: 'tests' },
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
          component: () => import('../views/certifications/CertificationsView.vue'),
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
          component: () => import('../views/changes/ChangesView.vue'),
          meta: { title: '变更管理' },
        },
        {
          path: 'approvals',
          name: 'Approvals',
          component: () => import('../views/approvals/ApprovalsView.vue'),
          meta: { title: '审批管理' },
        },
        {
          path: 'approvals/proposals',
          name: 'ProposalApprovals',
          component: () => import('../views/approvals/ProposalApprovals.vue'),
          meta: { title: '产品立项审批' },
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
          path: 'pm-workspace-test',
          name: 'PMWorkspaceTest',
          component: () => import('../views/pm/TestView.vue'),
          meta: { title: '测试页', menu: 'pm-workspace' },
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
