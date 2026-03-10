<template>
  <div class="memory-safety">
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
        <el-col :span="8">
          <SkeletonLoader type="chart" />
        </el-col>
        <el-col :span="16">
          <SkeletonLoader type="chart" />
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
        <el-col :span="24">
          <SkeletonLoader type="table" :rows="10" />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 - 无内存安全数据时显示 -->
    <el-card v-else-if="!loading && hasNoMemorySafetyData">
      <EmptyState
        type="no-data"
        title="暂无内存安全数据"
        description="还没有进行任何内存安全检测，请先运行Valgrind检测"
        :show-action="true"
        action-text="运行内存检测"
        @action="runMemoryCheck"
      />
    </el-card>

    <!-- 实际内容 -->
    <template v-if="!loading && !hasNoMemorySafetyData">
      <!-- 页面标题 -->
      <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="margin: 0;">内存安全报告</h2>
              <p class="subtitle" style="margin: 8px 0 0 0;">检测和分析C/C++代码中的内存安全问题</p>
            </div>
            <el-tooltip :content="wsConnected ? '实时更新已连接' : '实时更新已断开'">
              <div class="ws-status" :class="{ connected: wsConnected }">
                <div class="ws-indicator"></div>
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 内存安全评分概览 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card>
          <div class="score-overview">
            <div ref="scoreGaugeRef" style="width: 100%; height: 250px"></div>
            <div class="score-text">
              <div class="score-value">{{ safetyScore }}</div>
              <div class="score-label">内存安全评分</div>
              <div class="score-trend" :class="scoreTrend > 0 ? 'positive' : 'negative'">
                <el-icon><CaretTop v-if="scoreTrend > 0" /><CaretBottom v-else /></el-icon>
                {{ Math.abs(scoreTrend) }}% 较上周
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>问题分类统计</span>
          </template>
          <el-row :gutter="20" style="margin-top: 10px">
            <el-col :span="6">
              <div class="issue-stat-card critical">
                <div class="stat-icon">
                  <el-icon :size="32"><CircleCloseFilled /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ issueStats.critical }}</div>
                  <div class="stat-label">严重</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="issue-stat-card high">
                <div class="stat-icon">
                  <el-icon :size="32"><WarningFilled /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ issueStats.high }}</div>
                  <div class="stat-label">高危</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="issue-stat-card medium">
                <div class="stat-icon">
                  <el-icon :size="32"><InfoFilled /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ issueStats.medium }}</div>
                  <div class="stat-label">中等</div>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="issue-stat-card low">
                <div class="stat-icon">
                  <el-icon :size="32"><Warning /></el-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ issueStats.low }}</div>
                  <div class="stat-label">低级</div>
                </div>
              </div>
            </el-col>
          </el-row>

          <el-divider />

          <div style="margin-top: 20px">
            <h4>问题类型分布</h4>
            <div ref="issueTypeChartRef" style="width: 100%; height: 200px"></div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势对比和基准 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>内存安全趋势</span>
          </template>
          <div ref="trendChartRef" style="width: 100%; height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>行业基准对比</span>
          </template>
          <div ref="benchmarkChartRef" style="width: 100%; height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 模块/文件密度统计 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>模块内存安全密度</span>
      </template>
      <div ref="densityChartRef" style="width: 100%; height: 350px"></div>
    </el-card>

    <!-- 增量检测视图 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>增量检测视图</span>
          <el-select v-model="selectedMR" placeholder="选择MR" style="width: 300px">
            <el-option label="!1234 - feat: Add user authentication" value="1234" />
            <el-option label="!1233 - fix: Memory leak in data processor" value="1233" />
            <el-option label="!1232 - refactor: Optimize memory usage" value="1232" />
          </el-select>
        </div>
      </template>

      <el-row :gutter="20" v-if="selectedMR">
        <el-col :span="8">
          <el-statistic title="新增问题" :value="incrementalData.new_issues">
            <template #prefix>
              <el-icon color="#f56c6c"><Plus /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="修复问题" :value="incrementalData.fixed_issues">
            <template #prefix>
              <el-icon color="#67c23a"><Minus /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="8">
          <el-statistic title="净增技术债务" :value="incrementalData.net_debt">
            <template #prefix>
              <el-icon :color="incrementalData.net_debt > 0 ? '#f56c6c' : '#67c23a'">
                <TrendCharts />
              </el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-table :data="incrementalData.issues" style="margin-top: 20px" v-if="selectedMR">
        <el-table-column prop="file" label="文件" min-width="200" />
        <el-table-column prop="line" label="行号" width="80" />
        <el-table-column prop="type" label="问题类型" width="150" />
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.severity === 'critical'" type="danger" size="small">
              严重
            </el-tag>
            <el-tag v-else-if="scope.row.severity === 'high'" type="warning" size="small">
              高危
            </el-tag>
            <el-tag v-else-if="scope.row.severity === 'medium'" type="primary" size="small">
              中等
            </el-tag>
            <el-tag v-else type="info" size="small">低级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 'new'" type="danger" size="small">新增</el-tag>
            <el-tag v-else-if="scope.row.status === 'fixed'" type="success" size="small">
              已修复
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="viewIssueDetail(scope.row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 内存问题列表 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>内存问题列表</span>
          <div class="header-actions">
            <el-select v-model="filters.severity" placeholder="严重程度" clearable style="width: 150px; margin-right: 10px">
              <el-option label="全部" value="" />
              <el-option label="严重" value="critical" />
              <el-option label="高危" value="high" />
              <el-option label="中等" value="medium" />
              <el-option label="低级" value="low" />
            </el-select>
            <el-select v-model="filters.type" placeholder="问题类型" clearable style="width: 150px; margin-right: 10px">
              <el-option label="全部类型" value="" />
              <el-option label="内存泄漏" value="memory_leak" />
              <el-option label="缓冲区溢出" value="buffer_overflow" />
              <el-option label="悬空指针" value="dangling_pointer" />
              <el-option label="使用后释放" value="use_after_free" />
              <el-option label="双重释放" value="double_free" />
              <el-option label="未初始化内存" value="uninitialized_memory" />
            </el-select>
            <el-input
              v-model="filters.search"
              placeholder="搜索文件或函数"
              clearable
              style="width: 200px"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </div>
      </template>

      <el-table :data="filteredIssues" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80">
          <template #default="scope">
            <el-link type="primary" @click="viewIssueDetail(scope.row)">
              #{{ scope.row.id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="问题类型" width="150">
          <template #default="scope">
            <el-tag :type="getTypeTagType(scope.row.type)" size="small">
              {{ getTypeLabel(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="严重程度" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.severity === 'critical'" type="danger" size="small">
              严重
            </el-tag>
            <el-tag v-else-if="scope.row.severity === 'high'" type="warning" size="small">
              高危
            </el-tag>
            <el-tag v-else-if="scope.row.severity === 'medium'" type="primary" size="small">
              中等
            </el-tag>
            <el-tag v-else type="info" size="small">低级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file" label="文件" min-width="200" />
        <el-table-column prop="line" label="行号" width="80" />
        <el-table-column prop="function" label="函数" min-width="150" />
        <el-table-column prop="confidence" label="AI置信度" width="120">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.confidence"
              :color="getConfidenceColor(scope.row.confidence)"
              :show-text="false"
              style="width: 80px"
            />
            <span style="margin-left: 8px">{{ scope.row.confidence }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="detector" label="检测工具" width="100">
          <template #default="scope">
            <el-tag type="info" size="small">{{ scope.row.detector }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewIssueDetail(scope.row)">查看详情</el-button>
            <el-button
              v-if="scope.row.has_fix"
              size="small"
              type="primary"
              @click="applyFix(scope.row)"
            >
              应用修复
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.currentPage"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <!-- 问题详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="内存问题详情" width="70%" top="5vh">
      <div v-if="currentIssue">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border>
          <el-descriptions-item label="问题ID">
            #{{ currentIssue.id }}
          </el-descriptions-item>
          <el-descriptions-item label="问题类型">
            <el-tag :type="getTypeTagType(currentIssue.type)">
              {{ getTypeLabel(currentIssue.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag v-if="currentIssue.severity === 'critical'" type="danger" size="small">
              严重
            </el-tag>
            <el-tag v-else-if="currentIssue.severity === 'high'" type="warning" size="small">
              高危
            </el-tag>
            <el-tag v-else-if="currentIssue.severity === 'medium'" type="primary" size="small">
              中等
            </el-tag>
            <el-tag v-else type="info" size="small">低级</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="检测工具">
            {{ currentIssue.detector }}
          </el-descriptions-item>
          <el-descriptions-item label="文件">
            {{ currentIssue.file }}
          </el-descriptions-item>
          <el-descriptions-item label="行号">
            {{ currentIssue.line }}
          </el-descriptions-item>
          <el-descriptions-item label="函数">
            {{ currentIssue.function }}
          </el-descriptions-item>
          <el-descriptions-item label="AI置信度">
            {{ currentIssue.confidence }}%
          </el-descriptions-item>
        </el-descriptions>

        <!-- Valgrind报告 -->
        <div style="margin-top: 20px">
          <h4>检测工具报告（Valgrind）</h4>
          <el-card class="report-card">
            <pre class="report-content">{{ currentIssue.raw_report }}</pre>
          </el-card>
        </div>

        <!-- 调用栈分析 -->
        <div style="margin-top: 20px">
          <h4>调用栈分析</h4>
          <el-card>
            <el-timeline>
              <el-timeline-item
                v-for="(frame, index) in currentIssue.stack_trace"
                :key="index"
                :timestamp="frame.address"
                :type="index === 0 ? 'primary' : 'info'"
              >
                <div>
                  <strong>{{ frame.function }}</strong>
                  <div style="margin-top: 5px; color: #606266; font-size: 12px">
                    文件: {{ frame.file }}:{{ frame.line }}
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </div>

        <!-- 代码片段 -->
        <div style="margin-top: 20px">
          <h4>问题代码片段</h4>
          <el-card>
            <div class="code-snippet">
              <div
                v-for="(line, index) in currentIssue.code_snippet"
                :key="index"
                class="code-line"
                :class="{ 'highlight-line': line.number === currentIssue.line }"
              >
                <span class="line-number">{{ line.number }}</span>
                <span class="line-content">{{ line.content }}</span>
              </div>
            </div>
          </el-card>
        </div>

        <!-- AI分析 -->
        <div style="margin-top: 20px">
          <h4>AI智能分析</h4>
          <el-card>
            <el-alert :type="currentIssue.severity === 'critical' ? 'error' : 'warning'" :closable="false">
              <strong>根因分析：</strong>{{ currentIssue.ai_analysis.root_cause }}
            </el-alert>
            <div style="margin-top: 15px">
              <strong>影响评估：</strong>{{ currentIssue.ai_analysis.impact }}
            </div>
            <div style="margin-top: 10px">
              <strong>误报概率：</strong>
              <el-progress
                :percentage="currentIssue.ai_analysis.false_positive_risk"
                :color="getFalsePositiveColor(currentIssue.ai_analysis.false_positive_risk)"
                :show-text="true"
                style="width: 200px; display: inline-block; margin-left: 10px"
              />
            </div>
          </el-card>
        </div>

        <!-- 修复建议 -->
        <div style="margin-top: 20px" v-if="currentIssue.fix_suggestion">
          <h4>修复建议</h4>
          <el-card>
            <p><strong>推荐方案：</strong>{{ currentIssue.fix_suggestion.description }}</p>
            <div style="margin-top: 10px">
              <strong>现代C++推荐：</strong>{{ currentIssue.fix_suggestion.modern_cpp }}
            </div>
            <div v-if="currentIssue.fix_suggestion.fix_code" style="margin-top: 15px">
              <strong>修复代码：</strong>
              <div class="code-diff">
                <pre><code>{{ currentIssue.fix_suggestion.fix_code }}</code></pre>
              </div>
            </div>
          </el-card>
        </div>

        <!-- 操作按钮 -->
        <div style="margin-top: 20px; text-align: right">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button @click="markAsFalsePositive">标记为误报</el-button>
          <el-button @click="deferFix">延后处理</el-button>
          <el-button
            v-if="currentIssue.has_fix"
            type="primary"
            @click="applyFixFromDialog"
          >
            应用修复
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 修复确认对话框 -->
    <el-dialog v-model="fixConfirmVisible" title="确认应用修复" width="500px">
      <el-form :model="fixForm" label-width="100px">
        <el-form-item label="修复方式">
          <el-radio-group v-model="fixForm.method">
            <el-radio label="automatic">自动应用修复</el-radio>
            <el-radio label="create_mr">创建修复MR</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="说明" v-if="fixForm.method === 'create_mr'">
          <el-input
            v-model="fixForm.description"
            type="textarea"
            :rows="3"
            placeholder="MR描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fixConfirmVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmFix">确认</el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCloseFilled,
  WarningFilled,
  InfoFilled,
  Warning,
  CaretTop,
  CaretBottom,
  Plus,
  Minus,
  TrendCharts,
  Search
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useMemorySafetyStore, useProjectStore } from '@/stores'
import { SkeletonLoader, EmptyState } from '@/components/common'
import { useWebSocket } from '@/composables/useWebSocket'
import { memorySafetyApi } from '@/api'
import type { MemoryIssue, MemorySafetyScore } from '@/types'

// 初始化stores
const memorySafetyStore = useMemorySafetyStore()
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
  subscribe: ['memory_safety_updates', 'memory_issue_updates']
})

const currentProjectId = computed(() => projectStore.currentProject?.id)

// 加载状态和错误处理
const loading = ref(false)
const error = ref<string | null>(null)

// 内存安全评分 - 从store获取
const safetyScore = computed(() => {
  const score = memorySafetyStore.safetyScore
  if (!score) return 0
  return Math.round(score.overall)
})

const scoreTrend = computed(() => {
  const score = memorySafetyStore.safetyScore
  if (!score) return 0
  return score.trend || 0
})

// 问题统计 - 从store获取
const issueStats = computed(() => {
  const stats = memorySafetyStore.severityDistribution
  if (!stats) {
    return { critical: 0, high: 0, medium: 0, low: 0 }
  }
  return {
    critical: stats.critical || 0,
    high: stats.high || 0,
    medium: stats.medium || 0,
    low: stats.low || 0
  }
})

// 筛选条件
const filters = ref({
  severity: '',
  type: '',
  search: ''
})

// 分页
const pagination = ref({
  currentPage: 1,
  pageSize: 20,
  total: 0
})

// 加载状态
const loading = ref(false)

// 选中的MR
const selectedMR = ref('')

// 增量数据 - 从store获取
const incrementalData = computed(() => {
  const issues = memorySafetyStore.memoryIssues
  return {
    new_issues: issues.filter(i => i.status === 'new').length,
    fixed_issues: issues.filter(i => i.status === 'fixed').length,
    net_debt: 0, // 计算净技术债务
    issues: issues.filter(i => ['new', 'fixed'].includes(i.status))
  }
})

// 内存问题列表 - 从store获取
const issues = computed(() => memorySafetyStore.memoryIssues)

// 当前问题
const currentIssue = ref<any>(null)

// 详情对话框
const detailDialogVisible = ref(false)

// 修复确认对话框
const fixConfirmVisible = ref(false)
const fixForm = ref({
  method: 'automatic',
  description: ''
})

// 图表引用
const scoreGaugeRef = ref<HTMLElement>()
const issueTypeChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const benchmarkChartRef = ref<HTMLElement>()
const densityChartRef = ref<HTMLElement>()

let scoreGauge: echarts.ECharts | null = null
let issueTypeChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let benchmarkChart: echarts.ECharts | null = null
let densityChart: echarts.ECharts | null = null

// 计算属性：筛选后的问题列表
const filteredIssues = computed(() => {
  let result = [...issues.value]

  if (filters.value.severity) {
    result = result.filter(issue => issue.severity === filters.value.severity)
  }

  if (filters.value.type) {
    result = result.filter(issue => issue.type === filters.value.type)
  }

  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    result = result.filter(issue =>
      issue.file.toLowerCase().includes(search) ||
      issue.function.toLowerCase().includes(search)
    )
  }

  pagination.value.total = result.length

  const start = (pagination.value.currentPage - 1) * pagination.value.pageSize
  const end = start + pagination.value.pageSize
  return result.slice(start, end)
})

// 判断是否有内存安全数据
const hasNoMemorySafetyData = computed(() => {
  const score = memorySafetyStore.safetyScore
  const issues = memorySafetyStore.memoryIssues
  return (!score || score.overall === 0) && (!issues || issues.length === 0)
})

// 运行内存检测
const runMemoryCheck = () => {
  ElMessage.info('运行内存检测功能开发中')
}

// 方法：加载内存安全数据
const loadMemorySafetyData = async () => {
  if (!currentProjectId.value) {
    error.value = '请先选择项目'
    return
  }

  loading.value = true
  error.value = null

  try {
    // 并行加载所有必要的数据
    await Promise.all([
      memorySafetyStore.fetchMemorySafetyScore(currentProjectId.value),
      memorySafetyStore.fetchScoreTrend(currentProjectId.value, 30),
      memorySafetyStore.fetchTypeDistribution(currentProjectId.value),
      memorySafetyStore.fetchSeverityDistribution(currentProjectId.value),
      memorySafetyStore.fetchModuleDensity(currentProjectId.value),
      memorySafetyStore.fetchBenchmarkComparison(currentProjectId.value)
    ])

    // 加载内存问题列表
    await memorySafetyStore.fetchMemoryIssues(currentProjectId.value, {
      page: pagination.value.currentPage,
      per_page: pagination.value.pageSize,
      severity: filters.value.severity || undefined,
      type: filters.value.type || undefined,
      search: filters.value.search || undefined
    })

    // 初始化图表
    await nextTick()
    initScoreGauge()
    initIssueTypeChart()
    initTrendChart()
    initBenchmarkChart()
    initDensityChart()
  } catch (err: any) {
    console.error('Failed to load memory safety data:', err)
    error.value = err.message || '加载内存安全数据失败'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

// 方法：获取问题类型标签
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    memory_leak: '内存泄漏',
    buffer_overflow: '缓冲区溢出',
    dangling_pointer: '悬空指针',
    use_after_free: '使用后释放',
    double_free: '双重释放',
    uninitialized_memory: '未初始化内存'
  }
  return labels[type] || type
}

// 方法：获取问题类型标签颜色
const getTypeTagType = (type: string) => {
  if (type === 'memory_leak') return 'danger'
  if (type === 'buffer_overflow') return 'warning'
  if (type === 'dangling_pointer') return 'warning'
  if (type === 'use_after_free') return 'danger'
  if (type === 'double_free') return 'danger'
  if (type === 'uninitialized_memory') return 'primary'
  return ''
}

// 方法：获取置信度颜色
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 90) return '#67c23a'
  if (confidence >= 70) return '#e6a23c'
  return '#f56c6c'
}

// 方法：获取误报风险颜色
const getFalsePositiveColor = (risk: number) => {
  if (risk <= 10) return '#67c23a'
  if (risk <= 30) return '#e6a23c'
  return '#f56c6c'
}

// 方法：处理分页变化
const handleSizeChange = () => {
  pagination.value.currentPage = 1
}

const handleCurrentChange = () => {
  // 页面变化处理
}

// 方法：查看问题详情
const viewIssueDetail = (issue: any) => {
  currentIssue.value = issue
  detailDialogVisible.value = true
}

// 方法：应用修复
const applyFix = async (issue: MemoryIssue) => {
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
    const result = await memorySafetyStore.applyFix(issue.id)

    ElMessage.success('修复已应用到MR: ' + result.mr_id)

    // 重新加载数据
    if (currentProjectId.value) {
      await loadMemorySafetyData()
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

// 方法：从对话框应用修复
const applyFixFromDialog = async () => {
  if (!currentIssue.value) return
  await applyFix(currentIssue.value)
}

// 方法：确认修复
const confirmFix = () => {
  fixConfirmVisible.value = false
  detailDialogVisible.value = false

  if (fixForm.value.method === 'automatic') {
    ElMessage.success('修复已自动应用')
  } else {
    ElMessage.success('已创建修复MR')
  }
}

// 方法：标记为误报
const markAsFalsePositive = async (issue: MemoryIssue, reason: string = '用户标记为误报') => {
  try {
    await memorySafetyStore.markAsFalsePositive(issue.id, reason)
    ElMessage.success('已标记为误报，AI将学习此反馈')
    detailDialogVisible.value = false

    // 重新加载数据
    if (currentProjectId.value) {
      await loadMemorySafetyData()
    }
  } catch (error) {
    console.error('Mark as false positive failed:', error)
    ElMessage.error('标记误报失败')
  }
}

// 方法：延后处理
const deferFix = () => {
  ElMessage.info('已添加到延后处理列表')
  detailDialogVisible.value = false
}

// 方法：初始化评分仪表盘
const initScoreGauge = () => {
  if (!scoreGaugeRef.value) return

  scoreGauge = echarts.init(scoreGaugeRef.value)

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 10,
        radius: '80%',
        center: ['50%', '60%'],
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.3, '#f56c6c'],
              [0.7, '#e6a23c'],
              [1, '#67c23a']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 14,
          distance: -60,
          formatter: function (value: number) {
            if (value === 30) return '差'
            if (value === 70) return '良'
            if (value === 100) return '优'
            return ''
          }
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 20
        },
        detail: {
          fontSize: 40,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: function (value: number) {
            return Math.round(value) + '分'
          },
          color: 'auto'
        },
        data: [
          {
            value: safetyScore.value
          }
        ]
      }
    ]
  }

  scoreGauge.setOption(option)
}

