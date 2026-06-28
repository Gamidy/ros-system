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
  fetchEventChain as apiFetchEventChain,
  fetchCausationChain as apiFetchCausationChain,
} from '../api/ci_v2'
import type { RiskScoreData, ImpactGraphData, RecommendationData, EventChainItem } from '../api/ci_v2'

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

  // ── Event Chain ─────────────────────────────────────
  const eventChain = ref<EventChainItem[]>([])
  const eventChainLoading = ref(false)
  const eventChainError = ref<string | null>(null)
  const causationChain = ref<EventChainItem[]>([])
  const causationLoading = ref(false)

  async function loadEventChain(aggregateType: 'ecr' | 'eco', aggregateId: number): Promise<void> {
    eventChainLoading.value = true
    eventChainError.value = null
    try {
      const res = await apiFetchEventChain(aggregateType, aggregateId)
      eventChain.value = res
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '获取事件链失败'
      eventChainError.value = msg
    } finally {
      eventChainLoading.value = false
    }
  }

  async function loadCausationChain(aggregateType: 'ecr' | 'eco', aggregateId: number): Promise<void> {
    causationLoading.value = true
    try {
      const res = await apiFetchCausationChain(aggregateType, aggregateId)
      causationChain.value = res
    } catch (e: unknown) {
      // silent — causality is secondary info
    } finally {
      causationLoading.value = false
    }
  }

  function clearEventChain(): void {
    eventChain.value = []
    eventChainError.value = null
    eventChainLoading.value = false
    causationChain.value = []
    causationLoading.value = false
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
    // ── Event Chain ──
    eventChain,
    eventChainLoading,
    eventChainError,
    causationChain,
    causationLoading,
    loadEventChain,
    loadCausationChain,
    clearEventChain,
  }
})
