/**
 * WebSocket客户端工具类
 *
 * 提供WebSocket连接管理、消息订阅、重连等功能
 */

export interface WebSocketMessage {
  type: string
  data?: Record<string, unknown>
  topic?: string
  timestamp?: number
}

export type WebSocketMessageHandler = (message: WebSocketMessage) => void

export interface WebSocketClientOptions {
  url: string
  token?: string
  subscribe?: string[]
  heartbeatInterval?: number
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private token?: string
  private topics: Set<string> = new Set()
  private messageHandlers: Map<string, Set<WebSocketMessageHandler>> = new Map()
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatInterval: number
  private reconnectInterval: number
  private maxReconnectAttempts: number
  private reconnectAttempts: number = 0
  private isManualClose: boolean = false
  private connectionId: string | null = null

  constructor(options: WebSocketClientOptions) {
    this.url = options.url
    this.token = options.token
    this.heartbeatInterval = options.heartbeatInterval || 30000 // 30秒
    this.reconnectInterval = options.reconnectInterval || 3000 // 3秒
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10

    // 初始订阅
    if (options.subscribe) {
      options.subscribe.forEach((topic) => this.topics.add(topic))
    }
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // 构建URL（添加订阅参数）
        let wsUrl = this.url
        const params = new URLSearchParams()

        if (this.token) {
          params.append('token', this.token)
        }

        if (this.topics.size > 0) {
          params.append('subscribe', Array.from(this.topics).join(','))
        }

        if (params.toString()) {
          wsUrl += `?${params.toString()}`
        }

        // 创建WebSocket连接
        this.ws = new WebSocket(wsUrl)
        this.isManualClose = false

        // 连接打开
        this.ws.onopen = () => {
          console.log('[WebSocket] Connected')
          this.reconnectAttempts = 0
          this.startHeartbeat()
          resolve()
        }

        // 接收消息
        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error)
          }
        }

        // 连接关闭
        this.ws.onclose = (event) => {
          console.log('[WebSocket] Disconnected:', event.code, event.reason)
          this.stopHeartbeat()

          if (!this.isManualClose) {
            // 自动重连
            this.scheduleReconnect()
          }
        }

        // 连接错误
        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error)
          reject(error)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 订阅主题
   */
  subscribe(topic: string): void {
    this.topics.add(topic)

    // 如果已连接，立即发送订阅消息
    if (this.isConnected()) {
      this.send({
        type: 'subscribe',
        topic,
      })
    }
  }

  /**
   * 取消订阅
   */
  unsubscribe(topic: string): void {
    this.topics.delete(topic)

    // 如果已连接，发送取消订阅消息
    if (this.isConnected()) {
      this.send({
        type: 'unsubscribe',
        topic,
      })
    }
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('[WebSocket] Cannot send message: not connected')
    }
  }

  /**
   * 注册消息处理器
   */
  on(messageType: string, handler: WebSocketMessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set())
    }

    this.messageHandlers.get(messageType)!.add(handler)

    // 返回取消订阅函数
    return () => {
      this.off(messageType, handler)
    }
  }

  /**
   * 取消消息处理器
   */
  off(messageType: string, handler: WebSocketMessageHandler): void {
    const handlers = this.messageHandlers.get(messageType)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    // 保存连接ID
    if (message.type === 'connected' && message.data?.connection_id) {
      this.connectionId = message.data.connection_id as string
    }

    // 调用注册的处理器
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message)
        } catch (error) {
          console.error(`[WebSocket] Handler error for type ${message.type}:`, error)
        }
      })
    }
  }

  /**
   * 开始心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat()

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'ping',
        })
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 安排重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.reconnectTimer = setTimeout(async () => {
      console.log(`[WebSocket] Reconnecting... (attempt ${this.reconnectAttempts})`)

      try {
        await this.connect()
      } catch (error) {
        console.error('[WebSocket] Reconnect failed:', error)
      }
    }, this.reconnectInterval)
  }

  /**
   * 检查是否已连接
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * 获取连接ID
   */
  getConnectionId(): string | null {
    return this.connectionId
  }

  /**
   * 获取当前订阅的主题
   */
  getSubscriptions(): string[] {
    return Array.from(this.topics)
  }
}

/**
 * 创建WebSocket客户端的工厂函数
 */
export function createWebSocketClient(options: WebSocketClientOptions): WebSocketClient {
  return new WebSocketClient(options)
}

/**
 * 默认WebSocket客户端实例（用于快速访问）
 */
let defaultWsClient: WebSocketClient | null = null

/**
 * 初始化默认WebSocket客户端
 */
export function initWebSocketClient(options: WebSocketClientOptions): WebSocketClient {
  if (!defaultWsClient) {
    defaultWsClient = new WebSocketClient(options)
  }

  return defaultWsClient
}

/**
 * 获取默认WebSocket客户端
 */
export function getWebSocketClient(): WebSocketClient | null {
  return defaultWsClient
}
