<template>
  <div class="code-review">
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
        <el-col :span="8" v-for="i in 4" :key="i">
          <SkeletonLoader type="stat" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="24">
          <SkeletonLoader type="chart" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="24">
          <SkeletonLoader type="table" :rows="8" />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 - 无代码审查数据时显示 -->
    <el-card v-else-if="!loading && hasNoCodeReviewData">
      <EmptyState
        type="no-data"
        title="暂无代码审查数据"
        description="还没有进行任何代码审查，请先运行代码审查"
        :show-action="true"
        action-text="运行代码审查"
        @action="runCodeReview"
      />
    </el-card>

    <!-- 实际内容 -->
    <template v-if="!loading && !hasNoCodeReviewData">
      <!-- 页面标题和WebSocket状态 -->
      <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0;">代码质量报告</h2>
        <el-tooltip :content="wsConnected ? '实时更新已连接' : '实时更新已断开'">
          <div class="ws-status" :class="{ connected: wsConnected }">
            <div class="ws-indicator"></div>
          </div>
        </el-tooltip>
      </div>

      <!-- 质量评分卡片 -->
      <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="score-card">
          <div class="score-content">
            <div class="score-circle" :class="getScoreClass(qualityScore.overall)">
              <div class="score-value">{{ qualityScore.overall }}</div>
              <div class="score-label">总分</div>
            </div>
            <div class="score-details">
              <div class="score-item">
                <span class="label">内存安全</span>
                <el-progress
                  :percentage="qualityScore.memorySafety"
                  :color="getScoreColor(qualityScore.memorySafety)"
                  :show-text="false"
                />
              </div>
              <div class="score-item">
                <span class="label">性能</span>
                <el-progress
                  :percentage="qualityScore.performance"
                  :color="getScoreColor(qualityScore.performance)"
                  :show-text="false"
                />
              </div>
              <div class="score-item">
                <span class="label">现代C++</span>
                <el-progress
                  :percentage="qualityScore.modernCpp"
                  :color="getScoreColor(qualityScore.modernCpp)"
                  :show-text="false"
                />
              </div>
              <div class="score-item">
                <span class="label">线程安全</span>
                <el-progress
                  :percentage="qualityScore.threadSafety"
                  :color="getScoreColor(qualityScore.threadSafety)"
                  :show-text="false"
                />
              </div>
              <div class="score-item">
                <span class="label">代码风格</span>
                <el-progress
                  :percentage="qualityScore.codeStyle"
                  :color="getScoreColor(qualityScore.codeStyle)"
                  :show-text="false"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>问题统计</span>
              <div class="header-actions">
                <el-radio-group v-model="issuePeriod" size="small">
                  <el-radio-button label="今日">今日</el-radio-button>
                  <el-radio-button label="本周">本周</el-radio-button>
                  <el-radio-button label="本月">本月</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="6" v-for="(stat, index) in issueStats" :key="index">
              <div class="stat-item" :style="{ borderColor: stat.color }">
                <div class="stat-icon" :style="{ backgroundColor: stat.color }">
                  <el-icon :size="24">
                    <component :is="stat.icon" />
                  </el-icon>
                </div>
                <div class="stat-content">
                  <div class="stat-value">{{ stat.value }}</div>
                  <div class="stat-label">{{ stat.label }}</div>
                  <div class="stat-trend" :class="stat.trend > 0 ? 'trend-up' : 'trend-down'">
                    <el-icon><CaretTop v-if="stat.trend > 0" /><CaretBottom v-else /></el-icon>
                    {{ Math.abs(stat.trend) }}%
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 增量审查视图 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>增量审查</span>
              <el-tag type="success">当前MR</el-tag>
            </div>
          </template>
          <div class="incremental-review">
            <div class="review-summary">
              <div class="summary-item">
                <span class="summary-label">新增问题:</span>
                <span class="summary-value new">{{ incrementalReview.newIssues }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">修复问题:</span>
                <span class="summary-value fixed">{{ incrementalReview.fixedIssues }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">净增技术债务:</span>
                <span
                  class="summary-value"
                  :class="incrementalReview.netDebt > 0 ? 'debt-increase' : 'debt-decrease'"
                >
                  {{ incrementalReview.netDebt > 0 ? '+' : '' }}{{ incrementalReview.netDebt }}
                </span>
              </div>
            </div>

            <el-divider />

            <div class="changed-files">
              <div class="files-header">
                <span>变更文件 ({{ incrementalReview.changedFiles.length }})</span>
                <el-button type="text" size="small">查看全部</el-button>
              </div>
              <el-table
                :data="incrementalReview.changedFiles"
                style="width: 100%"
                max-height="300"
              >
                <el-table-column prop="path" label="文件路径" show-overflow-tooltip />
                <el-table-column prop="issues" label="问题数" width="80" align="center">
                  <template #default="scope">
                    <el-tag
                      :type="scope.row.issues > 0 ? 'danger' : 'success'"
                      size="small"
                    >
                      {{ scope.row.issues }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="score" label="评分" width="80" align="center">
                  <template #default="scope">
                    <span :style="{ color: getScoreColor(scope.row.score) }">
                      {{ scope.row.score }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 技术债务趋势 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>技术债务趋势</span>
              <el-radio-group v-model="debtTrendPeriod" size="small">
                <el-radio-button label="7天">近7天</el-radio-button>
                <el-radio-button label="30天">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="debtTrendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 问题列表 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>代码质量问题</span>
              <div class="header-actions">
                <el-select v-model="issueFilter.severity" placeholder="严重程度" size="small" style="width: 120px; margin-right: 10px">
                  <el-option label="全部" value="all" />
                  <el-option label="严重" value="critical" />
                  <el-option label="高" value="high" />
                  <el-option label="中" value="medium" />
                  <el-option label="低" value="low" />
                </el-select>
                <el-select v-model="issueFilter.type" placeholder="问题类型" size="small" style="width: 150px">
                  <el-option label="全部" value="all" />
                  <el-option label="内存安全" value="memory" />
                  <el-option label="性能" value="performance" />
                  <el-option label="现代C++" value="modern_cpp" />
                  <el-option label="线程安全" value="thread_safety" />
                  <el-option label="代码风格" value="code_style" />
                </el-select>
              </div>
            </div>
          </template>
          <el-table
            :data="filteredIssues"
            style="width: 100%"
            :default-sort="{ prop: 'severity', order: 'descending' }"
          >
            <el-table-column prop="file" label="文件" show-overflow-tooltip width="300" />
            <el-table-column prop="line" label="行号" width="80" align="center" />
            <el-table-column prop="severity" label="严重程度" width="100" align="center">
              <template #default="scope">
                <el-tag :type="getSeverityTagType(scope.row.severity)" size="small">
                  {{ getSeverityLabel(scope.row.severity) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="120">
              <template #default="scope">
                <el-tag type="info" size="small">{{ scope.row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="问题描述" show-overflow-tooltip />
            <el-table-column prop="aiFiltered" label="AI判断" width="100" align="center">
              <template #default="scope">
                <el-tag v-if="scope.row.aiFiltered" type="success" size="small">
                  误报
                </el-tag>
                <el-tag v-else type="info" size="small">
                  真实
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewIssueDetail(scope.row)">
                  详情
                </el-button>
                <el-button
                  v-if="scope.row.suggestion"
                  type="text"
                  size="small"
                  @click="applyFix(scope.row)"
                >
                  应用修复
                </el-button>
                <el-button type="text" size="small" @click="markFalsePositive(scope.row)">
                  标记误报
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="pagination.currentPage"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 问题详情对话框 -->
    <el-dialog v-model="issueDetailVisible" title="问题详情" width="70%">
      <div v-if="currentIssue" class="issue-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="文件">{{ currentIssue.file }}</el-descriptions-item>
          <el-descriptions-item label="行号">{{ currentIssue.line }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityTagType(currentIssue.severity)">
              {{ getSeverityLabel(currentIssue.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag type="info">{{ currentIssue.type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工具来源">{{ currentIssue.tool }}</el-descriptions-item>
          <el-descriptions-item label="AI判断">
            <el-tag :type="currentIssue.aiFiltered ? 'success' : 'info'">
              {{ currentIssue.aiFiltered ? '误报' : '真实问题' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>问题描述</el-divider>
        <div class="issue-message">{{ currentIssue.message }}</div>

        <el-divider v-if="currentIssue.code">代码片段</el-divider>
        <div v-if="currentIssue.code" class="code-snippet">
          <pre><code>{{ currentIssue.code }}</code></pre>
        </div>

        <el-divider v-if="currentIssue.suggestion">修复建议</el-divider>
        <div v-if="currentIssue.suggestion" class="fix-suggestion">
          <el-alert type="info" :closable="false">
            <template #title>
              <div>{{ currentIssue.suggestion }}</div>
            </template>
          </el-alert>

          <div v-if="currentIssue.fixCode" style="margin-top: 16px">
            <div class="fix-code-title">修复代码:</div>
            <div class="code-diff">
              <pre><code>{{ currentIssue.fixCode }}</code></pre>
            </div>
          </div>
        </div>

        <el-divider>AI分析</el-divider>
        <div class="ai-analysis">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="置信度">
              <el-progress
                :percentage="currentIssue.confidence"
                :color="getConfidenceColor(currentIssue.confidence)"
              />
            </el-descriptions-item>
            <el-descriptions-item label="AI建议">
              {{ currentIssue.aiSuggestion }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <template #footer>
        <el-button @click="issueDetailVisible = false">关闭</el-button>
        <el-button v-if="currentIssue && !currentIssue.aiFiltered" type="primary" @click="applyFix(currentIssue)">
          应用修复
        </el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import {
  WarningFilled,
  InfoFilled,
  CircleCloseFilled,
  CaretTop,
  CaretBottom
} from '@element-plus/icons-vue'
import { useCodeReviewStore, useDashboardStore, useProjectStore } from '@/stores'
import { SkeletonLoader, EmptyState } from '@/components/common'
import { useWebSocket } from '@/composables/useWebSocket'
import { codeReviewApi } from '@/api'
import type { CodeIssue, QualityScore } from '@/types'

const codeReviewStore = useCodeReviewStore()
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
  subscribe: ['code_review_updates', 'issue_updates']
})

// 获取当前项目ID
const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态
const loading = ref(false)
const error = ref<string | null>(null)

const issuePeriod = ref('今日')
const debtTrendPeriod = ref('7天')
const issueDetailVisible = ref(false)
const currentIssue = ref<CodeIssue | null>(null)

const debtTrendChartRef = ref<HTMLElement>()
const debtTrendChart = ref<ECharts>()

// 质量评分 - 从store获取
const qualityScore = computed(() => {
  const score = codeReviewStore.qualityScore
  if (!score) {
    return {
      overall: 0,
      memorySafety: 0,
      performance: 0,
      modernCpp: 0,
      threadSafety: 0,
      codeStyle: 0
    }
  }
  return {
    overall: Math.round(score.overall),
    memorySafety: Math.round(score.memory_safety),
    performance: Math.round(score.performance),
    modernCpp: Math.round(score.modern_cpp),
    threadSafety: Math.round(score.thread_safety),
    codeStyle: Math.round(score.code_style)
  }
})

// 问题统计 - 从store获取
const issueStats = computed(() => {
  const stats = codeReviewStore.codeReviewStats
  if (!stats) {
    return []
  }

  return [
    {
      label: '严重问题',
      value: stats.critical_issues,
      trend: -15, // TODO: 从趋势数据计算
      color: '#f56c6c',
      icon: CircleCloseFilled
    },
    {
      label: '高危问题',
      value: stats.high_issues,
      trend: -8,
      color: '#e6a23c',
      icon: WarningFilled
    },
    {
      label: '中等问题',
      value: stats.medium_issues,
      trend: 5,
      color: '#409eff',
      icon: InfoFilled
    },
    {
      label: '低级问题',
      value: stats.low_issues,
      trend: 12,
      color: '#67c23a',
      icon: InfoFilled
    }
  ]
})

// 增量审查 - 从API获取
const incrementalReview = ref({
  newIssues: 0,
  fixedIssues: 0,
  netDebt: 0,
  changedFiles: [] as Array<{ path: string; issues: number; score: number }>
})

// 问题列表 - 从store获取
const issues = computed(() => {
  return codeReviewStore.codeIssues.map(issue => ({
    id: issue.id,
    file: issue.file_path,
    line: issue.line_number,
    severity: issue.severity,
    type: issue.category,
    message: issue.message,
    tool: issue.detector,
    aiFiltered: issue.is_false_positive,
    confidence: issue.confidence,
    code: issue.code_snippet || '',
    suggestion: issue.fix_suggestion?.description || '',
    fixCode: issue.fix_suggestion?.fix_code || '',
    aiSuggestion: issue.has_fix ? 'AI已生成修复代码' : ''
  }))
})

// 问题筛选
const issueFilter = ref({
  severity: 'all',
  type: 'all'
})

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 10,
  total: computed(() => codeReviewStore.pagination.total)
})

// 过滤后的问题
const filteredIssues = computed(() => {
  let result = issues.value

  if (issueFilter.value.severity !== 'all') {
    result = result.filter(issue => issue.severity === issueFilter.value.severity)
  }

  if (issueFilter.value.type !== 'all') {
    const typeMap: Record<string, string> = {
      memory: '内存安全',
      performance: '性能',
      modern_cpp: '现代C++',
      thread_safety: '线程安全',
      code_style: '代码风格'
    }
    result = result.filter(issue => issue.type === typeMap[issueFilter.value.type])
  }

  return result
})

// 获取评分等级
const getScoreClass = (score: number) => {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  return 'score-poor'
}

// 获取评分颜色
const getScoreColor = (score: number) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

// 获取严重程度标签类型
const getSeverityTagType = (severity: string) => {
  const typeMap: Record<string, any> = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'success'
  }
  return typeMap[severity] || 'info'
}

// 获取严重程度标签
const getSeverityLabel = (severity: string) => {
  const labelMap: Record<string, string> = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低'
  }
  return labelMap[severity] || severity
}

// 获取置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 90) return '#67c23a'
  if (confidence >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 判断是否有代码审查数据
const hasNoCodeReviewData = computed(() => {
  const score = codeReviewStore.qualityScore
  const issues = codeReviewStore.codeIssues
  return (!score || score.overall === 0) && (!issues || issues.length === 0)
})

// 运行代码审查
const runCodeReview = () => {
  ElMessage.info('运行代码审查功能开发中')
}

// 查看问题详情
const viewIssueDetail = async (issue: any) => {
  try {
    await codeReviewStore.fetchCodeIssue(issue.id)
    currentIssue.value = codeReviewStore.currentIssue
    issueDetailVisible.value = true
  } catch (error) {
    console.error('Failed to load issue detail:', error)
  }
}

// 应用修复
const applyFix = async (issue: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要应用此修复建议吗？这将创建一个新的MR。',
      '确认应用修复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    loading.value = true
    const result = await codeReviewStore.applyFix(issue.id)

    ElMessage.success('修复已应用到MR: ' + result.mr_id)

    // 重新加载数据
    if (currentProjectId.value) {
      await loadCodeReviewData()
    }
  } catch (err: any) {
    if (err !== 'cancel') {
      console.error('Apply fix failed:', err)
      ElMessage.error(err.message || '应用修复失败')
    }
  } finally {
    loading.value = false
  }
}

// 标记误报
const markFalsePositive = async (issue: any, reason: string = '用户标记为误报') => {
  try {
    await codeReviewStore.markAsFalsePositive(issue.id, reason)
    ElMessage.success('已标记为误报')

    // 重新加载数据
    if (currentProjectId.value) {
      await loadCodeReviewData()
    }
  } catch (error) {
    console.error('Mark as false positive failed:', error)
    ElMessage.error('标记误报失败')
  }
}

// 分页处理
const handleSizeChange = (val: number) => {
  pagination.value.pageSize = val
  loadCodeIssues()
}

const handleCurrentChange = (val: number) => {
  pagination.value.currentPage = val
  loadCodeIssues()
}

// 加载代码审查数据
const loadCodeReviewData = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 并行加载数据
    await Promise.all([
      dashboardStore.fetchCodeReviewStats(currentProjectId.value),
      codeReviewStore.fetchQualityScore(currentProjectId.value),
      codeReviewStore.fetchQualityTrend(currentProjectId.value, 7),
      codeReviewStore.fetchTechDebtTrend(currentProjectId.value, 7)
    ])

    // 初始化图表
    await nextTick()
    initDebtTrendChart()
  } catch (err: any) {
    console.error('Failed to load code review data:', err)
    error.value = err.message || '加载代码审查数据失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 加载代码问题列表
const loadCodeIssues = async () => {
  if (!currentProjectId.value) return

  try {
    // 使用当前审查ID或项目ID
    const reviewId = codeReviewStore.currentReview?.id
    if (reviewId) {
      await codeReviewStore.fetchCodeIssues(reviewId, {
        page: pagination.value.currentPage,
        per_page: pagination.value.pageSize,
        severity: issueFilter.value.severity === 'all' ? undefined : issueFilter.value.severity,
        category: issueFilter.value.type === 'all' ? undefined : issueFilter.value.type
      })
    }
  } catch (err: any) {
    console.error('Failed to load code issues:', err)
  }
}

// 初始化技术债务趋势图
const initDebtTrendChart = () => {
  if (!debtTrendChartRef.value) return

  debtTrendChart.value = echarts.init(debtTrendChartRef.value)

  const trendData = codeReviewStore.techDebtTrend
  const xAxisData = trendData.map(item => {
    const date = new Date(item.date)
    return `${date.getMonth() + 1}/${date.getDate()}`
  })

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['严重问题', '高危问题', '中等问题']
    },
    xAxis: {
      type: 'category',
      data: xAxisData
    },
    yAxis: {
      type: 'value',
      name: '问题数量'
    },
    series: [
      {
        name: '严重问题',
        type: 'line',
        data: trendData.map(item => item.critical),
        smooth: true,
        itemStyle: { color: '#f56c6c' }
      },
      {
        name: '高危问题',
        type: 'line',
        data: trendData.map(item => item.high),
        smooth: true,
        itemStyle: { color: '#e6a23c' }
      },
      {
        name: '中等问题',
        type: 'line',
        data: trendData.map(item => item.medium),
        smooth: true,
        itemStyle: { color: '#409eff' }
      }
    ]
  }

  debtTrendChart.value.setOption(option)
}

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 订阅代码审查更新主题
  subscribeTo('code_review_updates')
  subscribeTo('issue_updates')

  // 监听状态更新消息
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新代码审查数据
      if (currentProjectId.value) {
        loadCodeReviewData()
        loadCodeIssues()
      }
    }
  })
}

onMounted(() => {
  loadCodeReviewData()
  loadCodeIssues()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()

  const resizeHandler = () => {
    debtTrendChart.value?.resize()
  }

  window.addEventListener('resize', resizeHandler)
  onUnmounted(() => {
    window.removeEventListener('resize', resizeHandler)

    // 清理图表资源
    debtTrendChart.value?.dispose()

    // 清理状态更新
    clearStatusUpdates()
  })
})

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadCodeReviewData()
    loadCodeIssues()
  }
})

// 监听筛选变化
watch(issueFilter, () => {
  pagination.value.currentPage = 1
  loadCodeIssues()
}, { deep: true })
</script>

<style scoped>
.code-review {
  padding: 20px;
}

.score-card {
  height: 100%;
}

.score-content {
  display: flex;
  gap: 20px;
}

.score-circle {
  flex-shrink: 0;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 8px solid;
}

.score-excellent {
  border-color: #67c23a;
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.1), rgba(103, 194, 58, 0.05));
}

