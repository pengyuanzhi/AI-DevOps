/**
 * API 客户端
 *
 * 提供与后端 REST API 交互的方法
 */

class APIClient {
    constructor(baseURL = '/api/dashboard') {
        this.baseURL = baseURL;
    }

    /**
     * 获取统计数据
     */
    async getStats() {
        try {
            const response = await fetch(`${this.baseURL}/stats`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Failed to fetch stats:', error);
            throw error;
        }
    }

    /**
     * 获取趋势数据
     */
    async getTrends(hours = 24) {
        try {
            const response = await fetch(`${this.baseURL}/trends?hours=${hours}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Failed to fetch trends:', error);
            throw error;
        }
    }
}

// 导出全局实例
window.apiClient = new APIClient();
