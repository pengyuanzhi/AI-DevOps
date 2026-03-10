<template>
  <div class="test-quality">
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
        <el-col :span="12">
          <SkeletonLoader type="chart" />
        </el-col>
        <el-col :span="12">
          <SkeletonLoader type="chart" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="12">
          <SkeletonLoader type="table" :rows="5" />
        </el-col>
        <el-col :span="12">
          <SkeletonLoader type="list" :rows="3" />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 - 无测试数据时显示 -->
    <el-card v-else-if="!loading && hasNoTestData">
      <EmptyState
        type="no-data"
        title="暂无测试数据"
        description="还没有任何测试执行记录，请先运行测试"
        :show-action="true"
        action-text="运行测试"
        @action="runTests"
      />
    </el-card>

    <!-- 实际内容 -->
    <template v-if="!loading && !hasNoTestData">
      <!-- 页面标题和WebSocket状态 -->
      <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0;">测试和质量概览</h2>
        <el-tooltip :content="wsConnected ? '实时更新已连接' : '实时更新已断开'">
          <div class="ws-status" :class="{ connected: wsConnected }">
            <div class="ws-indicator"></div>
          </div>
        </el-tooltip>
      </div>

      <!-- 测试统计卡片 -->
      <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success">
              <el-icon :size="24"><SuccessFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ testStats.total }}</div>
              <div class="stat-label">总测试数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon primary">
              <el-icon :size="24"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ testStats.passed }}</div>
              <div class="stat-label">通过数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon warning">
              <el-icon :size="24"><WarningFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ testStats.failed }}</div>
              <div class="stat-label">失败数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon info">
              <el-icon :size="24"><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ testStats.avgDuration }}s</div>
              <div class="stat-label">平均耗时</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 测试结果图表 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>测试结果分布</span>
              <el-radio-group v-model="testResultPeriod" size="small">
                <el-radio-button label="今日">今日</el-radio-button>
                <el-radio-button label="本周">本周</el-radio-button>
                <el-radio-button label="本月">本月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="testResultChartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 代码覆盖率 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>代码覆盖率</span>
              <el-tag type="success">{{ coverage.overall }}%</el-tag>
            </div>
          </template>
          <div class="coverage-content">
            <div class="coverage-item" v-for="(item, index) in coverage.breakdown" :key="index">
              <div class="coverage-label">
                <span>{{ item.label }}</span>
                <span class="coverage-value">{{ item.value }}%</span>
              </div>
              <el-progress
                :percentage="item.value"
                :color="getCoverageColor(item.value)"
                :stroke-width="20"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 智能测试选择 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>智能测试选择</span>
              <el-tag type="info" size="small">AI驱动</el-tag>
            </div>
          </template>
          <div class="test-selection-content">
            <div class="selection-stats">
              <div class="stat-item">
                <div class="stat-number">{{ testSelection.totalTests }}</div>
                <div class="stat-text">总测试数</div>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <div class="stat-number selected">{{ testSelection.selectedTests }}</div>
                <div class="stat-text">已选择</div>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <div class="stat-number skipped">{{ testSelection.skippedTests }}</div>
                <div class="stat-text">已跳过</div>
              </div>
            </div>
            <div class="time-saved">
              <el-icon color="#67c23a"><Clock /></el-icon>
              <span>节省时间: <strong>{{ testSelection.timeSaved }}</strong></span>
            </div>
            <el-divider />
            <div class="selection-reason">
              <div class="reason-title">选择原因:</div>
              <div class="reason-list">
                <el-tag
                  v-for="(reason, index) in testSelection.reasons"
                  :key="index"
                  type="info"
                  size="small"
                  style="margin: 4px"
                >
                  {{ reason }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 失败测试列表 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>失败测试</span>
              <el-button type="text" @click="viewAllFailedTests">查看全部</el-button>
            </div>
          </template>
          <el-table :data="failedTests" style="width: 100%" max-height="300">
            <el-table-column prop="name" label="测试名称" show-overflow-tooltip />
            <el-table-column prop="suite" label="测试套件" width="120" />
            <el-table-column prop="duration" label="耗时" width="80" />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewTestDetail(scope.row)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 测试历史趋势 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>测试通过率趋势</span>
              <el-radio-group v-model="trendPeriod" size="small">
                <el-radio-button label="7天">近7天</el-radio-button>
                <el-radio-button label="30天">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 测试执行时间分布 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>测试执行时间分布</span>
          </template>
          <div ref="durationChartRef" class="chart-container-small"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 测试详情对话框 -->
    <el-dialog v-model="testDetailVisible" title="测试详情" width="70%">
      <div v-if="currentTest" class="test-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="测试名称">{{ currentTest.name }}</el-descriptions-item>
          <el-descriptions-item label="测试套件">{{ currentTest.suite }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentTest.status === 'passed' ? 'success' : 'danger'">
              {{ currentTest.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ currentTest.duration }}s</el-descriptions-item>
          <el-descriptions-item label="文件">{{ currentTest.file }}</el-descriptions-item>
          <el-descriptions-item label="行号">{{ currentTest.line }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>错误信息</el-divider>
        <div v-if="currentTest.error" class="error-message">
          <pre>{{ currentTest.error }}</pre>
        </div>
        <div v-else class="no-error">
          <el-icon color="#67c23a"><SuccessFilled /></el-icon>
          <span>测试通过，无错误信息</span>
        </div>

        <el-divider v-if="currentTest.stack">堆栈跟踪</el-divider>
        <div v-if="currentTest.stack" class="stack-trace">
          <pre>{{ currentTest.stack }}</pre>
        </div>

        <el-divider v-if="currentTest.isFlaky">不稳定测试警告</el-divider>
        <el-alert
          v-if="currentTest.isFlaky"
          title="这是一个不稳定的测试"
          type="warning"
          :description="`该测试在过去30次运行中失败了${currentTest.flakyCount}次`"
          show-icon
          :closable="false"
        />
      </div>
    </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import {
  SuccessFilled,
  WarningFilled,
  Timer,
  CircleCheck,
  Clock
} from '@element-plus/icons-vue'
import { useTestStore, useDashboardStore, useProjectStore } from '@/stores'
import { SkeletonLoader, EmptyState } from '@/components/common'
import { useWebSocket } from '@/composables/useWebSocket'
import type { TestQualityStats, TestCoverage, TestCase } from '@/types'

const router = useRouter()
const testStore = useTestStore()
const dashboardStore = useDashboardStore()
const projectStore = useProjectStore()

// WebSocket实时通信
const {
  isConnected: wsConnected,
  subscribeTo,
  unsubscribeFrom,
  statusUpdates,
  clearStatusUpdates
} = useWebSocket({
  autoConnect: true,
  subscribe: ['test_updates', 'test_result_updates']
})

// 获取当前项目ID
const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态
const loading = ref(false)
const error = ref<string | null>(null)

const testResultPeriod = ref('今日')
const trendPeriod = ref('7天')
const testDetailVisible = ref(false)
const currentTest = ref<TestCase | null>(null)

// 图表引用
const testResultChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const durationChartRef = ref<HTMLElement>()

const testResultChart = ref<ECharts>()
const trendChart = ref<ECharts>()
const durationChart = ref<ECharts>()

// 测试统计 - 从store计算得出
const testStats = computed(() => {
  const stats = dashboardStore.testQualityStats
  if (!stats) {
    return {
      total: 0,
      passed: 0,
      failed: 0,
      avgDuration: 0
    }
  }

  return {
    total: stats.total_tests,
    passed: stats.passed_tests,
    failed: stats.failed_tests,
    avgDuration: stats.total_tests > 0
      ? Math.round((stats.total_tests * 2.5) / 60) // 简化计算
      : 0
  }
})

// 代码覆盖率 - 从store获取
const coverage = computed(() => {
  const cov = testStore.testCoverage
  if (!cov) {
    return {
      overall: 0,
      breakdown: [
        { label: '行覆盖率', value: 0 },
        { label: '函数覆盖率', value: 0 },
        { label: '分支覆盖率', value: 0 }
      ]
    }
  }

  return {
    overall: Math.round(cov.line_coverage),
    breakdown: [
      { label: '行覆盖率', value: Math.round(cov.line_coverage) },
      { label: '函数覆盖率', value: Math.round(cov.function_coverage) },
      { label: '分支覆盖率', value: Math.round(cov.branch_coverage) }
    ]
  }
})

// 智能测试选择 - 从store获取
const testSelection = computed(() => {
  const selection = testStore.testSelection
  if (!selection) {
    return {
      totalTests: 0,
      selectedTests: 0,
      skippedTests: 0,
      timeSaved: '0秒',
      reasons: []
    }
  }

  const minutes = Math.floor(selection.estimated_time_saved / 60)
  const seconds = selection.estimated_time_saved % 60

  return {
    totalTests: selection.total_tests,
    selectedTests: selection.selected_tests,
    skippedTests: selection.skipped_tests,
    timeSaved: minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`,
    reasons: selection.reasons.map(r => r.reason)
  }
})

// 失败测试 - 从store获取
const failedTests = computed(() => {
  return testStore.failedTests.map(test => ({
    id: test.id,
    name: test.name,
    suite: test.suite,
    duration: `${test.duration}s`,
    status: test.status,
    file: test.file_path,
    line: test.line_number,
    error: test.error_message || 'Unknown error',
    stack: test.stack_trace || 'No stack trace available',
    isFlaky: false, // TODO: 从API获取flaky信息
    flakyCount: 0
  }))
})

// 判断是否有测试数据
const hasNoTestData = computed(() => {
  const stats = dashboardStore.testQualityStats
  return !stats || stats.total_tests === 0
})

// 运行测试
const runTests = () => {
  ElMessage.info('运行测试功能开发中')
}

// 获取覆盖率颜色
const getCoverageColor = (value: number) => {
  if (value >= 80) return '#67c23a'
  if (value >= 60) return '#e6a23c'
  return '#f56c6c'
}

// 查看测试详情
const viewTestDetail = async (test: any) => {
  try {
    await testStore.fetchTestCase(test.id)
    currentTest.value = testStore.currentTestCase
    testDetailVisible.value = true
  } catch (error) {
    console.error('Failed to load test detail:', error)
  }
}

// 查看所有失败测试
const viewAllFailedTests = () => {
  router.push('/tests?status=failed')
}

// 加载测试质量数据
const loadTestData = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 并行加载所有数据
    await Promise.all([
      dashboardStore.fetchTestQualityStats(currentProjectId.value),
      testStore.fetchTestCoverage(currentProjectId.value),
      testStore.fetchPassRateTrend(currentProjectId.value, 7),
      testStore.fetchFailedTests(currentProjectId.value, { per_page: 10 })
    ])

    // 初始化图表
    await nextTick()
    initTestResultChart()
    initTrendChart()
    initDurationChart()
  } catch (err: any) {
    console.error('Failed to load test data:', err)
    error.value = err.message || '加载测试数据失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 初始化测试结果饼图
const initTestResultChart = () => {
  if (!testResultChartRef.value) return

  testResultChart.value = echarts.init(testResultChartRef.value)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '测试结果',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        data: [
          { value: testStats.value.passed, name: '通过', itemStyle: { color: '#67c23a' } },
          { value: testStats.value.failed, name: '失败', itemStyle: { color: '#f56c6c' } },
          { value: testStats.value.total - testStats.value.passed - testStats.value.failed, name: '跳过', itemStyle: { color: '#909399' } }
        ]
      }
    ]
  }

  testResultChart.value.setOption(option)
}

// 初始化趋势图
const initTrendChart = () => {
  if (!trendChartRef.value) return

  trendChart.value = echarts.init(trendChartRef.value)

  const passRateData = testStore.passRateTrend.map(item => (item.pass_rate * 100).toFixed(1))
  const xAxisData = testStore.passRateTrend.map(item => {
    const date = new Date(item.date)
    return `${date.getMonth() + 1}/${date.getDate()}`
  })

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: xAxisData
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
        name: '通过率',
        type: 'line',
        data: passRateData,
        smooth: true,
        itemStyle: { color: '#67c23a' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  trendChart.value.setOption(option)
}

// 初始化执行时间分布图
const initDurationChart = () => {
  if (!durationChartRef.value) return

  durationChart.value = echarts.init(durationChartRef.value)

  // TODO: 从API获取真实数据
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: ['<1s', '1-3s', '3-5s', '5-10s', '>10s']
    },
    yAxis: {
      type: 'value',
      name: '测试数量'
    },
    series: [
      {
        name: '测试数量',
        type: 'bar',
        data: [425, 512, 198, 89, 24],
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#409eff' },
              { offset: 1, color: '#a0cfff' }
            ]
          }
        }
      }
    ]
  }

  durationChart.value.setOption(option)
}

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 订阅测试更新主题
  subscribeTo('test_updates')
  subscribeTo('test_result_updates')

  // 监听状态更新消息
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新测试数据
      if (currentProjectId.value) {
        loadTestData()
      }
    }
  })
}

onMounted(() => {
  loadTestData()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()

  // 响应式调整
  const resizeHandler = () => {
    testResultChart.value?.resize()
    trendChart.value?.resize()
    durationChart.value?.resize()
  }

  window.addEventListener('resize', resizeHandler)
  onUnmounted(() => {
    window.removeEventListener('resize', resizeHandler)

    // 清理图表资源
    testResultChart.value?.dispose()
    trendChart.value?.dispose()
    durationChart.value?.dispose()

    // 清理状态更新
    clearStatusUpdates()
  })
})

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadTestData()
  }
})
</script>

<style scoped>
.test-quality {
  padding: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-icon.success {
  background: linear-gradient(135deg, #67c23a, #85ce61);
}

.stat-icon.primary {
  background: linear-gradient(135deg, #409eff, #66b1ff);
}

.stat-icon.warning {
  background: linear-gradient(135deg, #e6a23c, #ebb563);
}

.stat-icon.info {
  background: linear-gradient(135deg, #909399, #a6a9ad);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.chart-container-small {
  width: 100%;
  height: 250px;
}

.coverage-content {
  padding: 10px 0;
}

.coverage-item {
  margin-bottom: 20px;
}

.coverage-item:last-child {
  margin-bottom: 0;
}

.coverage-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.coverage-value {
  font-weight: bold;
  color: #303133;
}

.test-selection-content {
  padding: 10px 0;
}

.selection-stats {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-number.selected {
  color: #67c23a;
}

.stat-number.skipped {
  color: #909399;
}

.stat-text {
  font-size: 12px;
  color: #909399;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background-color: #dcdfe6;
}

.time-saved {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: #f0f9ff;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #606266;
}

.selection-reason {
  margin-top: 16px;
}

.reason-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.reason-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.test-detail {
  padding: 10px;
}

.error-message,
.stack-trace {
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.error-message pre,
.stack-trace pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #f56c6c;
}

.stack-trace pre {
  color: #606266;
}

.no-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background-color: #f0f9ff;
  border-radius: 4px;
  color: #67c23a;
  font-size: 14px;
}

/* WebSocket状态指示器 */
.ws-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: #f5f5f5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
}

.ws-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff4d4f;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.ws-status.connected .ws-indicator {
  background-color: #52c41a;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
