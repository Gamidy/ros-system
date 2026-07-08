// 安规管理 API 层
import api from './index'

// ── 安全标准库 ──
export function listSafetyStandards(params: {
  page?: number
  page_size?: number
  keyword?: string
  standard_type?: string
  status?: string
  applicable_market?: string
}) {
  return api.get('/safety/standards', { params })
}

export function getSafetyStandard(id: number) {
  return api.get(`/safety/standards/${id}`)
}

export function createSafetyStandard(data: Record<string, any>) {
  return api.post('/safety/standards', data)
}

export function updateSafetyStandard(id: number, data: Record<string, any>) {
  return api.put(`/safety/standards/${id}`, data)
}

export function deleteSafetyStandard(id: number) {
  return api.delete(`/safety/standards/${id}`)
}

export function archiveSafetyStandard(id: number) {
  return api.put(`/safety/standards/${id}/archive`)
}

// ── 安规检测项 ──
export function listSafetyInspectionItems(params: {
  page?: number
  page_size?: number
  standard_id?: number
  inspection_category?: string
  keyword?: string
  status?: string
}) {
  return api.get('/safety/inspection-items', { params })
}

export function getSafetyInspectionItem(id: number) {
  return api.get(`/safety/inspection-items/${id}`)
}

export function createSafetyInspectionItem(data: Record<string, any>) {
  return api.post('/safety/inspection-items', data)
}

export function updateSafetyInspectionItem(id: number, data: Record<string, any>) {
  return api.put(`/safety/inspection-items/${id}`, data)
}

export function deleteSafetyInspectionItem(id: number) {
  return api.delete(`/safety/inspection-items/${id}`)
}

export function batchImportInspectionItems(items: Record<string, any>[]) {
  return api.post('/safety/inspection-items/batch', items)
}

// ── 供应商安规资质 ──
export function listSupplierQualifications(params: {
  page?: number
  page_size?: number
  supplier_id?: number
  qualification_type?: string
  status?: string
  audit_status?: string
  expiry_soon?: number
  keyword?: string
}) {
  return api.get('/safety/supplier-qualifications', { params })
}

export function getSupplierQualification(id: number) {
  return api.get(`/safety/supplier-qualifications/${id}`)
}

export function createSupplierQualification(data: Record<string, any>) {
  return api.post('/safety/supplier-qualifications', data)
}

export function updateSupplierQualification(id: number, data: Record<string, any>) {
  return api.put(`/safety/supplier-qualifications/${id}`, data)
}

export function deleteSupplierQualification(id: number) {
  return api.delete(`/safety/supplier-qualifications/${id}`)
}

// ── 供应商安规审核记录 ──
export function listAuditRecords(qualificationId: number) {
  return api.get(`/safety/supplier-qualifications/${qualificationId}/audit-records`)
}

export function createAuditRecord(data: Record<string, any>) {
  return api.post('/safety/audit-records', data)
}

// ── 安规预警 ──
export function getSafetyAlerts(params: { days?: number; severity?: string }) {
  return api.get('/safety/alerts', { params })
}
