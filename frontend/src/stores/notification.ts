import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WSMessage } from '../utils/websocket'

export interface NotificationItem {
  id: string
  type: 'approval' | 'alert' | 'notification' | 'system' | 'review'
  title: string
  content: string
  read: boolean
  timestamp: string
  data?: unknown
  /** 前端路由 action，用于移动端通知条点击跳转 */
  action?: string
}

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<NotificationItem[]>([])
  const unreadCount = computed(() => notifications.value.filter((n) => !n.read).length)

  /** 最新未读通知的 action 路由（用于移动端通知条跳转） */
  const latestUnreadAction = computed<string | null>(() => {
    const unread = notifications.value.filter((n) => !n.read && n.action)
    if (unread.length === 0) return null
    // 返回最新的未读通知 action
    return unread[0].action ?? null
  })

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

  /** 聚合计数：从上一次清除以来收到了多少条新消息 */
  const pendingNotificationCount = ref(0)

  function incrementPendingCount(amount: number = 1) {
    pendingNotificationCount.value += amount
  }

  function resetPendingCount() {
    pendingNotificationCount.value = 0
  }

  /**
   * 从 WebSocket 消息创建通知
   */
  function handleWSMessage(msg: WSMessage) {
    const payload = msg.payload as Record<string, unknown> | undefined
    let title = '新消息'
    let content = ''

    function strVal(obj: Record<string, unknown> | undefined, key: string, fallback: string): string {
      const val = obj?.[key]
      return typeof val === 'string' ? val : fallback
    }

    switch (msg.type) {
      case 'approval':
        title = strVal(payload, 'title', '待审批提醒')
        content = strVal(payload, 'content', '您有新的审批请求需要处理')
        break
      case 'alert':
        title = strVal(payload, 'title', '系统预警')
        content = strVal(payload, 'content', '检测到异常状态')
        break
      case 'notification':
        title = strVal(payload, 'title', '通知')
        content = strVal(payload, 'content', strVal(payload, 'stage', '策划阶段有更新'))
        break
      case 'review':
        title = strVal(payload, 'title', '评审通知')
        content = strVal(payload, 'content', '有新的评审事项')
        break
      case 'system':
        title = strVal(payload, 'title', '系统消息')
        content = strVal(payload, 'content', '')
        break
    }

    const action = msg.action ?? ''

    addNotification({
      type: msg.type === 'review' ? 'review' : (msg.type as 'approval' | 'alert' | 'notification' | 'system'),
      title,
      content,
      read: false,
      timestamp: msg.timestamp || new Date().toISOString(),
      data: payload,
      action,
    })
  }

  /** 处理 notification_read 消息 — 已读状态同步 */
  function handleReadStatus(msg: WSMessage) {
    const payload = msg.payload as Record<string, unknown> | undefined
    const notificationId = payload?.notification_id
    if (typeof notificationId === 'string') {
      markRead(notificationId)
    }
  }

  return {
    notifications,
    unreadCount,
    latestUnreadAction,
    pendingNotificationCount,
    addNotification,
    markRead,
    markAllRead,
    removeNotification,
    clearAll,
    incrementPendingCount,
    resetPendingCount,
    handleWSMessage,
    handleReadStatus,
  }
})
