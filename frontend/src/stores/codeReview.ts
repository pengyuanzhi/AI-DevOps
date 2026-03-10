import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  CodeReview,
  CodeIssue,
  QualityScore,
  CodeReviewStats,
  PaginationParams
} from '../types'
import { codeReviewApi } from '../api'

export const useCodeReviewStore = defineStore('codeReview', () => {
  const codeReviews = ref<CodeReview[]>([])
  const currentReview = ref<CodeReview | null>(null)
  const codeIssues = ref<CodeIssue[]>([])
  const currentIssue = ref<CodeIssue | null>(null)
  const qualityScore = ref<QualityScore | null>(null)
  const codeReviewStats = ref<CodeReviewStats | null>(null)
  const loading = ref(false)

  const pagination = ref({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0
  })

  const qualityTrend = ref<Array<{
    date: string
    overall: number
    memory_safety: number
    performance: number
    modern_cpp: number
    thread_safety: number
    code_style: number
  }>>([])

  const techDebtTrend = ref<Array<{
    date: string
    total: number
    critical: number
    high: number
    medium: number
    low: number
  }>>([])

  const criticalIssues = computed(() =>
    codeIssues.value.filter(issue => issue.severity === 'critical')
  )

  const highIssues = computed(() =>
    codeIssues.value.filter(issue => issue.severity === 'high')
  )

  const falsePositives = computed(() =>
    codeIssues.value.filter(issue => issue.is_false_positive)
  )

  /**
   * 获取代码审查
   */
  async function fetchCodeReview(mrId: number) {
    loading.value = true
    try {
      currentReview.value = await codeReviewApi.getCodeReview(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发代码审查
   */
  async function triggerCodeReview(mrId: number) {
    loading.value = true
    try {
      currentReview.value = await codeReviewApi.triggerCodeReview(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取代码问题列表
   */
  async function fetchCodeIssues(reviewId: number, params?: PaginationParams & {
    severity?: string
    category?: string
    detector?: string
  }) {
    loading.value = true
    try {
      const result = await codeReviewApi.getCodeIssues(reviewId, params)
      codeIssues.value = result.data
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
   * 获取代码问题详情
   */
  async function fetchCodeIssue(issueId: number) {
    loading.value = true
    try {
      currentIssue.value = await codeReviewApi.getCodeIssue(issueId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 应用修复建议
   */
  async function applyFix(issueId: number) {
    loading.value = true
    try {
      await codeReviewApi.applyFix(issueId)
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
      await codeReviewApi.markAsFalsePositive(issueId, reason)
      // 更新本地状态
      const issue = codeIssues.value.find(i => i.id === issueId)
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
      await codeReviewApi.unmarkFalsePositive(issueId)
      // 更新本地状态
      const issue = codeIssues.value.find(i => i.id === issueId)
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
      await codeReviewApi.batchUpdateIssues(issueIds, action, reason)
      // 更新本地状态
      codeIssues.value.forEach(issue => {
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
   * 获取质量评分
   */
  async function fetchQualityScore(projectId: number, mrId?: number) {
    try {
      qualityScore.value = await codeReviewApi.getQualityScore(projectId, mrId)
    } catch (error) {
      console.error('Failed to fetch quality score:', error)
    }
  }

  /**
   * 获取质量评分趋势
   */
  async function fetchQualityTrend(projectId: number, days: number = 30) {
    try {
      qualityTrend.value = await codeReviewApi.getQualityScoreTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch quality trend:', error)
    }
  }

  /**
   * 获取技术债务趋势
   */
  async function fetchTechDebtTrend(projectId: number, days: number = 30) {
    try {
      techDebtTrend.value = await codeReviewApi.getTechnicalDebtTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch tech debt trend:', error)
    }
  }

  /**
   * 获取代码审查统计
   */
  async function fetchCodeReviewStats(projectId: number) {
    try {
      codeReviewStats.value = await codeReviewApi.getCodeReviewStats(projectId)
    } catch (error) {
      console.error('Failed to fetch code review stats:', error)
    }
  }

  /**
   * 获取增量审查视图
   */
  async function fetchIncrementalReview(mrId: number) {
    loading.value = true
    try {
      return await codeReviewApi.getIncrementalReview(mrId)
    } finally {
      loading.value = false
    }
  }

  return {
    codeReviews,
    currentReview,
    codeIssues,
    currentIssue,
    qualityScore,
    codeReviewStats,
    loading,
    pagination,
    qualityTrend,
    techDebtTrend,
    criticalIssues,
    highIssues,
    falsePositives,
    fetchCodeReview,
    triggerCodeReview,
    fetchCodeIssues,
    fetchCodeIssue,
    applyFix,
    markAsFalsePositive,
    unmarkFalsePositive,
    batchUpdateIssues,
    fetchQualityScore,
    fetchQualityTrend,
    fetchTechDebtTrend,
    fetchCodeReviewStats,
    fetchIncrementalReview
  }
})
