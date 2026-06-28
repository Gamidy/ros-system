<template>
  <div class="quality-dashboard">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#409eff">{{ stats.pendingIqc }}</div>
        <div class="kpi-label">待检来料</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#e6a23c">{{ stats.openComplaints }}</div>
        <div class="kpi-label">未关闭投诉</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#f56c6c">{{ stats.active8d }}</div>
        <div class="kpi-label">进行中8D</div>
      </el-card></el-col>
      <el-col :span="6"><el-card shadow="never" class="kpi-card">
        <div class="kpi-value" style="color:#67c23a">{{ stats.qualityRate }}%</div>
        <div class="kpi-label">来料合格率</div>
      </el-card></el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card shadow="never" class="section-card">
      <template #header><span>⚡ 快捷操作</span></template>
      <div class="quick-actions">
        <el-button type="primary" @click="$router.push('/quality/iqc')">🔬 来料检验</el-button>
        <el-button type="warning" @click="$router.push('/quality/complaints')">📢 客户投诉</el-button>
        <el-button type="danger" @click="$router.push('/quality/8d-reports')">📋 8D报告</el-button>
      </div>
    </el-card>

    <!-- 今日待办 -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span>🔴 待检来料 ({{ stats.pendingIqc }})</span></template>
          <div v-if="pendingIqc.length === 0" class="empty">暂无待检来料 ✅</div>
          <div v-for="r in pendingIqc.slice(0, 5)" :key="r.id" class="todo-item" @click="$router.push('/quality/iqc')">
            <div class="todo-title">{{ r.supplier }} - {{ r.part_code }}</div>
            <div class="todo-meta">批次: {{ r.batch_no || '-' }} 数量: {{ r.quantity }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header><span>🟡 未关闭投诉 ({{ stats.openComplaints }})</span></template>
          <div v-if="openComplaints.length === 0" class="empty">暂无待处理投诉 ✅</div>
          <div v-for="r in openComplaints.slice(0, 5)" :key="r.id" class="todo-item" @click="$router.push('/quality/complaints')">
            <div class="todo-title">{{ r.title }}</div>
            <div class="todo-meta">{{ r.customer_name }} | <el-tag size="small" :type="sevTag(r.severity)">{{ r.severity }}</el-tag></div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 质量趋势图 -->
    <el-card shadow="never" class="section-card">
      <template #header><span>📈 来料合格率趋势</span></template>
      <div ref="chartRef" style="height: 240px" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import api from '../../api'
import { initChart } from '../../utils/chart'

const stats = ref({ pendingIqc: 0, openComplaints: 0, active8d: 0, qualityRate: 100 })
const pendingIqc = ref<any[]>([])
const openComplaints = ref<any[]>([])
const chartRef = ref<HTMLElement | null>(null)

function sevTag(s: string) { return { critical: 'danger', high: 'warning', medium: 'info', low: 'info' }[s] || 'info' }

async function loadData() {
  try {
    const [iqcRes, compRes, d8Res] = await Promise.all([
      api.get('/quality/iqc', { params: { verdict: 'pending' } }).catch(() => ({ data: [] })),
      api.get('/quality/complaints').catch(() => ({ data: [] })),
      api.get('/api/quality/8d-reports').catch(() => ({ data: [] })),
    ])
    pendingIqc.value = iqcRes.data || []
    openComplaints.value = (compRes.data || []).filter((r: any) => r.status !== 'closed')
    const d8Data = d8Res.data || []
    const allIqc = await api.get('/quality/iqc').catch(() => ({ data: [] }))
    const allRecords = allIqc.data || []
    const totalSamples = allRecords.reduce((s: number, r: any) => s + (r.sample_qty || 0), 0)
    const totalRejects = allRecords.reduce((s: number, r: any) => s + (r.reject_qty || 0), 0)
    stats.value = {
      pendingIqc: pendingIqc.value.length,
      openComplaints: openComplaints.value.length,
      active8d: d8Data.filter((r: any) => !['closed', 'verified'].includes(r.status)).length,
      qualityRate: totalSamples > 0 ? Math.round((1 - totalRejects / totalSamples) * 100) : 100,
    }
  } catch { /* ignore */ }

  await nextTick()
  // Dummy chart
  if (chartRef.value) {
    initChart(chartRef.value, {
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'] },
      yAxis: { type: 'value', min: 85, max: 100 },
      series: [{ type: 'line', data: [96, 94, 97, 95, 98, 97], smooth: true, areaStyle: { opacity: 0.15 }, lineStyle: { color: '#67c23a', width: 2 } }],
    })
  }
}

onMounted(loadData)
</script>

<style scoped>
.quality-dashboard { padding: 16px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { text-align: center; cursor: default; }
.kpi-card :deep(.el-card__body) { padding: 20px 16px; }
.kpi-value { font-size: 32px; font-weight: 700; }
.kpi-label { font-size: 13px; color: #909399; margin-top: 4px; }
.section-card { margin-bottom: 16px; }
.quick-actions { display: flex; gap: 12px; }
.todo-item { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background 0.15s; }
.todo-item:hover { background: #f5f7fa; }
.todo-item:last-child { border-bottom: none; }
.todo-title { font-weight: 600; font-size: 14px; color: #303133; }
.todo-meta { font-size: 12px; color: #909399; margin-top: 4px; }
.empty { color: #909399; font-size: 13px; padding: 20px; text-align: center; }
</style>
