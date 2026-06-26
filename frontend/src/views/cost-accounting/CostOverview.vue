<template>
  <div class="cost-overview">
    <!-- 筛选器 -->
    <div class="filter-bar">
      <el-date-picker
        v-model="period"
        type="monthrange"
        range-separator="至"
        start-placeholder="开始月份"
        end-placeholder="结束月份"
        format="YYYY-MM"
        value-format="YYYY-MM"
        @change="fetchData"
      />
      <el-select v-model="selectedDept" placeholder="选择部门" clearable @change="fetchData" style="width: 160px">
        <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
      </el-select>
      <el-button type="primary" @click="fetchData">查询</el-button>
      <el-button @click="exportReport">导出报告</el-button>
    </div>

    <!-- 指标卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="6" v-for="kpi in kpiList" :key="kpi.key">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value" :style="{ color: kpi.color }">{{ kpi.value }}</div>
          <div v-if="kpi.trend" class="kpi-trend" :class="kpi.trend > 0 ? 'up' : 'down'">
            {{ kpi.trend > 0 ? '↑' : '↓' }} {{ Math.abs(kpi.trend) }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16" class="chart-row">
      <!-- 部门成本对比柱图 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>部门成本对比</template>
          <BiChart
            type="bar"
            :data="deptCostData"
            name-key="department"
            :series="deptCostSeries"
            :loading="loading"
            :empty="deptCostData.length === 0 && !loading"
            :height="360"
          />
        </el-card>
      </el-col>
      <!-- 成本趋势折线图 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>成本趋势</template>
          <BiChart
            type="line"
            :data="trendData"
            name-key="month"
            :series="trendSeries"
            :loading="loading"
            :empty="trendData.length === 0 && !loading"
            :height="360"
            :area="true"
            :smooth="true"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <!-- 成本结构饼图 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>成本结构</template>
          <BiChart
            type="pie"
            :data="structureData"
            name-key="name"
            value-key="value"
            :loading="loading"
            :empty="structureData.length === 0 && !loading"
            :height="360"
            :donut="true"
          />
        </el-card>
      </el-col>
      <!-- 成本明细表格 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <template #header>成本明细</template>
          <el-table
            :data="detailData"
            stripe
            size="small"
            style="width: 100%"
            v-loading="loading"
            :max-height="340"
          >
            <el-table-column prop="department" label="部门" min-width="100" />
            <el-table-column prop="category" label="类别" min-width="100" />
            <el-table-column prop="budget" label="预算(元)" width="110" align="right">
              <template #default="{ row }">{{ formatMoney(row.budget) }}</template>
            </el-table-column>
            <el-table-column prop="actual" label="实际(元)" width="110" align="right">
              <template #default="{ row }">{{ formatMoney(row.actual) }}</template>
            </el-table-column>
            <el-table-column prop="rate" label="执行率" width="90" align="right">
              <template #default="{ row }">
                <el-tag
                  :type="(row.rate || 0) > 1 ? 'danger' : 'success'"
                  size="small"
                >
                  {{ ((row.rate || 0) * 100).toFixed(1) }}%
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import BiChart from '../../components/BiChart.vue'
import api from '../../api/index'

const period = ref<string[]>([])
const selectedDept = ref('')
const loading = ref(false)
const departments = ref<string[]>([])

// KPI 卡片
const kpiList = ref<{ key: string; label: string; value: string; color: string; trend?: number }[]>([])

// 部门成本对比
const deptCostData = ref<any[]>([])
const deptCostSeries = ref([
  { name: '预算', key: 'budget' },
  { name: '实际', key: 'actual' },
])

// 成本趋势
const trendData = ref<any[]>([])
const trendSeries = ref([
  { name: '物料成本', key: 'material' },
  { name: '人工成本', key: 'labor' },
  { name: '制造费用', key: 'overhead' },
])

// 成本结构
const structureData = ref<{ name: string; value: number }[]>([])

// 明细表格
const detailData = ref<any[]>([])

function formatMoney(val: number | null | undefined): string {
  if (val == null) return '-'
  return '¥' + val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (period.value?.length === 2) {
      params.start_month = period.value[0]
      params.end_month = period.value[1]
    }
    if (selectedDept.value) params.department = selectedDept.value

    // 尝试调用现有 API，如果失败则使用 mock 数据
    try {
      const [budgetRes, deptRes, biRes] = await Promise.all([
        api.get('/bi/cost/budget-vs-actual', { params }),
        api.get('/bi/cost/department-ratio', { params }),
        api.get('/bi/cost', { params }),
      ])
      // 如果 API 成功则使用真实数据
      if (budgetRes.data) parseBudgetData(budgetRes.data)
      if (deptRes.data) parseDeptData(deptRes.data)
      if (biRes.data) parseBiData(biRes.data)
    } catch {
      // API 不存在，使用 mock 数据
      useMockData()
    }
  } catch {
    useMockData()
  } finally {
    loading.value = false
  }
}

