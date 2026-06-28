<template>
  <transition name="notif-slide-up">
    <div
      v-if="visible"
      class="mobile-notification-bar"
      @click="handleClick"
    >
      <div class="notif-bar-content">
        <span class="notif-bar-icon">🔔</span>
        <span class="notif-bar-text">{{ barText }}</span>
      </div>
      <button
        class="notif-bar-close"
        @click.stop="handleDismiss"
      >
        ✕
      </button>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../../stores/notification'
import { wsManager } from '../../utils/websocket'
import type { WSMessage } from '../../utils/websocket'

const props = defineProps<{
  /** 是否在移动端视图下显示 */
  isMobile: boolean
}>()

const router = useRouter()
const notifStore = useNotificationStore()

// ── 状态 ──
const visible = ref(false)
/** 聚合计数：从上一次清除以来收到了多少条新消息 */
const aggregateCount = ref(0)
/** 最新消息的 action 路由 */
const lastAction = ref<string | null>(null)
/** 聚合定时器 handle */
let aggregationTimer: ReturnType<typeof setTimeout> | null = null
/** 自动消失定时器 */
let autoHideTimer: ReturnType<typeof setTimeout> | null = null

// ── 通知类型 → 跳转 action 路由 ──
function resolveAction(msg: WSMessage): string {
  if (msg.action) return msg.action
  // 没有 action 字段时按类型推断
  switch (msg.type) {
    case 'approval':
      return '/approvals'
    case 'notification':
    case 'review':
      return '/product-plans'
    default:
      return '/notifications'
  }
}

// ── 聚合通知文本 ──
const barText = computed(() => {
  if (aggregateCount.value <= 1) {
    return '收到 1 条新消息'
  }
  return `收到 ${aggregateCount.value} 条新消息`
})

// ── WebSocket 监听 ──
import { onMounted, onUnmounted } from 'vue'

let unsubApproval: (() => void) | null = null
let unsubNotification: (() => void) | null = null
let unsubReview: (() => void) | null = null
let unsubAlert: (() => void) | null = null
let unsubRead: (() => void) | null = null

function showBar() {
  visible.value = true
  // 重置自动消失定时器（5秒后自动隐藏）
  if (autoHideTimer) clearTimeout(autoHideTimer)
  autoHideTimer = setTimeout(() => {
    visible.value = false
  }, 5000)
}

function onNotification(msg: WSMessage) {
  if (!props.isMobile) return

  // 通知 store 处理
  notifStore.handleWSMessage(msg)

  // 聚合逻辑
  const action = resolveAction(msg)
  lastAction.value = action
  aggregateCount.value++
  notifStore.incrementPendingCount()

  // 如果已在显示中，用聚合计数
  // 如果未显示，立即显示
  if (!visible.value) {
    showBar()
  }

  // 重置消失定时器
  if (autoHideTimer) clearTimeout(autoHideTimer)
  autoHideTimer = setTimeout(() => {
    visible.value = false
  }, 5000)
}

function onReadStatus(msg: WSMessage) {
  if (msg.type === 'notification_read') {
    notifStore.handleReadStatus(msg)
  }
}

function handleClick() {
  if (lastAction.value) {
    router.push(lastAction.value)
  }
  visible.value = false
  // 点击跳转后 → 全部标记为已读
  aggregateCount.value = 0
  notifStore.resetPendingCount()
}

function handleDismiss() {
  visible.value = false
  aggregateCount.value = 0
  notifStore.resetPendingCount()
}

onMounted(() => {
  // 订阅所有通知类型的 WebSocket 消息
  unsubApproval = wsManager.on('approval', onNotification)
  unsubNotification = wsManager.on('notification', onNotification)
  unsubReview = wsManager.on('review', onNotification)
  unsubAlert = wsManager.on('alert', (msg) => {
    // alert 类型也显示通知条
    notifStore.handleWSMessage(msg)
  })
  unsubRead = wsManager.on('notification_read', onReadStatus)
})

onUnmounted(() => {
  unsubApproval?.()
  unsubNotification?.()
  unsubReview?.()
  unsubAlert?.()
  unsubRead?.()
  if (aggregationTimer) clearTimeout(aggregationTimer)
  if (autoHideTimer) clearTimeout(autoHideTimer)
})
</script>

<style scoped>
.mobile-notification-bar {
  position: fixed;
  bottom: 64px; /* 在 MobileTabBar 上方 */
  left: 12px;
  right: 12px;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--c-accent, #409eff);
  color: white;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: background 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.mobile-notification-bar:active {
  background: var(--c-accent-dark, #337ecc);
}

.notif-bar-content {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.notif-bar-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.notif-bar-text {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notif-bar-close {
  width: 24px;
  height: 24px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 50%;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s ease;
}

.notif-bar-close:active {
  background: rgba(255, 255, 255, 0.35);
}

/* ── Transition ── */
.notif-slide-up-enter-active {
  transition: all 0.3s ease-out;
}
.notif-slide-up-leave-active {
  transition: all 0.2s ease-in;
}
.notif-slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.notif-slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
