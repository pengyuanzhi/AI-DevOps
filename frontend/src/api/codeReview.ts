import request from './request'
import type {
  CodeReview,
  CodeIssue,
  QualityScore,
  CodeReviewStats,
  PaginationParams,
  PaginatedResponse
} from '../types'

/**
 * 代码审查API服务
 * 提供代码审查、问题管理、质量评分等功能
 */
export const codeReviewApi = {
  /**
   * 获取MR的代码审查结果
   */
  async getCodeReview(mrId: number): Promise<CodeReview> {
    return request.get(`/api/v1/mrs/${mrId}/code-review`)
  },

  /**
   * 触发代码审查
   */
  async triggerCodeReview(mrId: number): Promise<CodeReview> {
    return request.post(`/api/v1/mrs/${mrId}/code-review`)
  },

  /**
   * 获取代码问题列表
   */
  async getCodeIssues(
    reviewId: number,
    params?: PaginationParams & {
      severity?: string
      category?: string
      detector?: string
    }
  ): Promise<PaginatedResponse<CodeIssue>> {
    return request.get(`/api/v1/code-reviews/${reviewId}/issues`, { params })
  },

  /**
   * 获取代码问题详情
   */
  async getCodeIssue(issueId: number): Promise<CodeIssue> {
    return request.get(`/api/v1/code-issues/${issueId}`)
  },

  /**
   * 应用修复建议
   */
  async applyFix(issueId: number): Promise<{ mr_id: number }> {
    return request.post(`/api/v1/code-issues/${issueId}/apply-fix`)
  },

  /**
   * 标记为误报
   */
  async markAsFalsePositive(issueId: number, reason: string): Promise<void> {
    return request.post(`/api/v1/code-issues/${issueId}/false-positive`, { reason })
  },

  /**
   * 取消误报标记
   */
  async unmarkFalsePositive(issueId: number): Promise<void> {
    return request.post(`/api/v1/code-issues/${issueId}/unmark-false-positive`)
  },

  /**
   * 获取质量评分
   */
  async getQualityScore(projectId: number, mrId?: number): Promise<QualityScore> {
    const url = mrId
      ? `/api/v1/projects/${projectId}/code-quality/score?mr_id=${mrId}`
      : `/api/v1/projects/${projectId}/code-quality/score`
    return request.get(url)
  },

  /**
   * 获取质量评分历史趋势
   */
  async getQualityScoreTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{
    date: string
    overall: number
    memory_safety: number
    performance: number
    modern_cpp: number
    thread_safety: number
    code_style: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/code-quality/trend`, { params })
  },

  /**
   * 获取代码审查统计
   */
  async getCodeReviewStats(projectId: number): Promise<CodeReviewStats> {
    return request.get(`/api/v1/projects/${projectId}/code-reviews/stats`)
  },

  /**
   * 获取增量审查视图
   */
  async getIncrementalReview(mrId: number): Promise<{
    new_issues: CodeIssue[]
    fixed_issues: CodeIssue[]
    net_debt: number
  }> {
    return request.get(`/api/v1/mrs/${mrId}/incremental-review`)
  },

  /**
   * 获取变更文件列表
   */
  async getChangedFiles(mrId: number): Promise<Array<{
    file_path: string
    issue_count: number
    quality_score: number
  }>> {
    return request.get(`/api/v1/mrs/${mrId}/changed-files`)
  },

  /**
   * 获取技术债务趋势
   */
  async getTechnicalDebtTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{
    date: string
    total: number
    critical: number
    high: number
    medium: number
    low: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/code-quality/tech-debt-trend`, { params })
  },

  /**
   * 批量操作问题
   */
  async batchUpdateIssues(issueIds: number[], action: 'mark_fp' | 'unmark_fp' | 'apply_fix', reason?: string): Promise<void> {
    return request.post('/api/v1/code-issues/batch', { issue_ids: issueIds, action, reason })
  },

  /**
   * 获取自定义规则列表
   */
  async getCustomRules(projectId: number): Promise<Array<{
    id: number
    name: string
    category: string
    severity: string
    pattern: string
    enabled: boolean
  }>> {
    return request.get(`/api/v1/projects/${projectId}/code-quality/custom-rules`)
  },

  /**
   * 创建自定义规则
   */
  async createCustomRule(
    projectId: number,
    data: {
      name: string
      category: string
      severity: string
      pattern: string
      description?: string
    }
  ): Promise<void> {
    return request.post(`/api/v1/projects/${projectId}/code-quality/custom-rules`, data)
  },

  /**
   * 更新自定义规则
   */
  async updateCustomRule(ruleId: number, data: Partial<{
    name: string
    category: string
    severity: string
    pattern: string
    description: string
    enabled: boolean
  }>): Promise<void> {
    return request.put(`/api/v1/code-quality/custom-rules/${ruleId}`, data)
  },

  /**
   * 删除自定义规则
   */
  async deleteCustomRule(ruleId: number): Promise<void> {
    return request.delete(`/api/v1/code-quality/custom-rules/${ruleId}`)
  }
}
