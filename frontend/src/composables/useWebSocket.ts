/**
 * WebSocket composable for Vue 3
 *
 * 提供响应式的WebSocket连接和消息处理
 */
import { ref, onUnmounted, watch } from 'vue'
import { createWebSocketClient, WebSocketClient, WebSocketMessage } from '@/utils/websocket'

export interface UseWebSocketOptions {
  url?: string
  token?: string
  subscribe?: string[]
  autoConnect?: boolean
}

export interface LogMessage extends WebSocketMessage {
  level: string
  message: string
  timestamp: number
  job_id?: number
}

export interface StatusUpdate extends WebSocketMessage {
  status: string
  progress?: number
  timestamp: number
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `${import.meta.env.VITE_API_URL || 'ws://localhost:8000'}/api/v1/ws/connect`,
    token,
    subscribe = [],
    autoConnect = true,
  } = options

  // 响应式状态
  const isConnected = ref(false)
  const connectionId = ref<string | null>(null)
  const logs = ref<LogMessage[]>([])
  const statusUpdates = ref<StatusUpdate[]>([])
  const error = ref<Error | null>(null)

  // WebSocket客户端实例
  let wsClient: WebSocketClient | null = null

  /**
   * 连接WebSocket
   */
  const connect = async () => {
    try {
      wsClient = createWebSocketClient({
        url,
        token,
        subscribe,
      })

      // 注册消息处理器
      setupMessageHandlers(wsClient)

      // 连接
      await wsClient.connect()

      isConnected.value = true
      connectionId.value = wsClient.getConnectionId()
      error.value = null
    } catch (err) {
      error.value = err as Error
      isConnected.value = false
      throw err
    }
  }

  /**
   * 断开连接
   */
  const disconnect = () => {
    if (wsClient) {
      wsClient.disconnect()
      wsClient = null
      isConnected.value = false
      connectionId.value = null
    }
  }

  /**
   * 设置消息处理器
   */
  const setupMessageHandlers = (client: WebSocketClient) => {
    // 连接成功
    client.on('connected', (message) => {
      connectionId.value = (message.data?.connection_id as string) || null
    })

    // 日志消息
    client.on('log', (message) => {
      logs.value.push(message as LogMessage)

      // 限制日志数量（最多保留1000条）
      if (logs.value.length > 1000) {
        logs.value = logs.value.slice(-1000)
      }
    })

    // 状态更新
    client.on('status_update', (message) => {
      statusUpdates.value.push(message as StatusUpdate)

      // 限制状态更新数量（最多保留100条）
      if (statusUpdates.value.length > 100) {
        statusUpdates.value = statusUpdates.value.slice(-100)
      }
    })

    // 进度更新
    client.on('progress', (message) => {
      statusUpdates.value.push(message as StatusUpdate)

      if (statusUpdates.value.length > 100) {
        statusUpdates.value = statusUpdates.value.slice(-100)
      }
    })

    // 错误消息
    client.on('error', (message) => {
      error.value = new Error(message.data?.message as string || 'Unknown error')
    })

    // Pong响应
    client.on('pong', () => {
      // 心跳正常，无需处理
    })
  }

  /**
   * 订阅主题
   */
  const subscribeTo = (topic: string) => {
    if (wsClient) {
      wsClient.subscribe(topic)
    }
  }

  /**
   * 取消订阅
   */
  const unsubscribeFrom = (topic: string) => {
    if (wsClient) {
      wsClient.unsubscribe(topic)
    }
  }

  /**
   * 发送消息
   */
  const send = (message: WebSocketMessage) => {
    if (wsClient) {
      wsClient.send(message)
    }
  }

  /**
   * 清空日志
   */
  const clearLogs = () => {
    logs.value = []
  }

  /**
   * 清空状态更新
   */
  const clearStatusUpdates = () => {
    statusUpdates.value = []
  }

  /**
   * 获取最近的日志
   */
  const getRecentLogs = (count: number = 100) => {
    return logs.value.slice(-count)
  }

  /**
   * 获取最新的状态更新
   */
  const getLatestStatus = () => {
    return statusUpdates.value[statusUpdates.value.length - 1] || null
  }

  // 自动连接
  if (autoConnect) {
    connect()
  }

  // 组件卸载时断开连接
  onUnmounted(() => {
    disconnect()
  })

  return {
    // 状态
    isConnected,
    connectionId,
    logs,
    statusUpdates,
    error,

    // 方法
    connect,
    disconnect,
    subscribeTo,
    unsubscribeFrom,
    send,
    clearLogs,
    clearStatusUpdates,
    getRecentLogs,
    getLatestStatus,
  }
}

/**
 * 用于构建日志的composable
 */
export function useBuildLogs(buildId: number) {
  const { isConnected, logs, connect, disconnect, subscribeTo, clearLogs, getRecentLogs } = useWebSocket({
    subscribe: [`build:${buildId}`],
    autoConnect: false,
  })

  const startWatching = async () => {
    await connect()
  }

  const stopWatching = () => {
    disconnect()
  }

  return {
    isConnected,
    logs,
    startWatching,
    stopWatching,
    clearLogs,
    getRecentLogs,
  }
}

/**
 * 用于测试结果的composable
 */
export function useTestResults(testRunId: number) {
  const { isConnected, statusUpdates, connect, disconnect, subscribeTo, clearStatusUpdates } = useWebSocket({
    subscribe: [`test:${testRunId}`],
    autoConnect: false,
  })

  const startWatching = async () => {
    await connect()
  }

  const stopWatching = () => {
    disconnect()
  }

  const getLatestResult = () => {
    return statusUpdates.value[statusUpdates.value.length - 1] || null
  }

  return {
    isConnected,
    statusUpdates,
    startWatching,
    stopWatching,
    clearStatusUpdates,
    getLatestResult,
  }
}
