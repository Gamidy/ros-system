import api from './index'

export interface ECRCreate {
  title: string
  ecr_type: string
  reason: string
  urgency: string
  affected_products?: string
  affected_documents?: string
  description?: string
}

export interface ECRUpdate {
  title?: string
  ecr_type?: string
  reason?: string
  urgency?: string
  affected_products?: string
  affected_documents?: string
  description?: string
}

export interface ECROut {
  id: number
  code: string
  title: string
  ecr_type: string
  reason: string
  urgency: string
  affected_products?: Record<string, unknown>
  affected_documents?: Record<string, unknown>
  description?: string
  status: string
  submitter_id: number
  submitter_name?: string
  created_at: string
  updated_at: string
  attachment_count: number
}

export interface ECRDetailOut extends ECROut {
  attachments: Array<{
    id: number
    ecr_id: number
    file_name: string
    file_path: string
    file_type?: string
    file_size: number
    uploaded_by?: string
    created_at: string
  }>
  eco_code?: string
  eco_id?: number
  eco_status?: string
}

export interface ECRListResponse {
  total: number
  page: number
  page_size: number
  items: ECROut[]
}

// 获取ECR列表
export function fetchECRs(params?: {
  status?: string
  ecr_type?: string
  urgency?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  return api.get('/ecr', { params }).then(res => res.data as ECRListResponse)
}

// 获取ECR详情
export function fetchECR(id: number) {
  return api.get(`/ecr/${id}`).then(res => res.data as ECRDetailOut)
}

// 创建ECR
export function createECR(data: ECRCreate) {
  return api.post('/ecr', data).then(res => res.data as ECROut)
}

// 更新ECR
export function updateECR(id: number, data: ECRUpdate) {
  return api.put(`/ecr/${id}`, data).then(res => res.data as ECROut)
}

// 删除ECR
export function deleteECR(id: number) {
  return api.delete(`/ecr/${id}`)
}

// 提交审批
export function submitECR(id: number) {
  return api.post(`/ecr/${id}/submit`).then(res => res.data as ECROut)
}

// 撤回审批
export function withdrawECR(id: number) {
  return api.post(`/ecr/${id}/withdraw`).then(res => res.data as ECROut)
}

// 开始评审
export function reviewECR(id: number) {
  return api.post(`/ecr/${id}/review`).then(res => res.data as ECROut)
}

// 批准ECR
export function approveECR(id: number) {
  return api.post(`/ecr/${id}/approve`).then(res => res.data as ECROut)
}

// 驳回ECR
export function rejectECR(id: number, reason: string) {
  return api.post(`/ecr/${id}/reject`, { rejection_reason: reason }).then(res => res.data as ECROut)
}

// 转ECO
export function convertToECO(id: number) {
  return api.post(`/ecr/${id}/convert`).then(res => res.data as ECROut)
}
