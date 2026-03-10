import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  DashboardStats,
  TestQualityStats,
  CodeReviewStats
} from '../types'
import { dashboardApi } from '../api'

export const useDashboardStore = defineStore('dashboard', () => {
  const dashboardStats = ref<DashboardStats | null>(null)
  const testQualityStats = ref<TestQualityStats | null>(null)
  const codeReviewStats = ref<CodeReviewStats | null>(null)
  const loading = ref(false)

  const healthTrend = ref<Array<{ date: string; health: number }>>([])
  const buildSuccessTrend = ref<Array<{ date: string; success_rate: number }>>([])
  const testPassRateTrend = ref<Array<{ date: string; pass_rate: number }>>([])

  /**
   * 获取Dashboard统计数据
   */
  async function fetchDashboardStats(projectId: number) {
    loading.value = true
    try {
      dashboardStats.value = await dashboardApi.getDashboardStats(projectId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取测试质量统计
   */
  async function fetchTestQualityStats(projectId: number) {
    loading.value = true
    try {
      testQualityStats.value = await dashboardApi.getTestQualityStats(projectId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取代码审查统计
   */
  async function fetchCodeReviewStats(projectId: number) {
    loading.value = true
    try {
      codeReviewStats.value = await dashboardApi.getCodeReviewStats(projectId)
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取健康度趋势
   */
  async function fetchHealthTrend(projectId: number, days: number = 30) {
    try {
      healthTrend.value = await dashboardApi.getHealthTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch health trend:', error)
    }
  }

  /**
   * 获取构建成功率趋势
   */
  async function fetchBuildSuccessTrend(projectId: number, days: number = 30) {
    try {
      buildSuccessTrend.value = await dashboardApi.getBuildSuccessTrend(projectId, { days })
    } catch (error) {
      console.error('Failed to fetch build success trend:', error)
    }
  }

  /**
   * 获取所有Dashboard数据
   */
  async function fetchAllDashboardData(projectId: number) {
    await Promise.all([
      fetchDashboardStats(projectId),
      fetchTestQualityStats(projectId),
      fetchCodeReviewStats(projectId),
      fetchHealthTrend(projectId, 30),
      fetchBuildSuccessTrend(projectId, 30)
    ])
  }

  return {
    dashboardStats,
    testQualityStats,
    codeReviewStats,
    loading,
    healthTrend,
    buildSuccessTrend,
    testPassRateTrend,
    fetchDashboardStats,
    fetchTestQualityStats,
    fetchCodeReviewStats,
    fetchHealthTrend,
    fetchBuildSuccessTrend,
    fetchAllDashboardData
  }
})