// 方法：初始化问题类型图
const initIssueTypeChart = () => {
  if (!issueTypeChartRef.value) return

  issueTypeChart = echarts.init(issueTypeChartRef.value)

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      bottom: '0%',
      left: 'center'
    },
    series: [
      {
        name: '问题类型',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: 28, name: '内存泄漏', itemStyle: { color: '#f56c6c' } },
          { value: 19, name: '缓冲区溢出', itemStyle: { color: '#e6a23c' } },
          { value: 23, name: '悬空指针', itemStyle: { color: '#409eff' } },
          { value: 15, name: '使用后释放', itemStyle: { color: '#67c23a' } },
          { value: 12, name: '双重释放', itemStyle: { color: '#909399' } },
          { value: 10, name: '未初始化内存', itemStyle: { color: '#f59f9f' } }
        ]
      }
    ]
  }

  issueTypeChart.setOption(option)
}

// 方法：初始化趋势图
const initTrendChart = () => {
  if (!trendChartRef.value) return

  trendChart = echarts.init(trendChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['内存安全评分', '严重问题数', '高危问题数']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['第1周', '第2周', '第3周', '第4周', '第5周', '第6周', '第7周', '第8周']
    },
    yAxis: [
      {
        type: 'value',
        name: '评分',
        min: 0,
        max: 100,
        position: 'left'
      },
      {
        type: 'value',
        name: '问题数',
        min: 0,
        position: 'right'
      }
    ],
    series: [
      {
        name: '内存安全评分',
        type: 'line',
        yAxisIndex: 0,
        data: [65, 67, 66, 68, 70, 69, 71, 72],
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
              { offset: 1, color: 'rgba(103, 194, 58, 0)' }
            ]
          }
        }
      },
      {
        name: '严重问题数',
        type: 'bar',
        yAxisIndex: 1,
        data: [15, 14, 16, 13, 12, 11, 10, 8],
        itemStyle: { color: '#f56c6c' }
      },
      {
        name: '高危问题数',
        type: 'bar',
        yAxisIndex: 1,
        data: [28, 27, 29, 26, 25, 24, 23, 23],
        itemStyle: { color: '#e6a23c' }
      }
    ]
  }

  trendChart.setOption(option)
}

