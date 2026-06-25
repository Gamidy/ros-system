// ProductPlan API layer
import api from './index'

export function listPlans(params?: Record<string, any>) { return api.get('/product-plans', { params }) }
export function createPlan(data: Record<string, any>) { return api.post('/product-plans', data) }
export function getPlanDetail(id: string) { return api.get(`/product-plans/${id}`) }
export function updatePlan(id: string, data: Record<string, any>) { return api.patch(`/product-plans/${id}`, data) }
export function updatePlanStage(id: string, data: Record<string, any>) { return api.patch(`/product-plans/${id}/stage`, data) }

// ── 项目概述 (Initiation) ──
export function getPlanInitiation(planId: string) { return api.get(`/product-plans/${planId}/initiation`) }
export function upsertPlanInitiation(planId: string, data: any) { return api.put(`/product-plans/${planId}/initiation`, data) }

// ── 市场与客户需求 (Market) ──
export function getPlanMarket(planId: string) { return api.get(`/product-plans/${planId}/market`) }
export function upsertPlanMarket(planId: string, data: any) { return api.put(`/product-plans/${planId}/market`, data) }

// ── 技术要求 (TechSpec) ──
export function getPlanTechSpec(planId: string) { return api.get(`/product-plans/${planId}/tech-spec`) }
export function upsertPlanTechSpec(planId: string, data: any) { return api.put(`/product-plans/${planId}/tech-spec`, data) }

// ── 团队 (Team) ──
export function listPlanTeam(planId: string) { return api.get(`/product-plans/${planId}/team`) }
export function addPlanTeamMember(planId: string, data: any) { return api.post(`/product-plans/${planId}/team`, data) }
export function updatePlanTeamMember(planId: string, id: number, data: any) { return api.put(`/product-plans/${planId}/team/${id}`, data) }
export function deletePlanTeamMember(planId: string, id: number) { return api.delete(`/product-plans/${planId}/team/${id}`) }
