<template>
  <div class="gantt-page">
    <!-- 项目头部 -->
    <div class="gantt-header" v-if="project">
      <div class="header-left">
        <el-button text @click="$router.push('/projects')">← 返回项目列表</el-button>
        <el-divider direction="vertical" />
        <span class="header-title">{{ project.code }} {{ project.name }}</span>
        <el-tag :type="classTag(project.project_class)" size="small">{{ project.project_class }}级</el-tag>
        <el-tag :type="statusTag(project.status)" size="small">{{ statusLabel(project.status) }}</el-tag>
      </div>
      <div class="header-right">
        <span class="date-info" v-if="project.start_date">开始: {{ project.start_date }}</span>
        <span class="date-info" v-if="project.target_end_date">截止: {{ project.target_end_date }}</span>
      </div>
    </div>

    <!-- 图例 -->
    <el-card shadow="never" class="legend-card">
      <div class="legend-row">
        <span class="legend-title">图例:</span>
        <span class="legend-item"><span class="dot dot-todo"></span>待办</span>
        <span class="legend-item"><span class="dot dot-progress"></span>进行中</span>
        <span class="legend-item"><span class="dot dot-done"></span>已完成</span>
        <span class="legend-item"><span class="dot dot-blocked"></span>阻塞</span>
        <span class="legend-item"><span class="dot dot-milestone"></span>里程碑</span>
        <span class="legend-item"><span class="dot dot-milestone-delayed"></span>里程碑延期</span>
        <span class="legend-item ml-4"><span class="dot dot-gate"></span>Gate节点</span>
      </div>
    </el-card>

    <!-- ECharts 甘特图 -->
    <el-card shadow="never" class="chart-card">
      <div ref="chartRef" class="gantt-chart" />
    </el-card>

    <!-- 统计 KPI -->
    <el-card shadow="never" class="stats-card" v-if="ganttData">
      <div class="kpi-row">
        <el-statistic title="总任务" :value="ganttData.tasks.length" />
        <el-statistic title="已完成" :value="doneCount" />
        <el-statistic title="进行中" :value="progressCount" />
        <el-statistic title="待办" :value="todoCount" />
        <el-statistic title="里程碑" :value="ganttData.milestones.length" />
        <el-statistic title="Gate节点" :value="ganttData.gates.length" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { initChart, disposeChart } from '../../utils/chart'
import type { EChartsOption } from 'echarts'

const route = useRoute()
const pid = computed(() => Number(route.params.id))

// ── Types ──
interface ProjectInfo {
  id: number; code: string; name: string;
  project_class: string; status: string;
  start_date: string | null; target_end_date: string | null;
}
interface GanttTask {
  id: number; title: string; assignee: string | null;
  status: string; priority: string;
  start_date: string | null; end_date: string | null;
  actual_date: string | null; milestone_id: number | null;
}
interface GanttMilestone {
  id: number; name: string; status: string;
  planned_date: string | null; actual_date: string | null;
  gate_code: string | null;
}
interface GanttGate {
  code: string; name: string; status: string | null;
  seq: number; planned_date: string | null; actual_date: string | null;
}
interface GanttDep {
  task_id: number; depends_on_task_id: number; dep_type: string;
}
interface GanttData {
  project: ProjectInfo; tasks: GanttTask[];
  milestones: GanttMilestone[]; gates: GanttGate[];
  date_range: { start: string | null; end: string | null };
  dependencies: GanttDep[];
}
interface MilestoneScatterItem {
  value: number[];
  name: string;
  itemStyle: Record<string, string>;
  symbol: string;
  symbolSize: number;
  _milestone: GanttMilestone;
}
interface GateScatterItem {
  value: number[];
  name: string;
  itemStyle: Record<string, string>;
  symbol: string;
  symbolSize: number;
  _gate: GanttGate;
}
interface TaskBarItem {
  value: number[];
  itemStyle: Record<string, string>;
}

