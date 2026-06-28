// 成本核算系统 API 层
import api from './index'

// ── 产品策划搜索（用于选择器）──
export function listProductPlans(params?: Record<string, any>) { return api.get('/product-plans', { params }) }

// ── 核算期间 ──
export function listPeriods(params?: Record<string, any>) { return api.get('/cost-accounting/periods', { params }) }
export function createPeriod(data: Record<string, any>) { return api.post('/cost-accounting/periods', data) }
export function updatePeriod(id: number, data: Record<string, any>) { return api.patch(`/cost-accounting/periods/${id}`, data) }
export function deletePeriod(id: number) { return api.delete(`/cost-accounting/periods/${id}`) }
export function closePeriod(id: number) { return api.post(`/cost-accounting/periods/${id}/close`) }

// ── 工时费率 ──
export function listLaborRates() { return api.get('/cost-accounting/labor-rates') }
export function createLaborRate(data: Record<string, any>) { return api.post('/cost-accounting/labor-rates', data) }
export function updateLaborRate(id: number, data: Record<string, any>) { return api.patch(`/cost-accounting/labor-rates/${id}`, data) }
export function deleteLaborRate(id: number) { return api.delete(`/cost-accounting/labor-rates/${id}`) }

// ── 产品人工成本 ──
export function listLaborCosts(planId: string, periodId: number) { return api.get(`/cost-accounting/product/${planId}/labor-costs`, { params: { period_id: periodId } }) }
export function createLaborCost(planId: string, periodId: number, data: Record<string, any>) { return api.post(`/cost-accounting/product/${planId}/labor-costs?period_id=${periodId}`, data) }
export function deleteLaborCost(planId: string, id: number) { return api.delete(`/cost-accounting/product/${planId}/labor-costs/${id}`) }
export function calculateLabor(planId: string, periodId: number) { return api.post(`/cost-accounting/product/${planId}/calculate-labor?period_id=${periodId}`) }

// ── 分摊规则 ──
export function listOverheadRules() { return api.get('/cost-accounting/overhead-rules') }
export function createOverheadRule(data: Record<string, any>) { return api.post('/cost-accounting/overhead-rules', data) }
export function updateOverheadRule(id: number, data: Record<string, any>) { return api.patch(`/cost-accounting/overhead-rules/${id}`, data) }
export function deleteOverheadRule(id: number) { return api.delete(`/cost-accounting/overhead-rules/${id}`) }
export function toggleOverheadRule(id: number) { return api.post(`/cost-accounting/overhead-rules/${id}/toggle`) }

// ── 产品分摊结果 ──
export function listOverheadCosts(planId: string, periodId: number) { return api.get(`/cost-accounting/product/${planId}/overhead-costs`, { params: { period_id: periodId } }) }
export function allocateOverhead(planId: string, periodId: number) { return api.post(`/cost-accounting/product/${planId}/allocate-overhead?period_id=${periodId}`) }

// ── 增强物料成本 ──
export function getEnhancedMaterialCosts(bomId: number, costType?: string) { return api.get(`/cost-accounting/material-costs/enhanced/${bomId}`, { params: { cost_type: costType } }) }

// ── 核算单 ──
export function generateSheet(productPlanId: string, periodId: number, bomId?: number) { return api.post('/cost-accounting/sheets/generate', { product_plan_id: productPlanId, period_id: periodId, bom_id: bomId }) }
export function listSheets(params: Record<string, any>) { return api.get('/cost-accounting/sheets', { params }) }
export function getSheetDetail(id: number) { return api.get(`/cost-accounting/sheets/${id}`) }
export function finalizeSheet(id: number) { return api.post(`/cost-accounting/sheets/${id}/finalize`) }
export function recalculateSheet(id: number) { return api.post(`/cost-accounting/sheets/${id}/recalculate`) }
export function deleteSheet(id: number) { return api.delete(`/cost-accounting/sheets/${id}`) }

// ── 差异分析 ──
export function getVarianceAnalysis(planId: string, periodId: number) { return api.get('/cost-accounting/analysis/variance', { params: { plan_id: planId, period_id: periodId } }) }
export function getVarianceDetail(planId: string, periodId: number) { return api.get('/cost-accounting/analysis/detail', { params: { plan_id: planId, period_id: periodId } }) }
export function getCostTrend(planId: string, limit?: number) { return api.get('/cost-accounting/analysis/trend', { params: { plan_id: planId, limit: limit || 6 } }) }

// ── 导出 ──
export function exportCostSheetCsv(sheetId: number) { return api.get('/cost-accounting/reports/export/csv', { params: { sheet_id: sheetId } }) }

// ═══════════════════════════════════════════
// P3 冷量联动成本重算
// ═══════════════════════════════════════════

// CapacityUnitCost CRUD
export function listCapacityCosts() { return api.get('/cost-recalc/capacity-costs') }
export function createCapacityCost(data: Record<string, any>) { return api.post('/cost-recalc/capacity-costs', data) }
export function updateCapacityCost(id: number, data: Record<string, any>) { return api.put(`/cost-recalc/capacity-costs/${id}`, data) }
export function deleteCapacityCost(id: number) { return api.delete(`/cost-recalc/capacity-costs/${id}`) }

// 冷量联动重算
export function triggerRecalculation(data: Record<string, any>) { return api.post('/cost-recalc/run', data) }
export function listRecalcResults(params: Record<string, any>) { return api.get('/cost-recalc/results', { params }) }
export function getRecalcResult(id: number) { return api.get(`/cost-recalc/results/${id}`) }
export function getRecalcResultsByPlan(planId: string, limit?: number) { return api.get(`/cost-recalc/results/by-plan/${planId}`, { params: { limit: limit || 10 } }) }

// 低效率产品查询（Dashboard 使用）
export function getLowEfficiencyProducts(minScore?: number, maxResults?: number) {
  return api.get('/cost-recalc/low-efficiency', { params: { min_score: minScore || 60, max_results: maxResults || 10 } })
}
