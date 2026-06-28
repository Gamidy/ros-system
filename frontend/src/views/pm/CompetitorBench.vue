<template>
  <div class="competitor-bench">
    <el-divider content-position="left">🔍 竞品对标</el-divider>

    <!-- No market selected -->
    <el-empty v-if="!market" description="请先在 Tab1 选择目标市场" :image-size="60" />

    <!-- Loading / Error states -->
    <div v-else-if="loading" style="text-align:center;padding:20px">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p style="color:#909399;font-size:13px;margin-top:8px">正在加载竞品数据...</p>
    </div>

    <!-- Data available -->
    <template v-else-if="benchmarkData.length > 0">
      <!-- 完整性提示 -->
      <div v-if="!allComplete" style="margin-bottom:12px;padding:8px 12px;background:#fdf6ec;border-radius:6px;font-size:13px;color:#e6a23c;border:1px solid #faecd8;">
        ⚠️ 部分竞品数据不完整，请在「竞品对标」页面补全数据
      </div>
      <div v-else style="margin-bottom:12px;padding:8px 12px;background:#f0f9eb;border-radius:6px;font-size:13px;color:#67c23a;border:1px solid #e1f3d8;">
        ✅ 所有竞品数据完整
      </div>

      <!-- 视图切换 + 一键采纳 -->
      <div class="bench-toolbar">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="table">📋 表格</el-radio-button>
          <el-radio-button value="radar">🕸️ 雷达图</el-radio-button>
          <el-radio-button value="bar">📊 柱状图</el-radio-button>
        </el-radio-group>
        <el-button type="warning" size="small" @click="handleAdoptBest">
          ⚡ 一键采纳最优参数
        </el-button>
      </div>

      <!-- ════════════════ TABLE VIEW ════════════════ -->
      <el-table v-show="viewMode === 'table'" :data="benchmarkData" border size="small" class="bench-table" empty-text="暂无竞品对标数据">
        <el-table-column prop="param_name" label="参数" width="110" />
        <el-table-column prop="our_target" label="我方目标" width="100">
          <template #default="{ row }">
            <strong>{{ row.our_target }}</strong>
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
              :style="getHeatmapStyle(row, brand)"
              :class="[
                'competitor-cell',
                { 'competitor-cell--adopted': isAdopted(row.param_key, brand) }
              ]"
            >
              <span class="cell-value">{{ getCompetitorValue(row, brand) }}</span>
              <el-button
                v-if="getCompetitorValue(row, brand) !== '-'"
                :type="isAdopted(row.param_key, brand) ? 'success' : 'primary'"
                size="small"
                link
                @click="handleAdopt(row, brand)"
              >
                {{ isAdopted(row.param_key, brand) ? '✓ 已采纳' : '[采纳]' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- ════════════════ RADAR VIEW ════════════════ -->
      <div v-show="viewMode === 'radar'" ref="radarChartRef" class="chart-container" />

      <!-- ════════════════ BAR VIEW ════════════════ -->
      <div v-show="viewMode === 'bar'" class="bar-chart-wrapper">
        <div class="bar-controls">
          <span class="bar-controls-label">参数维度：</span>
          <el-select v-model="barParamKey" size="small" style="width:200px" @change="renderBarChart">
            <el-option
              v-for="row in numericBenchmarkRows"
              :key="row.param_key"
              :label="row.param_name"
              :value="row.param_key"
            />
          </el-select>
        </div>
        <div ref="barChartRef" class="chart-container" />
      </div>
    </template>

    <!-- No data after load -->
    <el-empty v-else description="暂无竞品对标数据" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import api from '../../api'
import { initChart, disposeChart, getGlassTooltip, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  market: string
  coolingCapacity?: string
}>()

const emit = defineEmits<{
  adopt: [payload: { paramKey: string; value: number; brand: string }]
}>()

interface CompetitorEntry {
  value: number | string
  model?: string
}

interface BenchmarkRow {
  param_key: string
  param_name: string
  our_target: string
  competitors: Record<string, CompetitorEntry>
}

interface MarketOption {
  code: string
  name: string
  is_active?: string
}

interface CompetitorDataItem {
  brand: string
  model?: string
  is_complete?: boolean
  [key: string]: unknown
}

interface BenchmarkApiResponse {
  competitors?: CompetitorDataItem[]
  param_names?: Array<{ key: string; label: string; unit: string }>
}

const competitorData = ref<CompetitorDataItem[]>([])
const benchmarkData = ref<BenchmarkRow[]>([])
const loading = ref(false)
const adoptedKeys = ref<Set<string>>(new Set())
const allComplete = ref(false)

// 市场代码/名称映射（从父组件传入的 props.market 可能是代码如"VN"，需转名称如"越南"）
const marketOptions = ref<Array<{code: string; name: string}>>([])

// ── 视图状态 ──────────────────────────────────────────────────────
const viewMode = ref<'table' | 'radar' | 'bar'>('table')
const barParamKey = ref('')
const radarChartRef = ref<HTMLElement>()
const barChartRef = ref<HTMLElement>()

// 初始化时加载市场选项（代码→名称映射）
api.get('/pm/markets/all').then((res: { data: MarketOption[] }) => {
  const data = res.data
  if (Array.isArray(data)) {
    marketOptions.value = data
      .filter((m) => m.is_active !== 'false' && /^[A-Z]{2}$/.test(m.code))
      .map((m) => ({ code: m.code, name: m.name }))
  }
}).catch(() => {
  // 回退：从知识库加载
  api.get('/kb/items', { params: { category: 'market' } }).then((res2: { data: MarketOption[] }) => {
    const data = res2.data
    if (Array.isArray(data)) marketOptions.value = data
  }).catch(() => {})
})

// Compute unique brand names from all rows
const brands = computed(() => {
  const brandSet = new Set<string>()
  for (const row of benchmarkData.value) {
    if (row.competitors) {
      Object.keys(row.competitors).forEach(b => brandSet.add(b))
    }
  }
  return Array.from(brandSet)
})

/** 只包含有至少一个品牌数值数据的参数行（供图表使用） */
const numericBenchmarkRows = computed(() => {
  return benchmarkData.value.filter(row =>
    brands.value.some(b => {
      const e = row.competitors[b]
      return e && typeof e.value === 'number' && !isNaN(e.value)
    })
  )
})

// ── 热力图 / 优劣判断 ────────────────────────────────────────────
/** 参数是否为「越大越好」 */
function isHigherBetter(paramKey: string): boolean {
  const lowerBetterPrefixes = ['noise_', 'cooling_w', 'heating_w', 'factory_price', 'price', 'power_']
  return !lowerBetterPrefixes.some(p => paramKey.startsWith(p) || paramKey.includes(p))
}

/** 返回热力图背景色 */
function getHeatmapStyle(row: BenchmarkRow, brand: string): Record<string, string> {
  const entry = row.competitors?.[brand]
  if (!entry || typeof entry.value !== 'number') return {}

  const target = parseFloat(String(row.our_target))
  if (isNaN(target)) return {}

  const val = entry.value
  if (val === target) return { backgroundColor: '#f0f9eb' }

  const better = isHigherBetter(row.param_key)
  const isBetter = better ? val > target : val < target

  return {
    backgroundColor: isBetter ? '#d1fae5' : '#fee2e2',
  }
}

// ── 数据操作方法 ──────────────────────────────────────────────────
function getCompetitorValue(row: BenchmarkRow, brand: string): string {
  const entry = row.competitors?.[brand]
  if (!entry || entry.value === undefined || entry.value === null) return '-'
  return String(entry.value)
}

function isAdopted(paramKey: string, brand: string): boolean {
  return adoptedKeys.value.has(`${paramKey}|${brand}`)
}

function handleAdopt(row: BenchmarkRow, brand: string) {
  const entry = row.competitors?.[brand]
  if (!entry) return

  const key = `${row.param_key}|${brand}`
  adoptedKeys.value.add(key)
  adoptedKeys.value = new Set(adoptedKeys.value)

  emit('adopt', {
    paramKey: row.param_key,
    value: typeof entry.value === 'number' ? entry.value : parseFloat(String(entry.value)) || 0,
    brand: brand,
  })
}

/** 一键采纳：每项参数选最优品牌的数值 */
function handleAdoptBest() {
  let count = 0
  for (const row of benchmarkData.value) {
    let bestBrand = ''
    let bestVal: number | null = null
    const higherBetter = isHigherBetter(row.param_key)

    for (const brand of brands.value) {
      const entry = row.competitors[brand]
      if (!entry || typeof entry.value !== 'number') continue

      if (bestVal === null) {
        bestBrand = brand
        bestVal = entry.value
      } else if (higherBetter && entry.value > bestVal) {
        bestBrand = brand
        bestVal = entry.value
      } else if (!higherBetter && entry.value < bestVal) {
        bestBrand = brand
        bestVal = entry.value
      }
    }

    if (bestBrand && bestVal !== null) {
      handleAdopt(row, bestBrand)
      count++
    }
  }
  ElMessage.success(`已采纳 ${count} 项最优参数`)
}

// ── 雷达图 ────────────────────────────────────────────────────────
function buildRadarOption(): EChartsOption {
  const rows = numericBenchmarkRows.value
  if (rows.length === 0 || brands.value.length === 0) return {}

  // 计算每个维度的归一化范围
  const ranges: { min: number; max: number }[] = rows.map(row => {
    let min = Infinity
    let max = -Infinity
    for (const b of brands.value) {
      const e = row.competitors[b]
      if (e && typeof e.value === 'number') {
        min = Math.min(min, e.value)
        max = Math.max(max, e.value)
      }
    }
    // 考察我方目标
    const t = parseFloat(String(row.our_target))
    if (!isNaN(t)) {
      min = Math.min(min, t)
      max = Math.max(max, t)
    }
    if (min === Infinity) { min = 0; max = 100 }
    if (min === max) { min = min * 0.85; max = max * 1.15 }
    return { min, max }
  })

  const colors = getChartColors()

  // 归一化辅助：值 → 0~100
  function normalize(val: number, i: number): number {
    const r = ranges[i]
    const span = r.max - r.min
    return span > 0 ? ((val - r.min) / span) * 100 : 50
  }

  // 构建数据项
  const dataItems: Array<{
    value: number[]
    name: string
    lineStyle?: Record<string, unknown>
    areaStyle?: Record<string, unknown>
    itemStyle?: Record<string, unknown>
  }> = []

  // 我方目标基准线（虚线）
  const targetValues = rows.map((row, i) => {
    const t = parseFloat(String(row.our_target))
    return isNaN(t) ? undefined : normalize(t, i)
  })
  if (targetValues.some(v => v !== undefined)) {
    dataItems.push({
      value: targetValues.map(v => v ?? 0),
      name: '我方目标',
      lineStyle: { type: 'dashed', width: 2, color: '#FF3B30' },
      areaStyle: { opacity: 0 },
      itemStyle: { color: '#FF3B30' },
    })
  }

  // 各品牌
  brands.value.forEach((brand, bi) => {
    const values = rows.map((row, i) => {
      const e = row.competitors[brand]
      if (!e || typeof e.value !== 'number') return 0
      return normalize(e.value, i)
    })
    dataItems.push({
      value: values,
      name: brand,
      lineStyle: { width: 2, color: colors[bi % colors.length] },
      areaStyle: { opacity: 0.08, color: colors[bi % colors.length] },
      itemStyle: { color: colors[bi % colors.length] },
    })
  })

  return {
    color: colors,
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'item',
      formatter: (params: unknown) => {
        const p = params as { name?: string; value?: number[]; marker?: string }
        if (!p || !p.value) return ''
        const lines = rows.map((row, i) => {
          const rawMin = ranges[i].min
          const rawMax = ranges[i].max
          const span = rawMax - rawMin
          const rawVal = span > 0 ? (p.value![i] / 100) * span + rawMin : row.competitors?.[brands.value[0]]?.value ?? '—'
          return `${row.param_name}：${typeof rawVal === 'number' ? rawVal.toFixed(2) : rawVal}`
        })
        return `<strong>${p.name || ''}</strong><br/>${lines.join('<br/>')}`
      },
    },
    legend: {
      data: ['我方目标', ...brands.value],
      bottom: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { fontSize: 12, color: '#86868b' },
    },
    radar: {
      indicator: rows.map(row => ({
        name: row.param_name,
        max: 100,
      })),
      center: ['50%', '54%'],
      radius: '62%',
      axisName: {
        color: '#1d1d1f',
        fontSize: 11,
        borderRadius: 4,
        padding: [2, 6],
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(0,0,0,0.02)', 'rgba(0,0,0,0.04)'],
        },
      },
      axisLine: {
        lineStyle: { color: 'rgba(0,0,0,0.08)' },
      },
      splitLine: {
        lineStyle: { color: 'rgba(0,0,0,0.06)' },
      },
    },
    series: [{
      type: 'radar',
      data: dataItems,
      symbol: 'circle',
      symbolSize: 4,
    }],
  }
}