// ── State ──
const loading = ref(true)
const chartRef = ref<HTMLElement | null>(null)
const project = ref<ProjectInfo | null>(null)
const ganttData = ref<GanttData | null>(null)

const doneCount = computed(() => ganttData.value?.tasks.filter((t) => t.status === 'done').length || 0)
const progressCount = computed(() => ganttData.value?.tasks.filter((t) => t.status === 'in_progress').length || 0)
const todoCount = computed(() => ganttData.value?.tasks.filter((t) => t.status === 'todo' || t.status === 'blocked').length || 0)

function classTag(c: string | undefined): string {
  return ({ T: 'danger', A: 'warning', B: 'success', C: 'info' })[c || ''] || 'info'
}
function statusTag(s: string | undefined): string {
  return ({ planning: 'info', running: 'primary', completed: 'success', paused: 'warning' })[s || ''] || 'info'
}
function statusLabel(s: string | undefined): string {
  return ({ planning: '规划中', running: '进行中', completed: '已完成', paused: '已暂停' })[s || ''] || s || '未知'
}

const STATUS_COLORS: Record<string, string> = {
  todo: '#909399',
  in_progress: '#409eff',
  done: '#67c23a',
  blocked: '#f56c6c',
}

// ── Fetch data ──
async function fetchGantt() {
  loading.value = true
  try {
    const [gRes] = await Promise.all([
      api.get(`/projects/${pid.value}/gantt`),
    ])
    ganttData.value = gRes.data as GanttData
    project.value = (gRes.data as GanttData).project
    await nextTick()
    renderChart()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : (e && typeof e === 'object' && 'response' in e && (e as any).response?.data?.detail) || '加载Gantt数据失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

// ── Render Gantt Chart ──
function renderChart() {
  if (!chartRef.value || !ganttData.value) return

  const data = ganttData.value
  const tasks = data.tasks || []
  const milestones = data.milestones || []
  const gates = data.gates || []

  // Parse date range
  const minDate = new Date()
  const maxDate = new Date()

  tasks.forEach((t) => {
    if (t.start_date) {
      const d = new Date(t.start_date)
      if (d < minDate) minDate.setTime(d.getTime())
      if (d > maxDate) maxDate.setTime(d.getTime())
    }
    if (t.end_date) {
      const d = new Date(t.end_date)
      if (d < minDate) minDate.setTime(d.getTime())
      if (d > maxDate) maxDate.setTime(d.getTime())
    }
  })
  milestones.forEach((m) => {
    if (m.planned_date) {
      const d = new Date(m.planned_date)
      if (d < minDate) minDate.setTime(d.getTime())
      if (d > maxDate) maxDate.setTime(d.getTime())
    }
  })
  gates.forEach((g) => {
    if (g.planned_date) {
      const d = new Date(g.planned_date)
      if (d < minDate) minDate.setTime(d.getTime())
      if (d > maxDate) maxDate.setTime(d.getTime())
    }
  })

  minDate.setDate(minDate.getDate() - 14)
  maxDate.setDate(maxDate.getDate() + 14)

  // Tasks as horizontal bars
  const taskSeries: TaskBarItem[] = []

  tasks.forEach((t, idx) => {
    const start = t.start_date ? new Date(t.start_date).getTime() : minDate.getTime()
    const end = t.end_date ? new Date(t.end_date).getTime() : start + 7 * 24 * 60 * 60 * 1000

    taskSeries.push({
      value: [idx, start, end],
      itemStyle: { color: STATUS_COLORS[t.status] || '#909399' },
    })
  })

  // Milestones as scatter
  const milestoneData: (MilestoneScatterItem | null)[] = milestones.map((m) => {
    const date = m.planned_date || m.actual_date
    if (!date) return null
    const d = new Date(date).getTime()
    return {
      value: [tasks.length + 1, d],
      name: m.name,
      itemStyle: {
        color: m.status === 'achieved' ? '#67c23a' : m.status === 'delayed' ? '#f56c6c' : '#e6a23c',
      },
      symbol: 'diamond',
      symbolSize: m.status === 'achieved' ? 18 : 14,
      _milestone: m,
    }
  }).filter(Boolean) as MilestoneScatterItem[]

  // Gates as scatter
  const gateData: (GateScatterItem | null)[] = gates.map((g) => {
    const date = g.actual_date || g.planned_date
    if (!date) return null
    return {
      value: [tasks.length + 2, new Date(date).getTime()],
      name: `${g.code} ${g.name}`,
      itemStyle: {
        color: g.status === 'passed' ? '#67c23a' : g.status === 'failed' ? '#f56c6c' : '#909399',
      },
      symbol: 'rect',
      symbolSize: g.status === 'passed' ? 14 : 10,
      _gate: g,
    }
  }).filter(Boolean) as GateScatterItem[]

  const categories = [
    ...tasks.map((t) => t.title),
    '里程碑',
    'Gate节点',
  ]

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const p = params as any
        if (!p) return ''
        if (p.seriesIndex === 0) {
          const t = tasks[p.dataIndex] as GanttTask | undefined
          if (!t) return ''
          return `<b>${t.title}</b><br/>
            负责人: ${t.assignee || '-'}<br/>
            状态: ${statusLabel(t.status)}<br/>
            优先级: ${t.priority}<br/>
            开始: ${t.start_date || '-'}<br/>
            截止: ${t.end_date || '-'}`
        } else if (p.seriesIndex === 1) {
          const mData = p.data?._milestone as GanttMilestone | undefined
          if (!mData) return ''
          return `<b>🏁 ${mData.name}</b><br/>
            状态: ${(mData.status === 'achieved' ? '已达成' : mData.status === 'delayed' ? '已延期' : '待定')}<br/>
            计划: ${mData.planned_date || '-'}<br/>
            实际: ${mData.actual_date || '-'}`
        } else if (p.seriesIndex === 2) {
          const gData = p.data?._gate as GanttGate | undefined
          if (!gData) return ''
          return `<b>🚪 ${gData.code} ${gData.name}</b><br/>
            状态: ${(gData.status === 'passed' ? '通过' : gData.status === 'failed' ? '失败' : gData.status === 'skipped' ? '跳过' : '待定')}<br/>
            计划: ${gData.planned_date || '-'}<br/>
            实际: ${gData.actual_date || '-'}`
        }
        return ''
      },
      backgroundColor: 'rgba(255,255,255,0.9)',
      borderWidth: 0,
      extraCssText: 'backdrop-filter: blur(8px); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.08);',
    },
    grid: {
      left: 180,
      right: 40,
      top: 20,
      bottom: 30,
    },
    xAxis: {
      type: 'time',
      min: minDate.getTime(),
      max: maxDate.getTime(),
      axisLabel: {
        formatter: (v: number) => {
          const d = new Date(v)
          return `${d.getMonth() + 1}/${d.getDate()}`
        },
      },
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#f0f0f0' } },
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: { fontSize: 12, overflow: 'truncate', width: 160 },
      splitLine: { show: true, lineStyle: { color: '#f5f5f5' } },
    },
    series: [
      {
        type: 'bar',
        name: '任务',
        data: taskSeries,
        barWidth: 16,
        encode: { x: [1, 2], y: 0 },
        itemStyle: { borderRadius: [4, 4, 4, 4] as any },
        markLine: {
          silent: true,
          symbol: 'none',
          data: [
            {
              xAxis: new Date().getTime(),
              label: {
                formatter: '今天',
                color: '#f56c6c',
                fontSize: 11,
                position: 'start',
              },
              lineStyle: { color: '#f56c6c', type: 'dashed', width: 1 },
            },
          ],
        },
      },
      {
        type: 'scatter',
        name: '里程碑',
        data: milestoneData,
        symbol: 'diamond',
        symbolSize: 16,
        encode: { x: 1, y: 0 },
        label: {
          show: true,
          formatter: '{b}',
          position: 'right',
          fontSize: 11,
          color: '#606266',
        },
      },
      {
        type: 'scatter',
        name: 'Gate节点',
        data: gateData,
        symbol: 'rect',
        symbolSize: 12,
        encode: { x: 1, y: 0 },
      },
      // Dependency arrows
      ...(data.dependencies && data.dependencies.length > 0 ? [{
        type: 'lines',
        name: '依赖关系',
        data: data.dependencies
          .filter((d: GanttDep) => {
            const fromIdx = tasks.findIndex((t: GanttTask) => t.id === d.depends_on_task_id)
            const toIdx = tasks.findIndex((t: GanttTask) => t.id === d.task_id)
            return fromIdx >= 0 && toIdx >= 0
          })
          .map((d: GanttDep) => {
            const fromTask = tasks.find((t: GanttTask) => t.id === d.depends_on_task_id)!
            const toTask = tasks.find((t: GanttTask) => t.id === d.task_id)!
            const fromEnd = fromTask.end_date ? new Date(fromTask.end_date).getTime() : new Date(fromTask.start_date || '').getTime() + 86400000
            const toStart = toTask.start_date ? new Date(toTask.start_date).getTime() : new Date(toTask.end_date || '').getTime() - 86400000
            const fromIdx = tasks.findIndex((t: GanttTask) => t.id === d.depends_on_task_id)
            const toIdx = tasks.findIndex((t: GanttTask) => t.id === d.task_id)
            return {
              coords: [
                [fromEnd, fromIdx],
                [toStart, toIdx],
              ],
            }
          }),
        coordinateSystem: 'cartesian2d',
        lineStyle: {
          color: '#e6a23c',
          width: 1.5,
          type: 'dashed',
          curveness: 0.3,
        },
        symbol: ['none', 'arrow'],
        symbolSize: 8,
        z: 5,
      }] : []),
    ],
  }

  initChart(chartRef.value, option)
}

