import request from './request'
import type { Pipeline, PipelineFilters, PipelineStats } from '../types/pipeline'

export const pipelineApi = {
  /**
   * 获取流水线列表
   */
  async getPipelines(projectId: number, filters?: PipelineFilters): Promise<Pipeline[]> {
    return request.get(`/api/v1/projects/${projectId}/pipelines`, { params: filters })
  },

  /**
   * 获取流水线详情
   */
  async getPipeline(id: string): Promise<Pipeline> {
    return request.get(`/api/v1/pipelines/${id}`)
  },

  /**
   * 获取流水线统计信息
   */
  async getPipelineStats(projectId: number): Promise<PipelineStats> {
    return request.get(`/api/v1/projects/${projectId}/pipelines/stats`)
  },

  /**
   * 触发流水线
   */
  async triggerPipeline(projectId: number, ref: string): Promise<Pipeline> {
    return request.post(`/api/v1/projects/${projectId}/pipelines/trigger`, { ref })
  },

  /**
   * 重试流水线
   */
  async retryPipeline(id: string): Promise<Pipeline> {
    return request.post(`/api/v1/pipelines/${id}/retry`)
  },

  /**
   * 取消流水线
   */
  async cancelPipeline(id: string): Promise<void> {
    return request.post(`/api/v1/pipelines/${id}/cancel`)
  }
}
