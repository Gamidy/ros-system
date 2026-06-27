<template>
  <div class="bar-compare-wrapper" :style="{ height: height + 'px' }">
    <!-- 加载态 -->
    <div v-if="loading" class="chart-overlay">
      <el-skeleton :rows="5" animated />
    </div>
    <!-- 空态 -->
    <div v-else-if="empty" class="chart-overlay chart-empty">
      <el-empty :description="emptyText" :image-size="80" />
    </div>
    <!-- 参数选择器 -->
    <div v-show="!loading && !empty" class="bar-controls">
      <el-checkbox-group v-model="selectedParams" @change="onParamChange">
        <el-checkbox
          v-for="p in availableParams"
          :key="p.key"
          :label="p.key"
          :value="p.key"
        >
          {{ p.label }}
        </el-checkbox>
      </el-checkbox-group>
    </div>
    <!-- 图表容器 -->
    <div v-show="!loading && !empty" ref="chartRef" class="bar-canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { initChart, disposeChart, updateChart, getChartColors, getGlassTooltip } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

/** 参数定义 */
interface ParamDef {
  key: string
  label: string
  unit: string
}

/** 竞品数据条目 */
interface CompetitorEntry {
  id: number
  brand: string
  model: string
  [key: string]: unknown
}

/** 默认选中参数（前 4 个，避免过于拥挤） */
const DEFAULT_PARAMS = ['cooling_w', 'heating_w', 'noise_indoor_db', 'airflow_m3h']

/** 可对比的参数列表 */
const COMPARE_PARAMS: ParamDef[] = [
  { key: 'cooling_w', label: '制冷功率', unit: 'W' },
  { key: 'heating_w', label: '制热功率', unit: 'W' },
  { key: 'eer', label: 'EER', unit: '' },
  { key: 'cspf', label: 'CSPF', unit: '' },
  { key: 'noise_indoor_db', label: '室内噪音', unit: 'dB' },
  { key: 'noise_outdoor_db', label: '室外噪音', unit: 'dB' },
  { key: 'airflow_m3h', label: '循环风量', unit: 'm³/h' },
]

const props = withDefaults(defineProps<{
  /** 竞品列表 */
  competitors: CompetitorEntry[]
  height?: number
  loading?: boolean
  empty?: boolean
  emptyText?: string
}>(), {
  height: 420,
  loading: false,
  empty: false,
  emptyText: '暂无数据',
})

const emit = defineEmits<{
  (e: 'param-change', keys: string[]): void
}>()

const chartRef = ref<HTMLElement>()
const selectedParams = ref<string[]>([...DEFAULT_PARAMS])
const allCompetitors = ref<CompetitorEntry[]>([])

const availableParams = computed<ParamDef[]>(() => COMPARE_PARAMS)

// 同步外部数据
watch(() => props.competitors, (list) => {
  allCompetitors.value = list
}, { immediate: true })

function onParamChange(keys: string[]) {
  emit('param-change', keys)
  if (chartRef.value) {
    nextTick(() => updateChart(chartRef.value!, buildOption()))
  }
}

function getParamLabel(key: string): string {
  const found = COMPARE_PARAMS.find((p) => p.key === key)
  return found ? (found.unit ? `${found.label} (${found.unit})` : found.label) : key
}

function buildBarSeries(colors: string[]): Array<{
  name: string
  type: 'bar'
  data: number[]
  itemStyle: { color: string; borderRadius: number[] }
  barMaxWidth: number
  emphasis: { itemStyle: { shadowBlur: number; shadowColor: string } }
}> {
  return selectedParams.value.map((key, idx) => {
    const data = allCompetitors.value.map((c) => {
      const v = Number(c[key])
      return Number.isNaN(v) ? 0 : v
    })
    return {
      name: getParamLabel(key),
      type: 'bar' as const,
      data,
      itemStyle: {
        color: colors[idx % colors.length],
        borderRadius: [4, 4, 0, 0],
      },
      barMaxWidth: 28,
      emphasis: {
        itemStyle: {
          shadowBlur: 8,
          shadowColor: 'rgba(0, 0, 0, 0.12)',
        },
      },
    }
  })
}

function buildTooltipConfig() {
  return {
    ...getGlassTooltip(),
    trigger: 'axis' as const,
    axisPointer: { type: 'shadow' as const },
  }
}

function buildLegendConfig() {
  return {
    top: 8,
    right: 16,
    itemWidth: 12,
    itemHeight: 12,
    textStyle: { fontSize: 12, color: '#86868b' },
  }
}

function buildOption(): EChartsOption {
  const colors = getChartColors()
  const items = allCompetitors.value
  const params = selectedParams.value

  if (items.length === 0 || params.length === 0) {
    return { xAxis: {}, yAxis: {}, series: [] }
  }

  // xAxis: brand + model
  const xData = items.map((c) => `${c.brand}\\n${c.model}`)
  const series = buildBarSeries(colors)

  return {
    tooltip: buildTooltipConfig(),
    legend: buildLegendConfig(),
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 48,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#86868b', fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series,
  }
}

const option = computed<EChartsOption>(buildOption)

function render() {
  if (!chartRef.value) return
  initChart(chartRef.value, option.value)
}

watch(
  () => [props.competitors, props.loading, props.empty],
  () => {
    if (chartRef.value && !props.loading && !props.empty) {
      nextTick(() => updateChart(chartRef.value!, buildOption()))
    }
  },
  { deep: true },
)

onMounted(() => {
  if (!props.loading && !props.empty) {
    nextTick(() => render())
  }
})

onUnmounted(() => {
  if (chartRef.value) disposeChart(chartRef.value)
})

watch(() => [props.loading, props.empty], ([load, emp]) => {
  if (!load && !emp && chartRef.value) {
    nextTick(() => render())
  }
})
</script>

<style scoped>
.bar-compare-wrapper {
  position: relative;
  width: 100%;
}
.bar-canvas {
  width: 100%;
  height: calc(100% - 40px);
}
.bar-controls {
  padding: 8px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.bar-controls :deep(.el-checkbox) {
  margin-right: 8px;
  font-size: 12px;
}
.bar-controls :deep(.el-checkbox__label) {
  font-size: 12px;
}
.chart-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  z-index: 1;
}
.chart-empty {
  background: transparent;
}
</style>
