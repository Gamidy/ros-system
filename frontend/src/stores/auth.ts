import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'
import { type RoleName, ROLE_LABELS, ALL_MENUS, MENU_GROUPS, type MenuItem, type MenuGroup } from '../types/roles'

interface User {
  id: number
  username: string
  full_name: string | null
  email: string | null
  role: string
  department: string | null
  is_active: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem('token') || '')
  const loading = ref(false)

  // ── 角色相关状态 ──────────────────────────────

  /** 服务端下发的允许路由路径集合（来自 /api/auth/me 的 allowed_paths） */
  const allowedPaths = ref<Set<string>>(new Set())

  /** 当前用户的角色名（带类型守卫） */
  const roleName = computed<RoleName | null>(() => {
    if (!user.value?.role) return null
    // 通过 ROLE_LABELS 校验角色合法性，不再依赖前端硬编码的 ROLE_ROUTES
    const r = user.value.role as RoleName
    return ROLE_LABELS[r] ? r : 'engineer'
  })

  /** 角色中文名称 */
  const roleLabel = computed(() => {
    if (!roleName.value) return ''
    return ROLE_LABELS[roleName.value] || roleName.value
  })

  /** 当前用户可见的侧边栏菜单项（基于服务端下发的 allowedPaths） */
  const visibleMenus = computed<MenuItem[]>(() => {
    const paths = allowedPaths.value
    return ALL_MENUS.filter(m => paths.has(m.path))
  })

  /** 按分组筛选的侧边栏菜单（基于服务端下发的 allowedPaths） */
  const visibleGroups = computed<MenuGroup[]>(() => {
    const paths = allowedPaths.value
    return MENU_GROUPS.map(group => ({
      ...group,
      children: group.children.filter(m => paths.has(m.path))
    })).filter(g => g.children.length > 0)
  })

  /** 检查某个路由路径是否有权限访问（公开页面 /login、/register 始终放行） */
  function hasRouteAccess(path: string): boolean {
    // 公开页面不拦
    if (path === '/login' || path === '/register') return true
    // 未登录或未获取到权限数据则拦截
    if (!user.value || allowedPaths.value.size === 0) return false
    // 精确匹配
    if (allowedPaths.value.has(path)) return true
    // 前缀匹配：/product-plans/xxx → 有 /product-plans 权限即可
    for (const allowed of allowedPaths.value) {
      if (path.startsWith(allowed + '/') || path.startsWith(allowed + '?')) return true
    }
    return false
  }

  // ── 原有认证逻辑 ──────────────────────────────────

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await api.post('/auth/login', { username, password })
      token.value = res.data.access_token
      localStorage.setItem('token', token.value)
      await fetchUser()
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    const res = await api.get('/auth/me')
    user.value = res.data
    // 从服务端响应中提取 allowed_paths 并存入本地状态
    if (res.data.allowed_paths && Array.isArray(res.data.allowed_paths)) {
      allowedPaths.value = new Set(res.data.allowed_paths)
    }
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch {
      // 即使请求失败也清理本地状态
    }
    token.value = ''
    user.value = null
    allowedPaths.value = new Set()
    localStorage.removeItem('token')
  }

  async function init() {
    if (token.value) {
      try {
        await fetchUser()
      } catch {
        logout()
      }
    }
  }

  return {
    user, token, loading,
    roleName, roleLabel,
    allowedPaths, visibleMenus, visibleGroups,
    hasRouteAccess,
    login, logout, init, fetchUser,
  }
})
