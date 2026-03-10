import request from './request'
import type {
  MRAnalysis,
  TestSelection,
  AIDiagnosis,
  PaginationParams
} from '../types'

/**
 * AI分析API服务
 * 提供智能测试选择、代码审查、流水线维护等AI功能
 */
export const aiAnalysisApi = {
  // ==================== 智能测试选择 ====================

  /**
   * 获取MR的测试选择分析
   */
  async getTestSelection(mrId: number): Promise<TestSelection> {
    return request.get(`/api/v1/ai/mrs/${mrId}/test-selection`)
  },

  /**
   * 触发智能测试选择
   */
  async triggerTestSelection(mrId: number): Promise<TestSelection> {
    return request.post(`/api/v1/ai/mrs/${mrId}/test-selection`)
  },

  /**
   * 获取代码依赖关系图
   */
  async getDependencyGraph(mrId: number): Promise<{
    nodes: Array<{ id: string; label: string; type: string }>
    edges: Array<{ from: string; to: string; label?: string }>
  }> {
    return request.get(`/api/v1/ai/mrs/${mrId}/dependency-graph`)
  },

  /**
   * 获取影响域分析
   */
  async getImpactAnalysis(mrId: number): Promise<{
    changed_files: string[]
    affected_functions: string[]
    affected_modules: string[]
    impact_radius: number
  }> {
    return request.get(`/api/v1/ai/mrs/${mrId}/impact-analysis`)
  },

  // ==================== 代码审查AI分析 ====================

  /**
   * 获取MR的AI代码审查
   */
  async getAICodeReview(mrId: number): Promise<MRAnalysis> {
    return request.get(`/api/v1/ai/mrs/${mrId}/code-review`)
  },

  /**
   * 触发AI代码审查
   */
  async triggerAICodeReview(mrId: number): Promise<MRAnalysis> {
    return request.post(`/api/v1/ai/mrs/${mrId}/code-review`)
  },

  // ==================== 自主流水线维护 ====================

  /**
   * 获取流水线AI诊断
   */
  async getPipelineDiagnosis(pipelineId: number): Promise<AIDiagnosis> {
    return request.get(`/api/v1/ai/pipelines/${pipelineId}/diagnosis`)
  },

  /**
   * 触发流水线AI诊断
   */
  async triggerPipelineDiagnosis(pipelineId: number): Promise<AIDiagnosis> {
    return request.post(`/api/v1/ai/pipelines/${pipelineId}/diagnosis`)
  },

  /**
   * 应用AI自动修复
   */
  async applyAIFix(pipelineId: number): Promise<{ mr_id: number; fix_applied: boolean }> {
    return request.post(`/api/v1/ai/pipelines/${pipelineId}/apply-fix`)
  },

  /**
   * 获取失败的测试用例检测
   */
  async getFailedTestDetection(pipelineId: number): Promise<{
    detected_tests: Array<{
      test_id: number
      test_name: string
      failure_reason: string
      confidence: number
    }>
  }> {
    return request.get(`/api/v1/ai/pipelines/${pipelineId}/failed-tests`)
  },

  /**
   * 隔离失败的测试用例
   */
  async isolateFailedTest(pipelineId: number, testId: number): Promise<void> {
    return request.post(`/api/v1/ai/pipelines/${pipelineId}/isolate-test`, { test_id: testId })
  },

  // ==================== AI反馈机制 ====================

  /**
   * 提交AI反馈
   */
  async submitFeedback(data: {
    analysis_id: number
    analysis_type: 'test_selection' | 'code_review' | 'pipeline_maintenance'
    is_positive: boolean
    category?: 'false_positive' | 'not_applicable' | 'helpful' | 'not_helpful'
    comment?: string
  }): Promise<void> {
    return request.post('/api/v1/ai/feedback', data)
  },

  /**
   * 获取AI分析历史
   */
  async getAnalysisHistory(
    projectId: number,
    params?: PaginationParams
  ): Promise<PaginatedResponse<MRAnalysis>> {
    return request.get(`/api/v1/projects/${projectId}/ai/analysis-history`, { params })
  },

  // ==================== AI模型配置 ====================

  /**
   * 获取AI模型配置
   */
  async getAIModelConfig(projectId: number): Promise<{
    test_selection_model: string
    code_review_model: string
    pipeline_maintenance_model: string
    natural_language_model: string
  }> {
    return request.get(`/api/v1/projects/${projectId}/ai/model-config`)
  },

  /**
   * 更新AI模型配置
   */
  async updateAIModelConfig(
    projectId: number,
    config: {
      test_selection_model?: string
      code_review_model?: string
      pipeline_maintenance_model?: string
      natural_language_model?: string
    }
  ): Promise<void> {
    return request.put(`/api/v1/projects/${projectId}/ai/model-config`, config)
  },

  /**
   * 测试AI模型连接
   */
  async testAIModel(model: string): Promise<{ success: boolean; message: string }> {
    return request.post('/api/v1/ai/test-model', { model })
  },

  // ==================== 自然语言配置生成 ====================

  /**
   * 自然语言生成CI/CD配置
   */
  async generateConfigFromNaturalLanguage(data: {
    project_id: number
    description: string
    language?: 'zh' | 'en'
  }): Promise<{
    yaml_content: string
    explanation: string
    confidence: number
  }> {
    return request.post('/api/v1/ai/generate-config', data)
  },

  /**
   * 验证生成的配置
   */
  async validateGeneratedConfig(yamlContent: string): Promise<{
    valid: boolean
    errors?: string[]
    warnings?: string[]
  }> {
    return request.post('/api/v1/ai/validate-config', { yaml_content: yamlContent })
  },

  /**
   * 获取配置优化建议
   */
  async getConfigOptimization(projectId: number): Promise<{
    suggestions: Array<{
      type: string
      description: string
      priority: 'high' | 'medium' | 'low'
      example_before?: string
      example_after?: string
    }>
  }> {
    return request.get(`/api/v1/projects/${projectId}/ai/config-optimization`)
  }
}
