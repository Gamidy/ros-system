<template>
  <div class="bi-chart-wrapper" :style="{ height: height + 'px' }">
    <!-- 加载态 -->
    <div v-if="loading" class="bi-chart-overlay">
      <el-skeleton :rows="4" animated />
    </div>
    <!-- 空态 -->
    <div v-else-if="empty" class="bi-chart-overlay bi-chart-empty">
      <el-empty :description="emptyText" :image-size="80" />
    </div>
    <!-- 图表容器 -->
    <div v-show="!loading && !empty" ref="chartRef" class="bi-chart-canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { initChart, disposeChart, updateChart, echarts, getGlassTooltip, getChartColors } from '../utils/chart'
import type { EChartsOption } from 'echarts'

type ChartType = 'bar' | 'line' | 'pie'

const props = withDefaults(defineProps<{
  type: ChartType
  data: Record<string, unknown>[]
  /** 柱状图/折线图: xAxis 维度字段名; 饼图: name 字段名 */
  nameKey?: string
  /** 柱状图/折线图: series 值字段名; 饼图: value 字段名 */
  valueKey?: string
  /** 多系列折线/柱状: [{ name, key }] */
  series?: { name: string; key: string }[]
  title?: string
  height?: number
  loading?: boolean
  empty?: boolean
  emptyText?: string
  /** 图表主题色，默认使用 getChartColors() */
  theme?: string[]
  /** 饼图: 环形 */
  donut?: boolean
  /** 折线图: 面积 */
  area?: boolean
  /** 折线图: 平滑 */
  smooth?: boolean
  /** 柱状图: 横向 */
  horizontal?: boolean
  /** 是否显示图例 */
  showLegend?: boolean
}>(), {
  nameKey: 'name',
  valueKey: 'value',
  height: 320,
  emptyText: '暂无数据',
  loading: false,
  empty: false,
  showLegend: true,
})

const chartRef = ref<HTMLElement>()

const colors = computed(() => props.theme?.length ? props.theme : getChartColors())

