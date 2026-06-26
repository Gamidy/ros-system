/**
 * useSubTableProgress — 产品策划5子表完成状态管理
 *
 * 自动从子表 API 获取各表是否有数据来判断完成状态，
 * 替代前端硬编码的表单字段检查。
 *
 * Usage:
 * ```ts
 * const {
 *   subTabs, activeTab, tabStatus, progressPercent,
 *   refreshStatus, setSubTableDone, guideClick,
 * } = useSubTableProgress(planId)
 * ```
 */
import { ref, reactive, computed } from 'vue'
import * as planAPI from '../api/productPlan'
import api from '../api'

export interface SubTab {
  key: string
  label: string
}

export function useSubTableProgress(planId: string) {
  // ── 5 个子表定义 ──
  const subTabs: SubTab[] = [
    { key: 'initiation', label: '项目概述' },
    { key: 'market', label: '市场与客户' },
    { key: 'techSpec', label: '技术要求' },
    { key: 'costingNew', label: '成本核算' },
    { key: 'team', label: '团队' },
  ]

  const activeTab = ref('initiation')

  // ── 各子表完成状态（由 API 决定，不是前端猜测） ──
  const subTableDone = reactive<Record<string, boolean>>({
    initiation: false,
    market: false,
    techSpec: false,
    costingNew: false,
    team: false,
  })

  const isLoadingStatus = ref(false)

  /** 'done' | 'progress' 映射，供 Guide / Step 使用 */
  const tabStatus = computed<Record<string, string>>(() => {
    const result: Record<string, string> = {}
    for (const t of subTabs) {
      result[t.key] = subTableDone[t.key] ? 'done' : 'progress'
    }
    return result
  })

  /** 总体完成百分比 0–100 */
  const progressPercent = computed(() => {
    const doneCount = Object.values(subTableDone).filter(Boolean).length
    return Math.round((doneCount / subTabs.length) * 100)
  })

  /**
   * 从 5 个子表 API 拉取真实完成状态。
   * 返回后 tabStatus / progressPercent 即自动更新。
   */
  async function refreshStatus() {
    isLoadingStatus.value = true
    try {
      const results = await Promise.allSettled([
        planAPI.getPlanInitiation(planId),
        planAPI.getPlanMarket(planId),
        planAPI.getPlanTechSpec(planId),
        planAPI.listPlanTeam(planId),
        api.get(`/product-plans/${planId}`), // costs 内嵌在主 plan 中
      ])

      // Initiation: 200 = 有数据
      subTableDone.initiation = results[0].status === 'fulfilled'
      // Market: 200 = 有数据
      subTableDone.market = results[1].status === 'fulfilled'
      // TechSpec: 200 = 有数据
      subTableDone.techSpec = results[2].status === 'fulfilled'
      // Team: 成功且返回非空数组
      if (results[3].status === 'fulfilled') {
        const data = results[3].value.data
        subTableDone.team = Array.isArray(data) && data.length > 0
      } else {
        subTableDone.team = false
      }
      // Costing: 从主 plan 中取 costs 数组
      if (results[4].status === 'fulfilled') {
        const data = results[4].value.data
        subTableDone.costingNew = Array.isArray(data?.costs) && data.costs.length > 0
      } else {
        subTableDone.costingNew = false
      }
    } finally {
      isLoadingStatus.value = false
    }
  }

  /**
   * 手动设置某子表的完成状态（保存后即时反馈，不必等待 refreshStatus）
   */
  function setSubTableDone(key: string, done: boolean) {
    if (key in subTableDone) {
      subTableDone[key] = done
    }
  }

  /** Guide 引导条点击 — 激活对应 Tab / 移动端切换步骤 */
  function guideClick(key: string, _idx: number) {
    activeTab.value = key
    // _idx is used by the parent component to sync mobileStep when needed
  }

  return {
    subTabs,
    activeTab,
    tabStatus,
    progressPercent,
    isLoadingStatus,
    refreshStatus,
    setSubTableDone,
    guideClick,
  }
}
