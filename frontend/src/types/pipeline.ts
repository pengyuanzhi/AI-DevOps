export type PipelineStatus = 'pending' | 'running' | 'success' | 'failed' | 'canceled' | 'skipped'

export interface Pipeline {
  id: string
  gitlab_pipeline_id: number
  gitlab_project_id: number
  gitlab_mr_iid: number | null
  status: PipelineStatus
  ref: string
  sha: string
  source: string
  duration_seconds: number | null
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
  jobs?: Job[]
}

export interface Job {
  id: string
  gitlab_job_id: number
  pipeline_id: string
  gitlab_project_id: number
  name: string
  stage: string
  status: PipelineStatus
  duration_seconds: number | null
  logs: string | null
  retry_count: number
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
}

export interface PipelineFilters {
  status?: PipelineStatus
  branch?: string
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
