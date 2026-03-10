/**
 * API服务统一导出
 * 提供所有API服务的统一访问入口
 */

export { authApi } from './auth'
export { projectApi } from './project'
export { pipelineApi } from './pipeline'
export { dashboardApi } from './dashboard'
export { testApi } from './test'
export { codeReviewApi } from './codeReview'
export { aiAnalysisApi } from './aiAnalysis'
export { memorySafetyApi } from './memorySafety'

// 导出类型
export type {
  // 用户相关
  User,
  LoginRequest,
  LoginResponse,

  // 项目相关
  Project,

  // Pipeline相关
  Pipeline,
  PipelineStage,
  PipelineJob,
  PipelineFilters,
  PipelineStats,

  // AI诊断
  AIDiagnosis,

  // 测试相关
  TestSuite,
  TestCase,
  TestResult,
  TestCoverage,
  TestSelection,
  TestSelectionReason,
  TestQualityStats,

  // 代码审查相关
  CodeReview,
  CodeIssue,
  QualityScore,
  CodeReviewStats,

  // 内存安全相关
  MemoryIssue,
  MemorySafetyScore,
  StackFrame,
  CodeSnippet,
  AIAnalysis,
  FixSuggestion,

  // MR相关
  MergeRequest,
  MRAnalysis,

  // Dashboard统计
  DashboardStats,

  // 分页
  PaginationParams,
  PaginatedResponse,

  // WebSocket
  WSMessage,
  LogEntry,

  // API响应
  ApiResponse,
  ApiError
} from '../types'
