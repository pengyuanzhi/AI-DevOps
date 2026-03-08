/**
 * Dashboard 主逻辑
 *
 * 初始化并协调所有组件
 */

class Dashboard {
    constructor() {
        this.wsClient = null;
        this.activities = [];
        this.maxActivities = 20;
    }

    /**
     * 初始化 Dashboard
     */
    async init() {
        // 初始化图表
        window.chartManager.initAll();

        // 初始化 WebSocket 连接
        this.initWebSocket();

        // 首次加载数据
        await this.loadInitialData();

        // 加载趋势数据
        await this.loadTrends();

        console.log('Dashboard initialized');
    }

    /**
     * 初始化 WebSocket 连接
     */
    initWebSocket() {
        const wsUrl = `ws://${window.location.host}/api/dashboard/ws`;
        this.wsClient = new WebSocketClient(wsUrl);

        // 注册事件处理器
        this.wsClient.on('connected', () => {
            this.updateConnectionStatus('connected');
        });

        this.wsClient.on('disconnected', () => {
            this.updateConnectionStatus('disconnected');
        });

        this.wsClient.on('stats_update', (message) => {
            this.updateStats(message.data);
            this.addActivity('统计数据更新', message.timestamp);
        });

        this.wsClient.on('error', (error) => {
            console.error('WebSocket error:', error);
            this.addActivity('WebSocket 错误: ' + error.message);
        });

        // 连接
        this.wsClient.connect();
    }

    /**
     * 更新连接状态指示器
     */
    updateConnectionStatus(status) {
        const indicator = document.getElementById('connection-status');
        if (!indicator) return;

        indicator.className = 'status-indicator ' + status;
    }

    /**
     * 加载初始数据
     */
    async loadInitialData() {
        try {
            const response = await window.apiClient.getStats();
            if (response.success) {
                this.updateStats(response.data);
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.addActivity('加载数据失败: ' + error.message);
        }
    }

    /**
     * 加载趋势数据
     */
    async loadTrends() {
        try {
            const response = await window.apiClient.getTrends(24);
            if (response.success) {
                window.chartManager.updateTestTrendChart(response.data.trends);
            }
        } catch (error) {
            console.error('Failed to load trends:', error);
        }
    }

    /**
     * 更新统计数据
     */
    updateStats(data) {
        // 更新测试统计
        this.updateValue('tests-generated', data.tests?.generated || 0);
        this.updateValue('tests-pass-rate', (data.tests?.pass_rate || 0).toFixed(1) + '%');
        this.updateValue('tests-coverage', (data.tests?.coverage || 0).toFixed(1) + '%');

        // 更新代码审查统计
        this.updateValue('reviews-total', data.reviews?.total || 0);
        this.updateValue('reviews-avg-score', (data.reviews?.avg_score || 0).toFixed(1));
        this.updateValue('reviews-issues', data.reviews?.issues_found || 0);

        // 更新 MR 统计
        this.updateValue('mr-processed', data.merge_requests?.processed || 0);
        this.updateValue('mr-pending', data.merge_requests?.pending || 0);
        this.updateValue('mr-avg-time', (data.merge_requests?.avg_process_time || 0) + 's');

        // 更新 LLM 统计
        this.updateValue('llm-tokens', this.formatNumber(data.llm?.total_tokens || 0));
        this.updateValue('llm-api-calls', data.llm?.api_calls || 0);
        this.updateValue('llm-cost', '$' + (data.llm?.estimated_cost || 0).toFixed(2));
    }

    /**
     * 更新单个数值
     */
    updateValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            // 添加动画效果
            element.style.transition = 'transform 0.2s';
            element.style.transform = 'scale(1.1)';
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 200);
        }
    }

    /**
     * 格式化数字
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    /**
     * 添加活动记录
     */
    addActivity(message, timestamp) {
        const time = timestamp ? new Date(timestamp) : new Date();
        const timeStr = time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        this.activities.unshift({ time: timeStr, message });

        // 保持最大数量
        if (this.activities.length > this.maxActivities) {
            this.activities = this.activities.slice(0, this.maxActivities);
        }

        this.renderActivities();
    }

    /**
     * 渲染活动列表
     */
    renderActivities() {
        const listElement = document.getElementById('activity-list');
        if (!listElement) return;

        listElement.innerHTML = this.activities.map(activity => `
            <div class="activity-item">
                <span class="activity-time">${activity.time}</span>
                <span class="activity-message">${activity.message}</span>
            </div>
        `).join('');
    }

    /**
     * 销毁 Dashboard
     */
    destroy() {
        if (this.wsClient) {
            this.wsClient.disconnect();
        }
    }
}

// 页面加载完成后初始化 Dashboard
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new Dashboard();
    dashboard.init();

    // 暴露到全局以便调试
    window.dashboard = dashboard;
});
