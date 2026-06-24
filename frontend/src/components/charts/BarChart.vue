<template>
  <div ref="chartRef" class="bar-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { initChart, disposeChart, getGlassTooltip, getChartColors, updateChart } from '../../utils/chart'
import { echarts } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  data: { name: string; value: number }[]
  title?: string
  height?: number
  horizontal?: boolean
  colorIndex?: number
  barWidth?: number
}>()

const chartRef = ref<HTMLElement>()

const option = computed<EChartsOption>(() => {
  const colors = getChartColors()
  const baseColor = colors[props.colorIndex || 0]
  const gradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: baseColor + 'dd' },
    { offset: 1, color: baseColor + '88' },
  ])

  return {
    title: props.title
      ? { text: props.title, left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 600, color: '#1d1d1f' } }
      : undefined,
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: props.title ? 48 : 24, containLabel: true },
    xAxis: {
      type: props.horizontal ? 'value' : 'category',
      data: props.horizontal ? undefined : (props.data || []).map(d => d.name),
      axisLine: { lineStyle: { color: '#e0e0e0' } },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { show: props.horizontal, lineStyle: { color: '#f0f0f0' } },
    },
    yAxis: {
      type: props.horizontal ? 'category' : 'value',
      data: props.horizontal ? (props.data || []).map(d => d.name) : undefined,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#86868b', fontSize: 12 },
      splitLine: { show: !props.horizontal, lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        type: 'bar',
        data: (props.data || []).map(d => d.value),
        barWidth: props.barWidth || (props.horizontal ? 16 : 24),
        itemStyle: {
          color: gradient,
          borderRadius: props.horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0],
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 8,
            shadowColor: 'rgba(0, 0, 0, 0.12)',
          },
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
.bar-chart {
  width: 100%;
}
</style>