// AI配置管理 & 策划草案生成 API 层
import api from './index'

// ── AI Provider 配置 ──

export interface AIConfigForm {
  provider: string
  model: string
  api_base: string
  api_key: string
  temperature: number
  max_tokens?: number
  enabled?: boolean
}

export interface AIConfigRecord extends AIConfigForm {
  id: number
  api_key: string  // 回显时已解密，仅编辑时展示
  enabled: boolean
  created_at: string
  updated_at: string
}

export function listAIConfigs() {
  return api.get<AIConfigRecord[]>('/admin/ai-configs')
}

export function getAIConfig(id: number) {
  return api.get<AIConfigRecord>(`/admin/ai-configs/${id}`)
}

export function createAIConfig(data: AIConfigForm) {
  return api.post<AIConfigRecord>('/admin/ai-configs', data)
}

export function updateAIConfig(id: number, data: Partial<AIConfigForm>) {
  return api.put<AIConfigRecord>(`/admin/ai-configs/${id}`, data)
}

export function deleteAIConfig(id: number) {
  return api.delete(`/admin/ai-configs/${id}`)
}

export function testAIConnection(id: number) {
  return api.post<{ success: boolean; message: string }>(`/admin/ai-configs/${id}/test`)
}

// ── AI 调用日志 ──

export interface AICallLogRecord {
  id: number
  request_id: string
  provider: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  cost: number
  response_time_ms: number
  success: boolean
  error: string | null
  created_at: string
}

export interface AICallLogQuery {
  page?: number
  page_size?: number
  provider?: string
  start_date?: string
  end_date?: string
}

export interface AICallLogPage {
  items: AICallLogRecord[]
  total: number
  page: number
  page_size: number
  total_tokens?: number
  total_cost?: number
  success_rate?: number
}

export function listAICallLogs(params: AICallLogQuery = {}) {
  return api.get<AICallLogPage>('/admin/ai-call-logs', { params })
}

// ── AI 策划草案生成 ──

export interface GeneratePlanDraftRequest {
  market_id: number
  product_type: string
  extra_context?: string
  provider?: string
  model?: string
}

export interface GeneratePlanDraftResponse {
  success: boolean
  data: Record<string, any>
  message: string
}

export function generatePlanDraft(data: GeneratePlanDraftRequest) {
  return api.post<GeneratePlanDraftResponse>('/ai/generate-plan-draft', data)
}
