<template>
  <div class="radar-chart-wrapper" :style="{ height: height + 'px' }">
    <!-- 加载态 -->
    <div v-if="loading" class="chart-overlay">
      <el-skeleton :rows="5" animated />
    </div>
    <!-- 空态 -->
    <div v-else-if="empty" class="chart-overlay chart-empty">
      <el-empty :description="emptyText" :image-size="80" />
    </div>
    <!-- 多选筛选器 -->
    <div v-show="!loading && !empty" class="radar-controls">
      <el-checkbox-group v-model="selectedIds" @change="onSelectionChange">
        <el-checkbox
          v-for="item in allCompetitors"
          :key="item.id"
          :label="item.id"
          :value="item.id"
        >
          {{ item.brand }} {{ item.model }}
        </el-checkbox>
      </el-checkbox-group>
    </div>
    <!-- 图表容器 -->
    <div v-show="!loading && !empty" ref="chartRef" class="radar-canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { initChart, disposeChart, updateChart, echarts, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

/** 雷达图维度定义 */
interface RadarDimension {
  key: string
  label: string
  /** 合理最大值，用于归一化显示 */
  max: number
}

/** 竞品数据条目（来自 benchmark 接口） */
interface CompetitorEntry {
  id: number
  brand: string
  model: string
  [key: string]: unknown
}

const RADAR_DIMS: RadarDimension[] = [
  { key: 'eer', label: 'EER', max: 8 },
  { key: 'cspf', label: 'CSPF', max: 10 },
  { key: 'cooling_w', label: '制冷功率(W)', max: 4000 },
  { key: 'heating_w', label: '制热功率(W)', max: 4000 },
  { key: 'noise_indoor_db', label: '室内噪音(dB)', max: 70 },
  { key: 'airflow_m3h', label: '循环风量(m³/h)', max: 1500 },
]

const props = withDefaults(defineProps<{
  /** 竞品列表（来自 benchmark 接口的 competitors 字段） */
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
  (e: 'selection-change', ids: number[]): void
}>()

const chartRef = ref<HTMLElement>()
const selectedIds = ref<number[]>([])
const allCompetitors = ref<CompetitorEntry[]>([])

// 同步外部数据到内部
watch(() => props.competitors, (list) => {
  allCompetitors.value = list
  // 初始默认全选（最多 6 个以免雷达图太拥挤）
  if (list.length > 0 && selectedIds.value.length === 0) {
    selectedIds.value = list.slice(0, 6).map((c) => c.id)
  }
}, { immediate: true })

function onSelectionChange(ids: number[]) {
  emit('selection-change', ids)
  if (chartRef.value) {
    nextTick(() => updateChart(chartRef.value!, buildOption()))
  }
}

/** 找出每个维度的实际最大值来计算 indicator max */
function computeIndicatorMax(): RadarDimension[] {
  const items = allCompetitors.value
  if (items.length === 0) return RADAR_DIMS
  return RADAR_DIMS.map((dim) => {
    const values = items
      .map((c) => Number(c[dim.key]))
      .filter((v) => !Number.isNaN(v) && v > 0)
    const maxVal = values.length > 0 ? Math.max(...values) : dim.max
    // 留 20% 余量
    const computedMax = Math.ceil(maxVal * 1.2)
    return { ...dim, max: Math.max(computedMax, dim.max) }
  })
}

function buildRadarIndicators(): Array<{ name: string; max: number }> {
  return computeIndicatorMax().map((dim) => ({
    name: dim.label,
    max: dim.max,
  }))
}

function buildSeriesData(
  colors: string[],
): Array<{
  value: number[]
  name: string
  areaStyle: { color: echarts.graphic.LinearGradient }
  lineStyle: { color: string; width: number }
  itemStyle: { color: string }
}> {
  return allCompetitors.value
    .filter((c) => selectedIds.value.includes(c.id))
    .map((c, i) => {
      const values = RADAR_DIMS.map((dim) => {
        const v = Number(c[dim.key])
        return Number.isNaN(v) ? 0 : v
      })
      const color = colors[i % colors.length]
      return {
        value: values,
        name: `${c.brand} ${c.model}`,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color + '60' },
            { offset: 1, color: color + '10' },
          ]),
        },
        lineStyle: { color, width: 2 },
        itemStyle: { color },
      }
    })
}

function buildTooltipConfig() {
  return {
    trigger: 'item' as const,
    backgroundColor: 'rgba(255, 255, 255, 0.85)',
    borderColor: 'rgba(255, 255, 255, 0.3)',
    borderWidth: 1,
    textStyle: { color: '#1d1d1f', fontSize: 12 },
    extraCssText:
      'backdrop-filter: blur(12px); border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.08);',
  }
}

function buildLegendConfig(names: string[]) {
  return {
    data: names,
    bottom: 8,
    itemWidth: 12,
    itemHeight: 12,
    textStyle: { fontSize: 12, color: '#86868b' },
  }
}

function buildRadarConfig() {
  return {
    indicators: buildRadarIndicators(),
    center: ['50%', '50%'] as [string, string],
    radius: '65%',
    axisName: { color: '#4a3f35', fontSize: 12, fontWeight: 600 as const },
    splitArea: {
      areaStyle: {
        color: ['rgba(200, 200, 200, 0.05)', 'rgba(200, 200, 200, 0.1)'],
      },
    },
    splitLine: { lineStyle: { color: 'rgba(200, 200, 200, 0.3)' } },
    axisLine: { lineStyle: { color: 'rgba(200, 200, 200, 0.3)' } },
  }
}

function buildOption(): EChartsOption {
  const colors = getChartColors()
  const seriesData = buildSeriesData(colors)
  const names = seriesData.map((s) => s.name)

  return {
    tooltip: buildTooltipConfig(),
    legend: buildLegendConfig(names),
    radar: buildRadarConfig(),
    series: [
      {
        type: 'radar',
        data: seriesData,
        symbol: 'circle',
        symbolSize: 6,
        emphasis: { lineStyle: { width: 4 } },
      },
    ],
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
.radar-chart-wrapper {
  position: relative;
  width: 100%;
}
.radar-canvas {
  width: 100%;
  height: calc(100% - 40px);
}
.radar-controls {
  padding: 8px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.radar-controls :deep(.el-checkbox) {
  margin-right: 8px;
  font-size: 12px;
}
.radar-controls :deep(.el-checkbox__label) {
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
