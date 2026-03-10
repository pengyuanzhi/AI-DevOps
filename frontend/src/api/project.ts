import request from './request'
import type { Project, CreateProjectRequest, UpdateProjectRequest } from '../types/project'

export const projectApi = {
  /**
   * 获取项目列表
   */
  async getProjects(): Promise<Project[]> {
    return request.get('/api/v1/projects')
  },

  /**
   * 获取项目详情
   */
  async getProject(id: number): Promise<Project> {
    return request.get(`/api/v1/projects/${id}`)
  },

  /**
   * 创建项目
   */
  async createProject(data: CreateProjectRequest): Promise<Project> {
    return request.post('/api/v1/projects', data)
  },

  /**
   * 更新项目
   */
  async updateProject(id: number, data: UpdateProjectRequest): Promise<Project> {
    return request.put(`/api/v1/projects/${id}`, data)
  },

  /**
   * 删除项目
   */
  async deleteProject(id: number): Promise<void> {
    return request.delete(`/api/v1/projects/${id}`)
  },

  /**
   * 同步GitLab项目
   */
  async syncFromGitlab(gitlabProjectId: number): Promise<Project> {
    return request.post('/api/v1/projects/sync', { gitlab_project_id: gitlabProjectId })
  }
}
