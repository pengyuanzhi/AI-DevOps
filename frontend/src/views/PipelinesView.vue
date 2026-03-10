<template>
  <div class="pipelines">
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      style="margin-bottom: 20px"
    />

    <!-- 骨架屏 - 加载中显示 -->
    <div v-if="loading">
      <el-card>
        <SkeletonLoader type="table" :rows="10" />
      </el-card>
    </div>

    <!-- 空状态 - 无Pipeline时显示 -->
    <el-card v-else-if="!loading && filteredPipelines.length === 0">
      <EmptyState
        v-if="hasFilters"
        type="no-search"
        title="未找到匹配的Pipeline"
        :description="`没有找到与当前筛选条件匹配的Pipeline`"
        :show-action="true"
        action-text="清除筛选"
        @action="clearFilters"
      />
      <EmptyState
        v-else
        type="no-data"
        title="暂无Pipeline"
        description="还没有创建任何Pipeline，点击下方按钮开始创建"
        :show-action="true"
        action-text="创建Pipeline"
        @action="createPipeline"
      />
    </el-card>

    <!-- 实际内容 -->
    <template v-if="!loading && filteredPipelines.length > 0">
    <!-- 筛选和搜索 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-select v-model="filters.status" placeholder="状态" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="成功" value="success" />
          <el-option label="运行中" value="running" />
          <el-option label="失败" value="failed" />
          <el-option label="已取消" value="cancelled" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filters.branch" placeholder="分支" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="main" value="main" />
          <el-option label="develop" value="develop" />
          <el-option label="feature/*" value="feature" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filters.source" placeholder="来源" clearable @change="handleFilterChange">
          <el-option label="全部" value="" />
          <el-option label="Push" value="push" />
          <el-option label="Merge Request" value="merge_request" />
          <el-option label="Tag" value="tag" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-input
          v-model="filters.search"
          placeholder="搜索SHA或提交信息"
          clearable
          @change="handleFilterChange"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-col>
    </el-row>

    <!-- Pipeline列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>Pipeline列表 ({{ filteredPipelines.length }})</span>
            <!-- WebSocket连接状态指示器 -->
            <el-tooltip :content="wsConnected ? '实时更新已连接' : '实时更新已断开'" placement="top">
              <div class="ws-status" :class="{ connected: wsConnected }">
                <div class="ws-indicator"></div>
              </div>
            </el-tooltip>
          </div>
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button label="list">列表视图</el-radio-button>
            <el-radio-button label="graph">图形视图</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'">
        <el-table :data="paginatedPipelines" style="width: 100%" @row-click="viewPipelineDetail">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="project" label="项目" width="150" show-overflow-tooltip />
          <el-table-column prop="branch" label="分支" width="120" />
          <el-table-column prop="sha" label="SHA" width="80">
            <template #default="scope">
              <el-tooltip :content="scope.row.sha" placement="top">
                <span class="sha-short">{{ scope.row.sha.substring(0, 8) }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="scope">
              <el-tag :type="getStatusTagType(scope.row.status)" size="small">
                {{ getStatusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration" label="耗时" width="100" align="right">
            <template #default="scope">
              {{ formatDuration(scope.row.duration) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="scope">
              <el-button type="text" size="small" @click.stop="viewPipelineDetail(scope.row)">
                详情
              </el-button>
              <el-button
                v-if="scope.row.status === 'running'"
                type="text"
                size="small"
                @click.stop="cancelPipeline(scope.row)"
              >
                取消
              </el-button>
              <el-button
                type="text"
                size="small"
                @click.stop="retryPipeline(scope.row)"
              >
                重试
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="filteredPipelines.length"
            layout="total, sizes, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>

      <!-- 图形视图 -->
      <div v-else class="graph-view">
        <el-timeline>
          <el-timeline-item
            v-for="pipeline in paginatedPipelines"
            :key="pipeline.id"
            :timestamp="formatTime(pipeline.created_at)"
            placement="top"
          >
            <el-card @click="viewPipelineDetail(pipeline)" class="pipeline-card">
              <div class="pipeline-header">
                <div class="pipeline-info">
                  <el-tag :type="getStatusTagType(pipeline.status)" size="small">
                    {{ getStatusLabel(pipeline.status) }}
                  </el-tag>
                  <span class="pipeline-project">{{ pipeline.project }}</span>
                  <span class="pipeline-branch">{{ pipeline.branch }}</span>
                </div>
                <div class="pipeline-meta">
                  <span class="pipeline-duration">{{ formatDuration(pipeline.duration) }}</span>
                  <span class="pipeline-sha">{{ pipeline.sha.substring(0, 8) }}</span>
                </div>
              </div>

              <!-- Stage流程图 -->
              <div class="stages-flow">
                <div
                  v-for="(stage, index) in pipeline.stages"
                  :key="stage.name"
                  class="stage-item"
                  :class="getStageClass(stage)"
                >
                  <div class="stage-icon">
                    <el-icon v-if="stage.status === 'success'"><SuccessFilled /></el-icon>
                    <el-icon v-else-if="stage.status === 'failed'"><CircleCloseFilled /></el-icon>
                    <el-icon v-else-if="stage.status === 'running'"><Loading /></el-icon>
                    <el-icon v-else><Clock /></el-icon>
                  </div>
                  <div class="stage-info">
                    <div class="stage-name">{{ stage.name }}</div>
                    <div class="stage-duration">{{ formatDuration(stage.duration) }}</div>
                  </div>
                  <el-icon v-if="index < pipeline.stages.length - 1" class="stage-arrow">
                    <ArrowRight />
                  </el-icon>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50]"
            :total="filteredPipelines.length"
            layout="total, sizes, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>

    <!-- Pipeline详情对话框 -->
    <el-dialog
      v-model="pipelineDetailVisible"
      :title="`Pipeline详情: ${currentPipeline?.id}`"
      width="90%"
      top="5vh"
    >
      <div v-if="currentPipeline" class="pipeline-detail">
        <!-- 基本信息 -->
        <el-descriptions :column="3" border>
          <el-descriptions-item label="项目">{{ currentPipeline.project }}</el-descriptions-item>
          <el-descriptions-item label="分支">{{ currentPipeline.branch }}</el-descriptions-item>
          <el-descriptions-item label="SHA">{{ currentPipeline.sha }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(currentPipeline.status)">
              {{ getStatusLabel(currentPipeline.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ formatDuration(currentPipeline.duration) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(currentPipeline.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <!-- AI诊断 -->
        <div v-if="currentPipeline.ai_diagnosis" class="ai-diagnosis">
          <el-divider>AI诊断分析</el-divider>
          <el-alert
            :type="currentPipeline.status === 'failed' ? 'error' : 'success'"
            :closable="false"
          >
            <template #title>
              {{ currentPipeline.ai_diagnosis.summary }}
            </template>
            <div v-if="currentPipeline.ai_diagnosis.root_cause">
              <strong>根因分析:</strong> {{ currentPipeline.ai_diagnosis.root_cause }}
            </div>
            <div v-if="currentPipeline.ai_diagnosis.suggestion" style="margin-top: 8px">
              <strong>修复建议:</strong> {{ currentPipeline.ai_diagnosis.suggestion }}
            </div>
          </el-alert>
        </div>

        <!-- Stage流程图 -->
        <el-divider>Stage流程</el-divider>
        <div class="detail-stages-flow">
          <div
            v-for="(stage, index) in currentPipeline.stages"
            :key="stage.name"
            class="detail-stage-item"
            :class="getStageClass(stage)"
            @click="viewStageDetail(stage)"
          >
            <div class="stage-header">
              <div class="stage-icon-large">
                <el-icon v-if="stage.status === 'success'"><SuccessFilled /></el-icon>
                <el-icon v-else-if="stage.status === 'failed'"><CircleCloseFilled /></el-icon>
                <el-icon v-else-if="stage.status === 'running'"><Loading /></el-icon>
                <el-icon v-else><Clock /></el-icon>
              </div>
              <div class="stage-name">{{ stage.name }}</div>
              <el-tag :type="getStatusTagType(stage.status)" size="small">
                {{ getStatusLabel(stage.status) }}
              </el-tag>
            </div>
            <div class="stage-jobs">
              <div v-for="job in stage.jobs" :key="job.name" class="job-item">
                <el-icon v-if="job.status === 'success'"><SuccessFilled /></el-icon>
                <el-icon v-else-if="job.status === 'failed'"><CircleCloseFilled /></el-icon>
                <el-icon v-else-if="job.status === 'running'"><Loading /></el-icon>
                <el-icon v-else><Clock /></el-icon>
                <span>{{ job.name }}</span>
                <span class="job-duration">{{ formatDuration(job.duration) }}</span>
              </div>
            </div>
            <el-icon v-if="index < currentPipeline.stages.length - 1" class="stage-arrow-large">
              <ArrowRight />
            </el-icon>
          </div>
        </div>

        <!-- 性能分析 -->
        <el-divider>性能分析</el-divider>
        <div class="performance-analysis">
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="performance-card">
                <div class="performance-title">执行时间对比</div>
                <div ref="performanceChartRef" class="chart-container"></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="performance-card">
                <div class="performance-title">资源使用</div>
                <div ref="resourceChartRef" class="chart-container"></div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 实时日志 -->
        <el-divider>实时日志</el-divider>
        <div class="logs-section">
          <div class="logs-header">
            <el-select v-model="selectedJob" placeholder="选择Job" size="small" style="width: 200px">
              <el-option
                v-for="stage in currentPipeline.stages"
                v-for="job in stage.jobs"
                :key="job.id"
                :label="job.name"
                :value="job.id"
              />
            </el-select>
            <el-button size="small" @click="refreshLogs">刷新</el-button>
            <el-button size="small" @click="downloadLogs">下载</el-button>
            <el-switch v-model="autoScroll" active-text="自动滚动" size="small" />
          </div>
          <div class="logs-content" ref="logsContentRef">
            <div
              v-for="(log, index) in currentLogs"
              :key="index"
              class="log-line"
              :class="`log-${log.level}`"
            >
              <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
              <span class="log-level">{{ log.level.toUpperCase() }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import {
  Search,
  SuccessFilled,
  CircleCloseFilled,
  Clock,
  Loading,
  ArrowRight
} from '@element-plus/icons-vue'
import { usePipelineStore, useProjectStore } from '@/stores'
import { pipelineApi } from '@/api'
import { useWebSocket } from '@/composables/useWebSocket'
import { SkeletonLoader, EmptyState } from '@/components/common'
import type { Pipeline, PipelineFilters } from '@/types'

const router = useRouter()
const pipelineStore = usePipelineStore()
const projectStore = useProjectStore()

// 获取当前项目ID
const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态
const loading = ref(false)
const error = ref<string | null>(null)

// 筛选器
const filters = ref({
  status: '',
  branch: '',
  source: '',
  search: ''
})

// 视图模式
const viewMode = ref('list')

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20
})

// Pipeline详情
const pipelineDetailVisible = ref(false)
const currentPipeline = ref<any>(null)
const selectedJob = ref('')
const autoScroll = ref(true)
const currentLogs = ref<any[]>([])
const logsContentRef = ref<HTMLElement>()

// 图表
const performanceChartRef = ref<HTMLElement>()
const resourceChartRef = ref<HTMLElement>()
const performanceChart = ref<ECharts>()
const resourceChart = ref<ECharts>()

// WebSocket实时通信
const {
  isConnected: wsConnected,
  subscribeTo,
  unsubscribeFrom,
  statusUpdates,
  clearStatusUpdates
} = useWebSocket({
  autoConnect: true,
  subscribe: ['pipeline_updates', 'job_updates']
})

// Pipeline列表 - 从store获取
const pipelines = computed(() => pipelineStore.pipelines)

// 过滤后的Pipeline
const filteredPipelines = computed(() => {
  let result = pipelines.value

  if (filters.value.status) {
    result = result.filter(p => p.status === filters.value.status)
  }

  if (filters.value.branch) {
    if (filters.value.branch === 'feature') {
      result = result.filter(p => p.branch.startsWith('feature'))
    } else {
      result = result.filter(p => p.branch === filters.value.branch)
    }
  }

  if (filters.value.source) {
    result = result.filter(p => p.source === filters.value.source)
  }

  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    result = result.filter(p =>
      p.sha.includes(search) ||
      p.project.toLowerCase().includes(search)
    )
  }

  return result
})

// 判断是否有筛选条件
const hasFilters = computed(() => {
  return !!(filters.value.status || filters.value.branch || filters.value.source || filters.value.search)
})

// 清除筛选
const clearFilters = () => {
  filters.value = {
    status: '',
    branch: '',
    source: '',
    search: ''
  }
}

// 创建Pipeline
const createPipeline = () => {
  // 跳转到创建Pipeline页面或打开对话框
  ElMessage.info('创建Pipeline功能开发中')
}

// 分页后的Pipeline
const paginatedPipelines = computed(() => {
  const start = (pagination.value.currentPage - 1) * pagination.value.pageSize
  const end = start + pagination.value.pageSize
  return filteredPipelines.value.slice(start, end)
})

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const typeMap: Record<string, any> = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    cancelled: 'info',
    pending: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态标签
const getStatusLabel = (status: string) => {
  const labelMap: Record<string, string> = {
    success: '成功',
    failed: '失败',
    running: '运行中',
    cancelled: '已取消',
    pending: '待处理'
  }
  return labelMap[status] || status
}

// 格式化持续时间
const formatDuration = (seconds: number) => {
  if (seconds < 60) {
    return `${seconds}s`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}m ${secs}s`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }
}

// 格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleString('zh-CN')
  }
}

// 格式化日志时间
const formatLogTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN')
}

// 获取Stage样式类
const getStageClass = (stage: any) => {
  return `stage-${stage.status}`
}

// 处理筛选变化
const handleFilterChange = () => {
  pagination.value.currentPage = 1
}

// 分页处理
const handleSizeChange = (val: number) => {
  pagination.value.pageSize = val
}

const handleCurrentChange = (val: number) => {
  pagination.value.currentPage = val
}

// 查看Pipeline详情
const viewPipelineDetail = async (pipeline: any) => {
  currentPipeline.value = pipeline
  pipelineDetailVisible.value = true

  // 加载日志
  await loadLogs(pipeline)

  // 初始化图表
  await nextTick()
  initPerformanceChart()
  initResourceChart()
}

// 查看Stage详情
const viewStageDetail = (stage: any) => {
  console.log('View stage detail:', stage)
  // TODO: 显示Stage详情
}

// 加载日志
const loadLogs = async (pipeline: any) => {
  // 模拟日志数据
  currentLogs.value = [
    { timestamp: Date.now() - 10000, level: 'info', message: 'Starting pipeline...' },
    { timestamp: Date.now() - 9500, level: 'info', message: 'Cloning repository...' },
    { timestamp: Date.now() - 9000, level: 'info', message: 'Checking out commit: ' + pipeline.sha.substring(0, 8) },
    { timestamp: Date.now() - 8500, level: 'info', message: 'Stage: build' },
    { timestamp: Date.now() - 8000, level: 'info', message: 'Job: compile' },
    { timestamp: Date.now() - 7000, level: 'info', message: 'Running CMake...' },
    { timestamp: Date.now() - 6000, level: 'info', message: 'Compiling source files...' },
    { timestamp: Date.now() - 5000, level: 'warning', message: 'Warning: unused variable in main.cpp' },
    { timestamp: Date.now() - 4000, level: 'info', message: 'Linking binaries...' },
    { timestamp: Date.now() - 3000, level: 'info', message: 'Build completed successfully' },
    { timestamp: Date.now() - 2000, level: 'info', message: 'Stage: test' },
    { timestamp: Date.now() - 1000, level: 'info', message: 'Job: unit_tests' },
    { timestamp: Date.now() - 500, level: 'success', message: 'All tests passed!' }
  ]

  // 自动滚动到底部
  if (autoScroll.value) {
    await nextTick()
    scrollToBottom()
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (logsContentRef.value) {
    logsContentRef.value.scrollTop = logsContentRef.value.scrollHeight
  }
}

// 刷新日志
const refreshLogs = async () => {
  if (currentPipeline.value) {
    await loadLogs(currentPipeline.value)
  }
}

// 下载日志
const downloadLogs = () => {
  const logContent = currentLogs.value
    .map(log => `[${formatLogTime(log.timestamp)}] [${log.level.toUpperCase()}] ${log.message}`)
    .join('\n')

  const blob = new Blob([logContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `pipeline-${currentPipeline.value.id}-logs.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// 取消Pipeline
const cancelPipeline = async (pipeline: Pipeline) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消Pipeline ${pipeline.pipeline_id} 吗？`,
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await pipelineApi.cancelPipeline(pipeline.id.toString())
    ElMessage.success('Pipeline已取消')

    // 重新加载列表
    if (currentProjectId.value) {
      await loadPipelines()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Cancel pipeline failed:', error)
      ElMessage.error(error.message || '取消Pipeline失败')
    }
  }
}

// 重试Pipeline
const retryPipeline = async (pipeline: Pipeline) => {
  try {
    await ElMessageBox.confirm(
      `确定要重试Pipeline ${pipeline.pipeline_id} 吗？`,
      '确认重试',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    await pipelineApi.retryPipeline(pipeline.id.toString())
    ElMessage.success('Pipeline已重新运行')

    // 重新加载列表
    if (currentProjectId.value) {
      await loadPipelines()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Retry pipeline failed:', error)
      ElMessage.error(error.message || '重试Pipeline失败')
    }
  }
}

// 加载Pipeline列表
const loadPipelines = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 构建筛选参数
    const params: PipelineFilters = {}
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.source) params.source = filters.value.source as any
    if (filters.value.branch) params.ref = filters.value.branch
    if (filters.value.search) params.sha = filters.value.search

    await pipelineStore.fetchPipelines(currentProjectId.value)
  } catch (err: any) {
    console.error('Failed to load pipelines:', err)
    error.value = err.message || '加载Pipeline列表失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 初始化性能图表
const initPerformanceChart = () => {
  if (!performanceChartRef.value) return

  performanceChart.value = echarts.init(performanceChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: ['Pipeline 1', 'Pipeline 2', 'Pipeline 3', 'Pipeline 4', 'Pipeline 5']
    },
    yAxis: {
      type: 'value',
      name: '时间 (秒)'
    },
    series: [
      {
        name: '当前Pipeline',
        type: 'bar',
        data: [456, 234, 567, 345, 432],
        itemStyle: { color: '#409eff' }
      },
      {
        name: '平均时间',
        type: 'line',
        data: [420, 410, 430, 415, 425],
        smooth: true,
        itemStyle: { color: '#67c23a' }
      }
    ]
  }

  performanceChart.value.setOption(option)
}

// 初始化资源图表
const initResourceChart = () => {
  if (!resourceChartRef.value) return

  resourceChart.value = echarts.init(resourceChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['CPU使用率', '内存使用率']
    },
    xAxis: {
      type: 'category',
      data: ['0s', '30s', '60s', '90s', '120s', '150s', '180s']
    },
    yAxis: {
      type: 'value',
      name: '使用率 (%)',
      max: 100
    },
    series: [
      {
        name: 'CPU使用率',
        type: 'line',
        data: [20, 45, 78, 65, 55, 40, 30],
        smooth: true,
        itemStyle: { color: '#409eff' }
      },
      {
        name: '内存使用率',
        type: 'line',
        data: [15, 35, 55, 60, 52, 45, 38],
        smooth: true,
        itemStyle: { color: '#67c23a' }
      }
    ]
  }

  resourceChart.value.setOption(option)
}

onMounted(() => {
  // 加载Pipeline列表
  loadPipelines()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()

  window.addEventListener('resize', () => {
    performanceChart.value?.resize()
    resourceChart.value?.resize()
  })
})

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 监听Pipeline状态更新
  subscribeTo('pipeline_updates')

  // 监听Job状态更新
  subscribeTo('job_updates')

  // 监听状态更新消息
  const unsubscribe = statusUpdates.value

  // 当收到状态更新时，刷新Pipeline列表
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新列表
      if (currentProjectId.value) {
        loadPipelines()
      }
    }
  })
}

// 监听筛选变化
watch(filters, () => {
  pagination.value.currentPage = 1
  loadPipelines()
}, { deep: true })

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadPipelines()
  }
})

onUnmounted(() => {
  // 清理图表资源
  performanceChart.value?.dispose()
  resourceChart.value?.dispose()

  // 清理状态更新
  clearStatusUpdates()

  // WebSocket会自动断开（由useWebSocket composable处理）
})
</script>

<style scoped>
.pipelines {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* WebSocket状态指示器 */
.ws-status {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 12px;
  background-color: #f5f5f5;
  transition: all 0.3s;
}

.ws-status.connected {
  background-color: #f0f9ff;
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
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.sha-short {
  font-family: 'Courier New', monospace;
  color: #409eff;
  cursor: pointer;
}

.sha-short:hover {
  text-decoration: underline;
}

/* 图形视图 */
.graph-view {
  padding: 10px 0;
}

.pipeline-card {
  cursor: pointer;
  transition: all 0.3s;
}

.pipeline-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.pipeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pipeline-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pipeline-project {
  font-weight: bold;
  color: #303133;
}

.pipeline-branch {
  color: #909399;
  font-size: 14px;
}

.pipeline-meta {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: #606266;
}

.stages-flow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: #f5f7fa;
}

.stage-item.stage-success {
  background-color: #f0f9ff;
  border: 1px solid #b3e19d;
}

.stage-item.stage-failed {
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
}

.stage-item.stage-running {
  background-color: #fdf6ec;
  border: 1px solid #f5dab1;
}

.stage-icon {
  font-size: 20px;
}

.stage-item.stage-success .stage-icon {
  color: #67c23a;
}

.stage-item.stage-failed .stage-icon {
  color: #f56c6c;
}

.stage-item.stage-running .stage-icon {
  color: #e6a23c;
}

.stage-info {
  text-align: center;
}

.stage-name {
  font-size: 13px;
  font-weight: bold;
  color: #303133;
}

.stage-duration {
  font-size: 12px;
  color: #909399;
}

.stage-arrow {
  color: #c0c4cc;
  font-size: 18px;
}

/* Pipeline详情 */
.pipeline-detail {
  padding: 10px 0;
}

.ai-diagnosis {
  margin: 20px 0;
}

.detail-stages-flow {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin: 20px 0;
  overflow-x: auto;
  padding: 20px 0;
}

.detail-stage-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 150px;
  padding: 16px;
  border-radius: 8px;
  background-color: #f5f7fa;
  cursor: pointer;
  transition: all 0.3s;
  flex-shrink: 0;
}

.detail-stage-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.detail-stage-item.stage-success {
  background-color: #f0f9ff;
  border: 2px solid #b3e19d;
}

.detail-stage-item.stage-failed {
  background-color: #fef0f0;
  border: 2px solid #fbc4c4;
}

.detail-stage-item.stage-running {
  background-color: #fdf6ec;
  border: 2px solid #f5dab1;
}

.detail-stage-item.stage-pending {
  background-color: #fafafa;
  border: 2px solid #dcdfe6;
}

.stage-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-icon-large {
  font-size: 36px;
}

.detail-stage-item.stage-success .stage-icon-large {
  color: #67c23a;
}

.detail-stage-item.stage-failed .stage-icon-large {
  color: #f56c6c;
}

.detail-stage-item.stage-running .stage-icon-large {
  color: #e6a23c;
  animation: spin 1s linear infinite;
}

.detail-stage-item.stage-pending .stage-icon-large {
  color: #909399;
}

.stage-name {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  text-align: center;
}

.stage-jobs {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.job-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  color: #606266;
}

.job-duration {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

.stage-arrow-large {
  font-size: 24px;
  color: #c0c4cc;
  align-self: center;
  flex-shrink: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.performance-analysis {
  margin: 20px 0;
}

.performance-card {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
}

.performance-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 12px;
}

.chart-container {
  width: 100%;
  height: 200px;
}

.logs-section {
  margin: 20px 0;
}

.logs-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.logs-content {
  background-color: #1e1e1e;
  border-radius: 6px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-line {
  display: flex;
  gap: 12px;
  line-height: 1.6;
}

.log-time {
  color: #909399;
  min-width: 80px;
}

.log-level {
  min-width: 60px;
  font-weight: bold;
}

.log-info .log-level {
  color: #409eff;
}

.log-warning .log-level {
  color: #e6a23c;
}

.log-error .log-level {
  color: #f56c6c;
}

.log-success .log-level {
  color: #67c23a;
}

.log-message {
  color: #c0c4cc;
  flex: 1;
  word-break: break-all;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
