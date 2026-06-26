<template>
  <div class="event-timeline-view">
    <!-- ═══════ 顶部标题 + 选择器 ═══════ -->
    <div class="et-header">
      <h2>📋 事件时间线</h2>
      <div class="et-header-actions">
        <el-select
          v-model="selectedPlanId"
          placeholder="选择 ProductPlan"
          filterable
          clearable
          size="small"
          style="width:280px"
          @change="onPlanChange"
        >
          <el-option
            v-for="p in plans"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          />
        </el-select>
        <el-button size="small" @click="fetchPlans">刷新</el-button>
      </div>
    </div>

    <!-- ═══════ 统计图表区域 ═══════ -->
    <el-row :gutter="16" class="et-charts" v-if="statsLoaded">
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <template #header><span style="font-weight:600">事件类型分布</span></template>
          <div ref="pieChartRef" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <template #header><span style="font-weight:600">近7天趋势</span></template>
          <div ref="lineChartRef" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ═══════ 事件时间线 ═══════ -->
    <el-card v-if="selectedPlanId" shadow="never" class="timeline-card">
      <template #header>
        <div class="timeline-header">
          <span style="font-weight:600">事件记录</span>
          <el-tag type="info" size="small" effect="plain">共 {{ totalEvents }} 条</el-tag>
        </div>
      </template>

      <div v-loading="loading" element-loading-text="加载中...">
        <el-empty v-if="!loading && events.length === 0" description="暂无事件数据" :image-size="60" />

        <el-timeline v-else>
          <el-timeline-item
            v-for="evt in events"
            :key="evt.id"
            :timestamp="formatTime(evt.created_at)"
            placement="top"
            :color="timelineColor(evt.event_type)"
          >
            <div class="event-item">
              <div class="event-top">
                <el-tag :type="eventTagType(evt.event_type)" size="small" effect="dark">
                  {{ evt.event_type }}
                </el-tag>
                <span class="event-summary">{{ evt.payload_summary || evt.event_type }}</span>
              </div>
              <div class="event-meta" v-if="evt.source">
                来源: {{ evt.source }}
              </div>
              <div class="event-actions">
                <el-button
                  link
                  size="small"
                  type="primary"
                  @click="$router.push(`/event-timeline/detail/${selectedPlanId}`)"
                >
                  查看详情
                </el-button>
                <el-button
                  link
                  size="small"
                  type="warning"
                  :loading="replayingId === evt.id"
                  @click="handleReplay(evt)"
                >
                  重放
                </el-button>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="totalPages > 1">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="totalEvents"
            layout="prev, pager, next, total"
            background
            small
            @current-change="fetchTimeline"
          />
        </div>
      </div>
    </el-card>

    <!-- 未选择 plan 时占位 -->
    <el-empty
      v-if="!selectedPlanId"
      description="请先选择一个 ProductPlan"
      :image-size="80"
      style="margin-top:60px"
    />

    <!-- 重放结果弹窗 -->
    <el-dialog v-model="replayDialogVisible" title="重放结果" width="700px" :close-on-click-modal="false">
      <div v-if="replayResult">
        <el-alert
          :title="replayResult.success ? '✅ 重放成功' : '❌ 重放失败'"
          :type="replayResult.success ? 'success' : 'error'"
          show-icon
          :closable="false"
          style="margin-bottom:16px"
        />
        <pre class="replay-result-json">{{ JSON.stringify(replayResult, null, 2) }}</pre>
      </div>
      <div v-else-if="replayLoading" v-loading="replayLoading" style="height:100px" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../../api'