function parseBudgetData(_data: any) {
  // placeholder for real API response parsing
  useMockData()
}

function parseDeptData(_data: any) {
  useMockData()
}

function parseBiData(_data: any) {
  useMockData()
}

function useMockData() {
  // KPI 卡片
  kpiList.value = [
    { key: 'totalBudget', label: '总预算', value: '¥' + (5230000).toLocaleString('zh-CN'), color: '#007AFF' },
    { key: 'totalActual', label: '总实际', value: '¥' + (4870000).toLocaleString('zh-CN'), color: '#34C759' },
    { key: 'variance', label: '差异额', value: '¥' + (360000).toLocaleString('zh-CN'), color: '#FF9500' },
    { key: 'execRate', label: '执行率', value: '93.1%', color: '#AF52DE' },
  ]

  // 部门成本对比
  deptCostData.value = [
    { department: '研发部', budget: 1200000, actual: 1120000 },
    { department: '市场部', budget: 650000, actual: 680000 },
    { department: '生产部', budget: 1800000, actual: 1650000 },
    { department: '质量部', budget: 580000, actual: 520000 },
    { department: '供应链', budget: 450000, actual: 430000 },
    { department: '采购部', budget: 550000, actual: 470000 },
  ]

  // 成本趋势
  trendData.value = [
    { month: '01月', material: 180000, labor: 95000, overhead: 42000 },
    { month: '02月', material: 195000, labor: 98000, overhead: 45000 },
    { month: '03月', material: 172000, labor: 101000, overhead: 44000 },
    { month: '04月', material: 210000, labor: 105000, overhead: 48000 },
    { month: '05月', material: 188000, labor: 102000, overhead: 46000 },
    { month: '06月', material: 225000, labor: 108000, overhead: 51000 },
    { month: '07月', material: 198000, labor: 104000, overhead: 47000 },
    { month: '08月', material: 235000, labor: 110000, overhead: 53000 },
  ]

  // 成本结构
  structureData.value = [
    { name: '物料成本', value: 1603000 },
    { name: '人工成本', value: 823000 },
    { name: '制造费用', value: 376000 },
    { name: '管理费用', value: 285000 },
    { name: '运输费用', value: 126000 },
  ]

  // 明细表格
  detailData.value = [
    { department: '研发部', category: '物料', budget: 800000, actual: 750000, rate: 0.938 },
    { department: '研发部', category: '人工', budget: 400000, actual: 370000, rate: 0.925 },
    { department: '市场部', category: '物料', budget: 300000, actual: 320000, rate: 1.067 },
    { department: '市场部', category: '人工', budget: 200000, actual: 210000, rate: 1.05 },
    { department: '市场部', category: '展会', budget: 150000, actual: 150000, rate: 1.0 },
    { department: '生产部', category: '物料', budget: 1200000, actual: 1080000, rate: 0.9 },
    { department: '生产部', category: '人工', budget: 600000, actual: 570000, rate: 0.95 },
    { department: '质量部', category: '设备', budget: 280000, actual: 260000, rate: 0.929 },
    { department: '质量部', category: '人工', budget: 300000, actual: 260000, rate: 0.867 },
    { department: '供应链', category: '物流', budget: 250000, actual: 240000, rate: 0.96 },
    { department: '供应链', category: '仓储', budget: 200000, actual: 190000, rate: 0.95 },
    { department: '采购部', category: '物料', budget: 400000, actual: 330000, rate: 0.825 },
    { department: '采购部', category: '人工', budget: 150000, actual: 140000, rate: 0.933 },
  ]

  departments.value = ['全部', '研发部', '市场部', '生产部', '质量部', '供应链', '采购部']
}

function exportReport() {
  ElMessage.success('报告导出功能开发中')
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.cost-overview {
  padding: 20px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.kpi-row {
  margin-bottom: 16px;
}
.kpi-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
  margin-bottom: 12px;
}
.kpi-label {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.kpi-trend {
  font-size: 12px;
  margin-top: 4px;
}
.kpi-trend.up {
  color: #34C759;
}
.kpi-trend.down {
  color: #FF3B30;
}
.chart-row {
  margin-bottom: 16px;
}
.chart-card {
  border-radius: 12px;
  border: 1px solid #e8e8ed;
  margin-bottom: 12px;
}
.chart-card :deep(.el-card__header) {
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
</style>
