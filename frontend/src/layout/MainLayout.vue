<template>
  <div class="claude-layout">
    <!-- Sidebar -->
    <aside class="claude-sidebar" :class="{ collapsed: isCollapse }">
      <div class="sidebar-brand" @click="router.push('/dashboard')">
        <div class="brand-mark">
          <span class="brand-icon">R</span>
        </div>
        <span class="brand-text" v-show="!isCollapse">ROS</span>
      </div>
      
      <nav class="sidebar-nav">
        <router-link
          v-for="menu in authStore.visibleMenus"
          :key="menu.path"
          :to="menu.path"
          class="nav-item"
          :class="{ active: route.path === menu.path }"
        >
          <el-badge v-if="menu.path.includes('approval') && pendingApprovalCount > 0" 
            :value="pendingApprovalCount" :max="99" class="nav-badge">
            <el-icon class="nav-icon">
              <component :is="menu.icon" />
            </el-icon>
          </el-badge>
          <el-icon v-else class="nav-icon">
            <component :is="menu.icon" />
          </el-icon>
          <span class="nav-label" v-show="!isCollapse">{{ menu.title }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Main Content -->
    <div class="claude-main">
      <!-- Header -->
      <header class="claude-header">
        <div class="header-left">
          <button class="collapse-btn" @click="isCollapse = !isCollapse">
            <el-icon :size="18">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </button>
          <div class="breadcrumb">
            <router-link to="/dashboard" class="breadcrumb-link">首页</router-link>
            <span v-if="route.meta.title" class="breadcrumb-separator">/</span>
            <span v-if="route.meta.title" class="breadcrumb-current">{{ route.meta.title }}</span>
          </div>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" placement="bottom-end">
            <button class="user-btn">
              <div class="user-avatar">{{ userInitial }}</div>
              <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
              <el-icon :size="14"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu class="claude-dropdown">
                <el-dropdown-item @click="handleLogout" class="dropdown-item-logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Content Area -->
      <main class="claude-content">
        <router-view v-slot="{ Component }">
          <transition name="claude-page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isCollapse = ref(false)
const pendingApprovalCount = ref(0)

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

onMounted(async () => {
  if (!authStore.user) {
    try {
      await authStore.init()
    } catch {
      handleLogout()
      return
    }
  }
  try {
    const res = await api.get('/dashboard/summary')
    pendingApprovalCount.value = res.data?.layer2_project_ops?.pending_approvals_count || 0
  } catch {
    // Silently ignore
  }
})

function handleLogout() {
  authStore.logout()
  ElMessage.info('已退出')
  router.push('/login')
}
</script>

<style scoped>
.claude-layout {
  display: flex;
  height: 100vh;
  background: var(--c-bg-page);
}

/* Sidebar */
.claude-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--c-bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width var(--c-transition-base);
  overflow: hidden;
}
.claude-sidebar.collapsed {
  width: 64px;
}

.sidebar-brand {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  transition: background var(--c-transition-fast);
}
.sidebar-brand:hover {
  background: var(--c-bg-sidebar-hover);
}
.collapsed .sidebar-brand {
  padding: 0;
  justify-content: center;
}

.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: var(--c-radius-sm);
  background: var(--c-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-icon {
  color: white;
  font-weight: 700;
  font-size: 14px;
}
.brand-text {
  color: white;
  font-weight: 600;
  font-size: 18px;
  letter-spacing: -0.5px;
}

/* Sidebar Navigation */
.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--c-radius-sm);
  color: var(--c-text-secondary-dark);
  text-decoration: none;
  transition: all var(--c-transition-fast);
  position: relative;
  font-size: 14px;
  font-weight: 500;
}
.nav-item:hover {
  background: var(--c-bg-sidebar-hover);
  color: var(--c-text-primary-dark);
}
.nav-item.active {
  background: var(--c-bg-sidebar-active);
  color: white;
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--c-accent);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.collapsed .nav-item {
  padding: 10px;
  justify-content: center;
}
.collapsed .nav-item.active::before {
  display: none;
}

.nav-badge :deep(.el-badge__content) {
  background: var(--c-danger) !important;
  border: none !important;
  font-size: 10px;
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
  font-weight: 600;
}

/* Main Content Area */
.claude-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* Header */
.claude-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--c-bg-card);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
  z-index: var(--c-z-sticky);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--c-radius-sm);
  border: none;
  background: transparent;
  color: var(--c-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--c-transition-fast);
}
.collapse-btn:hover {
  background: var(--c-bg-hover);
  color: var(--c-text-primary);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.breadcrumb-link {
  color: var(--c-text-tertiary);
  text-decoration: none;
  transition: color var(--c-transition-fast);
}
.breadcrumb-link:hover {
  color: var(--c-accent);
}
.breadcrumb-separator {
  color: var(--c-text-muted);
  font-weight: 300;
}
.breadcrumb-current {
  color: var(--c-text-primary);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-divider {
  width: 1px;
  height: 24px;
  background: var(--c-border);
  margin: 0 4px;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: var(--c-radius-md);
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all var(--c-transition-fast);
  color: var(--c-text-primary);
}
.user-btn:hover {
  background: var(--c-bg-hover);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--c-radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

/* Content */
.claude-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--c-bg-page);
}

/* Page Transition */
.claude-page-enter-active,
.claude-page-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.claude-page-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.claude-page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Dropdown Styling */
:deep(.claude-dropdown) {
  border-radius: var(--c-radius-md);
  box-shadow: var(--c-shadow-lg);
  border: 1px solid var(--c-border);
  padding: 4px;
}
:deep(.dropdown-item-logout) {
  border-radius: var(--c-radius-sm);
  padding: 8px 12px;
  font-size: 14px;
  color: var(--c-danger);
  transition: background var(--c-transition-fast);
}
:deep(.dropdown-item-logout:hover) {
  background: var(--c-danger-light);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .claude-sidebar {
    position: fixed;
    z-index: var(--c-z-modal);
    height: 100vh;
    transform: translateX(-100%);
  }
  .claude-sidebar:not(.collapsed) {
    transform: translateX(0);
  }
  .claude-main {
    margin-left: 0;
  }
  .claude-content {
    padding: 16px;
  }
  .user-name {
    display: none;
  }
}
</style>
