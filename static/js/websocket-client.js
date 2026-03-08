/**
 * WebSocket 客户端
 *
 * 管理与服务器的 WebSocket 连接，处理实时数据更新
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1秒
        this.eventHandlers = new Map();
        this.isConnected = false;
    }

    /**
     * 连接到 WebSocket 服务器
     */
    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.emit('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.emit('message', message);

                    // 根据消息类型触发特定事件
                    if (message.type) {
                        this.emit(message.type, message);
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.emit('disconnected');

                // 尝试重连
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
                    console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);

                    setTimeout(() => {
                        this.connect();
                    }, delay);
                } else {
                    console.error('Max reconnect attempts reached');
                    this.emit('error', new Error('Max reconnect attempts reached'));
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.emit('error', error);
        }
    }

    /**
     * 断开连接
     */
    disconnect() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // 防止自动重连
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
        }
    }

    /**
     * 发送消息
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket is not connected');
        }
    }

    /**
     * 注册事件处理器
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    /**
     * 移除事件处理器
     */
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            const handlers = this.eventHandlers.get(event);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * 触发事件
     */
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for "${event}":`, error);
                }
            });
        }
    }
}

// 导出
window.WebSocketClient = WebSocketClient;
