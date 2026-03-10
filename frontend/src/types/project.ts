export interface Project {
  id: string
  gitlab_project_id: number
  name: string
  description: string | null
  gitlab_url: string
  default_branch: string
  config: Record<string, any>
  created_at: string
  updated_at: string
}

export interface CreateProjectRequest {
  gitlab_project_id: number
  name: string
  description?: string
  config?: Record<string, any>
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
  default_branch?: string
  config?: Record<string, any>
}
