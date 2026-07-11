import api from './index'

export interface ECOItem {
  id: number
  eco_id: number
  seq: number
  change_type: string
  object_type: string
  object_code?: string
  object_name?: string
  old_value?: string
  new_value?: string
  created_at: string
}

export interface ECOSummary {
  id: number
  code: string
  ecr_id?: number
  title: string
  status: string
  effective_date?: string
  created_at: string
}

export interface ECODetail extends ECOSummary {
  change_summary: string
  implementation_plan?: string
  created_by: number
  verified_by?: number
  verified_at?: string
  closed_by?: number
  closed_at?: string
  updated_at: string
  items: ECOItem[]
}

export const ecoApi = {
  list(params?: { skip?: number; limit?: number; status?: string }) {
    return api.get<ECOSummary[]>('/eco/', { params })
  },

  get(id: number) {
    return api.get<ECODetail>(`/eco/${id}`)
  },

  create(data: {
    ecr_id?: number
    title: string
    change_summary: string
    implementation_plan?: string
    effective_date?: string
    items?: Array<{
      seq?: number
      change_type: string
      object_type: string
      object_code?: string
      object_name?: string
      old_value?: string
      new_value?: string
    }>
  }) {
    return api.post<ECODetail>('/eco/', data)
  },

  update(id: number, data: Record<string, unknown>) {
    return api.put<ECODetail>(`/eco/${id}`, data)
  },

  implement(id: number) {
    return api.post<ECODetail>(`/eco/${id}/implement`)
  },

  verify(id: number) {
    return api.post<ECODetail>(`/eco/${id}/verify`)
  },

  effect(id: number) {
    return api.post<ECODetail>(`/eco/${id}/effect`)
  },

  close(id: number) {
    return api.post<ECODetail>(`/eco/${id}/close`)
  },

  cancel(id: number) {
    return api.post<ECODetail>(`/eco/${id}/cancel`)
  },
}