function renderRadarChart() {
  nextTick(() => {
    if (!radarChartRef.value) return
    disposeChart(radarChartRef.value)
    initChart(radarChartRef.value, buildRadarOption())
  })
}

// ── 柱状图 ────────────────────────────────────────────────────────
function buildBarOption(): EChartsOption {
  const selectedKey = barParamKey.value || numericBenchmarkRows.value[0]?.param_key || ''
  const selectedRow = benchmarkData.value.find(r => r.param_key === selectedKey)
  if (!selectedRow) return {}

  const colors = getChartColors()

  // 过滤有数值的品牌
  const brandData: Array<{ brand: string; value: number }> = []
  for (const brand of brands.value) {
    const e = selectedRow.competitors[brand]
    if (e && typeof e.value === 'number' && !isNaN(e.value)) {
      brandData.push({ brand, value: e.value })
    }
  }
  if (brandData.length === 0) return {}

  const target = parseFloat(String(selectedRow.our_target))
  const hasTarget = !isNaN(target)

  return {
    color: colors,
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'axis',
      formatter: (params: unknown) => {
        const items = params as Array<{ seriesName?: string; value?: number; marker?: string }>
        if (!items || items.length === 0) return ''
        const lines = items.map(it => `${it.marker || ''} ${it.seriesName || ''}：${it.value ?? '—'}`)
        if (hasTarget) lines.push(`<br/><span style="color:#FF3B30">─ 我方目标：${target}</span>`)
        return `<strong>${selectedRow.param_name}</strong><br/>${lines.join('<br/>')}`
      },
    },
    legend: { show: false },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 12,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: brandData.map(b => b.brand),
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#86868b', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#86868b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      name: selectedRow.param_name,
      nameTextStyle: { color: '#86868b', fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: brandData.map((b, i) => ({
        value: b.value,
        itemStyle: {
          color: colors[i % colors.length],
          borderRadius: [4, 4, 0, 0] as [number, number, number, number],
        },
      })),
      barWidth: 36,
      ...(hasTarget
        ? {
            markLine: {
              silent: true,
              symbol: 'none',
              lineStyle: { type: 'dashed', color: '#FF3B30', width: 2 },
              label: {
                formatter: `我方目标: ${target}`,
                color: '#FF3B30',
                fontSize: 12,
                position: 'insideEndTop' as const,
              },
              data: [{ yAxis: target } as Record<string, unknown>],
            },
          }
        : {}),
    }],
  }
}

