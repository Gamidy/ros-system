// DFM可制造性分析 API 层
import api from './index'

// ── 检查项模板 ──
export function listDFMChecklist(params: {
  page?: number; page_size?: number; dfm_category?: string
  severity?: string; keyword?: string; status?: string
}) { return api.get('/dfm/checklist', { params }) }

export function getDFMChecklist(id: number) { return api.get(`/dfm/checklist/${id}`) }
export function createDFMChecklist(data: Record<string, any>) { return api.post('/dfm/checklist', data) }
export function updateDFMChecklist(id: number, data: Record<string, any>) { return api.put(`/dfm/checklist/${id}`, data) }
export function deleteDFMChecklist(id: number) { return api.delete(`/dfm/checklist/${id}`) }

// ── 评分权重 ──
export function listDFMScoreWeights(product_type?: string) {
  return api.get('/dfm/score-weights', { params: { product_type } })
}
export function createDFMScoreWeight(data: Record<string, any>) { return api.post('/dfm/score-weights', data) }
export function updateDFMScoreWeight(id: number, data: Record<string, any>) { return api.put(`/dfm/score-weights/${id}`, data) }
export function deleteDFMScoreWeight(id: number) { return api.delete(`/dfm/score-weights/${id}`) }

// ── DFM报告 ──
export function listDFMReports(params: {
  page?: number; page_size?: number; project_id?: number
  prototype_id?: number; status?: string; keyword?: string
}) { return api.get('/dfm/reports', { params }) }

export function getDFMReport(id: number) { return api.get(`/dfm/reports/${id}`) }
export function createDFMReport(data: Record<string, any>) { return api.post('/dfm/reports', data) }
export function updateDFMReport(id: number, data: Record<string, any>) { return api.put(`/dfm/reports/${id}`, data) }
export function deleteDFMReport(id: number) { return api.delete(`/dfm/reports/${id}`) }
export function getDFMReportScore(id: number) { return api.get(`/dfm/reports/${id}/score`) }

// ── 报告问题项 ──
export function listDFMReportItems(reportId: number) { return api.get(`/dfm/reports/${reportId}/items`) }
export function createDFMReportItem(data: Record<string, any>) { return api.post('/dfm/report-items', data) }
export function updateDFMReportItem(id: number, data: Record<string, any>) { return api.put(`/dfm/report-items/${id}`, data) }
export function deleteDFMReportItem(id: number) { return api.delete(`/dfm/report-items/${id}`) }
