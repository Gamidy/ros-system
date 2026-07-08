<template>
  <div ref="chartRef" class="line-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { initChart, disposeChart, getGlassTooltip, getChartColors, updateChart } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  data: { name: string; value: number | number[] }[]
  title?: string
  height?: number
  smooth?: boolean
  area?: boolean
  colorIndex?: number
}>()

const chartRef = ref<HTMLElement>()

const option = computed<EChartsOption>(() => {
  const colors = getChartColors()
  const color = colors[props.colorIndex || 0]

  return {
    title: props.title
      ? { text: props.title, left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 600, color: '#1d1d1f' } }
      : undefined,
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'axis',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: props.title ? 48 : 24, containLabel: true },
    xAxis: {
      type: 'category',
      data: (props.data || []).map(d => d.name),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#86868b', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        type: 'line',
        data: (props.data || []).map(d => d.value),
        smooth: props.smooth ?? true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color, width: 3 },
        itemStyle: { color, borderColor: '#fff', borderWidth: 2 },
        areaStyle: props.area
          ? {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: color + '40' },
                  { offset: 1, color: color + '05' },
                ],
              },
            }
          : undefined,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.12)',
          },
          scale: true,
        },
      },
    ],
  }
})

function render() {
  if (!chartRef.value) return
  initChart(chartRef.value, option.value)
}

watch(() => props.data, () => {
  if (chartRef.value) updateChart(chartRef.value, option.value)
}, { deep: true })

onMounted(() => {
  render()
  if (chartRef.value) chartRef.value.style.height = (props.height || 280) + 'px'
})

onUnmounted(() => {
  if (chartRef.value) disposeChart(chartRef.value)
})
</script>

<style scoped>
.line-chart {
  width: 100%;
}
</style>