// 方法：初始化基准对比图
const initBenchmarkChart = () => {
  if (!benchmarkChartRef.value) return

  benchmarkChart = echarts.init(benchmarkChartRef.value)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['当前项目', '行业平均', '行业领先']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}分'
      }
    },
    yAxis: {
      type: 'category',
      data: ['内存泄漏', '缓冲区溢出', '指针安全', '整体评分']
    },
    series: [
      {
        name: '当前项目',
        type: 'bar',
        data: [68, 75, 70, 72],
        itemStyle: { color: '#409eff' }
      },
      {
        name: '行业平均',
        type: 'bar',
        data: [65, 70, 68, 68],
        itemStyle: { color: '#909399' }
      },
      {
        name: '行业领先',
        type: 'bar',
        data: [85, 88, 90, 88],
        itemStyle: { color: '#67c23a' }
      }
    ]
  }

  benchmarkChart.setOption(option)
}

// 方法：初始化密度图
const initDensityChart = () => {
  if (!densityChartRef.value) return

  densityChart = echarts.init(densityChartRef.value)

  const option = {
    title: {
      text: '各模块内存问题密度',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['严重', '高危', '中等', '低级'],
      top: '8%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['Auth', 'DataProcessor', 'CacheManager', 'UserManager', 'Network', 'UI', 'Utils']
    },
    yAxis: {
      type: 'value',
      name: '问题数/KLOC'
    },
    series: [
      {
        name: '严重',
        type: 'bar',
        stack: 'total',
        data: [2, 1, 0, 1, 0, 0, 1],
        itemStyle: { color: '#f56c6c' }
      },
      {
        name: '高危',
        type: 'bar',
        stack: 'total',
        data: [3, 4, 2, 3, 1, 0, 2],
        itemStyle: { color: '#e6a23c' }
      },
      {
        name: '中等',
        type: 'bar',
        stack: 'total',
        data: [5, 6, 4, 5, 3, 2, 4],
        itemStyle: { color: '#409eff' }
      },
      {
        name: '低级',
        type: 'bar',
        stack: 'total',
        data: [8, 7, 6, 9, 5, 4, 6],
        itemStyle: { color: '#909399' }
      }
    ]
  }

  densityChart.setOption(option)
}

