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

/** 需求录入条目 */
export interface RequirementItem {
  id: string
  market: string
  customer?: string
  contact?: string
  product_type: string
  capacity_target?: string
  price_target?: number | null
  energy_standard?: string
  sales_volume_forecast?: number | null
  notes?: string
  status: string
  reject_reason?: string
  submitter_name?: string
  submitter_phone?: string
  created_at?: string
  updated_at?: string
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

// ── 产品需求 (Product Requirement) ──

/** 提交需求 */
export function submitRequirement(data: Record<string, unknown>) { return api.post('/product-requirements', data) }

/** 查询需求列表 */
export function listRequirements(params?: Record<string, unknown>) { return api.get('/product-requirements', { params }) }

/** 更新需求状态（采纳/拒绝） */
export function updateRequirementStatus(id: number, status: string, reject_reason?: string) {
  return api.put(`/product-requirements/${id}/status`, { status, reject_reason })
}

/** 需求转策划（原端点） */
export function convertToPlan(id: number) { return api.post(`/product-requirements/${id}/convert`) }

/** 需求→策划一键转换（新端点，返回 { plan_id, plan_name }） */
export function convertRequirementToPlan(id: string) { return api.post(`/product-requirements/${id}/convert-to-plan`) }

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

// ── 复盘 (Review) ──
export interface ReviewData {
  id?: string
  product_plan_id?: string
  review_date?: string
  actual_cost_total?: number
  cost_variance_pct?: number
  actual_launch_date?: string
  schedule_variance_days?: number
  market_feedback?: string
  lessons_learned?: string
  rating?: number
  review_template_id?: string
  created_at?: string
  updated_at?: string
  // D4-2: 自动计算标识
  cost_variance_pct_auto?: number | null
  schedule_variance_days_auto?: number | null
  cost_variance_source?: string
  schedule_variance_source?: string
  manual_override?: boolean
}

export interface AutoVarianceData {
  cost_variance_pct: number | null
  schedule_variance_days: number | null
  has_project_data: boolean
  target_cost_total: number | null
  actual_cost_total: number | null
  planned_launch_date: string | null
  actual_launch_date: string | null
}

export function getReview(planId: string) { return api.get(`/product-plans/${planId}/review`) }
export function submitReview(planId: string, data: ReviewData) { return api.post(`/product-plans/${planId}/review`, data) }
export function updateReview(planId: string, data: ReviewData) { return api.put(`/product-plans/${planId}/review`, data) }
// D4-2: 获取自动计算的偏差值
export function getAutoVariance(planId: string) { return api.get(`/product-plans/${planId}/auto-variance`) }

// ── 复盘模板 (Review Template) ──
export interface TemplateField {
  field: string
  label: string
  required: boolean
  max_length?: number
}

export interface ReviewTemplateItem {
  id: string
  product_type: string
  name: string
  template_fields: TemplateField[]
  is_active: boolean
  created_at?: string
  updated_at?: string
}

/** 按产品类型获取可用复盘模板 */
export function listReviewTemplates(productType?: string) {
  return api.get('/review-templates', { params: { product_type: productType } })
}

/** 创建复盘模板（管理端） */
export function createReviewTemplate(data: {
  product_type: string
  name: string
  template_fields: TemplateField[]
  is_active?: boolean
}) {
  return api.post('/review-templates', data)
}

// ── 知识沉淀 (Knowledge) ──
export interface KnowledgeItem {
  id: number
  title: string
  category: string
  content: string
  source_type?: string
  source_id?: string
  created_at?: string
  created_by?: string
}

export function listPlanKnowledge(planId: string) { return api.get(`/product-plans/${planId}/knowledge`) }
export function createKnowledge(data: Record<string, unknown>) { return api.post('/knowledge', data) }

// ── 完整性校验 ──
export interface ValidationError {
  field: string
  message: string
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
}

/** 提交策划数据前进行完整性校验 */
export function validatePlan(data: Record<string, unknown>) { return api.post('/product-plans/validate', data) }

// ── D2-1 策划模板 ──
export interface PlanTemplateItem {
  id: string
  product_type: string
  market: string
  name: string
  description?: string
  preset_fields: Record<string, unknown>
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface CreatePlanTemplatePayload {
  product_type: string
  market: string
  name: string
  description?: string
  preset_fields?: Record<string, unknown>
  is_active?: boolean
}

/** 按产品类型和市场获取模板列表 */
export function listPlanTemplates(params?: { product_type?: string; market?: string }) {
  return api.get('/plan-templates', { params })
}

/** 创建模板（管理端） */
export function createPlanTemplate(data: CreatePlanTemplatePayload) {
  return api.post('/plan-templates', data)
}

/** 删除模板 */
export function deletePlanTemplate(id: string) {
  return api.delete(`/plan-templates/${id}`)
}
