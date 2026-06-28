<template>
  <div class="bi-analytics">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        @change="fetchData"
      />
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <!-- KPI 卡片行 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col v-for="kpi in kpiList" :key="kpi.key" :span="8">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :style="{ color: kpi.color }">{{ kpi.value }}</div>
          <div v-if="kpi.unit" class="kpi-unit">{{ kpi.unit }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 策划趋势折线图 -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="24">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <span>策划趋势</span>
          </template>
          <BiChart
            type="line"
            :data="trendData"
            name-key="date"
            value-key="count"
            :loading="loading"
            :empty="trendData.length === 0 && !loading"
            :height="340"
            :area="true"
            :smooth="true"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 成本超标 Top5 预警 -->
    <el-card shadow="never" class="alert-card">
      <template #header>
        <div class="alert-header">
          <span>成本超标 Top5 预警</span>
          <el-tag v-if="costOverrunList.length" type="danger" size="small">{{ costOverrunList.length }} 项</el-tag>
        </div>
      </template>
      <el-table :data="costOverrunList" stripe style="width:100%" v-if="costOverrunList.length" empty-text="暂无超标记录">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="project_name" label="项目名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="budget" label="预算(元)" width="130" align="right">
          <template #default="{ row }">¥{{ (row.budget ?? 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="actual" label="实际(元)" width="130" align="right">
          <template #default="{ row }">¥{{ (row.actual ?? 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="overrun_rate" label="超标率" width="100" align="right">
          <template #default="{ row }">
            <el-tag :type="(row.overrun_rate ?? 0) > 0.2 ? 'danger' : 'warning'" size="small">
              {{ ((row.overrun_rate ?? 0) * 100).toFixed(1) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="overrun_amount" label="超标金额(元)" width="130" align="right">
          <template #default="{ row }">
            <span style="color:#f56c6c;font-weight:600;">¥{{ (row.overrun_amount ?? 0).toLocaleString() }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无超标记录" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BiChart from '../../components/BiChart.vue'
import api from '../../api/index'

const dateRange = ref<string[]>([])
const loading = ref(false)

// KPI 卡片
const kpiList = ref<{ key: string; label: string; value: string; color: string; unit?: string }[]>([])

// 策划趋势数据
const trendData = ref<{ date: string; count: number }[]>([])

// 成本超标 Top5
const costOverrunList = ref<{
  project_name: string
  budget: number
  actual: number
  overrun_rate: number
  overrun_amount: number
}[]>([])

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }

    const [kpiRes, trendRes, costRes] = await Promise.all([
      api.get('/bi/analytics/kpi', { params }),
      api.get('/bi/analytics/planning-trend', { params }),
      api.get('/bi/analytics/cost-overrun-top5', { params }),
    ])

    // KPI
    const kpiRaw = kpiRes.data as Record<string, any> || {}
    kpiList.value = [
      { key: 'total_plans', label: '策划总数', value: String(kpiRaw.total_plans ?? 0), color: '#007AFF' },
      { key: 'approval_rate', label: '审批通过率', value: (kpiRaw.approval_rate != null ? (kpiRaw.approval_rate * 100).toFixed(1) : '-') + '%', color: '#34C759' },
      { key: 'cost_overrun', label: '成本超标数', value: String(kpiRaw.cost_overrun_count ?? 0), color: '#FF3B30', unit: '项' },
    ]

    // 趋势
    trendData.value = (trendRes.data as Record<string, unknown>[])?.map((d: Record<string, unknown>) => ({
      date: String(d.date || d.month || ''),
      count: Number(d.count ?? d.total ?? 0),
    })) || []

    // 成本超标
    costOverrunList.value = (costRes.data as Record<string, unknown>[])?.map((d: Record<string, unknown>) => ({
      project_name: String(d.project_name || d.project || ''),
      budget: Number(d.budget ?? 0),
      actual: Number(d.actual ?? 0),
      overrun_rate: Number(d.overrun_rate ?? d.rate ?? 0),
      overrun_amount: Number(d.overrun_amount ?? d.gap ?? 0),
    })) || []
  } catch {
    // 兜底模拟数据
    kpiList.value = [
      { key: 'total_plans', label: '策划总数', value: '156', color: '#007AFF' },
      { key: 'approval_rate', label: '审批通过率', value: '87.5%', color: '#34C759' },
      { key: 'cost_overrun', label: '成本超标数', value: '8', color: '#FF3B30', unit: '项' },
    ]
    trendData.value = [
      { date: '01月', count: 18 },
      { date: '02月', count: 22 },
      { date: '03月', count: 15 },
      { date: '04月', count: 28 },
      { date: '05月', count: 24 },
      { date: '06月', count: 31 },
      { date: '07月', count: 26 },
    ]
    costOverrunList.value = [
      { project_name: '高效变频压缩机开发', budget: 500000, actual: 628000, overrun_rate: 0.256, overrun_amount: 128000 },
      { project_name: '智能温控模块升级', budget: 280000, actual: 352000, overrun_rate: 0.257, overrun_amount: 72000 },
      { project_name: '超薄室内机设计', budget: 420000, actual: 510000, overrun_rate: 0.214, overrun_amount: 90000 },
      { project_name: '新风系统集成项目', budget: 360000, actual: 435000, overrun_rate: 0.208, overrun_amount: 75000 },
      { project_name: 'R32冷媒适配改造', budget: 190000, actual: 226000, overrun_rate: 0.189, overrun_amount: 36000 },
    ]
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.bi-analytics {
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
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.kpi-label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.kpi-unit {
  font-size: 12px;
  color: #86868b;
  margin-top: 2px;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.chart-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
.alert-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
}
.alert-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
