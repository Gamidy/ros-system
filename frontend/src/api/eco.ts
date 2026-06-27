import api from './index'

export interface ECOItemCreate {
  change_type: string
  object_type: string
  object_id?: number
  object_code?: string
  object_name?: string
  old_value?: string
  new_value?: string
  description?: string
}

export interface ECOItemOut extends ECOItemCreate {
  id: number
  eco_id: number
  seq: number
  created_at: string
}

export interface ECOCreate {
  ecr_id?: number
  title: string
  change_summary: string
  implementation_plan?: string
  effective_date?: string
  items?: ECOItemCreate[]
}

export interface ECOUpdate {
  title?: string
  change_summary?: string
  implementation_plan?: string
  effective_date?: string
}

export interface ECOOut {
  id: number
  code: string
  ecr_id?: number
  title: string
  change_summary: string
  implementation_plan?: string
  effective_date?: string
  status: string
  created_by: number
  created_at: string
  updated_at: string
  item_count: number
}

export interface ECODetailOut extends ECOOut {
  items: ECOItemOut[]
  ecr_code?: string
  ecr_title?: string
  created_by_name?: string
}

export interface ECOListResponse {
  total: number
  page: number
  page_size: number
  items: ECOOut[]
}

export interface ECOChDashboard {
  status_summary: Record<string, number>
  type_distribution: Record<string, number>
  this_month_new: number
  pending_verification: number
  changes: ECOOut[]
}

// 获取ECO列表
export function fetchECOs(params?: {
  status?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  return api.get('/eco', { params }).then(res => res.data as ECOListResponse)
}

// 获取ECO详情
export function fetchECO(id: number) {
  return api.get(`/eco/${id}`).then(res => res.data as ECODetailOut)
}

// 创建ECO
export function createECO(data: ECOCreate) {
  return api.post('/eco', data).then(res => res.data as ECOOut)
}

// 更新ECO
export function updateECO(id: number, data: ECOUpdate) {
  return api.put(`/eco/${id}`, data).then(res => res.data as ECOOut)
}

// 删除ECO
export function deleteECO(id: number) {
  return api.delete(`/eco/${id}`)
}

// 开始实施
export function implementECO(id: number) {
  return api.post(`/eco/${id}/implement`).then(res => res.data as ECOOut)
}

// 验证通过
export function verifyECO(id: number) {
  return api.post(`/eco/${id}/verify`).then(res => res.data as ECOOut)
}

// 生效
export function effectiveECO(id: number) {
  return api.post(`/eco/${id}/effective`).then(res => res.data as ECOOut)
}

// 关闭
export function closeECO(id: number) {
  return api.post(`/eco/${id}/close`).then(res => res.data as ECOOut)
}

// 取消
export function cancelECO(id: number) {
  return api.post(`/eco/${id}/cancel`).then(res => res.data as ECOOut)
}

// 新增明细项
export function addECOItem(ecoId: number, data: ECOItemCreate) {
  return api.post(`/eco/${ecoId}/items`, data).then(res => res.data as ECOItemOut)
}

// 更新明细项
export function updateECOItem(ecoId: number, itemId: number, data: Partial<ECOItemCreate>) {
  return api.put(`/eco/${ecoId}/items/${itemId}`, data).then(res => res.data as ECOItemOut)
}

// 删除明细项
export function deleteECOItem(ecoId: number, itemId: number) {
  return api.delete(`/eco/${ecoId}/items/${itemId}`)
}

// 变更看板
export function fetchChangeDashboard() {
  return api.get('/eco/changes').then(res => res.data as ECOChDashboard)
}
