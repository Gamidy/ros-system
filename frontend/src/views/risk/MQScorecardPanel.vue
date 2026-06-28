<template>
  <div class="mq-panel">
    <!-- 饼图 -->
    <el-card shadow="never" class="chart-card">
      <template #header><span style="font-weight:600">物料风险分布</span></template>
      <div ref="pieChartRef" class="chart-box" />
    </el-card>

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
            <div v-if="row._loading_detail" v-loading="true" style="height:60px" />
            <el-table
              v-else-if="(row._detail_items ?? []).length"
              :data="row._detail_items"
              size="small"
              stripe
            >
              <el-table-column prop="material_code" label="物料编码" width="140" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column label="风险等级" width="100">
                <template #default="{ row: d }">
                  <el-tag :type="riskTagType(d.risk_level)" size="small">{{ d.risk_level }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="risk_score" label="风险评分" width="90" />
              <el-table-column prop="suggestion" label="建议" min-width="160" show-overflow-tooltip />
            </el-table>
            <el-empty v-else description="暂无高风险物料数据" :image-size="40" />
          </template>
        </el-table-column>

        <el-table-column prop="plan_name" label="计划名称" min-width="160" />
        <el-table-column label="风险等级" width="110">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_level)" size="small" effect="dark">
              {{ row.risk_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="risk_score" label="评分" width="80" align="center" />
        <el-table-column prop="high_risk_count" label="高风险物料数" width="120" align="center" />
        <el-table-column prop="suggestion" label="建议" min-width="180" show-overflow-tooltip />
      </el-table>
      <el-empty v-if="!loading && planList.length === 0" description="暂无物料风险数据" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../../api'
import { initChart, disposeChart } from '../../utils/chart'
import type { EChartsOption } from 'echarts'
import type { TableRow, ChartDataPoint } from '@/types/common'

interface DetailItem {
  material_code?: string
  material_name?: string
  risk_level?: string
  risk_score?: number
  suggestion?: string
}

interface PlanItem extends TableRow {
  plan_id?: number | string
  plan_name?: string
  risk_level?: string
  risk_score?: number
  high_risk_count?: number
  suggestion?: string
  _detail_items?: DetailItem[]
  _loading_detail?: boolean
}

const loading = ref(false)
const planList = ref<PlanItem[]>([])
const pieChartRef = ref<HTMLElement>()

function riskTagType(level?: string): string {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success',
    critical: 'danger',
  }
  return map[level?.toLowerCase() ?? ''] || 'info'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/api/v2/dashboard/mq-summary')
    const data = res.data as Record<string, unknown>
    const items = (data?.items || data?.data || data?.records || []) as PlanItem[]
    planList.value = Array.isArray(items) ? items : Array.isArray(data) ? (data as unknown as PlanItem[]) : []
    // init detail cache
    planList.value.forEach((p: PlanItem) => {
      p._detail_items = []
      p._loading_detail = false
    })
    await nextTick()
    renderPieChart(data)
  } catch {
    planList.value = []
  } finally {
    loading.value = false
  }
}

// 饼图渲染
function renderPieChart(data: Record<string, unknown>) {
  if (!pieChartRef.value) return
  const distribution = (data?.distribution || data?.risk_distribution || []) as ChartDataPoint[]
  const chartData = Array.isArray(distribution) && distribution.length > 0
    ? distribution.map((d: ChartDataPoint) => ({
        name: (d.name ?? d.risk_level ?? d.type ?? '') as string,
        value: d.value ?? 0,
      }))
    : [
        { name: '高风险', value: (data?.high_count as number) ?? (data?.high_risk_count as number) ?? 0 },
        { name: '中风险', value: (data?.medium_count as number) ?? (data?.medium_risk_count as number) ?? 0 },
        { name: '低风险', value: (data?.low_count as number) ?? (data?.low_risk_count as number) ?? 0 },
      ]
  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 8, itemWidth: 12, itemHeight: 12, textStyle: { fontSize: 12 } },
    color: ['#F56C6C', '#E6A23C', '#67C23A', '#909399'],
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
      data: chartData.filter((d: ChartDataPoint) => (d.value ?? 0) > 0),
    }],
  }
  initChart(pieChartRef.value, option)
}

// 展开行 -> 拉取详情
async function onExpandChange(row: PlanItem, expandedRows: TableRow[]) {
  const expanded = expandedRows.includes(row)
  if (!expanded) return
  if ((row._detail_items?.length ?? 0) > 0) return
  row._loading_detail = true
  try {
    const res = await api.get(`/api/v2/dashboard/mq-detail/${row.plan_id ?? row.id}`)
    const data = res.data as Record<string, unknown>
    row._detail_items = (data?.items || data?.data || data?.details || data?.materials || []) as DetailItem[]
  } catch {
    row._detail_items = []
  } finally {
    row._loading_detail = false
  }
}

onMounted(fetchData)

onUnmounted(() => {
  if (pieChartRef.value) disposeChart(pieChartRef.value)
})
</script>

<style scoped>
.mq-panel {
  min-height: 200px;
}
.chart-card {
  border-radius: 8px;
}
.chart-box {
  width: 100%;
  height: 240px;
}
.table-card {
  border-radius: 8px;
}
</style>