// 设置WebSocket实时更新
const setupWebSocketUpdates = () => {
  // 订阅内存安全更新主题
  subscribeTo('memory_safety_updates')
  subscribeTo('memory_issue_updates')

  // 监听状态更新消息
  watch(() => statusUpdates.value.length, (newLength, oldLength) => {
    if (newLength > oldLength) {
      // 有新的状态更新，刷新内存安全数据
      if (currentProjectId.value) {
        loadMemorySafetyData()
      }
    }
  })
}

// 生命周期：挂载
onMounted(() => {
  loadMemorySafetyData()

  // 设置WebSocket实时更新
  setupWebSocketUpdates()
})

// 监听项目切换
watch(currentProjectId, () => {
  if (currentProjectId.value) {
    loadMemorySafetyData()
  }
})

// 监听筛选变化
watch(filters, () => {
  pagination.value.currentPage = 1
  if (currentProjectId.value) {
    loadMemorySafetyData()
  }
}, { deep: true })

// 监听分页变化
watch(() => pagination.value.currentPage, () => {
  if (currentProjectId.value) {
    loadMemorySafetyData()
  }
})

watch(() => pagination.value.pageSize, () => {
  pagination.value.currentPage = 1
  if (currentProjectId.value) {
    loadMemorySafetyData()
  }
})

