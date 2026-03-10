import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  MRAnalysis,
  TestSelection,
  AIDiagnosis,
  PaginationParams
} from '../types'
import { aiAnalysisApi } from '../api'

export const useAIAnalysisStore = defineStore('aiAnalysis', () => {
  const mrAnalyses = ref<MRAnalysis[]>([])
  const currentAnalysis = ref<MRAnalysis | null>(null)
  const testSelection = ref<TestSelection | null>(null)
  const pipelineDiagnosis = ref<AIDiagnosis | null>(null)
  const loading = ref(false)

  const dependencyGraph = ref<{
    nodes: Array<{ id: string; label: string; type: string }>
    edges: Array<{ from: string; to: string; label?: string }>
  }>({ nodes: [], edges: [] })

  const impactAnalysis = ref<{
    changed_files: string[]
    affected_functions: string[]
    affected_modules: string[]
    impact_radius: number
  }>({ changed_files: [], affected_functions: [], affected_modules: [], impact_radius: 0 })

  const aiModelConfig = ref<{
    test_selection_model: string
    code_review_model: string
    pipeline_maintenance_model: string
    natural_language_model: string
  }>({
    test_selection_model: 'zhipu-glm4',
    code_review_model: 'zhipu-glm4',
    pipeline_maintenance_model: 'zhipu-glm4',
    natural_language_model: 'zhipu-glm4'
  })

  // ==================== 智能测试选择 ====================

  /**
   * 获取测试选择分析
   */
  async function fetchTestSelection(mrId: number) {
    loading.value = true
    try {
      testSelection.value = await aiAnalysisApi.getTestSelection(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发智能测试选择
   */
  async function triggerTestSelection(mrId: number) {
    loading.value = true
    try {
      testSelection.value = await aiAnalysisApi.triggerTestSelection(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取依赖关系图
   */
  async function fetchDependencyGraph(mrId: number) {
    loading.value = true
    try {
      dependencyGraph.value = await aiAnalysisApi.getDependencyGraph(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取影响域分析
   */
  async function fetchImpactAnalysis(mrId: number) {
    loading.value = true
    try {
      impactAnalysis.value = await aiAnalysisApi.getImpactAnalysis(mrId)
    } finally {
      loading.value = false
    }
  }

  // ==================== 代码审查AI分析 ====================

  /**
   * 获取AI代码审查
   */
  async function fetchAICodeReview(mrId: number) {
    loading.value = true
    try {
      currentAnalysis.value = await aiAnalysisApi.getAICodeReview(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发AI代码审查
   */
  async function triggerAICodeReview(mrId: number) {
    loading.value = true
    try {
      currentAnalysis.value = await aiAnalysisApi.triggerAICodeReview(mrId)
    } finally {
      loading.value = false
    }
  }

  // ==================== 自主流水线维护 ====================

  /**
   * 获取流水线AI诊断
   */
  async function fetchPipelineDiagnosis(pipelineId: number) {
    loading.value = true
    try {
      pipelineDiagnosis.value = await aiAnalysisApi.getPipelineDiagnosis(pipelineId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发流水线AI诊断
   */
  async function triggerPipelineDiagnosis(pipelineId: number) {
    loading.value = true
    try {
      pipelineDiagnosis.value = await aiAnalysisApi.triggerPipelineDiagnosis(pipelineId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 应用AI自动修复
   */
  async function applyAIFix(pipelineId: number) {
    loading.value = true
    try {
      return await aiAnalysisApi.applyAIFix(pipelineId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取失败的测试用例检测
   */
  async function fetchFailedTestDetection(pipelineId: number) {
    loading.value = true
    try {
      return await aiAnalysisApi.getFailedTestDetection(pipelineId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 隔离失败的测试用例
   */
  async function isolateFailedTest(pipelineId: number, testId: number) {
    loading.value = true
    try {
      await aiAnalysisApi.isolateFailedTest(pipelineId, testId)
    } finally {
      loading.value = false
    }
  }

  // ==================== AI反馈机制 ====================

  /**
   * 提交AI反馈
   */
  async function submitFeedback(data: {
    analysis_id: number
    analysis_type: 'test_selection' | 'code_review' | 'pipeline_maintenance'
    is_positive: boolean
    category?: string
    comment?: string
  }) {
    loading.value = true
    try {
      await aiAnalysisApi.submitFeedback(data)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取AI分析历史
   */
  async function fetchAnalysisHistory(projectId: number, params?: PaginationParams) {
    loading.value = true
    try {
      const result = await aiAnalysisApi.getAnalysisHistory(projectId, params)
      mrAnalyses.value = result.data
      return result
    } finally {
      loading.value = false
    }
  }

  // ==================== AI模型配置 ====================

  /**
   * 获取AI模型配置
   */
  async function fetchAIModelConfig(projectId: number) {
    try {
      aiModelConfig.value = await aiAnalysisApi.getAIModelConfig(projectId)
    } catch (error) {
      console.error('Failed to fetch AI model config:', error)
    }
  }

  /**
   * 更新AI模型配置
   */
  async function updateAIModelConfig(projectId: number, config: Partial<typeof aiModelConfig.value>) {
    loading.value = true
    try {
      await aiAnalysisApi.updateAIModelConfig(projectId, config)
      aiModelConfig.value = { ...aiModelConfig.value, ...config }
    } finally {
      loading.value = false
    }
  }

  /**
   * 测试AI模型连接
   */
  async function testAIModel(model: string) {
    loading.value = true
    try {
      return await aiAnalysisApi.testAIModel(model)
    } finally {
      loading.value = false
    }
  }

  // ==================== 自然语言配置生成 ====================

  /**
   * 自然语言生成CI/CD配置
   */
  async function generateConfigFromNaturalLanguage(data: {
    project_id: number
    description: string
    language?: 'zh' | 'en'
  }) {
    loading.value = true
    try {
      return await aiAnalysisApi.generateConfigFromNaturalLanguage(data)
    } finally {
      loading.value = false
    }
  }

  /**
   * 验证生成的配置
   */
  async function validateGeneratedConfig(yamlContent: string) {
    loading.value = true
    try {
      return await aiAnalysisApi.validateGeneratedConfig(yamlContent)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取配置优化建议
   */
  async function fetchConfigOptimization(projectId: number) {
    loading.value = true
    try {
      return await aiAnalysisApi.getConfigOptimization(projectId)
    } finally {
      loading.value = false
    }
  }

  return {
    mrAnalyses,
    currentAnalysis,
    testSelection,
    pipelineDiagnosis,
    loading,
    dependencyGraph,
    impactAnalysis,
    aiModelConfig,
    // 智能测试选择
    fetchTestSelection,
    triggerTestSelection,
    fetchDependencyGraph,
    fetchImpactAnalysis,
    // 代码审查AI
    fetchAICodeReview,
    triggerAICodeReview,
    // 自主流水线维护
    fetchPipelineDiagnosis,
    triggerPipelineDiagnosis,
    applyAIFix,
    fetchFailedTestDetection,
    isolateFailedTest,
    // 反馈机制
    submitFeedback,
    fetchAnalysisHistory,
    // 模型配置
    fetchAIModelConfig,
    updateAIModelConfig,
    testAIModel,
    // 自然语言配置
    generateConfigFromNaturalLanguage,
    validateGeneratedConfig,
    fetchConfigOptimization
  }
})
