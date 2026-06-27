/**
 * WebSocket 连接组合式函数 — 用于接收服务端实时推送消息
 *
 * 用法:
 *   const { connect, on, off, connected } = useWebSocket()
 *   onMounted(() => {
 *     connect()
 *     on('dashboard_refresh', (msg) => { ... })
 *   })
 *   onUnmounted(() => { off('dashboard_refresh', handler) })
 *
 * 消息格式（服务端 → 客户端）:
 *   {
 *     type: string,        // 消息类型：approval | dashboard_refresh | alert | notification | system
 *     payload?: any,       // 消息载荷
 *     timestamp?: string,  // ISO 时间戳
 *   }
 *
 * 心跳:
 *   客户端自动每 30s 发送 { type: 'ping' }
 *   服务端回复 { type: 'pong' }
 */
import { ref, onUnmounted } from 'vue'

export interface WebSocketMessage {
  type: string
  action?: string
  payload?: Record<string, unknown>
  timestamp?: string
  [key: string]: unknown
}

type MessageHandler = (msg: WebSocketMessage) => void
type EventName = string

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const reconnectTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  const pingTimer = ref<ReturnType<typeof setInterval> | null>(null)

  /** 事件监听器 map: type → Set<handler> */
  const listeners = new Map<EventName, Set<MessageHandler>>()

  let manualDisconnect = false
  let reconnectAttempts = 0
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY = 3000
  const PING_INTERVAL = 30000

  // ── 连接管理 ─────────────────────────────

  function connect(): void {
    const token = localStorage.getItem('token')
    if (!token) {
      console.warn('[useWebSocket] 未找到 token，跳过 WebSocket 连接')
      return
    }

    manualDisconnect = false

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws?token=${token}`

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return // 已连接
    }

    try {
      ws.value = new WebSocket(url)
    } catch (err) {
      console.error('[useWebSocket] 创建 WebSocket 失败:', err)
      scheduleReconnect()
      return
    }

    ws.value.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
      console.info('[useWebSocket] 已连接')
      startPing()
    }

    ws.value.onclose = (event) => {
      connected.value = false
      stopPing()
      if (!manualDisconnect) {
        console.info(
          `[useWebSocket] 连接关闭 (code=${event.code})，重连中...`,
        )
        scheduleReconnect()
      }
    }

    ws.value.onerror = () => {
      console.warn('[useWebSocket] 连接错误')
    }

    ws.value.onmessage = (event: MessageEvent) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data)
        const handlers = listeners.get(msg.type)
        if (handlers) {
          handlers.forEach((handler) => {
            try {
              handler(msg)
            } catch (err) {
              console.error(
                `[useWebSocket] handler 异常 (type=${msg.type}):`,
                err,
              )
            }
          })
        }
      } catch {
        // 非 JSON 消息直接忽略
      }
    }
  }

  function disconnect(): void {
    manualDisconnect = true
    stopPing()
    clearReconnect()
    if (ws.value) {
      ws.value.close(1000, 'manual disconnect')
      ws.value = null
    }
    connected.value = false
  }

  // ── 事件监听 ─────────────────────────────

  function on(eventType: EventName, handler: MessageHandler): void {
    if (!listeners.has(eventType)) {
      listeners.set(eventType, new Set())
    }
    listeners.get(eventType)!.add(handler)
  }

  function off(eventType: EventName, handler: MessageHandler): void {
    listeners.get(eventType)?.delete(handler)
    if (listeners.get(eventType)?.size === 0) {
      listeners.delete(eventType)
    }
  }

  // ── 心跳 ─────────────────────────────────

  function startPing(): void {
    stopPing()
    pingTimer.value = setInterval(() => {
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({ type: 'ping' }))
      }
    }, PING_INTERVAL)
  }

  function stopPing(): void {
    if (pingTimer.value !== null) {
      clearInterval(pingTimer.value)
      pingTimer.value = null
    }
  }

  // ── 重连 ─────────────────────────────────

  function scheduleReconnect(): void {
    if (manualDisconnect) return
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.warn(
        `[useWebSocket] 已达最大重连次数 (${MAX_RECONNECT_ATTEMPTS})，停止重连`,
      )
      return
    }
    clearReconnect()
    reconnectAttempts++
    const delay = RECONNECT_DELAY * reconnectAttempts // 渐进延迟
    reconnectTimer.value = setTimeout(() => {
      console.info(
        `[useWebSocket] 第 ${reconnectAttempts} 次重连...`,
      )
      connect()
    }, delay)
  }

  function clearReconnect(): void {
    if (reconnectTimer.value !== null) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
  }

  // ── 生命周期 ─────────────────────────────

  onUnmounted(() => {
    disconnect()
    listeners.clear()
  })

  return {
    connect,
    disconnect,
    on,
    off,
    connected,
  }
}
