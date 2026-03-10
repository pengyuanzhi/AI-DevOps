import request from './request'
import type {
  DashboardStats,
  TestQualityStats,
  CodeReviewStats,
  PaginationParams
} from '../types'

/**
 * Dashboard API服务
 * 提供项目概览、测试质量、代码审查等Dashboard数据
 */
export const dashboardApi = {
  /**
   * 获取项目概览统计数据
   */
  async getDashboardStats(projectId: number): Promise<DashboardStats> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/stats`)
  },

  /**
   * 获取项目健康度历史趋势
   */
  async getHealthTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{ date: string; health: number }>> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/health-trend`, { params })
  },

  /**
   * 获取构建成功率趋势
   */
  async getBuildSuccessTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{ date: string; success_rate: number }>> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/build-trend`, { params })
  },

  /**
   * 获取最近失败的Pipeline列表
   */
  async getRecentFailedPipelines(
    projectId: number,
    params?: PaginationParams
  ): Promise<Array<{ id: number; pipeline_id: number; status: string; created_at: string; project: string }>> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/failed-pipelines`, { params })
  },

  /**
   * 获取AI检测到的问题列表
   */
  async getAIIssues(
    projectId: number,
    params?: PaginationParams
  ): Promise<Array<{ id: number; type: string; severity: string; created_at: string }>> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/ai-issues`, { params })
  },

  /**
   * 获取待处理的MR列表
   */
  async getPendingMRs(
    projectId: number,
    params?: PaginationParams
  ): Promise<Array<{ id: number; title: string; author: string; created_at: string }>> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/pending-mrs`, { params })
  },

  /**
   * 获取活跃Pipeline数量
   */
  async getActivePipelineCount(projectId: number): Promise<{ count: number }> {
    return request.get(`/api/v1/projects/${projectId}/dashboard/active-pipelines`)
  }
}
