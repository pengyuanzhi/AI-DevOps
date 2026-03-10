import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  MemoryIssue,
  MemorySafetyScore,
  PaginationParams
} from '../types'
import { memorySafetyApi } from '../api'

export const useMemorySafetyStore = defineStore('memorySafety', () => {
  const memoryIssues = ref<MemoryIssue[]>([])
  const currentIssue = ref<MemoryIssue | null>(null)
  const safetyScore = ref<MemorySafetyScore | null>(null)
  const loading = ref(false)

  const pagination = ref({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0
  })

  const scoreTrend = ref<Array<{ date: string; overall: number; issue_count: number }>>([])

  const typeDistribution = ref<Array<{
    type: string
    count: number
    percentage: number
  }>>([])

  const severityDistribution = ref({
    critical: 0,
    high: 0,
    medium: 0,
    low: 0
  })

  const moduleDensity = ref<Array<{
    module: string
    issue_count: number
    lines_of_code: number
    density: number
  }>>([])

  const benchmarkComparison = ref<{
    current_score: number
    industry_average: number
    top_10_percent: number
    percentile: number
  } | null>(null)

  // 计算属性
  const criticalIssues = computed(() =>
    memoryIssues.value.filter(issue => issue.severity === 'critical')
  )

  const highIssues = computed(() =>
    memoryIssues.value.filter(issue => issue.severity === 'high')
  )

  const mediumIssues = computed(() =>
    memoryIssues.value.filter(issue => issue.severity === 'medium')
  )

  const lowIssues = computed(() =>
    memoryIssues.value.filter(issue => issue.severity === 'low')
  )

  const leaks = computed(() =>
    memoryIssues.value.filter(issue => issue.type === 'memory_leak')
  )

  const overflows = computed(() =>
    memoryIssues.value.filter(issue => issue.type === 'buffer_overflow')
  )

  const danglingPointers = computed(() =>
    memoryIssues.value.filter(issue => issue.type === 'dangling_pointer')
  )

  const useAfterFrees = computed(() =>
    memoryIssues.value.filter(issue => issue.type === 'use_after_free')
  )

  const doubleFrees = computed(() =>
    memoryIssues.value.filter(issue => issue.type === 'double_free')
  )

  /**
   * 获取内存安全问题列表
   */
  async function fetchMemoryIssues(projectId: number, params?: PaginationParams & {
    severity?: string
    type?: string
    detector?: string
    mr_id?: number
  }) {
    loading.value = true
    try {
      const result = await memorySafetyApi.getMemoryIssues(projectId, params)
      memoryIssues.value = result.data
      pagination.value = {
        page: result.page,
        per_page: result.per_page,
        total: result.total,
        total_pages: result.total_pages
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取内存问题详情
   */
  async function fetchMemoryIssue(issueId: number) {
    loading.value = true
    try {
      currentIssue.value = await memorySafetyApi.getMemoryIssue(issueId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取内存安全评分
   */
  async function fetchMemorySafetyScore(projectId: number, mrId?: number) {
    try {
      safetyScore.value = await memorySafetyApi.getMemorySafetyScore(projectId, mrId)
    } catch (error) {
      console.error('Failed to fetch memory safety score:', error)
    }
  }

  /**
   * 获取评分趋势
   */
  async function fetchScoreTrend(projectId: number, days: number = 30) {
    try {
      scoreTrend.value = await memorySafetyApi.getMemorySafetyTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch score trend:', error)
    }
  }

  /**
   * 获取问题类型分布
   */
  async function fetchTypeDistribution(projectId: number) {
    try {
      typeDistribution.value = await memorySafetyApi.getIssueTypeDistribution(projectId)
    } catch (error) {
      console.error('Failed to fetch type distribution:', error)
    }
  }

  /**
   * 获取严重程度分布
   */
  async function fetchSeverityDistribution(projectId: number) {
    try {
      severityDistribution.value = await memorySafetyApi.getSeverityDistribution(projectId)
    } catch (error) {
      console.error('Failed to fetch severity distribution:', error)
    }
  }

  /**
   * 获取模块问题密度
   */
  async function fetchModuleDensity(projectId: number) {
    try {
      moduleDensity.value = await memorySafetyApi.getModuleDensity(projectId)
    } catch (error) {
      console.error('Failed to fetch module density:', error)
    }
  }

  /**
   * 获取基准对比
   */
  async function fetchBenchmarkComparison(projectId: number) {
    try {
      benchmarkComparison.value = await memorySafetyApi.getBenchmarkComparison(projectId)
    } catch (error) {
      console.error('Failed to fetch benchmark comparison:', error)
    }
  }

  /**
   * 应用修复建议
   */
  async function applyFix(issueId: number) {
    loading.value = true
    try {
      return await memorySafetyApi.applyMemoryFix(issueId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 标记为误报
   */
  async function markAsFalsePositive(issueId: number, reason: string) {
    loading.value = true
    try {
      await memorySafetyApi.markAsFalsePositive(issueId, reason)
      // 更新本地状态
      const issue = memoryIssues.value.find(i => i.id === issueId)
      if (issue) {
        issue.is_false_positive = true
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 取消误报标记
   */
  async function unmarkFalsePositive(issueId: number) {
    loading.value = true
    try {
      await memorySafetyApi.unmarkFalsePositive(issueId)
      // 更新本地状态
      const issue = memoryIssues.value.find(i => i.id === issueId)
      if (issue) {
        issue.is_false_positive = false
      }
    } finally {
      loading.value = false
    }
  }

  /**
   * 批量操作
   */
  async function batchUpdateIssues(
    issueIds: number[],
    action: 'mark_fp' | 'unmark_fp' | 'apply_fix',
    reason?: string
  ) {
    loading.value = true
    try {
      await memorySafetyApi.batchUpdateIssues(issueIds, action, reason)
      // 更新本地状态
      memoryIssues.value.forEach(issue => {
        if (issueIds.includes(issue.id)) {
          if (action === 'mark_fp') {
            issue.is_false_positive = true
          } else if (action === 'unmark_fp') {
            issue.is_false_positive = false
          }
        }
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发内存安全检测
   */
  async function triggerMemoryDetection(mrId: number) {
    loading.value = true
    try {
      return await memorySafetyApi.triggerMemoryDetection(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取检测任务状态
   */
  async function getDetectionStatus(jobId: string) {
    loading.value = true
    try {
      return await memorySafetyApi.getDetectionStatus(jobId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 导出内存问题报告
   */
  async function exportMemoryIssues(
    projectId: number,
    format: 'json' | 'csv' | 'pdf',
    filters?: {
      severity?: string
      type?: string
      start_date?: string
      end_date?: string
    }
  ) {
    loading.value = true
    try {
      return await memorySafetyApi.exportMemoryIssues(projectId, format, filters)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取内存安全问题统计
   */
  async function fetchMemoryIssueStats(projectId: number) {
    try {
      return await memorySafetyApi.getMemoryIssueStats(projectId)
    } catch (error) {
      console.error('Failed to fetch memory issue stats:', error)
    }
  }

  /**
   * 获取增量检测视图
   */
  async function fetchIncrementalMemoryIssues(mrId: number) {
    loading.value = true
    try {
      return await memorySafetyApi.getIncrementalMemoryIssues(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取所有内存安全数据
   */
  async function fetchAllMemoryData(projectId: number) {
    await Promise.all([
      fetchMemoryIssues(projectId),
      fetchMemorySafetyScore(projectId),
      fetchScoreTrend(projectId, 30),
      fetchTypeDistribution(projectId),
      fetchSeverityDistribution(projectId),
      fetchModuleDensity(projectId),
      fetchBenchmarkComparison(projectId)
    ])
  }

  return {
    memoryIssues,
    currentIssue,
    safetyScore,
    loading,
    pagination,
    scoreTrend,
    typeDistribution,
    severityDistribution,
    moduleDensity,
    benchmarkComparison,
    // 计算属性
    criticalIssues,
    highIssues,
    mediumIssues,
    lowIssues,
    leaks,
    overflows,
    danglingPointers,
    useAfterFrees,
    doubleFrees,
    // 方法
    fetchMemoryIssues,
    fetchMemoryIssue,
    fetchMemorySafetyScore,
    fetchScoreTrend,
    fetchTypeDistribution,
    fetchSeverityDistribution,
    fetchModuleDensity,
    fetchBenchmarkComparison,
    applyFix,
    markAsFalsePositive,
    unmarkFalsePositive,
    batchUpdateIssues,
    triggerMemoryDetection,
    getDetectionStatus,
    exportMemoryIssues,
    fetchMemoryIssueStats,
    fetchIncrementalMemoryIssues,
    fetchAllMemoryData
  }
})
