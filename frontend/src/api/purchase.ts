// 采购管理 API
import api from './index'

// ── 供应商 ──
export function listSuppliers(params?: Record<string, any>) {
  return api.get('/purchases/suppliers', { params })
}
export function getSupplier(id: number) {
  return api.get(`/purchases/suppliers/${id}`)
}
export function createSupplier(data: Record<string, any>) {
  return api.post('/purchases/suppliers', data)
}
export function updateSupplier(id: number, data: Record<string, any>) {
  return api.patch(`/purchases/suppliers/${id}`, data)
}
export function deleteSupplier(id: number) {
  return api.delete(`/purchases/suppliers/${id}`)
}

// ── 评估 ──
export function listEvaluations(supplierId: number) {
  return api.get(`/purchases/suppliers/${supplierId}/evaluations`)
}
export function createEvaluation(supplierId: number, data: Record<string, any>) {
  return api.post(`/purchases/suppliers/${supplierId}/evaluations`, data)
}

// ── 统计 ──
export function getSupplierStats() {
  return api.get('/purchases/suppliers/stats/summary')
}
export function getSupplierRanking(limit?: number) {
  return api.get('/purchases/suppliers/ranking/list', { params: { limit: limit || 20 } })
}
export function getSupplierCategories() {
  return api.get('/purchases/suppliers/categories/list')
}

// ── 收货管理 ──
export function listReceipts(params?: Record<string, any>) {
  return api.get('/purchases/receipts', { params })
}
export function getReceipt(id: number) {
  return api.get(`/purchases/receipts/${id}`)
}
export function createReceipt(data: Record<string, any>) {
  return api.post('/purchases/receipts', data)
}
export function deleteReceipt(id: number) {
  return api.delete(`/purchases/receipts/${id}`)
}

// ── 检验 ──
export function listInspections(receiptId: number) {
  return api.get(`/purchases/receipts/${receiptId}/inspections`)
}
export function createInspection(data: Record<string, any>) {
  return api.post('/purchases/inspections', data)
}
export function getReceiptStats() {
  return api.get('/purchases/receipts/stats/summary')
}
