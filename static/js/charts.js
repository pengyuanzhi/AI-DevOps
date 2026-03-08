/**
 * 图表管理
 *
 * 使用 Chart.js 创建和管理所有图表
 */

class ChartManager {
    constructor() {
        this.charts = new Map();
        this.chartColors = {
            primary: '#2563eb',
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#3b82f6',
            purple: '#8b5cf6',
            pink: '#ec4899',
        };
    }

    /**
     * 创建测试通过率趋势图
     */
    createTestTrendChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '测试通过率 (%)',
                    data: [],
                    borderColor: this.chartColors.primary,
                    backgroundColor: this.chartColors.primary + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2.5,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: value => value + '%'
                        }
                    },
                    x: {
                        ticks: {
                            maxTicksLimit: 12
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index',
                }
            }
        });

        this.charts.set('testTrend', chart);
        return chart;
    }

    /**
     * 创建问题分布图
     */
    createIssueDistributionChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['质量', '安全', '性能', '逻辑', '可维护性'],
                datasets: [{
                    label: '问题数量',
                    data: [65, 28, 45, 32, 38],
                    backgroundColor: [
                        this.chartColors.primary,
                        this.chartColors.danger,
                        this.chartColors.warning,
                        this.chartColors.info,
                        this.chartColors.purple,
                    ],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 1.5,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        this.charts.set('issueDistribution', chart);
        return chart;
    }

    /**
     * 创建 LLM 使用统计图
     */
    createLLMUsageChart(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['测试生成', '代码审查', '其他'],
                datasets: [{
                    data: [55, 30, 15],
                    backgroundColor: [
                        this.chartColors.primary,
                        this.chartColors.success,
                        this.chartColors.warning,
                    ],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 1.5,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                    }
                }
            }
        });

        this.charts.set('llmUsage', chart);
        return chart;
    }

    /**
     * 更新测试趋势图
     */
    updateTestTrendChart(trends) {
        const chart = this.charts.get('testTrend');
        if (!chart || !trends) return;

        const labels = trends.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        });

        const passRates = trends.map(item => {
            // 模拟计算通过率（实际应该从数据中获取）
            return 85 + Math.random() * 10;
        });

        chart.data.labels = labels;
        chart.data.datasets[0].data = passRates;
        chart.update('none'); // 'none' 模式避免完整重绘动画
    }

    /**
     * 获取图表
     */
    getChart(name) {
        return this.charts.get(name);
    }

    /**
     * 初始化所有图表
     */
    initAll() {
        this.createTestTrendChart('test-trend-chart');
        this.createIssueDistributionChart('issue-distribution-chart');
        this.createLLMUsageChart('llm-usage-chart');
    }
}

// 导出全局实例
window.chartManager = new ChartManager();
