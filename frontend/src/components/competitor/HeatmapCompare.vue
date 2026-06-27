<template>
  <div class="heatmap-compare">
    <!-- ═══════════════════════ 对比提示 ═══════════════════════ -->
    <div v-if="brands.length > 0 && !allUnknown" class="compare-summary-row">
      <div
        v-for="brand in brands"
        :key="brand"
        class="compare-summary-card"
        :class="summaryCardClass(brand)"
      >
        <div class="summary-brand">{{ brand }}</div>
        <div class="summary-stats">
          <span class="stat-leading">🟢 领先 <em>{{ leadingCount(brand) }}</em></span>
          <span class="stat-equal">🟡 持平 <em>{{ equalCount(brand) }}</em></span>
          <span class="stat-falling">🔴 落后 <em>{{ fallingCount(brand) }}</em></span>
        </div>
        <div class="summary-desc">
          与「{{ brand }}」相比，我们在 <strong>{{ leadingCount(brand) }}</strong> 个参数上领先，
          在 <strong>{{ fallingCount(brand) }}</strong> 个参数上落后
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ 视图切换 & 操作栏 ═══════════════════════ -->
    <div class="heatmap-toolbar">
      <div class="view-switch">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="table">📊 表格视图</el-radio-button>
          <el-radio-button value="card">📇 卡片视图</el-radio-button>
        </el-radio-group>
      </div>
      <div class="adopt-actions">
        <el-button
          size="small"
          type="primary"
          :disabled="selectedCells.size === 0"
          @click="adoptSelected"
        >
          ✅ 采纳选中 ({{ selectedCells.size }})
        </el-button>
        <el-button
          size="small"
          type="success"
          :disabled="!hasAnyBetterParam"
          @click="adoptAllBetter"
        >
          📋 一键采纳全部更优参数
        </el-button>
        <el-button
          size="small"
          plain
          :disabled="Object.keys(modelValue).length === 0"
          @click="resetTargets"
        >
          🔄 重置我方目标
        </el-button>
      </div>
    </div>

    <!-- ═══════════════════════ 表格视图 ═══════════════════════ -->
    <div v-show="viewMode === 'table'" class="table-card">
      <el-table :data="internalRows" border size="small" class="heatmap-table" max-height="600">
        <el-table-column prop="param_name" label="参数" width="150" fixed="left">
          <template #default="{ row }">
            <span class="param-cell-label">{{ row.param_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="🎯 我方目标" width="130" fixed="left">
          <template #default="{ row }">
            <div class="target-cell">
              <span class="target-value">{{ displayOurValue(row.param_key) }}</span>
              <el-tag
                v-if="adoptedParams.has(row.param_key)"
                size="small"
                type="success"
                effect="plain"
                class="adopted-tag"
              >已采纳</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          v-for="brand in brands"
          :key="brand"
          :label="brand"
          min-width="130"
        >
          <template #default="{ row }">
            <div
              class="heat-cell"
              :class="computedHeatClass(row, brand)"
              :style="{ backgroundColor: getHeatColor(row, brand) }"
              @click="toggleCell(row.param_key, brand)"
            >
              <span class="cell-value">{{ getCompetitorValue(row, brand) }}</span>
              <span v-if="isSelected(row.param_key, brand)" class="select-badge">✓</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- ═══════════════════════ 卡片视图 ═══════════════════════ -->
    <div v-show="viewMode === 'card'" class="card-view">
      <div v-for="brand in brands" :key="brand" class="compare-card">
        <div class="compare-card-header">
          <h4 class="card-brand-name">{{ brand }}</h4>
          <span class="card-summary">
            领先 <strong>{{ leadingCount(brand) }}</strong> /
            持平 <strong>{{ equalCount(brand) }}</strong> /
            落后 <strong>{{ fallingCount(brand) }}</strong>
          </span>
        </div>
        <div class="compare-card-body">
          <div
            v-for="row in internalRows"
            :key="row.param_key"
            class="card-param-row"
          >
            <div class="card-param-label">{{ row.param_name }}</div>
            <div class="card-values">
              <span class="card-our">{{ displayOurValue(row.param_key) }}</span>
              <span class="card-vs">对比</span>
              <span
                class="card-their"
                :class="computedHeatClass(row, brand)"
                :style="{ backgroundColor: getHeatColor(row, brand) }"
                @click="toggleCell(row.param_key, brand)"
              >
                {{ getCompetitorValue(row, brand) }}
                <span v-if="isSelected(row.param_key, brand)" class="select-badge-sm">✓</span>
              </span>
            </div>
            <el-tag
              v-if="adoptedParams.has(row.param_key)"
              size="small"
              type="success"
              effect="plain"
              class="card-adopted-tag"
            >已采纳</el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * HeatmapCompare.vue — 竞品参数横向对比热力图 + 采纳功能
 *
 * 功能:
 * 1. 热力图颜色映射 (我方优→绿, 持平→黄, 落后→红)
 * 2. 表格/卡片视图切换
 * 3. 一键采纳最优参数 (单选/批量)
 * 4. 对比提示 (领先/落后计数)
 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

/* ──────────────────────────────────────────────── 类型定义 ──────────────────────────────────────────────── */

interface CompetitorEntry {
  value: number | string
  model?: string
}

interface HeatmapRow {
  param_key: string
  param_name: string
  competitors: Record<string, CompetitorEntry>
}

/** 参数方向定义 */
interface ParamDirection {
  /** 越高越好 (true) / 越低越好 (false) */
  higherBetter: boolean
}

/* ──────────────────────────────────────────────── 常量 ──────────────────────────────────────────────── */

/** 每个参数的方向定义 — 空调行业常规判断 */
const PARAM_DIRECTIONS: Record<string, ParamDirection> = {
  cooling_capacity_w:  { higherBetter: true  },
  heating_capacity_w:  { higherBetter: true  },
  cooling_w:           { higherBetter: false },
  heating_w:           { higherBetter: false },
  eer:                 { higherBetter: true  },
  cspf:                { higherBetter: true  },
  iseer:               { higherBetter: true  },
  seer:                { higherBetter: true  },
  noise_indoor_db:     { higherBetter: false },
  noise_outdoor_db:    { higherBetter: false },
  airflow_m3h:         { higherBetter: true  },
  indoor_size_mm:      { higherBetter: false },
  outdoor_size_mm:     { higherBetter: false },
  factory_price:       { higherBetter: false },
  launch_year:         { higherBetter: true  },
  // energy_rating (能效等级) handled specially in compare logic
}

/** 能以字符串星数（如"5星"）比较的参数 */
const STAR_RATING_KEYS = new Set(['energy_rating'])

/* ──────────────────────────────────────────────── Props & Emits ──────────────────────────────────────────────── */

const props = withDefaults(defineProps<{
  /** 对标数据行 */
  benchmarkData: HeatmapRow[]
  /** 品牌列表 (列名) */
  brands: string[]
  /** 我方目标值 key→value (v-model) */
  modelValue: Record<string, string | number>
}>(), {
  benchmarkData: () => [],
  brands: () => [],
  modelValue: () => ({}),
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: Record<string, string | number>): void
}>()

/* ──────────────────────────────────────────────── 内部状态 ──────────────────────────────────────────────── */

/** 视图模式 */
const viewMode = ref<'table' | 'card'>('table')

/** 已采纳的参数 key 集合 */
const adoptedParams = ref<Set<string>>(new Set())

/** 选中的单元格: param_key → brand */
const selectedCells = ref<Map<string, string>>(new Map())

/* ──────────────────────────────────────────────── 计算属性 ──────────────────────────────────────────────── */

/** 内部行（过滤掉完全无数据的行） */
const internalRows = computed<HeatmapRow[]>(() => {
  return props.benchmarkData.filter((row) => {
    return Object.keys(row.competitors).length > 0
  })
})

/** 是否有任何参数可以计算对比 */
const allUnknown = computed(() => {
  for (const brand of props.brands) {
    for (const row of internalRows.value) {
      const result = compareCell(row, brand)
      if (result !== 'unknown') return false
    }
  }
  return true
})

/** 是否存在比我方更优的竞品参数 (用于控制批量采纳按钮) */
const hasAnyBetterParam = computed(() => {
  for (const brand of props.brands) {
    for (const row of internalRows.value) {
      const comp = getComparison(row, brand)
      if (comp === 'falling') return true
    }
  }
  return false
})

/* ──────────────────────────────────────────────── 方法 ──────────────────────────────────────────────── */

/** 将竞争者值转为字符串显示 */
function getCompetitorValue(row: HeatmapRow, brand: string): string {
  const entry = row.competitors?.[brand]
  if (!entry || entry.value === undefined || entry.value === null) return '-'
  return String(entry.value)
}

/** 显示我方目标值 */
function displayOurValue(paramKey: string): string {
  const val = props.modelValue[paramKey]
  if (val === undefined || val === null || val === '') return '—'
  return String(val)
}

/** 判断参数方向的辅助方法 */
function isHigherBetter(paramKey: string): boolean {
  if (STAR_RATING_KEYS.has(paramKey)) return true // more stars = better
  return PARAM_DIRECTIONS[paramKey]?.higherBetter ?? true
}

/**
 * 提取数值用于比较。
 * 返回 null 表示无法比较。
 */
function extractCompareValue(
  ourVal: string | number | undefined | null,
  theirVal: string | number | undefined | null,
  paramKey: string,
): { our: number; their: number } | null {
  if (ourVal == null || ourVal === '' || ourVal === '—') return null
  if (theirVal == null || theirVal === '' || theirVal === '-' || theirVal === '—') return null

  // 星数型（如 "5星"）
  if (STAR_RATING_KEYS.has(paramKey)) {
    const ourStars = parseInt(String(ourVal).replace(/[^\d]/g, ''), 10)
    const theirStars = parseInt(String(theirVal).replace(/[^\d]/g, ''), 10)
    if (isNaN(ourStars) || isNaN(theirStars)) return null
    return { our: ourStars, their: theirStars }
  }

  // 数值型
  const ourNum = Number(ourVal)
  const theirNum = Number(theirVal)
  if (isNaN(ourNum) || isNaN(theirNum)) return null

  return { our: ourNum, their: theirNum }
}

/**
 * 比较单元格: 我方目标 vs 特定竞品在该参数上的值
 * 返回 'leading'(领先) | 'equal'(持平) | 'falling'(落后) | 'unknown'(无法比较)
 */
function getComparison(row: HeatmapRow, brand: string): 'leading' | 'equal' | 'falling' | 'unknown' {
  const ourVal = props.modelValue[row.param_key]
  const theirVal = row.competitors?.[brand]?.value

  const nums = extractCompareValue(ourVal, theirVal, row.param_key)
  if (!nums) return 'unknown'

  const higherBetter = isHigherBetter(row.param_key)

  if (nums.our === nums.their) return 'equal'

  if (higherBetter) {
    return nums.our > nums.their ? 'leading' : 'falling'
  } else {
    return nums.our < nums.their ? 'leading' : 'falling'
  }
}

/** 比较结果（含未知时）用于热力类名 */
function compareCell(row: HeatmapRow, brand: string): 'leading' | 'equal' | 'falling' | 'unknown' {
  return getComparison(row, brand)
}

/** 领先数量 */
function leadingCount(brand: string): number {
  return internalRows.value.filter((r) => getComparison(r, brand) === 'leading').length
}

/** 持平数量 */
function equalCount(brand: string): number {
  return internalRows.value.filter((r) => getComparison(r, brand) === 'equal').length
}

/** 落后数量 */
function fallingCount(brand: string): number {
  return internalRows.value.filter((r) => getComparison(r, brand) === 'falling').length
}

/* ──────────────────────────────────────────────── 热力图颜色 ──────────────────────────────────────────────── */

/**
 * 计算差距强度 (0~1)，用于控制颜色深浅
 * 数值差距越大，颜色越深
 */
function getGapIntensity(row: HeatmapRow, brand: string): number {
  const ourVal = props.modelValue[row.param_key]
  const theirVal = row.competitors?.[brand]?.value
  const nums = extractCompareValue(ourVal, theirVal, row.param_key)
  if (!nums) return 0.3

  const maxVal = Math.max(Math.abs(nums.our), Math.abs(nums.their))
  if (maxVal === 0) return 0.3

  const diff = Math.abs(nums.our - nums.their)
  // 差距 30% 即为满色
  const ratio = Math.min(diff / maxVal / 0.3, 1)
  return Math.max(ratio, 0.15) // 至少 15% 可见
}

/** 获取热力颜色（CSS background-color 字符串） */
function getHeatColor(row: HeatmapRow, brand: string): string {
  const result = compareCell(row, brand)
  const intensity = getGapIntensity(row, brand)
  // 透明度从 0.08 到 0.35
  const alpha = 0.08 + intensity * 0.27

  switch (result) {
    case 'leading':
      return `rgba(103, 194, 58, ${alpha})`   // 绿色
    case 'falling':
      return `rgba(231, 76, 60, ${alpha})`     // 红色
    case 'equal':
      return `rgba(230, 162, 60, ${alpha})`    // 黄色
    default:
      return 'transparent'
  }
}

/** 获取热力 CSS 类名 */
function computedHeatClass(row: HeatmapRow, brand: string): string {
  const result = compareCell(row, brand)
  const classes: string[] = ['heat-cell-inner']
  if (result !== 'unknown') {
    classes.push(`heat-${result}`)
  }
  if (isSelected(row.param_key, brand)) {
    classes.push('heat-selected')
  }
  return classes.join(' ')
}

/** 汇总卡片边框样式 */
function summaryCardClass(brand: string): string {
  const lead = leadingCount(brand)
  const fall = fallingCount(brand)
  if (lead > fall) return 'summary-leading'
  if (fall > lead) return 'summary-falling'
  return 'summary-balanced'
}

/* ──────────────────────────────────────────────── 选中/采纳逻辑 ──────────────────────────────────────────────── */

/** 切换单元格选中状态 */
function toggleCell(paramKey: string, brand: string): void {
  const newMap = new Map(selectedCells.value)
  if (newMap.has(paramKey) && newMap.get(paramKey) === brand) {
    newMap.delete(paramKey)
  } else {
    newMap.set(paramKey, brand)
  }
  selectedCells.value = newMap
}

/** 判断是否已选中 */
function isSelected(paramKey: string, brand: string): boolean {
  return selectedCells.value.get(paramKey) === brand
}

/** 采纳选中的单元格 */
function adoptSelected(): void {
  if (selectedCells.value.size === 0) {
    ElMessage.warning('请先点击选中要采纳的竞品参数')
    return
  }

  const newTargets = { ...props.modelValue }
  const newAdopted = new Set(adoptedParams.value)

  for (const [paramKey, brand] of selectedCells.value.entries()) {
    const row = internalRows.value.find((r) => r.param_key === paramKey)
    if (!row) continue
    const entry = row.competitors?.[brand]
    if (!entry) continue
    newTargets[paramKey] = entry.value
    newAdopted.add(paramKey)
  }

  emit('update:modelValue', newTargets)
  adoptedParams.value = newAdopted
  selectedCells.value = new Map()
  ElMessage.success(`已采纳 ${newTargets.size} 个参数`)
}

/** 一键采纳全部更优参数: 对每个参数找到最优的竞品值，若优于我方则采纳 */
function adoptAllBetter(): void {
  const newTargets = { ...props.modelValue }
  const newAdopted = new Set(adoptedParams.value)
  let count = 0

  for (const row of internalRows.value) {
    const paramKey = row.param_key
    const ourVal = props.modelValue[paramKey]
    const higherBetter = isHigherBetter(paramKey)

    // 找出所有竞品在此参数上的值
    const candidates: Array<{ value: number | string; brand: string }> = []
    for (const brand of props.brands) {
      const entry = row.competitors?.[brand]
      if (!entry) continue
      candidates.push({ value: entry.value, brand })
    }

    if (candidates.length === 0) continue

    // 找到最佳值
    let bestCandidate = candidates[0]
    for (let i = 1; i < candidates.length; i++) {
      const numsCurrent = extractCompareValue(0, candidates[i].value, paramKey)
      const numsBest = extractCompareValue(0, bestCandidate.value, paramKey)
      if (!numsCurrent || !numsBest) continue

      if (higherBetter) {
        if (numsCurrent.their > numsBest.their) bestCandidate = candidates[i]
      } else {
        if (numsCurrent.their < numsBest.their) bestCandidate = candidates[i]
      }
    }

    // 检查是否优于我方
    const comparison = extractCompareValue(ourVal, bestCandidate.value, paramKey)
    if (!comparison) {
      // 我方无值，直接采纳
      newTargets[paramKey] = bestCandidate.value
      newAdopted.add(paramKey)
      count++
      continue
    }

    const isBetter = higherBetter
      ? comparison.their > comparison.our
      : comparison.their < comparison.our

    if (isBetter) {
      newTargets[paramKey] = bestCandidate.value
      newAdopted.add(paramKey)
      count++
    }
  }

  emit('update:modelValue', newTargets)
  adoptedParams.value = newAdopted
  ElMessage.success(`批量采纳完成：共更新 ${count} 个参数`)
}

/** 重置我方目标 */
function resetTargets(): void {
  emit('update:modelValue', {})
  adoptedParams.value = new Set()
  selectedCells.value = new Map()
  ElMessage.success('已重置我方目标')
}

/** 监听外部 modelValue 变化，同步 adoptedParams */
watch(() => props.modelValue, (val) => {
  const keys = Object.keys(val)
  if (keys.length > 0) {
    const newSet = new Set(adoptedParams.value)
    for (const k of keys) {
      newSet.add(k)
    }
    adoptedParams.value = newSet
  }
}, { deep: true, immediate: true })
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════
   热力图对比组件样式
   ═══════════════════════════════════════════════════════════════════ */
.heatmap-compare {
  --hm-leading: #67c23a;
  --hm-falling: #e74c3c;
  --hm-equal: #e6a23c;
  --hm-bg: #fffdf7;
  --hm-border: #e5dfd3;
  --hm-text: #4a3f35;
  --hm-text-muted: #8c8279;
}

/* ── 对比提示卡片 ────────────────────────────────────────────── */
.compare-summary-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.compare-summary-card {
  flex: 1;
  min-width: 240px;
  background: var(--hm-bg);
  border: 1px solid var(--hm-border);
  border-left: 4px solid var(--hm-border);
  border-radius: 8px;
  padding: 12px 16px;
}
.compare-summary-card.summary-leading {
  border-left-color: var(--hm-leading);
}
.compare-summary-card.summary-falling {
  border-left-color: var(--hm-falling);
}
.compare-summary-card.summary-balanced {
  border-left-color: var(--hm-equal);
}
.summary-brand {
  font-size: 15px;
  font-weight: 700;
  color: var(--hm-text);
  margin-bottom: 4px;
}
.summary-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  margin-bottom: 4px;
}
.summary-stats em {
  font-style: normal;
  font-weight: 700;
  font-size: 14px;
}
.stat-leading { color: var(--hm-leading); }
.stat-equal { color: var(--hm-equal); }
.stat-falling { color: var(--hm-falling); }
.summary-desc {
  font-size: 12px;
  color: var(--hm-text-muted);
  line-height: 1.5;
}
.summary-desc strong {
  color: var(--hm-text);
}

/* ── 工具栏 ──────────────────────────────────────────────────── */
.heatmap-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.view-switch {
  display: flex;
  align-items: center;
}
.adopt-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ── 表格视图 ────────────────────────────────────────────────── */
.table-card {
  background: var(--hm-bg);
  border: 1px solid var(--hm-border);
  border-radius: 10px;
  padding: 8px;
  overflow-x: auto;
}
.heatmap-table {
  font-size: 13px;
  width: 100%;
}
.heatmap-table :deep(.el-table__body tr:hover > td) {
  background: #fdfaf3 !important;
}
.param-cell-label {
  font-weight: 600;
  color: var(--hm-text);
  white-space: nowrap;
}
.target-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.target-value {
  font-weight: 700;
  color: var(--hm-accent, #d97757);
}
.adopted-tag {
  flex-shrink: 0;
  font-size: 10px;
  padding: 0 4px;
}
.heat-cell {
  position: relative;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  user-select: none;
}
.heat-cell:hover {
  box-shadow: 0 0 0 2px rgba(217, 119, 87, 0.3);
  transform: scale(1.02);
}
.heat-cell.heat-selected {
  box-shadow: 0 0 0 2px #409eff, 0 0 0 4px rgba(64, 158, 255, 0.2);
}
.cell-value {
  font-variant-numeric: tabular-nums;
  color: var(--hm-text);
  font-weight: 500;
}
.select-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-left: 4px;
}

/* ── 卡片视图 ────────────────────────────────────────────────── */
.card-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.compare-card {
  background: var(--hm-bg);
  border: 1px solid var(--hm-border);
  border-radius: 10px;
  overflow: hidden;
}
.compare-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #faf8f3;
  border-bottom: 1px solid var(--hm-border);
}
.card-brand-name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--hm-text);
}
.card-summary {
  font-size: 12px;
  color: var(--hm-text-muted);
}
.card-summary strong {
  font-size: 14px;
}
.compare-card-body {
  padding: 8px 16px;
}
.card-param-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
  gap: 12px;
  border-bottom: 1px dashed #f0ede6;
}
.card-param-row:last-child {
  border-bottom: none;
}
.card-param-label {
  min-width: 120px;
  font-size: 12px;
  font-weight: 600;
  color: var(--hm-text);
  flex-shrink: 0;
}
.card-values {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.card-our {
  font-weight: 700;
  color: var(--hm-accent, #d97757);
  font-size: 13px;
  min-width: 50px;
}
.card-vs {
  font-size: 11px;
  color: var(--hm-text-muted);
}
.card-their {
  position: relative;
  padding: 2px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: box-shadow 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 40px;
  user-select: none;
}
.card-their:hover {
  box-shadow: 0 0 0 2px rgba(217, 119, 87, 0.3);
}
.card-their.heat-selected {
  box-shadow: 0 0 0 2px #409eff, 0 0 0 4px rgba(64, 158, 255, 0.2);
}
.select-badge-sm {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}
.card-adopted-tag {
  flex-shrink: 0;
  font-size: 10px;
  padding: 0 6px;
  margin-left: auto;
}
</style>
