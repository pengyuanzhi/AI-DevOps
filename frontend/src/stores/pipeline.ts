import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Pipeline, PipelineFilters } from '../types/pipeline'
import { pipelineApi } from '../api/pipeline'

export const usePipelineStore = defineStore('pipeline', () => {
  const pipelines = ref<Pipeline[]>([])
  const currentPipeline = ref<Pipeline | null>(null)
  const loading = ref(false)
  const filters = ref<PipelineFilters>({
    status: undefined,
    branch: undefined,
    page: 1,
    per_page: 20
  })

  const paginatedPipelines = computed(() => {
    // 简单分页逻辑，实际应该在后端处理
    const page = filters.value.page || 1
    const perPage = filters.value.per_page || 20
    const start = (page - 1) * perPage
    const end = start + perPage
    return pipelines.value.slice(start, end)
  })

  async function fetchPipelines(projectId: number) {
    loading.value = true
    try {
      pipelines.value = await pipelineApi.getPipelines(projectId, filters.value)
    } finally {
      loading.value = false
    }
  }

  async function fetchPipeline(id: string) {
    loading.value = true
    try {
      currentPipeline.value = await pipelineApi.getPipeline(id)
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: Partial<PipelineFilters>) {
    filters.value = { ...filters.value, ...newFilters }
  }

  return {
    pipelines,
    currentPipeline,
    loading,
    filters,
    paginatedPipelines,
    fetchPipelines,
    fetchPipeline,
    setFilters
  }
})
