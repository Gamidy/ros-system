import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WSMessage } from '../utils/websocket'

export interface NotificationItem {
  id: string
  type: 'approval' | 'alert' | 'notification' | 'system'
  title: string
  content: string
  read: boolean
  timestamp: string
  data?: unknown
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<NotificationItem[]>([])
  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  function addNotification(item: Omit<NotificationItem, 'id'>) {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    notifications.value.unshift({ ...item, id })
    // 最多保留 200 条
    if (notifications.value.length > 200) {
      notifications.value = notifications.value.slice(0, 200)
    }
  }

  function markRead(id: string) {
    const n = notifications.value.find((x) => x.id === id)
    if (n) n.read = true
  }

  function markAllRead() {
    notifications.value.forEach((n) => (n.read = true))
  }

  function removeNotification(id: string) {
    const idx = notifications.value.findIndex((x) => x.id === id)
    if (idx !== -1) notifications.value.splice(idx, 1)
  }

  function clearAll() {
    notifications.value = []
  }

  /**
   * 从 WebSocket 消息创建通知
   */
  function handleWSMessage(msg: WSMessage) {
    const payload = msg.payload as Record<string,unknown>
    let title = '新消息'
    let content = ''

    switch (msg.type) {
      case 'approval':
        title = payload?.title || '待审批提醒'
        content = payload?.content || '您有新的审批请求需要处理'
        break
      case 'alert':
        title = payload?.title || '系统预警'
        content = payload?.content || '检测到异常状态'
        break
      case 'notification':
        title = payload?.title || '通知'
        content = payload?.content || ''
        break
      case 'system':
        title = payload?.title || '系统消息'
        content = payload?.content || ''
        break
    }

    addNotification({
      type: msg.type,
      title,
      content,
      read: false,
      timestamp: msg.timestamp || new Date().toISOString(),
      data: payload,
    })
  }

  return {
    notifications,
    unreadCount,
    addNotification,
    markRead,
    markAllRead,
    removeNotification,
    clearAll,
    handleWSMessage,
  }
})
