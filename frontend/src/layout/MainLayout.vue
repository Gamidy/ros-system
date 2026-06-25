<template>
  <div class="claude-layout">
    <!-- Sidebar Overlay (mobile only) -->
    <div class="sidebar-overlay" v-if="mobileOpen" @click="mobileOpen = false"></div>
    
    <!-- Sidebar -->
    <aside class="claude-sidebar" :class="{ collapsed: isCollapse, 'mobile-open': mobileOpen }">
      <div class="sidebar-brand" @click="router.push('/dashboard')">
        <div class="brand-mark">
          <span class="brand-icon">R</span>
        </div>
        <span class="brand-text" v-show="!isCollapse || mobileOpen">ROS</span>
      </div>
      
      <nav class="sidebar-nav">
        <el-menu
          :default-active="route.path"
          :collapse="isCollapse"
          router
          class="sidebar-el-menu"
          @select="mobileOpen = false"
        >
          <template v-for="group in authStore.visibleGroups" :key="group.title">
            <el-sub-menu :index="group.title">
              <template #title>
                <el-icon><component :is="group.icon" /></el-icon>
                <span>{{ group.title }}</span>
              </template>
              <el-menu-item
                v-for="item in group.children"
                :key="item.path"
                :index="item.path"
              >
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </nav>
    </aside>

    <!-- Main Content -->
    <div class="claude-main" :class="{ 'menu-open': mobileOpen }">
      <!-- Header -->
      <header class="claude-header">
        <div class="header-left">
          <!-- Desktop collapse button -->
          <button class="collapse-btn desktop-only" @click="isCollapse = !isCollapse">
            <el-icon :size="18">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </button>
          <!-- Mobile hamburger button -->
          <button class="mobile-menu-btn mobile-only" @click="toggleMobileSidebar">
            <el-icon :size="20">
              <Fold v-if="mobileOpen" />
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isCollapse = ref(false)
const pendingApprovalCount = ref(0)

// ── Mobile responsive state ──
const isMobile = ref(window.innerWidth < 768)
const mobileOpen = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    mobileOpen.value = false
  }
}

function toggleMobileSidebar() {
  mobileOpen.value = !mobileOpen.value
}

onMounted(async () => {
  window.addEventListener('resize', checkMobile)
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

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const userInitial = computed(() => {
  const name = authStore.user?.username || 'U'
  return name.charAt(0).toUpperCase()
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
  overflow-y: auto;
  padding: 4px 0;
}

/* ── el-menu overrides for sidebar ── */
.sidebar-el-menu {
  border-right: none !important;
  background: transparent !important;
}
.sidebar-el-menu:not(.el-menu--collapse) {
  width: 240px;
}
/* sub-menu title styling */
.sidebar-el-menu .el-sub-menu__title {
  color: var(--c-text-secondary-dark) !important;
  font-size: 13px;
  font-weight: 600;
  height: 44px;
  line-height: 44px;
  padding: 0 16px !important;
  background: transparent !important;
  border-bottom: none !important;
  transition: background var(--c-transition-fast);
}
.sidebar-el-menu .el-sub-menu__title:hover {
  background: var(--c-bg-sidebar-hover) !important;
  color: var(--c-text-primary-dark) !important;
}
/* sub-menu arrow icon */
.sidebar-el-menu .el-sub-menu__title .el-icon {
  color: var(--c-text-secondary-dark);
}
/* menu items inside sub-menus */
.sidebar-el-menu .el-menu-item {
  color: var(--c-text-secondary-dark) !important;
  font-size: 13px;
  height: 40px;
  line-height: 40px;
  padding: 0 16px 0 48px !important;
  background: transparent !important;
  border-radius: 0;
  transition: background var(--c-transition-fast);
}
.sidebar-el-menu .el-menu-item:hover {
  background: var(--c-bg-sidebar-hover) !important;
  color: var(--c-text-primary-dark) !important;
}
.sidebar-el-menu .el-menu-item.is-active {
  color: white !important;
  background: var(--c-bg-sidebar-active) !important;
}
.sidebar-el-menu .el-menu-item .el-icon {
  color: inherit;
  font-size: 16px;
}
/* collapse mode */
.sidebar-el-menu.el-menu--collapse .el-sub-menu__title {
  padding: 0 14px !important;
  justify-content: center;
}
.sidebar-el-menu.el-menu--collapse .el-sub-menu__title span {
  display: none;
}
/* remove default popup offset in collapse mode */
.el-menu--collapse .el-menu .el-sub-menu,
.el-menu--collapse .el-menu .el-menu-item {
  min-width: 200px;
}
/* no extra dividers / borders */
.sidebar-el-menu .el-menu-item,
.sidebar-el-menu .el-sub-menu {
  border-bottom: none !important;
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

/* ── Sidebar Overlay (mobile) ── */
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  z-index: var(--c-z-modal);
  display: none;
}

/* ── Desktop/Mobile visibility ── */
@media (min-width: 769px) {
  .mobile-only { display: none !important; }
}
@media (max-width: 768px) {
  .desktop-only { display: none !important; }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .sidebar-overlay {
    display: block;
  }
  
  .claude-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: calc(var(--c-z-modal) + 1);
    height: 100vh;
    transform: translateX(-100%);
    width: 280px;
    transition: transform 0.3s ease;
  }
  .claude-sidebar.mobile-open {
    transform: translateX(0);
  }
  /* On mobile, collapsed state doesn't apply (use mobile-open instead) */
  .claude-sidebar.collapsed.mobile-open {
    width: 280px;
  }
  
  .claude-main {
    margin-left: 0;
    width: 100%;
  }
  
  .claude-content {
    padding: 12px;
  }
  
  .user-name {
    display: none;
  }
  
  /* Mobile menu button - always visible on mobile */
  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--c-radius-sm);
    border: none;
    background: transparent;
    color: var(--c-text-tertiary);
    cursor: pointer;
    transition: all var(--c-transition-fast);
  }
  .mobile-menu-btn:hover {
    background: var(--c-bg-hover);
    color: var(--c-text-primary);
  }
  
  /* Breadcrumb text smaller on mobile */
  .breadcrumb {
    font-size: 13px;
  }
  .breadcrumb-current {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* Tiny screens (≤400px) - even tighter */
@media (max-width: 400px) {
  .claude-content {
    padding: 8px;
  }
  .header-right {
    gap: 4px;
  }
}
</style>
