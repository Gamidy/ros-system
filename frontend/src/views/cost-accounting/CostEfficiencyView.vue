<template>
  <div class="cost-efficiency-view">
    <h2>成本效率看板</h2>
    <p class="hint">各产品冷量联动重算的最新效率评分，低于60分需要关注。</p>

    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">已重算产品</div>
          <div class="kpi-value">{{ totalProducts }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">低效率(<60)</div>
          <div class="kpi-value" style="color: #f56c6c">{{ lowEfficiencyCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">平均效率评分</div>
          <div class="kpi-value" :style="{ color: avgScore >= 80 ? '#67c23a' : avgScore >= 60 ? '#e6a23c' : '#f56c6c' }">
            {{ avgScore }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">阈值筛选</div>
          <div>
            <el-select v-model="threshold" size="small" @change="fetchData" style="width: 100px">
              <el-option :value="40" label="≤40分" />
              <el-option :value="50" label="≤50分" />
              <el-option :value="60" label="≤60分" />
              <el-option :value="100" label="全部" />
            </el-select>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-table :data="products" border stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="cost_efficiency_score" label="效率评分" width="100" sortable>
        <template #default="{ row }">
          <el-tag :type="scoreTagType(row.cost_efficiency_score)" size="large">
            {{ row.cost_efficiency_score }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="冷量段" width="120">
        <template #default="{ row }">
          {{ row.capacity_key || '-' }}
          <span v-if="row.main_capacity" class="sub">({{ row.main_capacity }})</span>
        </template>
      </el-table-column>
      <el-table-column label="基准成本(元)" width="140" align="right">
        <template #default="{ row }">{{ formatMoney(row.baseline_material_cost) }}</template>
      </el-table-column>
      <el-table-column label="实际BOM(元)" width="140" align="right">
        <template #default="{ row }">{{ formatMoney(row.actual_bom_cost) }}</template>
      </el-table-column>
      <el-table-column label="差异额" width="120" align="right">
        <template #default="{ row }">
          <span :class="row.variance_amount > 0 ? 'over' : 'under'">
            {{ row.variance_amount > 0 ? '+' : '' }}{{ formatMoney(row.variance_amount) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="差异率" width="100" align="right">
        <template #default="{ row }">
          <el-tag :type="row.variance_pct > 0 ? 'danger' : 'success'" size="small">
            {{ row.variance_pct > 0 ? '+' : '' }}{{ row.variance_pct }}%
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="更新时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="goToPlan(row.product_plan_id)">
            查看策划
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && products.length === 0" description="暂无重算数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getLowEfficiencyProducts } from '../../api/costAccounting'

const router = useRouter()
const loading = ref(false)
const products = ref<any[]>([])
const threshold = ref(60)

const totalProducts = computed(() => products.value.length)
const lowEfficiencyCount = computed(() => products.value.filter((p: any) => p.cost_efficiency_score < 60).length)
const avgScore = computed(() => {
  if (products.value.length === 0) return '-'
  const sum = products.value.reduce((s: number, p: any) => s + p.cost_efficiency_score, 0)
  return (sum / products.value.length).toFixed(1)
})

function scoreTagType(score: number) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

function formatMoney(v: number) {
  if (v == null) return '0.00'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getLowEfficiencyProducts(threshold.value, 50)
    products.value = (res as any).data || []
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function goToPlan(planId: string) {
  router.push(`/product-plans/${planId}`)
}

onMounted(fetchData)
</script>

<style scoped>
.cost-efficiency-view {
  padding: 20px;
}
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}
.kpi-row {
  margin-bottom: 16px;
}
.kpi-card {
  text-align: center;
}
.kpi-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}
.sub {
  font-size: 11px;
  color: #c0c4cc;
}
.over { color: #f56c6c; font-weight: 600; }
.under { color: #67c23a; font-weight: 600; }
</style>