function renderBarChart() {
  nextTick(() => {
    if (!barChartRef.value) return
    disposeChart(barChartRef.value)
    initChart(barChartRef.value, buildBarOption())
  })
}

// ── 数据转换 ──────────────────────────────────────────────────────
/** 将后端返回的 {market, competitors, param_names} 转换为 BenchmarkRow[] */
function transformBenchmarkData(raw: BenchmarkApiResponse): BenchmarkRow[] {
  if (!raw || !raw.param_names || !raw.competitors) return []

  const competitors = raw.competitors
  const paramNames = raw.param_names

  return paramNames.map((p) => {
    const row: BenchmarkRow = {
      param_key: p.key,
      param_name: p.unit ? `${p.label} (${p.unit})` : p.label,
      our_target: '—',
      competitors: {},
    }

    for (const c of competitors) {
      let val = c[p.key]
      // 对能效字段做市场适配
      if (val === undefined || val === null) {
        // 如果是EER字段且不存在，尝试用 cspf/iseer/seer
        if (p.key === 'eer') {
          val = c.cspf ?? c.iseer ?? c.seer
        }
      }
      if (val !== undefined && val !== null) {
        row.competitors[c.brand] = { value: (Number(val) || val) as number | string, model: c.model || '' }
      }
    }

    return row
  })
}