import { initChart, disposeChart, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

// ── Data ──
const plans = ref<any[]>([])
const selectedPlanId = ref<number | string | null>(null)
const events = ref<any[]>([])
const loading = ref(false)
const totalEvents = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const statsLoaded = ref(false)

// replay
const replayingId = ref<number | null>(null)
const replayDialogVisible = ref(false)
const replayLoading = ref(false)
const replayResult = ref<any>(null)

// chart refs
const pieChartRef = ref<HTMLElement>()
const lineChartRef = ref<HTMLElement>()

// computed
const totalPages = ref(0)

// ── Helpers ──
function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function eventTagType(type: string): string {
  const map: Record<string, string> = {
    created: 'success',
    updated: 'primary',
    deleted: 'danger',
    submitted: 'warning',
    approved: 'success',
    rejected: 'danger',
    reverted: 'info',
  }
  return map[type] || 'info'
}

function timelineColor(type: string): string {
  const map: Record<string, string> = {
    created: '#67C23A',
    updated: '#409EFF',
    deleted: '#F56C6C',
    submitted: '#E6A23C',
    approved: '#67C23A',
    rejected: '#F56C6C',
  }
  return map[type] || '#909399'
}

// ── API: 获取 ProductPlan 列表 ──
async function fetchPlans() {
  try {
    const res = await api.get('/product-plans')
    plans.value = Array.isArray(res.data) ? res.data : res.data?.data || []
  } catch {
    plans.value = []
  }
}

// ── API: 获取事件时间线 ──
async function fetchTimeline() {
  if (!selectedPlanId.value) return
  loading.value = true
  try {
    const res = await api.get(`/api/v2/events/timeline/${selectedPlanId.value}`, {
      params: { page: currentPage.value, page_size: pageSize.value },
    })
    const data = res.data
    events.value = data?.items || data?.data || data?.records || []
    totalEvents.value = data?.total || events.value.length
    totalPages.value = data?.pages || Math.ceil(totalEvents.value / pageSize.value)
  } catch {
    events.value = []
    totalEvents.value = 0
    totalPages.value = 0
  } finally {
    loading.value = false
  }
}

// ── API: 获取统计数据（饼图 + 折线图） ──
async function fetchStats() {
  statsLoaded.value = false
  try {
    const res = await api.get('/api/v2/events/stats', {
      params: { plan_id: selectedPlanId.value || undefined },
    })
    const data = res.data
    await nextTick()
    renderPieChart(data?.type_distribution || data?.pie || [])
    renderLineChart(data?.recent_trend || data?.trend || [])
    statsLoaded.value = true
  } catch {
    statsLoaded.value = false
  }
}

// ── Charts ──
function renderPieChart(data: any[]) {
  if (!pieChartRef.value) return
  const chartData = data.map((d: any) => ({
    name: d.name || d.event_type || d.type,
    value: d.value || d.count || 0,
  }))
  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 8, itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 12 } },
    color: getChartColors(),
    series: [{
      type: 'pie',
      radius: ['30%', '55%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
      },
      data: chartData,
    }],
  }
  initChart(pieChartRef.value, option)
}

function renderLineChart(data: any[]) {
  if (!lineChartRef.value) return
  const dates = data.map((d: any) => d.date || d.day || d.name)
  const values = data.map((d: any) => d.count || d.value || 0)
  const option: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: 'value', minInterval: 1 },
    color: getChartColors(),
    series: [{
      type: 'line',
      smooth: true,
      data: values,
      areaStyle: {
        opacity: 0.15,
      },
      markLine: {
        silent: true,
        lineStyle: { type: 'dashed' },
        data: [{ type: 'average', name: '平均值' }],
      },
    }],
  }
  initChart(lineChartRef.value, option)
}

// ── Events ──
async function onPlanChange() {
  currentPage.value = 1
  events.value = []
  if (!selectedPlanId.value) return
  await Promise.all([fetchTimeline(), fetchStats()])
}

async function handleReplay(evt: any) {
  replayingId.value = evt.id
  replayDialogVisible.value = true
  replayLoading.value = true
  replayResult.value = null
  try {
    const res = await api.post(`/api/v2/events/replay/${selectedPlanId.value}`)
    replayResult.value = res.data
  } catch (e: unknown) {
    const _err = e && typeof e === 'object' && 'response' in e ? (e as {response?: {data?: {detail?: string}}}).response?.data?.detail : null
    replayResult.value = { success: false, error: _err || '重放请求失败' }
  } finally {
    replayingId.value = null
    replayLoading.value = false
  }
}

// ── Lifecycle ──
onMounted(() => {
  fetchPlans()
})

onUnmounted(() => {
  if (pieChartRef.value) disposeChart(pieChartRef.value)
  if (lineChartRef.value) disposeChart(lineChartRef.value)
})
</script>

<style scoped>
.event-timeline-view {
  padding: 0 4px;
}
.et-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.et-header h2 {
  margin: 0;
  font-size: 18px;
}
.et-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.et-charts {
  margin-bottom: 16px;
}
.chart-card {
  border-radius: 8px;
}
.chart-box {
  width: 100%;
  height: 220px;
}
.timeline-card {
  border-radius: 8px;
}
.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.event-item {
  padding: 4px 0;
}
.event-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.event-summary {
  font-size: 13px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-meta {
  font-size: 12px;
  color: #909399;
  margin: 2px 0;
}
.event-actions {
  margin-top: 4px;
  display: flex;
  gap: 8px;
}
.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
.replay-result-json {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
