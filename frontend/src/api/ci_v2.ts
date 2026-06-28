/**
 * CIE v2.0 — 前端 API 调用层
 *
 * 对应后端: backend/app/api/ci_v2.py (7个端点)
 * 全类型注解, 无 any
 */
import api from './index'

// ── 类型定义 ───────────────────────────────────────

export interface RiskScoreData {
  ecr_id: number
  risk_score: number
  risk_level: string
  risk_vector: Record<string, number>
  mitigation_suggestions: string[]
  created_at: string
}

export interface ImpactNode {
  id: string
  node_type: string
  label: string
  impact_score: number
  affected_objects: Record<string, unknown>[]
  depth: number
}

export interface ImpactEdge {
  source_id: string
  target_id: string
  weight: number
  label: string
}

export interface ImpactGraphData {
  nodes: ImpactNode[]
  edges: ImpactEdge[]
  ripple_score: number
  max_depth: number
  node_count: number
  edge_count: number
}

export interface RecommendationData {
  recommendation: string
  required_approvers: string[]
  reason: string
  confidence: number
  risk_level: string
  risk_score: number
}

export interface ModelWeightsItem {
  version_id: string
  weights: Record<string, number>
  sample_count: number
  is_active: boolean
  created_at: string
}

export interface ModelParamsData {
  active: ModelWeightsItem | null
  history: ModelWeightsItem[]
}

// ── API 函数 ───────────────────────────────────────

/**
 * 查询 ECR 的风险评分
 * GET /api/v2/risk/{ecr_id}
 */
export function fetchRiskScore(ecrId: number): Promise<RiskScoreData> {
  return api.get(`/api/v2/risk/${ecrId}`).then(res => res.data as RiskScoreData)
}

/**
 * 查询 ECR 的变更影响图
 * GET /api/v2/impact-graph/{ecr_id}
 */
export function fetchImpactGraph(ecrId: number): Promise<ImpactGraphData> {
  return api.get(`/api/v2/impact-graph/${ecrId}`).then(res => res.data as ImpactGraphData)
}

/**
 * 查询 ECR 的审批推荐
 * GET /api/v2/approval-recommendation/{ecr_id}
 */
export function fetchApprovalRecommendation(ecrId: number): Promise<RecommendationData> {
  return api.get(`/api/v2/approval-recommendation/${ecrId}`)
    .then(res => res.data as RecommendationData)
}

/**
 * 批量风险评分 (最多20个)
 * POST /api/v2/risk/batch
 */
export function fetchBatchRisk(ecrIds: number[]): Promise<(RiskScoreData | null)[]> {
  return api.post('/api/v2/risk/batch', { ecr_ids: ecrIds })
    .then(res => res.data as (RiskScoreData | null)[])
}

/**
 * 提交预测结果反馈
 * POST /api/v2/feedback
 */
export function submitFeedback(ecrId: number, outcome: string, detail?: Record<string, unknown>): Promise<Record<string, unknown>> {
  return api.post('/api/v2/feedback', { ecr_id: ecrId, actual_outcome: outcome, outcome_detail: detail || null })
    .then(res => res.data)
}

/**
 * 查询模型参数
 * GET /api/v2/model-params
 */
export function fetchModelParams(): Promise<ModelParamsData> {
  return api.get('/api/v2/model-params').then(res => res.data as ModelParamsData)
}

/**
 * 回滚模型参数到指定版本
 * POST /api/v2/model-params/{version_id}
 */
export function rollbackModelParams(versionId: string): Promise<ModelWeightsItem> {
  return api.post(`/api/v2/model-params/${versionId}`)
    .then(res => res.data as ModelWeightsItem)
}

// ── Digital Thread — 事件链 ──────────────────────────

export interface EventChainItem {
  id: number
  event_type: string
  aggregate_type: string
  aggregate_id: number
  correlation_id: string
  causation_id: number | null
  event_data: string | null
  producer: string
  created_at: string
}

/**
 * 获取某个聚合 (ECR/ECO) 的完整事件链
 * GET /api/v2/event-graph/{aggregate_type}/{aggregate_id}
 */
export function fetchEventChain(aggregateType: 'ecr' | 'eco', aggregateId: number): Promise<EventChainItem[]> {
  return api.get(`/api/v2/event-graph/${aggregateType}/${aggregateId}`)
    .then(res => res.data as EventChainItem[])
}

/**
 * 获取因果链回溯（从最新事件沿 causation_id 回溯）
 * GET /api/v2/event-graph/{aggregate_type}/{aggregate_id}/causation
 */
export function fetchCausationChain(aggregateType: 'ecr' | 'eco', aggregateId: number): Promise<EventChainItem[]> {
  return api.get(`/api/v2/event-graph/${aggregateType}/${aggregateId}/causation`)
    .then(res => res.data as EventChainItem[])
}
