import request from './request'
import type {
  MemoryIssue,
  MemorySafetyScore,
  PaginationParams,
  PaginatedResponse
} from '../types'

/**
 * 内存安全API服务
 * 提供内存安全问题检测、分析、修复建议等功能
 */
export const memorySafetyApi = {
  /**
   * 获取内存安全问题列表
   */
  async getMemoryIssues(
    projectId: number,
    params?: PaginationParams & {
      severity?: string
      type?: string
      detector?: string
      mr_id?: number
    }
  ): Promise<PaginatedResponse<MemoryIssue>> {
    return request.get(`/api/v1/projects/${projectId}/memory-issues`, { params })
  },

  /**
   * 获取内存问题详情
   */
  async getMemoryIssue(issueId: number): Promise<MemoryIssue> {
    return request.get(`/api/v1/memory-issues/${issueId}`)
  },

  /**
   * 获取内存安全评分
   */
  async getMemorySafetyScore(projectId: number, mrId?: number): Promise<MemorySafetyScore> {
    const url = mrId
      ? `/api/v1/projects/${projectId}/memory-safety/score?mr_id=${mrId}`
      : `/api/v1/projects/${projectId}/memory-safety/score`
    return request.get(url)
  },

  /**
   * 获取内存安全评分趋势
   */
  async getMemorySafetyTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{
    date: string
    overall: number
    issue_count: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/memory-safety/trend`, { params })
  },

  /**
   * 获取内存问题类型分布
   */
  async getIssueTypeDistribution(projectId: number): Promise<Array<{
    type: string
    count: number
    percentage: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/memory-issues/distribution`)
  },

  /**
   * 获取严重程度分布
   */
  async getSeverityDistribution(projectId: number): Promise<{
    critical: number
    high: number
    medium: number
    low: number
  }> {
    return request.get(`/api/v1/projects/${projectId}/memory-issues/severity-distribution`)
  },

  /**
   * 获取模块内存问题密度
   */
  async getModuleDensity(projectId: number): Promise<Array<{
    module: string
    issue_count: number
    lines_of_code: number
    density: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/memory-issues/module-density`)
  },

  /**
   * 获取增量检测视图
   */
  async getIncrementalMemoryIssues(mrId: number): Promise<{
    new_issues: MemoryIssue[]
    fixed_issues: MemoryIssue[]
    net_change: number
  }> {
    return request.get(`/api/v1/mrs/${mrId}/memory-issues/incremental`)
  },

  /**
   * 获取与行业基准对比
   */
  async getBenchmarkComparison(projectId: number): Promise<{
    current_score: number
    industry_average: number
    top_10_percent: number
    percentile: number
  }> {
    return request.get(`/api/v1/projects/${projectId}/memory-safety/benchmark`)
  },

  /**
   * 应用修复建议
   */
  async applyMemoryFix(issueId: number): Promise<{ mr_id: number }> {
    return request.post(`/api/v1/memory-issues/${issueId}/apply-fix`)
  },

  /**
   * 标记为误报
   */
  async markAsFalsePositive(issueId: number, reason: string): Promise<void> {
    return request.post(`/api/v1/memory-issues/${issueId}/false-positive`, { reason })
  },

  /**
   * 取消误报标记
   */
  async unmarkFalsePositive(issueId: number): Promise<void> {
    return request.post(`/api/v1/memory-issues/${issueId}/unmark-false-positive`)
  },

  /**
   * 触发内存安全检测
   */
  async triggerMemoryDetection(mrId: number): Promise<{ job_id: string }> {
    return request.post(`/api/v1/mrs/${mrId}/memory-detection`)
  },

  /**
   * 获取检测任务状态
   */
  async getDetectionStatus(jobId: string): Promise<{
    status: 'pending' | 'running' | 'completed' | 'failed'
    progress: number
    result?: {
      issue_count: number
      score: number
    }
  }> {
    return request.get(`/api/v1/memory-detection/jobs/${jobId}`)
  },

  /**
   * 批量操作内存问题
   */
  async batchUpdateIssues(
    issueIds: number[],
    action: 'mark_fp' | 'unmark_fp' | 'apply_fix',
    reason?: string
  ): Promise<void> {
    return request.post('/api/v1/memory-issues/batch', { issue_ids: issueIds, action, reason })
  },

  /**
   * 获取Valgrind原始报告
   */
  async getValgrindReport(pipelineId: number): Promise<string> {
    return request.get(`/api/v1/pipelines/${pipelineId}/valgrind-report`)
  },

  /**
   * 获取Address Sanitizer报告
   */
  async getASanReport(pipelineId: number): Promise<string> {
    return request.get(`/api/v1/pipelines/${pipelineId}/asan-report`)
  },

  /**
   * 导出内存问题报告
   */
  async exportMemoryIssues(
    projectId: number,
    format: 'json' | 'csv' | 'pdf',
    filters?: {
      severity?: string
      type?: string
      start_date?: string
      end_date?: string
    }
  ): Promise<Blob> {
    return request.post(
      `/api/v1/projects/${projectId}/memory-issues/export`,
      { format, filters },
      { responseType: 'blob' }
    )
  },

  /**
   * 获取内存安全问题统计
   */
  async getMemoryIssueStats(projectId: number): Promise<{
    total: number
    by_type: Record<string, number>
    by_severity: Record<string, number>
    by_detector: Record<string, number>
    trend: Array<{ date: string; count: number }>
  }> {
    return request.get(`/api/v1/projects/${projectId}/memory-issues/stats`)
  }
}
