/**
 * CIE v2.0 — Pinia 状态管理
 *
 * 封装 API 调用层，提供响应式状态和 action
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchRiskScore as apiFetchRiskScore,
  fetchImpactGraph as apiFetchImpactGraph,
  fetchApprovalRecommendation as apiFetchApprovalRecommendation,
} from '../api/ci_v2'
import type { RiskScoreData, ImpactGraphData, RecommendationData } from '../api/ci_v2'

export const useCIEv2Store = defineStore('ci_v2', () => {
  // ── 风险评分 ──────────────────────────────────────────

  const riskScore = ref<RiskScoreData | null>(null)
  const riskLoading = ref(false)
  const riskError = ref<string | null>(null)

  async function loadRiskScore(ecrId: number): Promise<void> {
    riskLoading.value = true
    riskError.value = null
    try {
      const res = await apiFetchRiskScore(ecrId)
      riskScore.value = res
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取风险评分失败'
      riskError.value = msg
    } finally {
      riskLoading.value = false
    }
  }

  // ── 影响图 ────────────────────────────────────────────
  const graphData = ref<ImpactGraphData | null>(null)
  const graphLoading = ref(false)
  const graphError = ref<string | null>(null)

  async function fetchImpactGraph(ecrId: number): Promise<void> {
    graphLoading.value = true
    graphError.value = null
    try {
      const res = await apiFetchImpactGraph(ecrId)
      graphData.value = res
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取影响图失败'
      graphError.value = msg
    } finally {
      graphLoading.value = false
    }
  }

  // ── 审批推荐 ──────────────────────────────────────────

  const recommendation = ref<RecommendationData | null>(null)
  const recLoading = ref(false)
  const recError = ref<string | null>(null)

  async function loadApprovalRecommendation(ecrId: number): Promise<void> {
    recLoading.value = true
    recError.value = null
    try {
      const res = await apiFetchApprovalRecommendation(ecrId)
      recommendation.value = res
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取审批推荐失败'
      recError.value = msg
    } finally {
      recLoading.value = false
    }
  }

  function clearRecommendation(): void {
    recommendation.value = null
    recError.value = null
    recLoading.value = false
  }

  function clearGraphData(): void {
    graphData.value = null
    graphError.value = null
    graphLoading.value = false
  }

  return {
    riskScore,
    riskLoading,
    riskError,
    loadRiskScore,
    graphData,
    graphLoading,
    graphError,
    fetchImpactGraph,
    clearGraphData,
    recommendation,
    recLoading,
    recError,
    loadApprovalRecommendation,
    clearRecommendation,
  }
})
