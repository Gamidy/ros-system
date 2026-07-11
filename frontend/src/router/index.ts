import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      component: () => import('../layout/AppLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', name: 'Dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '驾驶舱' } },
        { path: 'platforms', name: 'Platforms', component: () => import('../views/PlatformList.vue'), meta: { title: '产品平台' } },
        { path: 'series', name: 'Series', component: () => import('../views/SeriesList.vue'), meta: { title: '产品系列' } },
        { path: 'models', name: 'Models', component: () => import('../views/ModelList.vue'), meta: { title: '产品型号' } },
        { path: 'materials', name: 'Materials', component: () => import('../views/MaterialList.vue'), meta: { title: '物料管理' } },
        { path: 'bom', name: 'BOM', component: () => import('../views/BOMView.vue'), meta: { title: 'BOM管理' } },
        { path: 'projects', name: 'Projects', component: () => import('../views/ProjectList.vue'), meta: { title: '项目管理' } },
        { path: 'projects/:id', name: 'ProjectDetail', component: () => import('../views/ProjectDetail.vue'), meta: { title: '项目详情' } },
        { path: 'ecr', name: 'ECR', component: () => import('../views/EcrView.vue'), meta: { title: 'ECR变更申请' } },
        { path: 'eco', name: 'ECO', component: () => import('../views/EcoView.vue'), meta: { title: 'ECO变更指令' } }
      ]
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) return next()
  if (!token) return next('/login')
  next()
})

export default router