.score-good {
  border-color: #e6a23c;
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.1), rgba(230, 162, 60, 0.05));
}

.score-poor {
  border-color: #f56c6c;
  background: linear-gradient(135deg, rgba(245, 108, 108, 0.1), rgba(245, 108, 108, 0.05));
}

.score-value {
  font-size: 36px;
  font-weight: bold;
  color: #303133;
}

.score-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.score-details {
  flex: 1;
}

.score-item {
  margin-bottom: 12px;
}

.score-item:last-child {
  margin-bottom: 0;
}

.score-item .label {
  display: block;
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 2px solid;
  border-radius: 8px;
  background-color: #fafafa;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-trend {
  font-size: 12px;
  margin-top: 4px;
}

.trend-up {
  color: #f56c6c;
}

.trend-down {
  color: #67c23a;
}

.incremental-review {
  padding: 10px 0;
}

.review-summary {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
}

.summary-item {
  text-align: center;
}

.summary-label {
  font-size: 12px;
  color: #909399;
  margin-right: 8px;
}

.summary-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.summary-value.new {
  color: #f56c6c;
}

.summary-value.fixed {
  color: #67c23a;
}

.debt-increase {
  color: #f56c6c;
}

.debt-decrease {
  color: #67c23a;
}

.changed-files {
  margin-top: 16px;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: bold;
  color: #303133;
}

.chart-container {
  width: 100%;
  height: 250px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.issue-detail {
  padding: 10px;
}

.issue-message {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
}

.code-snippet,
.code-diff {
  background-color: #282c34;
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
}

.code-snippet pre,
.code-diff pre {
  margin: 0;
}

.code-snippet code,
.code-diff code {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #abb2bf;
}

.fix-suggestion {
  margin-top: 16px;
}

.fix-code-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.ai-analysis {
  margin-top: 16px;
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
