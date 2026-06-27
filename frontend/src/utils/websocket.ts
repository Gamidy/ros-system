export interface WSMessage {
  type: 'approval' | 'alert' | 'notification' | 'system' | 'review' | 'notification_read' | 'pong' | 'dashboard_refresh'
  action?: string
  payload: unknown
  timestamp: string
}

class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string = ''
  private readonly BASE_RECONNECT_INTERVAL: number = 3000
  private readonly MAX_RECONNECT_ATTEMPTS: number = 5
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts: number = 0
  private listeners: Map<string, ((data: WSMessage) => void)[]> = new Map()
  private isManualClose: boolean = false
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null
  private heartbeatIntervalMs: number = 30000

  connect(token?: string) {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      this.url = `${protocol}//${host}/ws`
      if (token) {
        this.url += `?token=${encodeURIComponent(token)}`
      }

      this.isManualClose = false
      this.reconnectAttempts = 0
      this._connect()
    } catch (e) {
      console.error('[wsManager] connect() 失败:', e)
      this._scheduleReconnect()
    }
  }

  private _connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return
    }

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        this._startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          this._dispatch(message)
        } catch {
          // Ignore malformed messages
        }
      }

      this.ws.onclose = () => {
        this._stopHeartbeat()
        if (!this.isManualClose) {
          this._scheduleReconnect()
        }
      }

      this.ws.onerror = () => {
        // Error will trigger onclose, reconnect handled there
      }
    } catch {
      this._scheduleReconnect()
    }
  }

  private _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, this.heartbeatIntervalMs)
  }

  private _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private _scheduleReconnect() {
    if (this.reconnectTimer) return
    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) return

    this.reconnectAttempts++
    // 指数退避: 3s, 6s, 12s, 24s, 24s（封顶）
    const delay = Math.min(this.BASE_RECONNECT_INTERVAL * Math.pow(2, this.reconnectAttempts - 1), 24000)
    console.log(`[wsManager] ${this.reconnectAttempts}/${this.MAX_RECONNECT_ATTEMPTS} 次重连，${delay}ms 后...`)
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this._connect()
    }, delay)
  }

  private _dispatch(message: WSMessage) {
    const handlers = this.listeners.get(message.type) || []
    handlers.forEach((fn) => {
      try {
        fn(message)
      } catch {
        // Ignore handler errors
      }
    })
    // Also dispatch to wildcard listeners
    const wildcard = this.listeners.get('*') || []
    wildcard.forEach((fn) => {
      try {
        fn(message)
      } catch {
        // Ignore handler errors
      }
    })
  }

  /**
   * 订阅某类消息
   */
  on(type: WSMessage['type'] | '*', handler: (data: WSMessage) => void) {
    const key = type
    if (!this.listeners.has(key)) {
      this.listeners.set(key, [])
    }
    this.listeners.get(key)!.push(handler)

    // Return unsubscribe function
    return () => this.off(key, handler)
  }

  off(type: WSMessage['type'] | '*', handler: (data: WSMessage) => void) {
    const handlers = this.listeners.get(type)
    if (!handlers) return
    const idx = handlers.indexOf(handler)
    if (idx !== -1) handlers.splice(idx, 1)
  }

  /**
   * 发送消息
   */
  send(message: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  close() {
    this.isManualClose = true
    this._stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
    this.ws = null
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsManager = new WebSocketManager()
