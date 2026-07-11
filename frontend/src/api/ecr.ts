import api from './index'

export interface ECRItem {
  id: number
  code: string
  title: string
  ecr_type: string
  urgency: string
  status: string
  submitter_name?: string
  created_at: string
}

export interface ECRDetail extends ECRItem {
  reason: string
  affected_products?: Record<string, unknown>
  affected_documents?: Record<string, unknown>
  description?: string
  submitter_id: number
  reviewer_id?: number
  rejection_reason?: string
  reviewed_at?: string
  updated_at: string
  attachments: Array<{
    id: number
    file_name: string
    file_type?: string
    file_size: number
    created_at: string
  }>
}

export const ecrApi = {
  list(params?: { skip?: number; limit?: number; status?: string; ecr_type?: string }) {
    return api.get<ECRItem[]>('/ecr/', { params })
  },

  get(id: number) {
    return api.get<ECRDetail>(`/ecr/${id}`)
  },

  create(data: {
    title: string
    ecr_type?: string
    reason: string
    urgency?: string
    description?: string
  }) {
    return api.post<ECRDetail>('/ecr/', data)
  },

  update(id: number, data: Record<string, unknown>) {
    return api.put<ECRDetail>(`/ecr/${id}`, data)
  },

  submit(id: number) {
    return api.post<ECRDetail>(`/ecr/${id}/submit`)
  },

  review(id: number, data: { action: string; rejection_reason?: string }) {
    return api.post<ECRDetail>(`/ecr/${id}/review`, data)
  },
}
