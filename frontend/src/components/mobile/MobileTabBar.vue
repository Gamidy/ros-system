<template>
  <nav class="mobile-tab-bar">
    <router-link
      v-for="tab in tabs"
      :key="tab.route"
      :to="tab.route"
      class="tab-item"
      :class="{ active: isActive(tab.route) }"
    >
      <div class="tab-icon-wrapper">
        <span class="tab-icon">{{ tab.icon }}</span>
        <el-badge
          v-if="tab.badgeKey"
          :value="badgeCount"
          :hidden="badgeCount === 0"
          class="tab-badge"
        />
      </div>
      <span class="tab-label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useNotificationStore } from '../../stores/notification'

interface TabItem {
  label: string
  icon: string
  route: string
  /** Key to look up badge count; only 'notifications' is supported */
  badgeKey?: 'notifications'
}

const route = useRoute()
const notifStore = useNotificationStore()

const tabs: TabItem[] = [
  { label: '首页', icon: '🏠', route: '/dashboard' },
  { label: '策划', icon: '📋', route: '/product-plans' },
  { label: '审批', icon: '✅', route: '/approvals' },
  { label: '通知', icon: '🔔', route: '/notifications', badgeKey: 'notifications' },
  { label: '我的', icon: '👤', route: '/profile' },
]

const badgeCount = computed<number>(() => notifStore.unreadCount)

function isActive(tabRoute: string): boolean {
  return route.path === tabRoute || route.path.startsWith(tabRoute + '/')
}
</script>

<style scoped>
.mobile-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: 56px;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  background: var(--c-bg-card, #ffffff);
  border-top: 1px solid var(--c-border, #e5e5e5);
  z-index: 1000;
  box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.06);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  text-decoration: none;
  color: var(--c-text-tertiary, #999);
  transition: color 0.2s ease;
  position: relative;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.tab-item.active {
  color: var(--c-accent, #409eff);
}

.tab-item:active {
  opacity: 0.7;
}

.tab-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.tab-icon {
  font-size: 20px;
  line-height: 1;
}

.tab-badge {
  position: absolute;
  top: -2px;
  right: -6px;
}

.tab-badge :deep(.el-badge__content) {
  border-radius: 10px;
  font-weight: 600;
  font-size: 10px;
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
  border: 2px solid var(--c-bg-card, #ffffff);
  background: var(--c-danger, #f56c6c);
}

.tab-label {
  font-size: 10px;
  line-height: 1;
  margin-top: 2px;
}
</style>
