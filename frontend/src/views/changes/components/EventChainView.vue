<template>
  <el-card shadow="never" style="margin-bottom: 16px">
    <template #header>
      <div class="card-header">
        <span>事件链 (Digital Thread)</span>
        <el-tag v-if="eventCount > 0" size="small" type="info">{{ eventCount }} 个事件</el-tag>
      </div>
    </template>

    <!-- 加载中 -->
    <div v-if="loading" style="text-align:center;padding:32px">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-else-if="error"
      :title="error"
      type="warning"
      show-icon
      :closable="false"
      style="margin-bottom: 8px"
    />

    <!-- 空状态 -->
    <el-empty
      v-else-if="!events.length"
      description="暂无事件记录"
      :image-size="60"
      style="padding: 24px"
    />

    <!-- 事件时间线 -->
    <div v-else class="event-chain-container">
      <!-- ECharts 时间线图 -->
      <div ref="chartRef" style="width:100%;height:180px"></div>

      <!-- 事件列表明细 -->
      <el-timeline style="margin-top:16px">
        <el-timeline-item
          v-for="(evt) in events"
          :key="evt.id"
          :timestamp="formatTime(evt.created_at)"
          :color="eventColor(evt.event_type)"
        >
          <div class="event-item">
            <div class="event-header">
              <el-tag :type="eventTagType(evt.event_type)" size="small" effect="dark">
                {{ eventLabel(evt.event_type) }}
              </el-tag>
              <span class="event-producer" v-if="evt.producer">{{ evt.producer }}</span>
            </div>
            <div class="event-meta">
              <span>#{{ evt.id }}</span>
              <span v-if="evt.causation_id" style="margin-left:12px;color:#909399">
                由 #{{ evt.causation_id }} 触发
              </span>
            </div>
            <div v-if="evt.event_data" class="event-data">
              <el-tooltip :content="evt.event_data" placement="top" :show-after="300">
                <span class="data-preview">{{ truncate(evt.event_data, 80) }}</span>
              </el-tooltip>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useCIEv2Store } from '@/stores/ci_v2'
import type { EventChainItem } from '@/api/ci_v2'

const props = defineProps<{
  aggregateType: 'ecr' | 'eco'
  aggregateId: number
}>()

const store = useCIEv2Store()
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const events = computed(() => store.eventChain)
const loading = computed(() => store.eventChainLoading)
const error = computed(() => store.eventChainError)
const eventCount = computed(() => events.value.length)

// ── 事件类型映射 ──
const eventLabelMap: Record<string, string> = {
  'ecr.submitted': '提交审批',
  'ecr.reviewing': '开始评审',
  'ecr.approved': '已批准',
  'ecr.rejected': '已驳回',
  'ecr.converted': '已转ECO',
  'eco.implementing': '实施中',
  'eco.verified': '已验证',
  'eco.effective': '已生效',
  'eco.closed': '已关闭',
  'eco.rollback_required': '需回滚',
}
const eventTagMap: Record<string, string> = {
  'ecr.submitted': 'warning',
  'ecr.reviewing': 'primary',
  'ecr.approved': 'success',
  'ecr.rejected': 'danger',
  'ecr.converted': 'info',
  'eco.implementing': 'warning',
  'eco.verified': 'success',
  'eco.effective': 'primary',
  'eco.closed': 'info',
  'eco.rollback_required': 'danger',
}
const eventColorMap: Record<string, string> = {
  'ecr.submitted': '#e6a23c',
  'ecr.reviewing': '#409eff',
  'ecr.approved': '#67c23a',
  'ecr.rejected': '#f56c6c',
  'ecr.converted': '#909399',
  'eco.implementing': '#e6a23c',
  'eco.verified': '#67c23a',
  'eco.effective': '#409eff',
  'eco.closed': '#909399',
  'eco.rollback_required': '#f56c6c',
}

function eventLabel(type: string): string {
  return eventLabelMap[type] || type
}
function eventTagType(type: string): string {
  return eventTagMap[type] || 'info'
}
function eventColor(type: string): string {
  return eventColorMap[type] || '#409eff'
}

function formatTime(t: string): string {
  if (!t) return ''
  return t.slice(0, 16).replace('T', ' ')
}

function truncate(s: string, max: number): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

// ── ECharts 时间线图 ──
function buildChartOption(items: EventChainItem[]): echarts.EChartsOption {
  if (!items.length) return {}

  const times = items.map(e => e.created_at?.slice(0, 16).replace('T', ' ') || '')
  const labels = items.map(e => eventLabel(e.event_type))
  const colors = items.map(e => eventColor(e.event_type))

  return {
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: { show: false },
    series: [{
      type: 'line',
      data: labels.map((_, i) => i + 1),
      step: 'end',
      lineStyle: { width: 2, color: '#409eff' },
      itemStyle: {
        color: (params: { dataIndex: number }) => colors[params.dataIndex] || '#409eff',
      },
      symbol: 'circle',
      symbolSize: 10,
      label: {
        show: true,
        formatter: (params: { dataIndex: number }) => labels[params.dataIndex],
        fontSize: 11,
        color: '#606266',
      },
      tooltip: {
        formatter: (params: { dataIndex: number }) => {
          const e = items[params.dataIndex]
          return `<b>${eventLabel(e.event_type)}</b><br/>时间: ${times[params.dataIndex]}<br/>生产者: ${e.producer}`
        },
      },
    }],
    tooltip: { trigger: 'item' },
  }
}

function renderChart(): void {
  if (!chartRef.value || !events.value.length) return
  nextTick(() => {
    if (!chartRef.value) return
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value)
    }
    chartInstance.setOption(buildChartOption(events.value), true)
  })
}

// ── 加载数据 ──
onMounted(async () => {
  await store.loadEventChain(props.aggregateType, props.aggregateId)
  renderChart()
})

watch(() => store.eventChain, () => {
  renderChart()
}, { deep: true })

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

// ── 暴露刷新方法 ──
function refresh(): void {
  store.loadEventChain(props.aggregateType, props.aggregateId)
}

defineExpose({ refresh })
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.event-chain-container {
  padding: 4px 0;
}
.event-item {
  padding: 2px 0;
}
.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.event-producer {
  font-size: 12px;
  color: #909399;
}
.event-meta {
  font-size: 12px;
  color: #c0c4cc;
  margin-bottom: 2px;
}
.event-data {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}
.data-preview {
  cursor: help;
  border-bottom: 1px dashed #dcdfe6;
}
</style>
