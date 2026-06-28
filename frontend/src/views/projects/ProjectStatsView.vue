<template>
  <div class="stats-page">
    <div class="page-header">
      <span class="page-title">📊 项目统计看板</span>
    </div>

    <!-- KPI 卡片 -->
    <div class="kpi-grid">
      <el-card shadow="never" class="kpi-card total">
        <div class="kpi-value">{{ stats.total_projects || 0 }}</div>
        <div class="kpi-label">总项目数</div>
      </el-card>
      <el-card shadow="never" class="kpi-card running">
        <div class="kpi-value">{{ stats.by_status?.running || 0 }}</div>
        <div class="kpi-label">进行中</div>
      </el-card>
      <el-card shadow="never" class="kpi-card overdue">
        <div class="kpi-value">{{ stats.overdue_count || 0 }}</div>
        <div class="kpi-label">已超期</div>
      </el-card>
      <el-card shadow="never" class="kpi-card risk">
        <div class="kpi-value">{{ stats.high_risk_count || 0 }}</div>
        <div class="kpi-label">A级高风险</div>
      </el-card>
      <el-card shadow="never" class="kpi-card gate">
        <div class="kpi-value">{{ stats.gate_progress?.rate || 0 }}%</div>
        <div class="kpi-label">Gate通过率</div>
      </el-card>
    </div>

    <!-- 双图表行 -->
    <div class="chart-row">
      <el-card shadow="never" class="chart-card">
        <template #header><span class="card-title">项目状态分布</span></template>
        <div ref="statusChartRef" class="chart" />
      </el-card>
      <el-card shadow="never" class="chart-card">
        <template #header><span class="card-title">项目等级分布</span></template>
        <div ref="classChartRef" class="chart" />
      </el-card>
    </div>

    <!-- 来源分布 + 健康概览 -->
    <div class="chart-row">
      <el-card shadow="never" class="chart-card">
        <template #header><span class="card-title">来源分类</span></template>
        <div ref="sourceChartRef" class="chart" />
      </el-card>
      <el-card shadow="never" class="chart-card">
        <template #header><span class="card-title">Gate通过率</span></template>
        <div class="gate-progress-center">
          <el-progress type="dashboard" :percentage="stats.gate_progress?.rate || 0" :stroke-width="10" color="#409eff">
            <template #default>{{ stats.gate_progress?.rate || 0 }}%</template>
          </el-progress>
          <div class="gate-detail">
            <span>已通过: {{ stats.gate_progress?.passed || 0 }}</span>
            <span>总节点: {{ stats.gate_progress?.total || 0 }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 近期项目 -->
    <el-card shadow="never" class="list-card">
      <template #header><span class="card-title">近期到期项目</span></template>
      <el-table :data="upcomingProjects" stripe size="small" v-if="upcomingProjects.length > 0" style="width:100%">
        <el-table-column prop="code" label="编号" width="90" />
        <el-table-column prop="name" label="项目名称" min-width="150" />
        <el-table-column label="等级" width="60">
          <template #default="{ row }"><el-tag :type="classTag(row.project_class)" size="small">{{ row.project_class }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }"><el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="target_end_date" label="截止日期" width="110" />
        <el-table-column label="剩余" width="80">
          <template #default="{ row }">
            <span :style="{ color: daysLeft(row.target_end_date) < 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
              {{ daysLeft(row.target_end_date) >= 0 ? daysLeft(row.target_end_date) + '天' : '已超期' + Math.abs(daysLeft(row.target_end_date)) + '天' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text size="small" @click="$router.push('/projects/' + row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无项目数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { initChart, disposeChart, getChartColors } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const stats = ref<any>({})
const upcomingProjects = ref<any[]>([])
const statusChartRef = ref<HTMLElement | null>(null)
const classChartRef = ref<HTMLElement | null>(null)
const sourceChartRef = ref<HTMLElement | null>(null)

function classTag(c: string): string { return ({ T: 'danger', A: 'warning', B: 'success', C: 'info' })[c] || 'info' }
function statusTag(s: string): string { return ({ planning: 'info', running: 'primary', completed: 'success', paused: 'warning' })[s] || 'info' }
function statusLabel(s: string): string { return ({ planning: '规划中', running: '进行中', completed: '已完成', paused: '已暂停' })[s] || s }
function daysLeft(d: string | null): number {
  if (!d) return 999
  return Math.ceil((new Date(d).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
}

const STATUS_LABELS: Record<string, string> = {
  planning: '规划中', running: '进行中', completed: '已完成', paused: '已暂停',
}
const SOURCE_LABELS: Record<string, string> = {
  P01: '新平台', P02: '衍生开发', P03: '降本优化', P04: '性能提升',
  P05: '品质改善', P06: '法规合规', P07: '技术预研',
}

function renderStatusChart() {
  if (!statusChartRef.value || !stats.value?.by_status) return
  const data = Object.entries(stats.value.by_status).map(([k, v]) => ({
    name: STATUS_LABELS[k] || k, value: v as number,
  }))
  const colors = getChartColors()
  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['35%', '60%'], center: ['50%', '50%'],
      data: data.map((d, i) => ({ ...d, itemStyle: { color: colors[i % colors.length] } })),
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.1)' } },
    }],
  }
  initChart(statusChartRef.value, option)
}

function renderClassChart() {
  if (!classChartRef.value || !stats.value?.by_class) return
  const classes = ['T', 'A', 'B', 'C']
  const data = classes.map(c => ({
    name: c + '级', value: (stats.value.by_class as Record<string, number>)[c] || 0,
  }))
  const colors = ['#f56c6c', '#e6a23c', '#67c23a', '#909399']
  const option: EChartsOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(d => d.name) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'bar', data: data.map((d, i) => ({ value: d.value, itemStyle: { color: colors[i] } })),
      barWidth: 40, label: { show: true, position: 'top' },
    }],
  }
  initChart(classChartRef.value, option)
}

