<template>
  <div class="cost-analytics">
    <!-- 范围筛选器 -->
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
      <el-select v-model="selectedDept" placeholder="选择部门" clearable @change="fetchData">
        <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
      </el-select>
      <el-button type="primary" @click="fetchData">查询</el-button>
    </div>

    <el-row :gutter="16" class="chart-row">
      <!-- 预算 vs 实际对比柱图 -->
      <el-col :span="14">
        <el-card shadow="never" class="chart-card">
          <template #header>预算 vs 实际对比</template>
          <BiChart
            type="bar"
            :data="budgetData"
            name-key="month"
            :series="budgetSeries"
            :loading="loading"
            :empty="budgetData.length === 0 && !loading"
            :height="360"
          />
        </el-card>
      </el-col>
      <!-- 部门占比饼图 -->
      <el-col :span="10">
        <el-card shadow="never" class="chart-card">
          <template #header>部门费用占比</template>
          <BiChart
            type="pie"
            :data="deptCostData"
            name-key="name"
            value-key="value"
            :loading="loading"
            :empty="deptCostData.length === 0 && !loading"
            :height="360"
            :donut="true"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 超标预警列表 -->
    <el-card shadow="never" class="alert-card">
      <template #header>
        <div class="alert-header">
          <span>超标预警</span>
          <el-tag v-if="overBudgetList.length" type="danger" size="small">{{ overBudgetList.length }} 项</el-tag>
        </div>
      </template>
      <el-table :data="overBudgetList" stripe style="width: 100%" v-if="overBudgetList.length">
        <el-table-column prop="department" label="部门" width="140" />
        <el-table-column prop="category" label="费用类别" width="140" />
        <el-table-column prop="budget" label="预算(元)" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.budget) }}</template>
        </el-table-column>
        <el-table-column prop="actual" label="实际(元)" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.actual) }}</template>
        </el-table-column>
        <el-table-column prop="rate" label="超标率" width="100" align="right">
          <template #default="{ row }">
            <el-tag :type="row.rate > 0.2 ? 'danger' : 'warning'" size="small">
              {{ (row.rate * 100).toFixed(1) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="gap" label="超支金额" width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.gap) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无超标预警" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import BiChart from '../../components/BiChart.vue'
import api from '../../api/index'

const period = ref<string[]>([])
const selectedDept = ref('')
const loading = ref(false)

const departments = ref<string[]>([])
const budgetData = ref<any[]>([])
const budgetSeries = ref<{ name: string; key: string }[]>([
  { name: '预算', key: 'budget' },
  { name: '实际', key: 'actual' },
])
const deptCostData = ref<{ name: string; value: number }[]>([])
const overBudgetList = ref<any[]>([])

function formatMoney(val: number): string {
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

    const [budgetRes, deptRes, alertRes, deptListRes] = await Promise.all([
      api.get('/bi/cost/budget-vs-actual', { params }),
      api.get('/bi/cost/department-ratio', { params }),
      api.get('/bi/cost/over-budget', { params }),
      api.get('/bi/cost/departments'),
    ])

    budgetData.value = (budgetRes.data as Record<string,unknown>[])?.map((d: Record<string,unknown>) => ({
      month: d.month || '',
      budget: Number(d.budget ?? 0),
      actual: Number(d.actual ?? 0),
    })) || []

    deptCostData.value = (deptRes.data as Record<string,unknown>[])?.map((d: Record<string,unknown>) => ({
      name: String(d.name || d.department || ''),
      value: Number(d.value ?? d.cost ?? 0),
    })) || []

    overBudgetList.value = (alertRes.data as Record<string,unknown>[])?.map((d: Record<string,unknown>) => ({
      department: d.department || '',
      category: d.category || '',
      budget: Number(d.budget ?? 0),
      actual: Number(d.actual ?? 0),
      rate: Number(d.rate ?? 0),
      gap: Number(d.gap ?? 0),
    })) || []

    departments.value = (deptListRes.data as string[]) || []
  } catch {
    // 兜底模拟数据
    budgetData.value = [
      { month: '01月', budget: 120000, actual: 105000 },
      { month: '02月', budget: 120000, actual: 128000 },
      { month: '03月', budget: 130000, actual: 115000 },
      { month: '04月', budget: 130000, actual: 142000 },
      { month: '05月', budget: 140000, actual: 132000 },
      { month: '06月', budget: 140000, actual: 158000 },
    ]
    deptCostData.value = [
      { name: '研发部', value: 380000 },
      { name: '市场部', value: 210000 },
      { name: '生产部', value: 320000 },
      { name: '质量部', value: 150000 },
      { name: '供应链', value: 110000 },
    ]
    overBudgetList.value = [
      { department: '研发部', category: '样品材料', budget: 80000, actual: 102000, rate: 0.275, gap: 22000 },
      { department: '市场部', category: '展会费用', budget: 50000, actual: 68500, rate: 0.37, gap: 18500 },
      { department: '生产部', category: '模具维护', budget: 30000, actual: 37200, rate: 0.24, gap: 7200 },
      { department: '质量部', category: '检测设备', budget: 40000, actual: 46000, rate: 0.15, gap: 6000 },
    ]
    departments.value = ['全部', '研发部', '市场部', '生产部', '质量部', '供应链', '采购部']
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.cost-analytics {
  padding: 20px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
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
