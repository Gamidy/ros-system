<template>
  <div class="mrc-panel">
    <!-- 雷达图 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header><span style="font-weight:600">四维就绪度雷达</span></template>
          <div ref="radarChartRef" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header><span style="font-weight:600">就绪层级分布</span></template>
          <div ref="barChartRef" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 列表 -->
    <el-card shadow="never" class="table-card" style="margin-top:16px">
      <el-table
        :data="planList"
        stripe
        style="width:100%"
        v-loading="loading"
        @expand-change="onExpandChange"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="row._loading_gap" v-loading="true" style="height:60px" />
            <div v-else-if="(row._gap_items ?? []).length" style="padding:8px 0">
              <el-tag v-for="g in row._gap_items" :key="g.name"
                :type="gapTagType(g.severity)"
                size="small"
                style="margin:2px 4px"
              >
                {{ g.name || g.dimension }}: {{ g.description || g.detail || g.gap }}
              </el-tag>
            </div>
            <el-empty v-else description="暂无差距项" :image-size="40" />
          </template>
        </el-table-column>

        <el-table-column prop="plan_name" label="计划名称" min-width="160" />
        <el-table-column label="总评分" width="160" align="center">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round((row.total_score ?? row.score ?? 0) * 100)"
              :status="progressStatus(row.total_score ?? row.score ?? 0)"
              :stroke-width="16"
              :text-inside="true"
              style="width:120px"
            />
          </template>
        </el-table-column>
        <el-table-column label="就绪等级" width="100">
          <template #default="{ row }">
            <el-tag :type="readinessTagType(row.readiness_level)" size="small" effect="dark">
              {{ row.readiness_level ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="gap_count" label="差距项数" width="90" align="center" />
      </el-table>
      <el-empty v-if="!loading && planList.length === 0" description="暂无制造就绪度数据" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../../api'
import { initChart, disposeChart } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const loading = ref(false)
const planList = ref<any[]>([])
const radarChartRef = ref<HTMLElement>()
const barChartRef = ref<HTMLElement>()

function readinessTagType(level: string): string {
  const map: Record<string, string> = {
    ready: 'success',
    partial: 'warning',
    not_ready: 'danger',
    L1: 'info',
    L2: 'warning',
    L3: 'success',
    L4: 'primary',
    L5: 'success',
  }
  return map[level] || 'info'
}

function progressStatus(score: number): string {
  if (score >= 0.8) return 'success'
  if (score >= 0.5) return 'warning'
  return 'exception'
}

function gapTagType(severity: string): string {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'info',
    critical: 'danger',
  }
  return map[severity?.toLowerCase()] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/api/v2/dashboard/mrc-summary')
    const data = res.data
    const items = data?.items || data?.data || data?.records || []
    planList.value = Array.isArray(items) ? items : Array.isArray(data) ? data : []
    planList.value.forEach((p: any) => {
      p._gap_items = []
      p._loading_gap = false
    })
    await nextTick()
    renderRadarChart(data)
    renderBarChart(data)
  } catch {
    planList.value = []
  } finally {
    loading.value = false
  }
}

// 四维雷达图
function renderRadarChart(data: any) {
  if (!radarChartRef.value) return

  // 尝试从整体数据或首个计划取维度值
  const dimensions = data?.dimensions || data?.radar_dimensions || []
  let radarIndicators: any[] = []
  let seriesData: any[] = []

  if (dimensions.length > 0) {
    radarIndicators = dimensions.map((d: any) => ({
      name: d.name,
      max: d.max ?? 100,
    }))
    seriesData = [{
      value: dimensions.map((d: any) => d.value ?? d.score ?? 0),
      name: data?.plan_name || '整体就绪度',
    }]
  } else if (planList.value.length > 0) {
    // 从各计划维度聚合
    radarIndicators = [
      { name: '设计就绪度', max: 100 },
      { name: '工艺就绪度', max: 100 },
      { name: '模具就绪度', max: 100 },
      { name: '供应就绪度', max: 100 },
    ]
    seriesData = planList.value.slice(0, 5).map((p: any) => ({
      value: [
        (p.design_score ?? p.design ?? 0) * 100,
        (p.process_score ?? p.process ?? 0) * 100,
        (p.tooling_score ?? p.tooling ?? 0) * 100,
        (p.supply_score ?? p.supply ?? 0) * 100,
      ],
      name: p.plan_name,
    }))
  } else {
    radarIndicators = [
      { name: '设计就绪度', max: 100 },
      { name: '工艺就绪度', max: 100 },
      { name: '模具就绪度', max: 100 },
      { name: '供应就绪度', max: 100 },
    ]
    seriesData = [{ value: [0, 0, 0, 0], name: '暂无数据' }]
  }

  const option: EChartsOption = {
    tooltip: { trigger: 'item' },
    legend: seriesData.length > 1 ? { bottom: 4, textStyle: { fontSize: 11 } } : undefined,
    radar: {
      indicator: radarIndicators,
      radius: '60%',
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#606266', fontSize: 12 },
    },
    series: [{
      type: 'radar',
      data: seriesData,
      areaStyle: { opacity: 0.15 },
      lineStyle: { width: 2 },
      itemStyle: { opacity: 0.8 },
    }],
  }
  initChart(radarChartRef.value, option)
}

// 就绪层级分布柱状图
function renderBarChart(data: any) {
  if (!barChartRef.value) return
  const levels = data?.level_distribution || data?.readiness_distribution || []
  let chartData: any[]
  if (Array.isArray(levels) && levels.length > 0) {
    chartData = levels
  } else {
    chartData = planList.value.map((p: any) => ({
      name: p.plan_name,
      value: (p.total_score ?? p.score ?? 0) * 100,
    }))
  }
  const option: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: chartData.map((d: any) => d.name || d.plan_name || d.level || ''),
      axisLabel: { fontSize: 11, rotate: chartData.length > 4 ? 30 : 0 },
    },
    yAxis: { type: 'value', min: 0, max: 100, name: '就绪度' },
    color: ['#409EFF'],
    series: [{
      type: 'bar',
      data: chartData.map((d: any) => d.value ?? d.count ?? d.score ?? 0),
      barWidth: '40%',
      itemStyle: { borderRadius: [4, 4, 0, 0] },
    }],
  }
  initChart(barChartRef.value, option)
}

async function onExpandChange(row: any, expandedRows: any[]) {
  const expanded = expandedRows.includes(row)
  if (!expanded) return
  if (row._gap_items?.length > 0) return
  row._loading_gap = true
  try {
    const res = await api.get(`/api/v2/dashboard/mrc-detail/${row.plan_id ?? row.id}`)
    const data = res.data
    row._gap_items = data?.gaps || data?.gap_items || data?.items || data?.data || []
  } catch {
    row._gap_items = []
  } finally {
    row._loading_gap = false
  }
}

onMounted(fetchData)

onUnmounted(() => {
  if (radarChartRef.value) disposeChart(radarChartRef.value)
  if (barChartRef.value) disposeChart(barChartRef.value)
})
</script>

<style scoped>
.mrc-panel {
  min-height: 200px;
}
.chart-card {
  border-radius: 8px;
  height: 100%;
}
.chart-box {
  width: 100%;
  height: 260px;
}
.table-card {
  border-radius: 8px;
}
</style>
