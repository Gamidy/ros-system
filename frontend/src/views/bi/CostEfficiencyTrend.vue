<template>
  <div class="cost-efficiency-trend">
    <div class="filter-bar">
      <el-select v-model="limitPeriods" @change="fetchData" style="width: 160px">
        <el-option :value="6" label="最近 6 期" />
        <el-option :value="12" label="最近 12 期" />
        <el-option :value="24" label="最近 24 期" />
      </el-select>
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <!-- KPI 汇总 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">覆盖期间</div>
          <div class="kpi-value">{{ summary.periods_with_data || '-' }}</div>
          <div class="kpi-unit">个核算期</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">BTU段数</div>
          <div class="kpi-value">{{ summary.btu_segments_with_data || '-' }}</div>
          <div class="kpi-unit">个冷量段</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">重算总次数</div>
          <div class="kpi-value">{{ summary.total_recalc_count || '-' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">综合平均分</div>
          <div class="kpi-value" :style="{ color: summary.overall_avg_score >= 80 ? '#67c23a' : summary.overall_avg_score >= 60 ? '#e6a23c' : '#f56c6c' }">
            {{ summary.overall_avg_score || '-' }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 效率趋势折线图 -->
    <el-card shadow="never" class="chart-card">
      <template #header>
        <span>各BTU段成本效率趋势</span>
        <span class="chart-hint">折线=平均效率评分，越高越好(60分及格)</span>
      </template>
      <BiChart
        type="line"
        :data="chartData"
        name-key="period_name"
        :series="chartSeries"
        :loading="loading"
        :empty="chartData.length === 0 && !loading"
        :height="400"
        :smooth="true"
      />
    </el-card>

    <!-- 原始数据表格 -->
    <el-card shadow="never" class="table-card" v-if="tableData.length">
      <template #header>
        <span>明细数据</span>
      </template>
      <el-table :data="tableData" border stripe max-height="360">
        <el-table-column prop="period_name" label="期间" width="120" />
        <el-table-column prop="capacity_key" label="BTU段" width="100" />
        <el-table-column prop="avg_score" label="平均分" width="90" sortable>
          <template #default="{ row }">
            <el-tag :type="row.avg_score >= 80 ? 'success' : row.avg_score >= 60 ? 'warning' : 'danger'" size="small">
              {{ row.avg_score }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="product_count" label="产品数" width="80" align="center" />
        <el-table-column prop="avg_variance_pct" label="平均差异率" width="120" align="right">
          <template #default="{ row }">
            <span :class="row.avg_variance_pct > 0 ? 'over' : 'under'">
              {{ row.avg_variance_pct > 0 ? '+' : '' }}{{ row.avg_variance_pct }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="min_score" label="最低分" width="80" align="center" />
        <el-table-column prop="max_score" label="最高分" width="80" align="center" />
      </el-table>
    </el-card>

    <el-empty v-if="!loading && chartData.length === 0" description="暂无成本效率重算数据，请先在核算单中执行冷量联动重算" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BiChart from '../../components/BiChart.vue'
import api from '../../api/index'

const loading = ref(false)
const limitPeriods = ref(12)
const summary = ref<Record<string, any>>({})
const chartData = ref<Record<string, any>[]>([])
const chartSeries = ref<{ name: string; key: string }[]>([])
const tableData = ref<Record<string, any>[]>([])

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/bi/cost-efficiency', {
      params: { limit_periods: limitPeriods.value, min_score: 0 }
    })
    const data = (res as any).data || res
    summary.value = data.summary || {}

    // 构建 chart 数据
    const periods = data.periods || []
    const series = data.series || []
    const chartRows: Record<string, any>[] = []
    const capacityKeys: string[] = []

    for (const s of series) {
      if (s.capacity_key) {
        capacityKeys.push(s.capacity_key)
      }
    }

    // Build rows by period
    for (let i = 0; i < periods.length; i++) {
      const row: Record<string, any> = { period_name: periods[i].name }
      for (const s of series) {
        if (s.capacity_key && s.data && s.data[i]) {
          row[s.capacity_key] = s.data[i].avg_score
        }
      }
      chartRows.push(row)
    }
    chartData.value = chartRows

    // Series definitions
    chartSeries.value = capacityKeys.map(k => ({ name: k, key: k }))

    // Build table data
    const rows: Record<string, any>[] = []
    for (const s of series) {
      if (s.capacity_key && s.data) {
        for (const dp of s.data) {
          // We need to know which period this belongs to
          // Find by period_name
          const pn = dp.period_name
          if (pn) {
            rows.push({
              period_name: pn,
              capacity_key: s.capacity_key,
              avg_score: dp.avg_score ?? '-',
              product_count: dp.product_count ?? 0,
              avg_variance_pct: dp.avg_variance_pct ?? 0,
              min_score: dp.min_score ?? '-',
              max_score: dp.max_score ?? '-',
            })
          }
        }
      }
    }
    tableData.value = rows

  } catch (e: unknown) {
    console.error('成本效率趋势加载失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.cost-efficiency-trend {
  padding: 20px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}
.kpi-row {
  margin-bottom: 16px;
}
.kpi-card {
  text-align: center;
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.kpi-label {
  font-size: 12px;
  color: #86868b;
  margin-bottom: 4px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
}
.kpi-unit {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}
.chart-card, .table-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.chart-card :deep(.el-card__header), .table-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
.chart-hint {
  font-size: 11px;
  color: #c0c4cc;
  font-weight: 400;
  margin-left: 8px;
}
.over { color: #f56c6c; font-weight: 600; }
.under { color: #67c23a; font-weight: 600; }
</style>
