<template>
  <div ref="chartRef" class="pie-chart" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { initChart, disposeChart, getGlassTooltip, getChartColors, updateChart } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  data: { name: string; value: number }[]
  title?: string
  height?: number
  donut?: boolean
  showLegend?: boolean
}>()

const chartRef = ref<HTMLElement>()

const option = computed<EChartsOption>(() => {
  return {
    title: props.title
      ? { text: props.title, left: 'center', top: 8, textStyle: { fontSize: 14, fontWeight: 600, color: '#1d1d1f' } }
      : undefined,
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'item',
    },
    legend: props.showLegend
      ? { bottom: 8, itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 12, color: '#86868b' } }
      : undefined,
    color: getChartColors(),
    series: [
      {
        type: 'pie',
        radius: props.donut ? ['40%', '70%'] : '70%',
        center: ['50%', '50%'],
        data: Array.isArray(props.data) ? props.data : [],
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          fontSize: 12,
          color: '#1d1d1f',
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.12)',
          },
          scale: true,
          scaleSize: 8,
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
.pie-chart {
  width: 100%;
}
</style>