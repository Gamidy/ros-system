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
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/register/RegisterView.vue'),
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
          path: 'pm-workspace-test',
          name: 'PMWorkspaceTest',
          component: () => import('../views/pm/TestView.vue'),
          meta: { title: '测试页', menu: 'pm-workspace' },
        },
        {
          path: 'pm-workspace',
          name: 'PMWorkspace',
          component: () => import('../views/pm/PMWorkspace.vue'),
          meta: { title: '工作台', menu: 'pm-workspace' },
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
  const isPublic = to.name === 'Login' || to.name === 'Register'

  // 1. 未登录 → 公开页放行，其他跳登录
  if (!token) {
    if (isPublic) return next()
    return next('/login')
  }

  // 2. 已登录 → 公开页直接放行
  if (isPublic) return next()

  // 3. 已登录且有 token → 确保用户信息已加载，进行角色路由权限检查
  const authStore = useAuthStore()

  try {
    // 如果用户信息尚未加载，先获取
    if (!authStore.user) {
      await authStore.fetchUser()
    }
  } catch {
    // 获取用户信息失败（如 token 过期），清空并跳转登录
    authStore.logout()
    return next('/login')
  }

  // 4. 角色路由权限检查
  if (!authStore.hasRouteAccess(to.path)) {
    ElMessage.warning('没有访问该页面的权限，已跳转到驾驶舱')
    return next('/dashboard')
  }

  next()
})

export default router
