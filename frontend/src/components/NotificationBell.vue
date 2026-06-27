<template>
  <div class="notification-bell">
    <el-popover
      v-model:visible="visible"
      placement="bottom-end"
      :width="360"
      trigger="click"
      popper-class="notification-popover"
    >
      <template #reference>
        <div class="bell-wrapper" @click="visible = !visible">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="bell-badge">
            <el-icon :size="22"><Bell /></el-icon>
          </el-badge>
        </div>
      </template>

      <div class="notification-panel">
        <div class="panel-header">
          <span class="panel-title">通知消息</span>
          <div class="panel-actions">
            <el-button
              v-if="unreadCount > 0"
              link
              type="primary"
              size="small"
              @click="markAllRead"
            >
              全部已读
            </el-button>
            <el-button link type="info" size="small" @click="clearAll">
              清空
            </el-button>
          </div>
        </div>

        <div class="panel-list">
          <div
            v-for="item in displayList"
            :key="item.id"
            class="notification-item"
            :class="{ unread: !item.read }"
            @click="markRead(item.id)"
          >
            <div class="item-dot" :class="item.type" />
            <div class="item-content">
              <div class="item-title">{{ item.title }}</div>
              <div class="item-desc">{{ item.content }}</div>
              <div class="item-time">{{ formatTime(item.timestamp) }}</div>
            </div>
            <el-icon class="item-close" @click.stop="removeNotification(item.id)"><Close /></el-icon>
          </div>

          <div v-if="displayList.length === 0" class="empty-state">
            <el-icon :size="40" class="empty-icon"><ChatDotRound /></el-icon>
            <p>暂无新消息</p>
          </div>
        </div>

        <div v-if="notifications.length > maxDisplay" class="panel-footer">
          <el-button link type="primary" size="small">
            查看全部 {{ notifications.length }} 条消息
          </el-button>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useNotificationStore } from '../stores/notification'

const notificationStore = useNotificationStore()
const visible = ref(false)
const maxDisplay = ref(10)

const unreadCount = computed(() => notificationStore.unreadCount)
const notifications = computed(() => notificationStore.notifications)

const displayList = computed(() => {
  return notifications.value.slice(0, maxDisplay.value)
})

function markRead(id: string) {
  notificationStore.markRead(id)
}

function markAllRead() {
  notificationStore.markAllRead()
}

function clearAll() {
  notificationStore.clearAll()
}

function removeNotification(id: string) {
  notificationStore.removeNotification(id)
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.notification-bell {
  display: flex;
  align-items: center;
}
.bell-wrapper {
  cursor: pointer;
  padding: 6px;
  border-radius: var(--c-radius-full);
  transition: background var(--c-transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}
.bell-wrapper:hover {
  background: rgba(0, 0, 0, 0.04);
}
.bell-badge :deep(.el-badge__content) {
  border-radius: var(--c-radius-full);
  font-weight: 600;
  font-size: 10px;
  height: 16px;
  line-height: 16px;
  padding: 0 5px;
  border: 2px solid #fff;
  background: var(--c-danger);
}

/* Panel */
.notification-panel {
  max-height: 420px;
  display: flex;
  flex-direction: column;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--c-border-light);
  flex-shrink: 0;
}
.panel-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--c-text-primary);
}
.panel-actions {
  display: flex;
  gap: 4px;
}
.panel-list {
  overflow-y: auto;
  max-height: 320px;
  padding: 4px 0;
}
.panel-footer {
  padding: 8px 16px;
  border-top: 1px solid var(--c-border-light);
  text-align: center;
  flex-shrink: 0;
}

/* Notification Item */
.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background var(--c-transition-fast);
  position: relative;
}
.notification-item:hover {
  background: rgba(0, 0, 0, 0.03);
}
.notification-item.unread {
  background: rgba(0, 122, 255, 0.04);
}
.notification-item.unread:hover {
  background: rgba(0, 122, 255, 0.08);
}
.item-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.item-dot.approval { background: var(--c-accent); }
.item-dot.alert { background: var(--c-danger); }
.item-dot.notification { background: var(--c-success); }
.item-dot.review { background: var(--c-warning, #e6a23c); }
.item-dot.system { background: var(--c-info); }
.item-content {
  flex: 1;
  min-width: 0;
}
.item-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text-primary);
  line-height: 1.4;
  margin-bottom: 2px;
}
.item-desc {
  font-size: 12px;
  color: var(--c-text-secondary);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-time {
  font-size: 11px;
  color: var(--c-text-tertiary);
  margin-top: 4px;
}
.item-close {
  color: var(--c-text-tertiary);
  opacity: 0;
  transition: opacity var(--c-transition-fast), color var(--c-transition-fast);
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}
.notification-item:hover .item-close {
  opacity: 1;
}
.item-close:hover {
  color: var(--c-danger);
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  color: var(--c-text-tertiary);
  font-size: 13px;
}
.empty-icon {
  color: var(--c-text-muted);
  margin-bottom: 8px;
}
</style>

<style>
.notification-popover {
  background: var(--c-bg-card) !important;
  backdrop-filter: blur(0px) !important;
  -webkit-backdrop-filter: blur(0px) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--c-radius-md) !important;
  box-shadow: var(--c-shadow) !important;
  padding: 0 !important;
}
.notification-popover .el-popover__title {
  display: none;
}
</style>