function renderSourceChart() {
  if (!sourceChartRef.value || !stats.value?.by_source) return
  const data = Object.entries(stats.value.by_source).map(([k, v]) => ({
    name: SOURCE_LABELS[k] || k, value: v as number,
  }))
  if (data.length === 0) return
  const colors = getChartColors()
  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{
      type: 'pie', radius: ['30%', '55%'],
      data: data.map((d, i) => ({ ...d, itemStyle: { color: colors[i % colors.length] } })),
      label: { formatter: '{b}\n{c}个', fontSize: 10 },
    }],
  }
  initChart(sourceChartRef.value, option)
}

async function fetchStats() {
  try {
    const [overviewRes, projectsRes] = await Promise.all([
      api.get('/projects/dashboard/overview'),
      api.get('/projects', { params: { limit: 50 } }),
    ])
    stats.value = overviewRes.data || {}

    // Filter upcoming projects (running/planning with end date, sorted)
    const all = (projectsRes.data || []) as any[]
    upcomingProjects.value = all
      .filter((p: any) => !p.is_deleted && p.target_end_date && ['running', 'planning'].includes(p.status))
      .sort((a: any, b: any) => new Date(a.target_end_date).getTime() - new Date(b.target_end_date).getTime())
      .slice(0, 20)

    await nextTick()
    renderStatusChart()
    renderClassChart()
    renderSourceChart()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载统计数据失败')
  }
}

onMounted(fetchStats)
onUnmounted(() => {
  [statusChartRef, classChartRef, sourceChartRef].forEach(ref => {
    if (ref.value) disposeChart(ref.value)
  })
})
</script>

<style scoped>
.stats-page { padding: 16px; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: #303133; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { text-align: center; }
.kpi-card :deep(.el-card__body) { padding: 18px 12px; }
.kpi-value { font-size: 28px; font-weight: 700; line-height: 1.2; margin-bottom: 4px; }
.kpi-label { font-size: 12px; color: #909399; }
.total .kpi-value { color: #409eff; }
.running .kpi-value { color: #67c23a; }
.overdue .kpi-value { color: #f56c6c; }
.risk .kpi-value { color: #e6a23c; }
.gate .kpi-value { color: #409eff; }

.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.chart-card .card-title { font-weight: 600; }
.chart { width: 100%; height: 280px; }

.gate-progress-center { display: flex; flex-direction: column; align-items: center; padding: 20px; }
.gate-detail { display: flex; gap: 20px; margin-top: 12px; font-size: 12px; color: #909399; }

.list-card { margin-bottom: 16px; }
.list-card .card-title { font-weight: 600; }

@media (max-width: 900px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
  .chart-row { grid-template-columns: 1fr; }
}
</style>