async function fetchBenchmark(market: string) {
  if (!market) return
  loading.value = true
  try {
    // 市场代码 → 名称转换
    const mkt = marketOptions.value.find((m) => m.code === market || m.name === market)
    const marketName = mkt ? mkt.name : market
    const res = await api.get('/pm/competitors/benchmark', { params: { market: marketName } })
    competitorData.value = res.data.competitors || []
    benchmarkData.value = transformBenchmarkData(res.data)
    // Check completeness
    allComplete.value = competitorData.value.every((c) => c.is_complete)
    adoptedKeys.value = new Set()

    // 初始化柱状图参数选择
    const numericRows = numericBenchmarkRows.value
    if (numericRows.length > 0 && !barParamKey.value) {
      barParamKey.value = numericRows[0].param_key
    }
  } catch {
    benchmarkData.value = []
  } finally {
    loading.value = false
  }
}

// ── Watchers ───────────────────────────────────────────────────────
// Watch market changes
watch(() => props.market, (newMarket) => {
  if (newMarket) {
    fetchBenchmark(newMarket)
  } else {
    benchmarkData.value = []
  }
}, { immediate: true })

// 当数据变化时，重新渲染当前视图的图表
watch(benchmarkData, () => {
  if (viewMode.value === 'radar') {
    renderRadarChart()
  } else if (viewMode.value === 'bar') {
    // 如果当前选中参数已不存在，重置
    if (barParamKey.value && !benchmarkData.value.some(r => r.param_key === barParamKey.value)) {
      const numericRows = numericBenchmarkRows.value
      barParamKey.value = numericRows.length > 0 ? numericRows[0].param_key : ''
    }
    renderBarChart()
  }
}, { deep: false })

// 视图切换时渲染对应的图表
watch(viewMode, (mode) => {
  if (mode === 'radar') {
    renderRadarChart()
  } else if (mode === 'bar') {
    renderBarChart()
  }
})

// ── 生命周期 ──────────────────────────────────────────────────────
onUnmounted(() => {
  if (radarChartRef.value) disposeChart(radarChartRef.value)
  if (barChartRef.value) disposeChart(barChartRef.value)
})
</script>

<style scoped>
.competitor-bench {
  margin-top: 16px;
}
.bench-table {
  margin-top: 8px;
}
.competitor-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}
.competitor-cell--adopted {
  border: 1px solid #67c23a;
  border-radius: 4px;
  padding: 4px 8px;
}
.cell-value {
  font-variant-numeric: tabular-nums;
}

/* 工具栏 */
.bench-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

/* 图表容器 */
.chart-container {
  width: 100%;
  height: 420px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px;
  box-sizing: border-box;
}

/* 柱状图控件 */
.bar-chart-wrapper {
  width: 100%;
}
.bar-controls {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.bar-controls-label {
  font-size: 13px;
  color: #606266;
  margin-right: 8px;
  white-space: nowrap;
}
</style>
