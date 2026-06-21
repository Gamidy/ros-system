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
          meta: { title: '实验与测试' },
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
          path: 'admin-config',
          name: 'AdminConfig',
          component: () => import('../views/admin/AdminConfig.vue'),
          meta: { title: '系统设置', menu: 'admin-config' },
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
    authStore.logout()
    return next('/login')
  }
  if (!authStore.hasRouteAccess(to.path)) {
    ElMessage.warning('没有访问该页面的权限，已跳转到驾驶舱')
    return next('/dashboard')
  }
  next()
})

export default router