function buildOption(): EChartsOption {
  const baseOption: EChartsOption = {
    title: props.title
      ? { text: props.title, left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 600, color: '#1d1d1f' } }
      : undefined,
    tooltip: {
      ...getGlassTooltip(),
      trigger: props.type === 'pie' ? 'item' : 'axis',
      axisPointer: props.type !== 'pie' ? { type: 'shadow' } : undefined,
    },
    color: colors.value,
  }

  if (props.type === 'pie') {
    return {
      ...baseOption,
      legend: props.showLegend
        ? { bottom: 8, itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 12, color: '#86868b' } }
        : undefined,
      series: [{
        type: 'pie',
        radius: props.donut ? ['40%', '70%'] : '70%',
        center: ['50%', '50%'],
        data: (props.data || []).map((d: Record<string, unknown>) => ({
          name: d[props.nameKey],
          value: d[props.valueKey],
        })),
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          fontSize: 12,
          color: '#1d1d1f',
          formatter: '{b}: {d}%',
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.12)',
          },
          scale: true,
          scaleSize: 8,
        } as any,
      }],
    } as EChartsOption
  }

  // bar / line 共用 grid
  const grid = {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: props.title ? 48 : 24,
    containLabel: true,
  }

  if (props.series && props.series.length > 0) {
    // 多系列
    return {
      ...baseOption,
      legend: props.showLegend
        ? { top: 8, right: 16, itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 12, color: '#86868b' } }
        : undefined,
      grid: props.title ? { ...grid, top: 56 } : grid,
      xAxis: {
        type: props.horizontal ? 'value' : 'category',
        data: props.horizontal ? undefined : (props.data || []).map((d: Record<string, unknown>) => d[props.nameKey]),
        axisLine: { lineStyle: { color: '#e0e0e0' } },
        axisLabel: { color: '#86868b', fontSize: 12 },
        splitLine: { show: !!props.horizontal, lineStyle: { color: '#f0f0f0' } },
      },
      yAxis: {
        type: props.horizontal ? 'category' : 'value',
        data: props.horizontal ? (props.data || []).map((d: Record<string, unknown>) => d[props.nameKey]) : undefined,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#86868b', fontSize: 12 },
        splitLine: { show: !props.horizontal, lineStyle: { color: '#f0f0f0' } },
      },
      series: props.series.map((s, i) => ({
        type: props.type,
        name: s.name,
        data: (props.data || []).map((d: Record<string, unknown>) => d[s.key]),
        smooth: props.type === 'line' ? (props.smooth ?? true) : undefined,
        symbol: props.type === 'line' ? 'circle' : undefined,
        symbolSize: props.type === 'line' ? 6 : undefined,
        lineStyle: props.type === 'line' ? { color: colors.value[i % colors.value.length], width: 3 } : undefined,
        itemStyle: props.type === 'bar'
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: colors.value[i % colors.value.length] + 'dd' },
                { offset: 1, color: colors.value[i % colors.value.length] + '88' },
              ]),
              borderRadius: props.horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0],
            }
          : {
              color: colors.value[i % colors.value.length],
              borderColor: '#fff',
              borderWidth: 2,
            },
        barWidth: props.type === 'bar' ? (props.horizontal ? 16 : 24) : undefined,
        areaStyle: props.type === 'line' && props.area
          ? {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: colors.value[i % colors.value.length] + '40' },
                  { offset: 1, color: colors.value[i % colors.value.length] + '05' },
                ],
              },
            }
          : undefined,
        emphasis: {
          itemStyle: props.type === 'line'
            ? { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.12)' }
            : { shadowBlur: 8, shadowColor: 'rgba(0, 0, 0, 0.12)' },
          scale: props.type === 'line' ? true : undefined,
        },
      })) as any,
    } as EChartsOption
  }

  // 单系列 bar / line
  return {
    ...baseOption,
    grid,
    xAxis: {
      type: props.horizontal ? 'value' : 'category',
      data: props.horizontal ? undefined : (props.data || []).map((d: Record<string, unknown>) => d[props.nameKey]),
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { show: !!props.horizontal, lineStyle: { color: '#f0f0f0' } },
    },
    yAxis: {
      type: props.horizontal ? 'category' : 'value',
      data: props.horizontal ? (props.data || []).map((d: Record<string, unknown>) => d[props.nameKey]) : undefined,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { show: !props.horizontal, lineStyle: { color: '#f0f0f0' } },
    },
    series: [{
      type: props.type,
      data: (props.data || []).map((d: Record<string, unknown>) => d[props.valueKey]),
      smooth: props.type === 'line' ? (props.smooth ?? true) : undefined,
      symbol: props.type === 'line' ? 'circle' : undefined,
      symbolSize: props.type === 'line' ? 6 : undefined,
      lineStyle: props.type === 'line' ? { color: colors.value[0], width: 3 } : undefined,
      itemStyle: props.type === 'bar'
        ? {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: colors.value[0] + 'dd' },
              { offset: 1, color: colors.value[0] + '88' },
            ]),
            borderRadius: props.horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0],
          }
        : {
            color: colors.value[0],
            borderColor: '#fff',
            borderWidth: 2,
          },
      barWidth: props.type === 'bar' ? (props.horizontal ? 16 : 24) : undefined,
      areaStyle: props.type === 'line' && props.area
        ? {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: colors.value[0] + '40' },
                { offset: 1, color: colors.value[0] + '05' },
              ],
            },
          }
        : undefined,
      emphasis: {
        itemStyle: {
          shadowBlur: props.type === 'line' ? 10 : 8,
          shadowColor: 'rgba(0, 0, 0, 0.12)',
        },
        scale: props.type === 'line' ? true : undefined,
      },
    }] as any,
  } as EChartsOption
}

const option = computed<EChartsOption>(buildOption)

function render() {
  if (!chartRef.value) return
  initChart(chartRef.value, option.value)
}

watch(() => [props.data, props.type, props.series, props.theme], () => {
  if (chartRef.value && !props.loading && !props.empty) {
    const el = chartRef.value
    nextTick(() => updateChart(el, buildOption()))
  }
}, { deep: true })

onMounted(() => {
  if (!props.loading && !props.empty) {
    nextTick(() => render())
  }
})

onUnmounted(() => {
  if (chartRef.value) disposeChart(chartRef.value)
})

// 当 loading/empty 从 true 变为 false 时重新渲染
watch(() => [props.loading, props.empty], ([load, emp]) => {
  if (!load && !emp && chartRef.value) {
    nextTick(() => render())
  }
})
</script>

<style scoped>
.bi-chart-wrapper {
  position: relative;
  width: 100%;
}
.bi-chart-canvas {
  width: 100%;
  height: 100%;
}
.bi-chart-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  z-index: 1;
}
.bi-chart-empty {
  background: transparent;
}
</style>
