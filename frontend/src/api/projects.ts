// 项目管理 API
import api from './index'

// ── 类型 ──
export interface ProjectCreate {
  name: string
  code?: string
  description?: string
  status?: string
  priority?: string
  start_date?: string
  end_date?: string
  manager_id?: number
  [key: string]: any
}

export interface ProjectUpdate {
  name?: string
  description?: string
  status?: string
  priority?: string
  start_date?: string
  end_date?: string
  manager_id?: number
  [key: string]: any
}

export interface ProjectOut {
  id: number
  name: string
  code: string
  description?: string
  status: string
  priority: string
  start_date?: string
  end_date?: string
  manager_id?: number
  manager_name?: string
  created_at: string
  updated_at: string
  [key: string]: any
}

// ── CRUD ──
export function listProjects(params?: Record<string, any>) {
  return api.get('/projects', { params })
}

export function getProject(id: number) {
  return api.get(`/projects/${id}`)
}

export function createProject(data: ProjectCreate) {
  return api.post('/projects', data)
}

export function updateProject(id: number, data: ProjectUpdate) {
  return api.patch(`/projects/${id}`, data)
}

export function deleteProject(id: number) {
  return api.delete(`/projects/${id}`)
}

// ── 扩展操作 ──
export function getProjectStats(params?: Record<string, any>) {
  return api.get('/projects/stats', { params })
}

export function getProjectGantt(id: number) {
  return api.get(`/projects/${id}/gantt`)
}
