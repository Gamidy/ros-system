// ProductPlan API layer
import api from './index'

// 策划列表查询参数
export interface PlanListParams {
  page?: number
  page_size?: number
  status?: string
  series?: string
  search?: string
}

// ── Payload 接口定义 ──

/** 创建策划 */
export interface CreatePlanPayload {
  name: string
  series?: string
  market?: string
  market_id?: number | null
  product_type?: string
}

/** 项目概述 (Initiation) */
export interface InitiationPayload {
  background?: string
  type?: string
  market?: string
  refrigerant?: string
  capacity?: string
  voltage?: string
  series?: string
  energy?: string
  dev_category?: string
  origin?: string
  duration?: number
  ip?: string
  goals?: string
  deliverables?: string
  sample_qty?: number
  version_id?: number
}

/** 市场与客户需求 (Market) */
export interface MarketPayload {
  main_capacity?: string
  energy_efficiency?: string
  cert_requirements?: string
  target_price?: number
  customer_requirements?: string
  version_id?: number
}

/** 技术要求 (TechSpec) */
export interface TechSpecPayload {
  core_performance?: string
  safety_compliance?: string
  optional_config?: string
  version_id?: number
}

/** 更新策划基本信息 */
export interface UpdatePlanPayload {
  name?: string
  series?: string
  market?: string
  competitor_id?: number
  cost_target?: string
  performance_target?: string
}

/** 创建项目关联 */
export interface CreateProjectLinkPayload {
  project_id: number
  link_type?: string
  snapshot_data?: string
  scenario_group_id?: string
}

/** 更新项目关联 */
export interface UpdateProjectLinkPayload {
  link_type?: string
  snapshot_data?: string
  version_major?: number
  version_minor?: number
  scenario_group_id?: string
}

/** 项目关联列表查询参数 */
export interface ProjectLinkListParams {
  link_type?: string
}

/** 团队成员 (Team) */
export interface TeamMemberPayload {
  member_name: string
  role_name: string
  department?: string
  responsibility?: string
  email?: string
  phone?: string
  version_id?: number
}

// ── API 函数 ──

export function listPlans(params?: PlanListParams) { return api.get('/product-plans', { params }) }
export function createPlan(data: CreatePlanPayload) { return api.post('/product-plans', data) }
export function getPlanDetail(id: string) { return api.get(`/product-plans/${id}`) }
export function updatePlan(id: string, data: UpdatePlanPayload) { return api.patch(`/product-plans/${id}`, data) }
// ── 审批操作 ──
export function approvePlan(planId: string, comment?: string) { return api.post(`/product-plans/${planId}/approve`, { comment }) }
export function rejectPlan(planId: string, comment?: string) { return api.post(`/product-plans/${planId}/reject`, { comment }) }
export function withdrawPlan(planId: string) { return api.post(`/product-plans/${planId}/withdraw`) }
export function updatePlanStage(planId: string, stage: string) { return api.patch(`/product-plans/${planId}/stage`, { stage }) }

// ── 项目概述 (Initiation) ──
export function getPlanInitiation(planId: string) { return api.get(`/product-plans/${planId}/initiation`) }
export function upsertPlanInitiation(planId: string, data: InitiationPayload) { return api.put(`/product-plans/${planId}/initiation`, data) }

// ── 市场与客户需求 (Market) ──
export function getPlanMarket(planId: string) { return api.get(`/product-plans/${planId}/market`) }
export function upsertPlanMarket(planId: string, data: MarketPayload) { return api.put(`/product-plans/${planId}/market`, data) }

// ── 技术要求 (TechSpec) ──
export function getPlanTechSpec(planId: string) { return api.get(`/product-plans/${planId}/tech-spec`) }
export function upsertPlanTechSpec(planId: string, data: TechSpecPayload) { return api.put(`/product-plans/${planId}/tech-spec`, data) }

// ── 团队 (Team) ──
export function listPlanTeam(planId: string) { return api.get(`/product-plans/${planId}/team`) }
export function addPlanTeamMember(planId: string, data: TeamMemberPayload) { return api.post(`/product-plans/${planId}/team`, data) }
export function updatePlanTeamMember(planId: string, id: number, data: TeamMemberPayload) { return api.put(`/product-plans/${planId}/team/${id}`, data) }
export function deletePlanTeamMember(planId: string, id: number) { return api.delete(`/product-plans/${planId}/team/${id}`) }

// ── 项目关联 (Project Links) ──
export function listPlanProjectLinks(planId: string, params?: ProjectLinkListParams) { return api.get(`/product-plans/${planId}/project-links`, { params }) }
export function createPlanProjectLink(planId: string, data: CreateProjectLinkPayload) { return api.post(`/product-plans/${planId}/project-links`, data) }
export function updatePlanProjectLink(planId: string, linkId: number, data: UpdateProjectLinkPayload) { return api.put(`/product-plans/${planId}/project-links/${linkId}`, data) }
export function deletePlanProjectLink(planId: string, linkId: number) { return api.delete(`/product-plans/${planId}/project-links/${linkId}`) }

// ── 市场选项 (Markets) ──
export interface MarketOption {
  code: string
  name: string
  region?: string
  energy_standard: string
  energy_label: string
  energy_unit?: string
  is_active?: string
}
export function fetchMarkets() { return api.get('/pm/markets') }
export function fetchAllMarkets() { return api.get('/pm/markets/all') }
