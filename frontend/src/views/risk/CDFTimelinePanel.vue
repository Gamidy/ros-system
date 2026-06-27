<template>
  <div class="cdf-panel">
    <!-- 概览统计 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="(stat, idx) in overviewStats" :key="idx">
        <el-card shadow="never" class="stat-card" :style="{ borderLeftColor: stat.color }">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 各类型认证数量统计 -->
    <el-card shadow="never" class="chart-card" style="margin-bottom:16px">
      <template #header><span style="font-weight:600">各类型认证数量</span></template>
      <div ref="barChartRef" class="chart-box" />
    </el-card>

    <!-- 计划列表 -->
    <el-card shadow="never" class="table-card">
      <el-table
        :data="planList"
        stripe
        style="width:100%"
        v-loading="loading"
        @expand-change="onExpandChange"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row._loading_timeline" v-loading="true" style="height:60px" />
            <el-timeline v-else-if="(row._timeline_items ?? []).length">
              <el-timeline-item
                v-for="(item, tidx) in row._timeline_items"
                :key="tidx"
                :timestamp="item.date || item.phase || ''"
                placement="top"
                :color="timelineColor(item.status)"
              >
                <div style="display:flex;align-items:center;gap:8px">
                  <el-tag :type="timelineTagType(item.status)" size="small" effect="dark">
                    {{ item.cert_type || item.type || item.phase }}
                  </el-tag>
                  <span style="font-size:13px">{{ item.description || item.name || item.detail }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无认证时间线" :image-size="40" />
          </template>
        </el-table-column>

        <el-table-column prop="plan_name" label="计划名称" min-width="140" />
        <el-table-column prop="target_market" label="目标市场" width="120" />
        <el-table-column prop="required_cert_count" label="所需认证数" width="110" align="center" />
        <el-table-column prop="mandatory_cert_count" label="强制认证数" width="110" align="center" />
        <el-table-column prop="estimated_days" label="预估天数" width="100" align="center" />
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_level)" size="small" effect="dark">
              {{ row.risk_level ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && planList.length === 0" description="暂无认证数据" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../../api'
import { initChart, disposeChart, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'
import type { TableRow, ChartDataPoint } from '@/types/common'

interface CertType {
  name?: string
  type?: string
  cert_type?: string
  count?: number
}

interface TimelineItem {
  date?: string
  phase?: string
  status?: string
  cert_type?: string
  type?: string
  name?: string
  description?: string
  detail?: string
  sort_order?: number
  phase_order?: number
}

interface PlanItem extends TableRow {
  plan_id?: number | string
  plan_name?: string
  target_market?: string
  required_cert_count?: number
  mandatory_cert_count?: number
  estimated_days?: number
  risk_level?: string
  cert_types?: CertType[]
  certifications?: CertType[]
  _timeline_items?: TimelineItem[]
  _loading_timeline?: boolean
}

const loading = ref(false)
const planList = ref<PlanItem[]>([])
const overviewData = ref<Record<string, unknown>>({})
const barChartRef = ref<HTMLElement>()

const overviewStats = computed(() => [
  { label: '总计划数', value: overviewData.value?.total_plans ?? overviewData.value?.total ?? '-', color: '#409eff' },
  { label: '强制认证总数', value: overviewData.value?.total_mandatory ?? overviewData.value?.mandatory_total ?? '-', color: '#e6a23c' },
  { label: '平均预估天数', value: overviewData.value?.avg_days ?? overviewData.value?.average_days ?? '-', color: '#67c23a' },
  { label: '高风险计划数', value: overviewData.value?.high_risk_count ?? '-', color: '#f56c6c' },
])

function riskTagType(level?: string): string {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success',
    critical: 'danger',
  }
  return map[level?.toLowerCase() ?? ''] || 'info'
}

function timelineColor(status?: string): string {
  const map: Record<string, string> = {
    completed: '#67C23A',
    in_progress: '#409EFF',
    pending: '#909399',
    delayed: '#E6A23C',
    failed: '#F56C6C',
  }
  return map[status ?? ''] || '#909399'
}

function timelineTagType(status?: string): string {
  const map: Record<string, string> = {
    completed: 'success',
    in_progress: 'primary',
    pending: 'info',
    delayed: 'warning',
    failed: 'danger',
  }
  return map[status ?? ''] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/api/v2/dashboard/cdf-summary')
    const data = res.data as Record<string, unknown>
    overviewData.value = (data?.overview || data?.summary || data || {}) as Record<string, unknown>
    const items = (data?.items || data?.data || data?.records || data?.plans || []) as PlanItem[]
    planList.value = Array.isArray(items) ? items : Array.isArray(data) ? (data as unknown as PlanItem[]) : []
    planList.value.forEach((p: PlanItem) => {
      p._timeline_items = []
      p._loading_timeline = false
    })
    await nextTick()
    renderBarChart(data)
  } catch {
    planList.value = []
    overviewData.value = {}
  } finally {
    loading.value = false
  }
}

function renderBarChart(data: Record<string, unknown>) {
  if (!barChartRef.value) return
  const certTypes = (data?.cert_type_distribution || data?.type_distribution || data?.distribution || []) as ChartDataPoint[]
  let chartData: ChartDataPoint[]
  if (Array.isArray(certTypes) && certTypes.length > 0) {
    chartData = certTypes
  } else {
    // 从各计划聚合
    const agg: Record<string, number> = {}
    planList.value.forEach((p: PlanItem) => {
      const types = p.cert_types || p.certifications || []
      ;(Array.isArray(types) ? types : []).forEach((ct: CertType) => {
        const name = ct.name || ct.type || ct.cert_type
        if (name) agg[name] = (agg[name] || 0) + (ct.count ?? 1)
      })
    })
    chartData = Object.entries(agg).map(([name, count]) => ({ name, value: count }))
    if (chartData.length === 0) {
      chartData = [
        { name: '强制认证', value: (data?.mandatory_count as number) ?? (overviewData.value?.total_mandatory as number) ?? 0 },
        { name: '自愿认证', value: (data?.voluntary_count as number) ?? 0 },
      ].filter(d => d.value > 0)
    }
  }
  const option: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: chartData.map((d: ChartDataPoint) => (d.name ?? d.type ?? '') as string),
      axisLabel: { fontSize: 11, rotate: chartData.length > 5 ? 30 : 0 },
    },
    yAxis: { type: 'value', minInterval: 1, name: '数量' },
    color: getChartColors(),
    series: [{
      type: 'bar',
      data: chartData.map((d: ChartDataPoint) => d.value ?? d.count ?? 0),
      barWidth: '50%',
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  }
  initChart(barChartRef.value, option)
}

async function onExpandChange(row: PlanItem, expandedRows: TableRow[]) {
  const expanded = expandedRows.includes(row)
  if (!expanded) return
  if (row._timeline_items?.length > 0) return
  row._loading_timeline = true
  try {
    const res = await api.get(`/api/v2/dashboard/cdf-detail/${row.plan_id ?? row.id}`)
    const data = res.data as Record<string, unknown>
    const items = (data?.timeline || data?.items || data?.data || data?.stages || data?.certifications || []) as TimelineItem[]
    row._timeline_items = Array.isArray(items)
      ? items.sort((a: TimelineItem, b: TimelineItem) => (a.sort_order ?? a.phase_order ?? 0) - (b.sort_order ?? b.phase_order ?? 0))
      : []
  } catch {
    row._timeline_items = []
  } finally {
    row._loading_timeline = false
  }
}

onMounted(fetchData)

onUnmounted(() => {
  if (barChartRef.value) disposeChart(barChartRef.value)
})
</script>

<style scoped>
.cdf-panel {
  min-height: 200px;
}
.stat-card {
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid #409eff;
  text-align: center;
}
.stat-value {
  font-size: 26px;
  font-weight: bold;
  color: #303133;
}
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: #909399;
}
.chart-card {
  border-radius: 8px;
}
.chart-box {
  width: 100%;
  height: 220px;
}
.table-card {
  border-radius: 8px;
}
</style>