// 生命周期：卸载
onUnmounted(() => {
  if (scoreGauge) scoreGauge.dispose()
  if (issueTypeChart) issueTypeChart.dispose()
  if (trendChart) trendChart.dispose()
  if (benchmarkChart) benchmarkChart.dispose()
  if (densityChart) densityChart.dispose()

  // 清理状态更新
  clearStatusUpdates()
})
</script>

<style scoped>
.memory-safety {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.subtitle {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.score-overview {
  position: relative;
  text-align: center;
}

.score-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.score-value {
  font-size: 48px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.score-label {
  font-size: 16px;
  color: #909399;
  margin-top: 10px;
}

.score-trend {
  font-size: 14px;
  margin-top: 8px;
}

.score-trend.positive {
  color: #67c23a;
}

.score-trend.negative {
  color: #f56c6c;
}

.issue-stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  border-radius: 8px;
}

.issue-stat-card.critical {
  background: linear-gradient(135deg, #fef0f0 0%, #fef2f2 100%);
}

.issue-stat-card.high {
  background: linear-gradient(135deg, #fdf6ec 0%, #fef8f0 100%);
}

.issue-stat-card.medium {
  background: linear-gradient(135deg, #ecf5ff 0%, #f5f9ff 100%);
}

.issue-stat-card.low {
  background: linear-gradient(135deg, #f4f4f5 0%, #f9f9fa 100%);
}

.stat-icon {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.report-card {
  background: #f5f7fa;
}

.report-content {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #303133;
}

.code-snippet {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 10px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.code-line {
  display: flex;
  padding: 2px 0;
}

.code-line.highlight-line {
  background: #ffe6e6;
  border-radius: 2px;
}

.line-number {
  display: inline-block;
  width: 50px;
  color: #909399;
  text-align: right;
  margin-right: 15px;
  user-select: none;
}

.line-content {
  flex: 1;
  color: #303133;
}

.code-diff {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 15px;
  margin-top: 10px;
}

.code-diff pre {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
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
