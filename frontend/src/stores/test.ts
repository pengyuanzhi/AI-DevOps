import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  TestSuite,
  TestCase,
  TestCoverage,
  TestSelection,
  TestQualityStats,
  PaginationParams
} from '../types'
import { testApi } from '../api'

export const useTestStore = defineStore('test', () => {
  const testSuites = ref<TestSuite[]>([])
  const currentTestSuite = ref<TestSuite | null>(null)
  const testCases = ref<TestCase[]>([])
  const currentTestCase = ref<TestCase | null>(null)
  const testCoverage = ref<TestCoverage | null>(null)
  const testSelection = ref<TestSelection | null>(null)
  const loading = ref(false)

  const pagination = ref({
    page: 1,
    per_page: 20,
    total: 0,
    total_pages: 0
  })

  const coverageTrend = ref<Array<{
    date: string
    line_coverage: number
    function_coverage: number
    branch_coverage: number
  }>>([])

  const passRateTrend = ref<Array<{ date: string; pass_rate: number }>>([])

  const failedTests = computed(() =>
    testCases.value.filter(tc => tc.status === 'failed')
  )

  /**
   * 获取测试套件列表
   */
  async function fetchTestSuites(projectId: number, params?: PaginationParams) {
    loading.value = true
    try {
      const result = await testApi.getTestSuites(projectId, params)
      testSuites.value = result.data
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
   * 获取测试套件详情
   */
  async function fetchTestSuite(suiteId: number) {
    loading.value = true
    try {
      currentTestSuite.value = await testApi.getTestSuite(suiteId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取测试用例列表
   */
  async function fetchTestCases(suiteId: number, params?: PaginationParams & { status?: string }) {
    loading.value = true
    try {
      const result = await testApi.getTestCases(suiteId, params)
      testCases.value = result.data
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
   * 获取测试用例详情
   */
  async function fetchTestCase(caseId: number) {
    loading.value = true
    try {
      currentTestCase.value = await testApi.getTestCase(caseId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取代码覆盖率
   */
  async function fetchTestCoverage(projectId: number, pipelineId?: number) {
    try {
      testCoverage.value = await testApi.getTestCoverage(projectId, pipelineId)
    } catch (error) {
      console.error('Failed to fetch test coverage:', error)
    }
  }

  /**
   * 获取覆盖率趋势
   */
  async function fetchCoverageTrend(projectId: number, days: number = 30) {
    try {
      coverageTrend.value = await testApi.getCoverageTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch coverage trend:', error)
    }
  }

  /**
   * 获取测试通过率趋势
   */
  async function fetchPassRateTrend(projectId: number, days: number = 30) {
    try {
      passRateTrend.value = await testApi.getTestPassRateTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch pass rate trend:', error)
    }
  }

  /**
   * 获取智能测试选择
   */
  async function fetchTestSelection(mrId: number) {
    loading.value = true
    try {
      testSelection.value = await testApi.getTestSelection(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发测试选择
   */
  async function triggerTestSelection(mrId: number) {
    loading.value = true
    try {
      testSelection.value = await testApi.triggerTestSelection(mrId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 重新运行测试
   */
  async function rerunTests(suiteId: number, testIds?: number[]) {
    loading.value = true
    try {
      await testApi.rerunTests(suiteId, testIds)
    } finally {
      loading.value = false
    }
  }

  return {
    testSuites,
    currentTestSuite,
    testCases,
    currentTestCase,
    testCoverage,
    testSelection,
    loading,
    pagination,
    coverageTrend,
    passRateTrend,
    failedTests,
    fetchTestSuites,
    fetchTestSuite,
    fetchTestCases,
    fetchTestCase,
    fetchTestCoverage,
    fetchCoverageTrend,
    fetchPassRateTrend,
    fetchTestSelection,
    triggerTestSelection,
    rerunTests
  }
})
