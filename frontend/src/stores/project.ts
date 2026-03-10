import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from '../types/project'
import { projectApi } from '../api/project'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      projects.value = await projectApi.getProjects()
    } finally {
      loading.value = false
    }
  }

  async function fetchProject(id: number) {
    loading.value = true
    try {
      currentProject.value = await projectApi.getProject(id)
    } finally {
      loading.value = false
    }
  }

  function setCurrentProject(project: Project) {
    currentProject.value = project
  }

  return {
    projects,
    currentProject,
    loading,
    fetchProjects,
    fetchProject,
    setCurrentProject
  }
})
