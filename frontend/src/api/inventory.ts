// 库存管理 API
import api from './index'

// ── 库存总览 ──
export function listInventory(params?: Record<string, any>) {
  return api.get('/inventory', { params })
}

export function getInventoryItem(id: number) {
  return api.get(`/inventory/${id}`)
}

export function updateInventoryItem(id: number, data: Record<string, any>) {
  return api.patch(`/inventory/${id}`, data)
}

// ── 仓库管理 ──
export function listWarehouses(params?: Record<string, any>) {
  return api.get('/inventory/warehouses', { params })
}

export function getWarehouse(id: number) {
  return api.get(`/inventory/warehouses/${id}`)
}

export function createWarehouse(data: Record<string, any>) {
  return api.post('/inventory/warehouses', data)
}

export function updateWarehouse(id: number, data: Record<string, any>) {
  return api.patch(`/inventory/warehouses/${id}`, data)
}

export function deleteWarehouse(id: number) {
  return api.delete(`/inventory/warehouses/${id}`)
}

// ── 库存流水 ──
export function listTransactions(params?: Record<string, any>) {
  return api.get('/inventory/transactions', { params })
}

// ── 盘点管理 ──
export function listCounts(params?: Record<string, any>) {
  return api.get('/inventory/counts', { params })
}

export function createCount(data: Record<string, any>) {
  return api.post('/inventory/counts', data)
}

export function updateCount(id: number, data: Record<string, any>) {
  return api.patch(`/inventory/counts/${id}`, data)
}

// ── 库位管理 ──
export function listLocations(params?: Record<string, any>) {
  return api.get('/inventory/locations', { params })
}

// ── 库存预警 ──
export function listInventoryAlerts(params?: Record<string, any>) {
  return api.get('/inventory/alerts', { params })
}

// ── 补货建议 ──
export function listReplenishments(params?: Record<string, any>) {
  return api.get('/inventory/replenishments', { params })
}
