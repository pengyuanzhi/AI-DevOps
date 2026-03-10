// 用户相关类型
export interface User {
  id: number
  username: string
  email: string
  full_name: string
  avatar?: string
  roles: string[]
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
  expires_in: number
}

// 项目相关类型
export interface Project {
  id: number
  name: string
  description: string
  gitlab_project_id: number
  gitlab_url: string
  default_branch: string
  created_at: string
  updated_at: string
}

// Pipeline相关类型
export interface Pipeline {
  id: number
  project_id: number
  project: string
  pipeline_id: number
  sha: string
  ref: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'skipped'
  source: 'push' | 'merge_request' | 'web' | 'trigger' | 'schedule' | 'api'
  duration: number
  created_at: string
  updated_at: string
  finished_at?: string
  stages: PipelineStage[]
  ai_diagnosis?: AIDiagnosis
}

export interface PipelineStage {
  name: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'skipped'
  duration: number
  jobs: PipelineJob[]
}

export interface PipelineJob {
  id: number
  name: string
  stage: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'skipped'
  duration: number
  created_at: string
  started_at?: string
  finished_at?: string
}

export interface PipelineFilters {
  status?: string
  source?: string
  ref?: string
  sha?: string
  page?: number
  per_page?: number
}

export interface PipelineStats {
  total: number
  success: number
  failed: number
  running: number
  success_rate: number
  avg_duration: number
}

// AI诊断相关类型
export interface AIDiagnosis {
  summary: string
  root_cause?: string
  suggestion?: string
  confidence: number
  auto_fix_available?: boolean
  auto_fix_confidence?: number
}

// 测试相关类型
export interface TestSuite {
  id: number
  name: string
  framework: 'qt_test' | 'gtest' | 'catch2'
  total_tests: number
  passed: number
  failed: number
  skipped: number
  duration: number
  created_at: string
}

export interface TestCase {
  id: number
  name: string
  suite: string
  file_path: string
  line_number: number
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped' | 'timeout'
  duration: number
  output: string
  error_message?: string
  stack_trace?: string
}

export interface TestResult {
  test_case_id: number
  status: 'passed' | 'failed' | 'skipped'
  duration: number
  output: string
  error_message?: string
  created_at: string
}

export interface TestCoverage {
  lines: number
  functions: number
  branches: number
  line_coverage: number
  function_coverage: number
  branch_coverage: number
}

export interface TestSelection {
  id: number
  merge_request_id: number
  total_tests: number
  selected_tests: number
  skipped_tests: number
  estimated_time_saved: number
  original_time: number
  confidence: number
  selected_test_ids: number[]
  reasons: TestSelectionReason[]
  created_at: string
}

export interface TestSelectionReason {
  test_id: number
  test_name: string
  reason: string
  priority: 'high' | 'medium' | 'low'
}

// 代码审查相关类型
export interface CodeReview {
  id: number
  merge_request_id: number
  total_issues: number
  critical_issues: number
  high_issues: number
  medium_issues: number
  low_issues: number
  quality_score: number
  false_positive_rate: number
  created_at: string
}

export interface CodeIssue {
  id: number
  review_id: number
  file_path: string
  line_number: number
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
  message: string
  code_snippet?: string
  fix_suggestion?: string
  confidence: number
  has_fix: boolean
  detector: 'clang_tidy' | 'cppcheck' | 'ai'
  is_false_positive: boolean
  created_at: string
}

export interface QualityScore {
  overall: number
  memory_safety: number
  performance: number
  modern_cpp: number
  thread_safety: number
  code_style: number
}

// 内存安全相关类型
export interface MemoryIssue {
  id: number
  type: 'memory_leak' | 'buffer_overflow' | 'dangling_pointer' | 'use_after_free' | 'double_free' | 'uninitialized_memory'
  severity: 'critical' | 'high' | 'medium' | 'low'
  file_path: string
  line_number: number
  function: string
  confidence: number
  detector: 'valgrind' | 'address_sanitizer'
  raw_report: string
  stack_trace: StackFrame[]
  code_snippet: CodeSnippet[]
  ai_analysis: AIAnalysis
  fix_suggestion?: FixSuggestion
  has_fix: boolean
  is_false_positive: boolean
  created_at: string
}

export interface StackFrame {
  function: string
  file: string
  line: number
  address: string
}

export interface CodeSnippet {
  number: number
  content: string
}

export interface AIAnalysis {
  root_cause: string
  impact: string
  false_positive_risk: number
}

export interface FixSuggestion {
  description: string
  modern_cpp: string
  fix_code?: string
}

export interface MemorySafetyScore {
  overall: number
  trend: number
  issue_stats: {
    critical: number
    high: number
    medium: number
    low: number
  }
}

// MR相关类型
export interface MergeRequest {
  id: number
  project_id: number
  project: string
  title: string
  description: string
  author: string
  source_branch: string
  target_branch: string
  sha: string
  status: 'open' | 'closed' | 'merged'
  created_at: string
  updated_at: string
}

export interface MRAnalysis {
  id: number
  mr_id: number
  analysis_type: 'test_selection' | 'code_review' | 'pipeline_maintenance'
  confidence: number
  status: 'pending' | 'accepted' | 'rejected' | 'false_positive'
  result: any
  created_at: string
}

// Dashboard统计数据类型
export interface DashboardStats {
  project_health: number
  today_builds: number
  build_success_rate: number
  avg_build_time: number
  avg_test_time: number
  active_pipelines: number
}

export interface TestQualityStats {
  total_tests: number
  passed_tests: number
  failed_tests: number
  skipped_tests: number
  test_success_rate: number
  coverage_lines: number
  coverage_functions: number
  coverage_branches: number
}

export interface CodeReviewStats {
  total_reviews: number
  total_issues: number
  critical_issues: number
  high_issues: number
  medium_issues: number
  low_issues: number
  quality_score: number
  false_positive_count: number
}

// 通用分页类型
export interface PaginationParams {
  page?: number
  per_page?: number
  limit?: number
  offset?: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// WebSocket消息类型
export interface WSMessage {
  type: 'log' | 'status' | 'progress' | 'error' | 'complete'
  topic: string
  data: any
  timestamp: number
}

export interface LogEntry {
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical'
  message: string
  timestamp: number
  source?: string
}

// API响应类型
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface ApiError {
  code: number
  message: string
  details?: any
}
