<template>
  <div class="quality-page">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4" v-for="kpi in kpiCards" :key="kpi.label">
        <el-card shadow="hover" :body-style="{ padding: '16px' }">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :class="{ 'kpi-danger': kpi.danger, 'kpi-warn': kpi.warn }">
            <template v-if="kpi.suffix">{{ kpi.value }}<span class="kpi-suffix">{{ kpi.suffix }}</span></template>
            <template v-else>{{ kpi.value }}</template>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表行 -->
    <el-row :gutter="16" class="chart-row">
      <!-- 供应商合格率排名 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>供应商合格率排名</span></template>
          <div ref="supplierChartRef" style="height:320px"></div>
          <div v-if="stats.by_supplier.length === 0" class="empty-hint">暂无数据</div>
        </el-card>
      </el-col>
      <!-- 月度趋势 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>月度合格率趋势</span></template>
          <div ref="trendChartRef" style="height:320px"></div>
          <div v-if="stats.trend.length === 0" class="empty-hint">暂无数据</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <!-- 缺陷分类 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header><span>缺陷分类 TOP10</span></template>
          <div ref="defectChartRef" style="height:300px"></div>
          <div v-if="stats.top_defects.length === 0" class="empty-hint">暂无缺陷记录</div>
        </el-card>
      </el-col>
      <!-- 最近不合格记录 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><span>最近不合格记录</span></template>
          <el-table :data="stats.recent_rejects" border stripe size="small" max-height="280" style="width:100%">
            <el-table-column prop="inspected_at" label="日期" width="150">
              <template #default="{ row }">{{ (row.inspected_at || '').replace('T',' ').slice(0,16) }}</template>
            </el-table-column>
            <el-table-column prop="supplier_name" label="供应商" width="120" />
            <el-table-column prop="part_no" label="物料编码" width="110" />
            <el-table-column prop="defect_desc" label="缺陷描述" min-width="120" />
            <el-table-column prop="defect_qty" label="不良数" width="70" />
            <el-table-column label="结果" width="70">
              <template #default="{ row }">
                <el-tag :type="row.result === 'reject' ? 'danger' : 'warning'" size="small">
                  {{ row.result === 'reject' ? '退货' : '让步' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="stats.recent_rejects.length === 0" class="empty-hint" style="padding:20px">无不合格记录</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../../api'

interface StatsData {
  total_inspections: number; pass_rate: number; concession_rate: number; reject_rate: number
  month_total: number; month_pass_rate: number
  by_supplier: Array<{supplier_name:string; pass_rate:number; total_inspections:number}>
  trend: Array<{month:string; pass_rate:number; total:number; pass_count:number; reject_count:number}>
  top_defects: Array<{defect_desc:string; count:number}>
  recent_rejects: Array<any>
}

const stats = ref<StatsData>({
  total_inspections: 0, pass_rate: 0, concession_rate: 0, reject_rate: 0,
  month_total: 0, month_pass_rate: 0,
  by_supplier: [], trend: [], top_defects: [], recent_rejects: [],
})

const kpiCards = computed(() => [
  { label: '检验总数', value: stats.value.total_inspections, danger: false, warn: false },
  { label: '合格率', value: stats.value.pass_rate, suffix: '%', danger: stats.value.pass_rate < 80, warn: stats.value.pass_rate < 95 && stats.value.pass_rate >= 80 },
  { label: '让步率', value: stats.value.concession_rate, suffix: '%', danger: false, warn: stats.value.concession_rate > 10 },
  { label: '退货率', value: stats.value.reject_rate, suffix: '%', danger: stats.value.reject_rate > 5, warn: stats.value.reject_rate > 2 && stats.value.reject_rate <= 5 },
  { label: '本月检验', value: stats.value.month_total, danger: false, warn: false },
  { label: '本月合格率', value: stats.value.month_pass_rate, suffix: '%', danger: stats.value.month_pass_rate < 80, warn: stats.value.month_pass_rate < 95 && stats.value.month_pass_rate >= 80 },
])

const supplierChartRef = ref<HTMLElement | null>(null)
const trendChartRef = ref<HTMLElement | null>(null)
const defectChartRef = ref<HTMLElement | null>(null)
let charts: echarts.ECharts[] = []

async function fetchData() {
  const res = await api.get('/purchases/quality-stats')
  stats.value = res.data
  await nextTick()
  renderCharts()
}

function renderCharts() {
  // Cleanup
  charts.forEach(c => c.dispose())
  charts = []

  // Supplier bar chart
  if (supplierChartRef.value && stats.value.by_supplier.length > 0) {
    const c = echarts.init(supplierChartRef.value)
    const sorted = [...stats.value.by_supplier].sort((a, b) => b.pass_rate - a.pass_rate).slice(0, 15)
    c.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 100, right: 20, top: 10, bottom: 30 },
      xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
      yAxis: { type: 'category', data: sorted.map(s => s.supplier_name || '未知'), axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', data: sorted.map(s => ({
          value: s.pass_rate,
          itemStyle: { color: s.pass_rate >= 95 ? '#67c23a' : s.pass_rate >= 80 ? '#e6a23c' : '#f56c6c' }
        }))
      }],
    })
    charts.push(c)
  }

  // Trend line chart
  if (trendChartRef.value && stats.value.trend.length > 0) {
    const c = echarts.init(trendChartRef.value)
    const months = stats.value.trend.map(t => t.month)
    c.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['合格率', '检验总数'], bottom: 0 },
      grid: { left: 50, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: months, axisLabel: { rotate: 45, fontSize: 10 } },
      yAxis: [
        { type: 'value', name: '合格率 %', max: 100, axisLabel: { formatter: '{value}%' } },
        { type: 'value', name: '数量' },
      ],
      series: [
        { name: '合格率', type: 'line', data: stats.value.trend.map(t => t.pass_rate), smooth: true, lineStyle: { color: '#67c23a', width: 2 }, itemStyle: { color: '#67c23a' } },
        { name: '检验总数', type: 'bar', yAxisIndex: 1, data: stats.value.trend.map(t => t.total), barWidth: 12, itemStyle: { color: '#409eff' } },
      ],
    })
    charts.push(c)
  }

  // Defect pie chart
  if (defectChartRef.value && stats.value.top_defects.length > 0) {
    const c = echarts.init(defectChartRef.value)
    const colors = ['#f56c6c','#e6a23c','#409eff','#67c23a','#909399','#b37feb','#5cdbd3','#ff85c0','#ffc069','#95de64']
    c.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: stats.value.top_defects.map((d, i) => ({
          name: d.defect_desc || '未描述',
          value: d.count,
          itemStyle: { color: colors[i % colors.length] }
        })),
        label: { fontSize: 11, formatter: '{b}\n{d}%' },
      }],
    })
    charts.push(c)
  }
}

onMounted(fetchData)
onUnmounted(() => charts.forEach(c => c.dispose()))
</script>

<style scoped>
.kpi-row { margin-bottom: 16px; }
.chart-row { margin-bottom: 16px; }
.kpi-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #303133; }
.kpi-suffix { font-size: 14px; color: #909399; font-weight: 400; margin-left: 2px; }
.kpi-danger .kpi-value { color: #f56c6c; }
.kpi-warn .kpi-value { color: #e6a23c; }
.empty-hint { text-align: center; color: #c0c4cc; font-size: 14px; padding: 40px 0; }
</style>
