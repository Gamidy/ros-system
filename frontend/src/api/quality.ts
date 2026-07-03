// 品质管理 API
import api from './index'

// ── 质量工作台 ──
export function getQualityDashboard(params?: Record<string, any>) {
  return api.get('/quality/dashboard', { params })
}

// ── 8D报告 ──
export function listEightDReports(params?: Record<string, any>) {
  return api.get('/quality/8d-reports', { params })
}

export function getEightDReport(id: number) {
  return api.get(`/quality/8d-reports/${id}`)
}

export function createEightDReport(data: Record<string, any>) {
  return api.post('/quality/8d-reports', data)
}

export function updateEightDReport(id: number, data: Record<string, any>) {
  return api.patch(`/quality/8d-reports/${id}`, data)
}

export function deleteEightDReport(id: number) {
  return api.delete(`/quality/8d-reports/${id}`)
}

// ── 来料检验 IQC ──
export function listIQC(params?: Record<string, any>) {
  return api.get('/quality/iqc', { params })
}

export function getIQC(id: number) {
  return api.get(`/quality/iqc/${id}`)
}

export function createIQC(data: Record<string, any>) {
  return api.post('/quality/iqc', data)
}

export function updateIQC(id: number, data: Record<string, any>) {
  return api.patch(`/quality/iqc/${id}`, data)
}

// ── 客户投诉 ──
export function listComplaints(params?: Record<string, any>) {
  return api.get('/quality/complaints', { params })
}

export function getComplaint(id: number) {
  return api.get(`/quality/complaints/${id}`)
}

export function createComplaint(data: Record<string, any>) {
  return api.post('/quality/complaints', data)
}

export function updateComplaint(id: number, data: Record<string, any>) {
  return api.patch(`/quality/complaints/${id}`, data)
}

// ── 改善任务 ──
export function listImprovementTasks(params?: Record<string, any>) {
  return api.get('/quality/improvement-tasks', { params })
}

export function getImprovementTask(id: number) {
  return api.get(`/quality/improvement-tasks/${id}`)
}

export function createImprovementTask(data: Record<string, any>) {
  return api.post('/quality/improvement-tasks', data)
}

export function updateImprovementTask(id: number, data: Record<string, any>) {
  return api.patch(`/quality/improvement-tasks/${id}`, data)
}

export function deleteImprovementTask(id: number) {
  return api.delete(`/quality/improvement-tasks/${id}`)
}
