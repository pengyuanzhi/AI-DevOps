import request from './request'
import type {
  TestSuite,
  TestCase,
  TestResult,
  TestCoverage,
  TestSelection,
  TestQualityStats,
  PaginationParams,
  PaginatedResponse
} from '../types'

/**
 * 测试API服务
 * 提供测试套件、测试用例、覆盖率、智能测试选择等功能
 */
export const testApi = {
  /**
   * 获取测试套件列表
   */
  async getTestSuites(
    projectId: number,
    params?: PaginationParams
  ): Promise<PaginatedResponse<TestSuite>> {
    return request.get(`/api/v1/projects/${projectId}/tests/suites`, { params })
  },

  /**
   * 获取测试套件详情
   */
  async getTestSuite(suiteId: number): Promise<TestSuite> {
    return request.get(`/api/v1/tests/suites/${suiteId}`)
  },

  /**
   * 获取测试用例列表
   */
  async getTestCases(
    suiteId: number,
    params?: PaginationParams & { status?: string }
  ): Promise<PaginatedResponse<TestCase>> {
    return request.get(`/api/v1/tests/suites/${suiteId}/cases`, { params })
  },

  /**
   * 获取测试用例详情
   */
  async getTestCase(caseId: number): Promise<TestCase> {
    return request.get(`/api/v1/tests/cases/${caseId}`)
  },

  /**
   * 获取测试结果
   */
  async getTestResults(
    suiteId: number,
    params?: PaginationParams
  ): Promise<PaginatedResponse<TestResult>> {
    return request.get(`/api/v1/tests/suites/${suiteId}/results`, { params })
  },

  /**
   * 获取代码覆盖率
   */
  async getTestCoverage(projectId: number, pipelineId?: number): Promise<TestCoverage> {
    const url = pipelineId
      ? `/api/v1/projects/${projectId}/tests/coverage?pipeline_id=${pipelineId}`
      : `/api/v1/projects/${projectId}/tests/coverage`
    return request.get(url)
  },

  /**
   * 获取覆盖率趋势
   */
  async getCoverageTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{
    date: string
    line_coverage: number
    function_coverage: number
    branch_coverage: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/tests/coverage-trend`, { params })
  },

  /**
   * 获取测试质量统计
   */
  async getTestQualityStats(projectId: number): Promise<TestQualityStats> {
    return request.get(`/api/v1/projects/${projectId}/tests/stats`)
  },

  /**
   * 获取测试通过率趋势
   */
  async getTestPassRateTrend(
    projectId: number,
    params: { days: number }
  ): Promise<Array<{ date: string; pass_rate: number }>> {
    return request.get(`/api/v1/projects/${projectId}/tests/pass-rate-trend`, { params })
  },

  /**
   * 获取测试执行时间分布
   */
  async getTestDurationDistribution(projectId: number): Promise<Array<{
    range: string
    count: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/tests/duration-distribution`)
  },

  /**
   * 获取失败的测试列表
   */
  async getFailedTests(
    projectId: number,
    params?: PaginationParams
  ): Promise<PaginatedResponse<TestCase>> {
    return request.get(`/api/v1/projects/${projectId}/tests/failed`, { params })
  },

  /**
   * 获取不稳定的测试（flaky tests）
   */
  async getFlakyTests(
    projectId: number,
    params?: PaginationParams
  ): Promise<Array<{
    test_id: number
    test_name: string
    failure_rate: number
    total_runs: number
  }>> {
    return request.get(`/api/v1/projects/${projectId}/tests/flaky`, { params })
  },

  /**
   * 获取智能测试选择结果
   */
  async getTestSelection(mrId: number): Promise<TestSelection> {
    return request.get(`/api/v1/mrs/${mrId}/test-selection`)
  },

  /**
   * 触发测试选择
   */
  async triggerTestSelection(mrId: number): Promise<TestSelection> {
    return request.post(`/api/v1/mrs/${mrId}/test-selection`)
  },

  /**
   * 重新运行测试
   */
  async rerunTests(suiteId: number, testIds?: number[]): Promise<{ job_id: string }> {
    return request.post(`/api/v1/tests/suites/${suiteId}/rerun`, { test_ids: testIds })
  },

  /**
   * 获取测试日志
   */
  async getTestLogs(testResultId: number): Promise<string> {
    return request.get(`/api/v1/tests/results/${testResultId}/logs`)
  }
}