onMounted(fetchGantt)
onUnmounted(() => {
  if (chartRef.value) disposeChart(chartRef.value)
})
</script>

<style scoped>
.gantt-page { padding: 16px; }
.gantt-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; flex-wrap: wrap; gap: 8px;
}
.header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.header-title { font-size: 18px; font-weight: 700; color: #303133; }
.header-right { display: flex; gap: 16px; color: #909399; font-size: 13px; }
.date-info { white-space: nowrap; }
.legend-card { margin-bottom: 12px; }
.legend-card :deep(.el-card__body) { padding: 10px 16px; }
.legend-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 12px; }
.legend-title { color: #909399; font-weight: 600; }
.legend-item { display: flex; align-items: center; gap: 4px; color: #606266; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.dot-todo { background: #909399; }
.dot-progress { background: #409eff; }
.dot-done { background: #67c23a; }
.dot-blocked { background: #f56c6c; }
.dot-milestone { background: #e6a23c; border-radius: 2px; transform: rotate(45deg); width: 8px; height: 8px; }
.dot-milestone-delayed { background: #f56c6c; border-radius: 2px; transform: rotate(45deg); width: 8px; height: 8px; }
.dot-gate { background: #909399; border-radius: 2px; width: 8px; height: 8px; }
.ml-4 { margin-left: 16px; }
.chart-card { margin-bottom: 12px; }
.gantt-chart { width: 100%; height: 500px; }
.stats-card { margin-bottom: 12px; }
.stats-card :deep(.el-card__body) { padding: 12px 16px; }
.kpi-row { display: flex; gap: 32px; flex-wrap: wrap; }
.kpi-row :deep(.el-statistic) { text-align: center; }
.kpi-row :deep(.el-statistic__head) { font-size: 12px; color: #909399; }
.kpi-row :deep(.el-statistic__content) { font-size: 20px; font-weight: 700; color: #303133; }
</style>
