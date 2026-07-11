import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台', icon: 'HomeFilled' }
      },
      {
        path: 'materials',
        name: 'Materials',
        component: () => import('@/views/materials/MaterialList.vue'),
        meta: { title: '物料管理', icon: 'Box' }
      },
      {
        path: 'materials/:id',
        name: 'MaterialDetail',
        component: () => import('@/views/materials/MaterialDetail.vue'),
        meta: { title: '物料详情', hidden: true }
      },
      {
        path: 'boms',
        name: 'BOMs',
        component: () => import('@/views/boms/BOMList.vue'),
        meta: { title: 'BOM管理', icon: 'Connection' }
      },
      {
        path: 'boms/:id',
        name: 'BOMDetail',
        component: () => import('@/views/boms/BOMDetail.vue'),
        meta: { title: 'BOM详情', hidden: true }
      },
      {
        path: 'changes',
        name: 'Changes',
        component: () => import('@/views/changes/ChangeList.vue'),
        meta: { title: '变更管理', icon: 'Switch' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/projects/ProjectList.vue'),
        meta: { title: '项目管理', icon: 'Project' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/ProjectDetail.vue'),
        meta: { title: '项目详情', hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (!to.meta.public && !userStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
