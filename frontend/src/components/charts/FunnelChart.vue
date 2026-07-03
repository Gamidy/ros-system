<template>
  <div class="funnel-chart-wrapper" :style="{ height: height + 'px' }">
    <div v-if="!data || data.length === 0" class="funnel-empty">
      <el-empty :description="emptyText" :image-size="80" />
    </div>
    <div v-else ref="chartRef" class="funnel-canvas" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { initChart, disposeChart, updateChart, getGlassTooltip, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

interface FunnelDataItem {
  name: string
  value: number
}

const props = withDefaults(defineProps<{
  data: FunnelDataItem[]
  height?: number
  emptyText?: string
}>(), {
  height: 320,
  emptyText: '暂无数据',
})

const chartRef = ref<HTMLElement>()
const colors = getChartColors()

const option = computed<EChartsOption>(() => {
  // _total available if needed
  return {
    tooltip: {
      ...getGlassTooltip(),
      trigger: 'item',
      formatter: (params: { name: string; value: number; percent: number }) => {
        return `${params.name}<br/>数量: ${params.value}<br/>占比: ${params.percent}%`
      },
    },
    color: colors,
    series: [{
      type: 'funnel',
      left: '10%',
      top: 20,
      bottom: 20,
      width: '80%',
      minSize: '10%',
      maxSize: '100%',
      sort: 'descending',
      gap: 4,
      label: {
        show: true,
        position: 'inside',
        fontSize: 13,
        fontWeight: 600,
        color: '#fff',
        formatter: (params: { name: string; value: number }) => {
          return `${params.name}\n${params.value}`
        },
      },
      labelLine: { show: false },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 2,
      },
      emphasis: {
        label: { fontSize: 16, fontWeight: 'bold' },
      },
      data: (Array.isArray(props.data) ? props.data : []).map((d, i) => ({
        name: d.name,
        value: d.value,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }],
  } as EChartsOption
})

function render() {
  if (!chartRef.value) return
  initChart(chartRef.value!, option.value)
}

watch(() => props.data, () => {
  if (chartRef.value && props.data.length > 0) {
    nextTick(() => updateChart(chartRef.value!, option.value))
  }
}, { deep: true })

onMounted(() => {
  if (props.data.length > 0) {
    nextTick(() => render())
  }
})

onUnmounted(() => {
  if (chartRef.value) disposeChart(chartRef.value)
})
</script>

<style scoped>
.funnel-chart-wrapper {
  position: relative;
  width: 100%;
}
.funnel-canvas {
  width: 100%;
  height: 100%;
}
.funnel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
}
</style>
