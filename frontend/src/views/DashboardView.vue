<template>
  <div class="dashboard">
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 骨架屏 - 加载中显示 -->
    <div v-if="loading">
      <el-row :gutter="20">
        <el-col :span="6" v-for="i in 4" :key="i">
          <SkeletonLoader type="stat" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="16">
          <SkeletonLoader type="chart" />
        </el-col>
        <el-col :span="8">
          <SkeletonLoader type="table" :rows="5" />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 - 无数据时显示 -->
    <EmptyState
      v-else-if="!loading && !hasData"
      type="no-data"
      title="暂无Dashboard数据"
      description="当前项目还没有任何统计数据，请先运行一些Pipeline"
      :show-action="false"
    />

    <!-- 实际内容 -->
    <el-row :gutter="20" v-if="!loading && !error && hasData">
      <!-- 关键指标卡片 -->
      <el-col :span="6" v-for="metric in metrics" :key="metric.title">
        <el-card class="metric-card">
          <div class="metric-content">
            <div class="metric-icon" :style="{ backgroundColor: metric.color }">
              <el-icon :size="30">
                <component :is="metric.icon" />
              </el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-title">{{ metric.title }}</div>
              <div class="metric-value">{{ metric.value }}</div>
              <div class="metric-trend" :class="metric.trendClass">
                {{ metric.trend }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 构建趋势图 -->
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>构建/测试成功率趋势</span>
              <el-radio-group v-model="trendPeriod" size="small">
                <el-radio-button label="7天">近7天</el-radio-button>
                <el-radio-button label="30天">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 最近失败的Pipeline -->
      <el-col :span="8">
        <el-card class="list-card">
          <template #header>
            <div class="card-header">
              <span>最近失败的Pipeline</span>
              <el-button type="text" @click="viewAll">查看全部</el-button>
            </div>
          </template>
          <el-table :data="failedPipelines" style="width: 100%">
            <el-table-column prop="name" label="项目" />
            <el-table-column prop="branch" label="分支" width="100" />
            <el-table-column prop="duration" label="耗时" width="80" />
            <el-table-column label="操作" width="80">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewDetail(scope.row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- AI检测到的问题 -->
      <el-col :span="12">
        <el-card class="list-card">
          <template #header>
            <span>AI检测到的问题</span>
          </template>
          <el-table :data="aiIssues" style="width: 100%">
            <el-table-column prop="type" label="类型" width="120">
              <template #default="scope">
                <el-tag :type="getIssueTypeTag(scope.row.type)">
                  {{ scope.row.type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="scope">
                {{ scope.row.confidence }}%
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 待处理的MR -->
      <el-col :span="12">
        <el-card class="list-card">
          <template #header>
            <span>待处理的MR</span>
          </template>
          <el-table :data="pendingMRs" style="width: 100%">
            <el-table-column prop="title" label="标题" show-overflow-tooltip />
            <el-table-column prop="author" label="作者" width="100" />
            <el-table-column prop="created_at" label="创建时间" width="120" />
            <el-table-column label="操作" width="80">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewMR(scope.row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import {
  Odometer,
  TrendCharts,
  SuccessFilled,
  WarningFilled
} from '@element-plus/icons-vue'
import { useDashboardStore, useProjectStore } from '@/stores'
import { useWebSocket } from '@/composables/useWebSocket'
import { SkeletonLoader, EmptyState } from '@/components/common'
import type { DashboardStats } from '@/types'

const router = useRouter()
const dashboardStore = useDashboardStore()
const projectStore = useProjectStore()

const trendPeriod = ref('7天')
const trendChartRef = ref<HTMLElement>()
const trendChart = ref<ECharts>()
const loading = ref(false)
const error = ref<string | null>(null)

// WebSocket实时通信
const {
  isConnected: wsConnected,
  subscribeTo,
  unsubscribeFrom,
  statusUpdates,
  clearStatusUpdates
} = useWebSocket({
  autoConnect: true,
  subscribe: ['dashboard_updates']
})

// 获取当前项目ID
const currentProjectId = computed(() => projectStore.currentProject?.id)

// 关键指标数据 - 从store计算得出
const metrics = computed(() => {
  const stats = dashboardStore.dashboardStats
  if (!stats) {
    return []
  }

  return [
    {
      title: '项目健康度',
      value: stats.project_health.toFixed(1),
      trend: '+2.3%', // TODO: 从趋势数据计算
      trendClass: 'trend-up',
      color: '#67c23a',
      icon: Odometer
    },
    {
      title: '今日构建',
      value: stats.today_builds.toString(),
      trend: '+12',
      trendClass: 'trend-up',
      color: '#409eff',
      icon: SuccessFilled
    },
    {
      title: '平均构建时间',
      value: formatDuration(stats.avg_build_time),
      trend: '-1.2m',
      trendClass: 'trend-up',
      color: '#e6a23c',
      icon: TrendCharts
    },
    {
      title: '失败率',
      value: ((1 - stats.build_success_rate) * 100).toFixed(1) + '%',
      trend: '-0.8%',
      trendClass: 'trend-down',
      color: '#f56c6c',
      icon: WarningFilled
    }
  ]
})

// 判断是否有数据
const hasData = computed(() => {
  const stats = dashboardStore.dashboardStats
  return stats && stats.today_builds > 0
})

// 格式化时长
const formatDuration = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes}m`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
}

// 失败的Pipeline列表 - 从API获取
const failedPipelines = ref<any[]>([])

// AI检测到的问题列表
const aiIssues = ref<any[]>([])

// 待处理的MR列表
const pendingMRs = ref<any[]>([])

// 趋势数据
const buildSuccessTrend = computed(() => dashboardStore.buildSuccessTrend)
const testPassRateTrend = computed(() => dashboardStore.testPassRateTrend)

const getIssueTypeTag = (type: string) => {
  const tagMap: Record<string, any> = {
    '内存泄漏': 'danger',
    '代码风格': 'warning',
    '性能问题': 'info',
    '安全问题': 'danger',
    'bug': 'danger'
  }
  return tagMap[type] || 'info'
}

const viewAll = () => {
  router.push('/pipelines?status=failed')
}

const viewDetail = (row: any) => {
  router.push(`/pipelines/${row.id}`)
}

const viewMR = (row: any) => {
  // 跳转到GitLab MR页面
  window.open(row.web_url, '_blank')
}

const initTrendChart = () => {
  if (!trendChartRef.value) return

  trendChart.value = echarts.init(trendChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['构建成功率', '测试成功率']
    },
    xAxis: {
      type: 'category',
      data: buildSuccessTrend.value.map(item => {
        const date = new Date(item.date)
        return `${date.getMonth() + 1}/${date.getDate()}`
      })
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '{value}%'
      },
      min: 0,
      max: 100
    },
    series: [
      {
        name: '构建成功率',
        type: 'line',
        data: buildSuccessTrend.value.map(item => (item.success_rate * 100).toFixed(1)),
        smooth: true
      },
      {
        name: '测试成功率',
        type: 'line',
        data: testPassRateTrend.value.map(item => (item.pass_rate * 100).toFixed(1)),
        smooth: true
      }
    ]
  }

  trendChart.value.setOption(option)
}

// 加载Dashboard数据
const loadDashboardData = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 加载所有Dashboard数据
    await dashboardStore.fetchAllDashboardData(currentProjectId.value)

    // 加载最近失败的Pipeline
    failedPipelines.value = await dashboardStore.getRecentFailedPipelines?.(currentProjectId.value, { per_page: 5 }) || []

    // 加载AI检测到的问题
    aiIssues.value = await dashboardStore.getAIIssues?.(currentProjectId.value, { per_page: 5 }) || []

    // 加载待处理的MR
    pendingMRs.value = await dashboardStore.getPendingMRs?.(currentProjectId.value, { per_page: 5 }) || []

    // 初始化趋势图
    initTrendChart()
  } catch (err: any) {
    console.error('Failed to load dashboard data:', err)
    error.value = err.message || '加载数据失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 监听趋势周期变化
watch(trendPeriod, async (newPeriod) => {
  const days = newPeriod === '7天' ? 7 : 30
  if (currentProjectId.value) {
    await Promise.all([
      dashboardStore.fetchHealthTrend(currentProjectId.value, days),
      dashboardStore.fetchBuildSuccessTrend(currentProjectId.value, days)
    ])
    initTrendChart()
  }
})

onMounted(() => {
  loadDashboardData()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()

  window.addEventListener('resize', () => {
    trendChart.value?.resize()
  })
})

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 订阅Dashboard更新
  if (currentProjectId.value) {
    subscribeTo(`dashboard.${currentProjectId.value}`)
  }

  // 监听状态更新消息
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新Dashboard数据
      if (currentProjectId.value) {
        loadDashboardData()
      }
    }
  })
}

// 监听项目切换
watch(currentProjectId, (newId) => {
  if (newId) {
    // 切换WebSocket订阅
    if (wsConnected.value) {
      // 订阅新项目的Dashboard更新
      subscribeTo(`dashboard.${newId}`)
    }

    // 加载Dashboard数据
    loadDashboardData()
  }
})

// 清理资源
onUnmounted(() => {
  // 清理图表资源
  trendChart.value?.dispose()

  // 清理状态更新
  clearStatusUpdates()

  // WebSocket会自动断开（由useWebSocket composable处理）
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.metric-card {
  cursor: pointer;
  transition: all 0.3s;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.metric-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.metric-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.metric-info {
  flex: 1;
}

.metric-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.metric-trend {
  font-size: 12px;
}

.trend-up {
  color: #67c23a;
}

.trend-down {
  color: #f56c6c;
}

.chart-card,
.list-card {
  height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 320px;
}
</style>
