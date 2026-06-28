<template>
  <div class="cost-analysis-view">
    <!-- 顶部导航 tabs -->
    <el-menu
      :default-active="activeTab"
      mode="horizontal"
      class="nav-tabs"
      @select="handleTabSelect"
    >
      <el-menu-item index="/cost-accounting/periods">核算期间</el-menu-item>
      <el-menu-item index="/cost-accounting/labor-rates">工时费率</el-menu-item>
      <el-menu-item index="/cost-accounting/overhead-rules">分摊规则</el-menu-item>
      <el-menu-item index="/cost-accounting/analysis">成本分析</el-menu-item>
    </el-menu>

    <!-- 筛选区 -->
    <div class="filter-bar">
      <el-form :inline="true" size="default">
        <el-form-item label="产品策划">
          <el-select
            v-model="selectedPlanId"
            placeholder="搜索产品策划"
            clearable
            filterable
            remote
            :remote-method="searchProductPlans"
            :loading="searchLoading"
            style="width: 260px"
          >
            <el-option
              v-for="p in productPlans"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="核算期间">
          <el-select
            v-model="selectedPeriodId"
            placeholder="选择核算期间"
            clearable
            style="width: 180px"
          >
            <el-option
              v-for="p in periods"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="loadAnalysis"
            :loading="loading"
          >
            加载分析
          </el-button>
          <el-button
            :disabled="!analysisResult"
            @click="exportCSV"
          >
            导出CSV
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 加载状态 & 错误提示 -->
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      @close="errorMsg = ''"
      style="margin-bottom: 16px"
    />

    <!-- 分析结果区域 -->
    <template v-if="analysisResult">
      <!-- 4个指标卡片 -->
      <div class="metric-cards">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">合计差异率</div>
          <div class="metric-value">
            <el-tag
              :type="varianceTagType(analysisResult.total?.variance_pct)"
              size="large"
              effect="dark"
            >
              {{ formatPercent(analysisResult.total?.variance_pct) }}
            </el-tag>
          </div>
        </el-card>

        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">物料差异</div>
          <div class="metric-value">
            <span :class="varianceClass(analysisResult.material?.variance)">
              {{ formatMoney(analysisResult.material?.variance) }}
            </span>
          </div>
          <div class="metric-sub">
            目标: {{ formatMoney(analysisResult.material?.target) }}
            / 实际: {{ formatMoney(analysisResult.material?.actual) }}
          </div>
        </el-card>

        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">人工差异</div>
          <div class="metric-value">
            <span :class="varianceClass(analysisResult.labor?.variance)">
              {{ formatMoney(analysisResult.labor?.variance) }}
            </span>
          </div>
          <div class="metric-sub">
            目标: {{ formatMoney(analysisResult.labor?.target) }}
            / 实际: {{ formatMoney(analysisResult.labor?.actual) }}
          </div>
        </el-card>

        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">费用差异</div>
          <div class="metric-value">
            <span :class="varianceClass(analysisResult.overhead?.variance)">
              {{ formatMoney(analysisResult.overhead?.variance) }}
            </span>
          </div>
          <div class="metric-sub">
            目标: {{ formatMoney(analysisResult.overhead?.target) }}
            / 实际: {{ formatMoney(analysisResult.overhead?.actual) }}
          </div>
        </el-card>
      </div>

      <!-- CSS 进度条对比 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>📊 成本进度对比</span></template>
        <div v-for="item in progressItems" :key="item.label" class="progress-row">
          <div class="progress-label">{{ item.label }}</div>
          <div class="progress-bars">
            <div class="progress-track">
              <div
                class="progress-fill target-fill"
                :style="{ width: item.targetPct + '%' }"
              >
                <span class="progress-text" v-if="item.targetPct > 10">目标</span>
              </div>
            </div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :class="item.isOverBudget ? 'over-budget' : 'under-budget'"
                :style="{ width: item.actualPct + '%' }"
              >
                <span class="progress-text" v-if="item.actualPct > 10">实际</span>
              </div>
            </div>
            <div class="progress-values">
              <span>目标: {{ formatMoney(item.target) }}</span>
              <span :class="item.isOverBudget ? 'text-danger' : 'text-success'">
                实际: {{ formatMoney(item.actual) }}
                ({{ item.isOverBudget ? '超支' : '节约' }})
              </span>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 差异详情表格 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>📋 差异详情</span></template>
        <el-table
          :data="varianceDetails"
          border
          stripe
          size="small"
          style="width: 100%"
          v-loading="detailLoading"
        >
          <el-table-column prop="name" label="成本项" min-width="160" />
          <el-table-column prop="target" label="目标" width="130" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.target) }}
            </template>
          </el-table-column>
          <el-table-column prop="actual" label="实际" width="130" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.actual) }}
            </template>
          </el-table-column>
          <el-table-column prop="variance" label="差异" width="130" align="right">
            <template #default="{ row }">
              <span :class="varianceClass(row.variance)">
                {{ formatMoney(row.variance) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="variance_pct" label="差异率%" width="110" align="right">
            <template #default="{ row }">
              <el-tag
                :type="varianceTagType(row.variance_pct)"
                size="small"
                effect="plain"
              >
                {{ formatPercent(row.variance_pct) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 趋势部分 -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="section-header">
            <span>📈 多期间趋势</span>
            <el-button
              size="small"
              :loading="trendLoading"
              @click="loadTrend"
            >
              加载趋势
            </el-button>
          </div>
        </template>

        <el-table
          v-if="trendData.length > 0"
          :data="trendData"
          border
          stripe
          size="small"
          style="width: 100%"
        >
          <el-table-column prop="period_id" label="期间ID" min-width="80" />
          <el-table-column prop="total_target" label="目标总成本" width="130" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.total_target) }}
            </template>
          </el-table-column>
          <el-table-column prop="total_actual" label="实际总成本" width="130" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.total_actual) }}
            </template>
          </el-table-column>
          <el-table-column label="差异" width="130" align="right">
            <template #default="{ row }">
              <span :class="varianceClass(row.total_actual - row.total_target)">
                {{ formatMoney(row.total_actual - row.total_target) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="variance_pct" label="差异率" width="110" align="right">
            <template #default="{ row }">
              <el-tag
                :type="varianceTagType(row.variance_pct)"
                size="small"
                effect="plain"
              >
                {{ formatPercent(row.variance_pct) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="material_actual" label="物料成本" width="120" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.material_actual) }}
            </template>
          </el-table-column>
          <el-table-column prop="labor_actual" label="人工成本" width="120" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.labor_actual) }}
            </template>
          </el-table-column>
          <el-table-column prop="overhead_actual" label="费用成本" width="120" align="right">
            <template #default="{ row }">
              {{ formatMoney(row.overhead_actual) }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="点击「加载趋势」查看多期间数据" :image-size="50" />
      </el-card>
    </template>

    <!-- 未加载时的空白提示 -->
    <el-empty
      v-if="!analysisResult && !loading && !errorMsg"
      description="请选择产品策划和核算期间，点击「加载分析」"
      :image-size="60"
      style="margin-top: 60px"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as API from '../../api/costAccounting'

const router = useRouter()

/* ===================== 顶部导航 ===================== */
const activeTab = ref('/cost-accounting/analysis')

const handleTabSelect = (index: string) => {
  router.push(index)
}

/* ===================== 筛选 ===================== */
interface Period {
  id: number
  name: string
}
interface ProductPlan {
  id: number
  name: string
}

const selectedPlanId = ref<number | undefined>(undefined)
const selectedPeriodId = ref<number | undefined>(undefined)
const periods = ref<Period[]>([])
const productPlans = ref<ProductPlan[]>([])
const searchLoading = ref(false)

const loading = ref(false)
const errorMsg = ref('')

const searchProductPlans = async (keyword: string) => {
  if (!keyword) {
    productPlans.value = []
    return
  }
  searchLoading.value = true
  try {
    const res = await API.listProductPlans({ keyword, page: 1, size: 20 })
    productPlans.value = res.data?.items ?? res.data ?? []
  } catch {
    productPlans.value = []
  } finally {
    searchLoading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await API.listPeriods()
    periods.value = res.data ?? res ?? []
  } catch {
    periods.value = []
  }
})

/* ===================== API类型定义 ===================== */
interface CostCategory {
  actual: number
  target: number
  variance: number
  variance_pct: number
}

interface VarianceAnalysis {
  material: CostCategory
  labor: CostCategory
  overhead: CostCategory
  total: CostCategory
}

interface VarianceDetail {
  id: number
  category: string
  name: string
  target: number
  actual: number
  variance: number
  variance_pct: number
}

interface TrendRecord {
  period_id: number
  sheet_no: string
  status: string
  material_actual: number
  labor_actual: number
  overhead_actual: number
  total_actual: number
  total_target: number
  variance_pct: number
}

/* ===================== 分析数据 ===================== */
const analysisResult = ref<VarianceAnalysis | null>(null)
const varianceDetails = ref<VarianceDetail[]>([])
const detailLoading = ref(false)
const trendData = ref<TrendRecord[]>([])
const trendLoading = ref(false)

const loadAnalysis = async () => {
  if (!selectedPlanId.value) {
    ElMessage.warning('请选择产品策划')
    return
  }
  if (!selectedPeriodId.value) {
    ElMessage.warning('请选择核算期间')
    return
  }

  loading.value = true
  errorMsg.value = ''
  analysisResult.value = null
  varianceDetails.value = []
  trendData.value = []

  try {
    // 加载差异分析概要
    const res = await API.getVarianceAnalysis(
      String(selectedPlanId.value),
      selectedPeriodId.value
    )
    analysisResult.value = res.data ?? res
  } catch (e: unknown) {
    errorMsg.value = (e as any)?.response?.data?.detail || (e as any)?.message || '加载差异分析失败'
    ElMessage.error(errorMsg.value)
    return
  } finally {
    loading.value = false
  }

  // 加载差异详情
  detailLoading.value = true
  try {
    const detailRes = await API.getVarianceDetail(
      String(selectedPlanId.value),
      selectedPeriodId.value
    )
    varianceDetails.value = detailRes.data?.items ?? detailRes.data ?? detailRes ?? []
  } catch {
    varianceDetails.value = []
  } finally {
    detailLoading.value = false
  }
}

/* ===================== 趋势 ===================== */
const loadTrend = async () => {
  if (!selectedPlanId.value) {
    ElMessage.warning('请先选择产品策划')
    return
  }
  trendLoading.value = true
  try {
    const res = await API.getCostTrend(String(selectedPlanId.value), 6)
    trendData.value = res.data?.items ?? res.data ?? res ?? []
  } catch (e: unknown) {
    ElMessage.error((e as any)?.response?.data?.detail || (e as any)?.message || '加载趋势数据失败')
    trendData.value = []
  } finally {
    trendLoading.value = false
  }
}

/* ===================== 进度条数据 ===================== */
interface ProgressItem {
  label: string
  target: number
  actual: number
  targetPct: number
  actualPct: number
  isOverBudget: boolean
}

const progressItems = computed<ProgressItem[]>(() => {
  if (!analysisResult.value) return []
  const a = analysisResult.value
  const maxVal = Math.max(
    a.material?.target ?? 0, a.material?.actual ?? 0,
    a.labor?.target ?? 0, a.labor?.actual ?? 0,
    a.overhead?.target ?? 0, a.overhead?.actual ?? 0,
    1
  )
  const toPct = (v: number) => Math.round((v / maxVal) * 100)

  return [
    {
      label: '物料成本',
      target: a.material?.target ?? 0,
      actual: a.material?.actual ?? 0,
      targetPct: toPct(a.material?.target ?? 0),
      actualPct: toPct(a.material?.actual ?? 0),
      isOverBudget: (a.material?.actual ?? 0) > (a.material?.target ?? 0),
    },
    {
      label: '人工成本',
      target: a.labor?.target ?? 0,
      actual: a.labor?.actual ?? 0,
      targetPct: toPct(a.labor?.target ?? 0),
      actualPct: toPct(a.labor?.actual ?? 0),
      isOverBudget: (a.labor?.actual ?? 0) > (a.labor?.target ?? 0),
    },
    {
      label: '费用成本',
      target: a.overhead?.target ?? 0,
      actual: a.overhead?.actual ?? 0,
      targetPct: toPct(a.overhead?.target ?? 0),
      actualPct: toPct(a.overhead?.actual ?? 0),
      isOverBudget: (a.overhead?.actual ?? 0) > (a.overhead?.target ?? 0),
    },
  ]
})

/* ===================== 格式化工具 ===================== */
const formatMoney = (val?: number) => {
  if (val === null || val === undefined) return '-'
  return `¥${Number(val).toFixed(2)}`
}

const formatPercent = (val?: number) => {
  if (val === null || val === undefined) return '-'
  return `${Number(val).toFixed(2)}%`
}

const varianceClass = (val?: number) => {
  if (val === null || val === undefined) return ''
  if (val > 0) return 'variance-up'
  if (val < 0) return 'variance-down'
  return ''
}

const varianceTagType = (val?: number): 'danger' | 'success' | 'info' => {
  if (val === null || val === undefined) return 'info'
  if (val > 0) return 'danger'
  if (val < 0) return 'success'
  return 'info'
}

/* ===================== 导出CSV ===================== */
const exportCSV = () => {
  if (!analysisResult.value) {
    ElMessage.warning('请先加载分析数据')
    return
  }

  const rows: string[] = []
  // 头部
  rows.push('成本差异分析报告')
  rows.push(`产品策划ID: ${selectedPlanId.value}, 核算期间ID: ${selectedPeriodId.value}`)
  rows.push('')

  // 概要
  const a = analysisResult.value
  rows.push('--- 差异概览 ---')
  rows.push(`合计差异率,${formatPercent(a.total?.variance_pct)}`)
  rows.push(`物料差异,${formatMoney(a.material?.variance)}`)
  rows.push(`人工差异,${formatMoney(a.labor?.variance)}`)
  rows.push(`费用差异,${formatMoney(a.overhead?.variance)}`)
  rows.push('')

  // 明细
  rows.push('--- 差异明细 ---')
  rows.push('成本项,目标,实际,差异,差异率%')
  for (const d of varianceDetails.value) {
    rows.push(`${d.name},${d.target},${d.actual},${d.variance},${(d.variance_pct * 100).toFixed(2)}%`)
  }

  // 趋势
  if (trendData.value.length > 0) {
    rows.push('')
    rows.push('--- 多期间趋势 ---')
    rows.push('期间ID,目标总成本,实际总成本,差异,差异率%,物料成本(实际),人工成本(实际),费用成本(实际)')
    for (const t of trendData.value) {
      rows.push(`${t.period_id},${t.total_target},${t.total_actual},${(t.total_actual - t.total_target)},${(t.variance_pct * 100).toFixed(2)}%,${t.material_actual},${t.labor_actual},${t.overhead_actual}`)
    }
  }

  const csvContent = rows.join('\n')
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `cost-analysis-${selectedPlanId.value}-${selectedPeriodId.value}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('CSV导出成功')
}
</script>

<style scoped>
.cost-analysis-view {
  padding: 0;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 顶部导航 */
.nav-tabs {
  margin-bottom: 16px;
}

/* 筛选区 */
.filter-bar {
  background: #fff;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

/* 指标卡片 */
.metric-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.metric-card {
  text-align: center;
}

.metric-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
}

.metric-sub {
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}

/* 通用卡片 */
.section-card {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 进度条 */
.progress-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-row:last-child {
  margin-bottom: 0;
}

.progress-label {
  width: 70px;
  font-size: 13px;
  font-weight: 600;
  line-height: 22px;
  flex-shrink: 0;
}

.progress-bars {
  flex: 1;
}

.progress-track {
  height: 20px;
  background: #f0f2f5;
  border-radius: 10px;
  position: relative;
  margin-bottom: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.4s ease;
}

.target-fill {
  background: #409eff;
}

.over-budget {
  background: #f56c6c;
}

.under-budget {
  background: #67c23a;
}

.progress-text {
  font-size: 11px;
  color: #fff;
  font-weight: 600;
  white-space: nowrap;
}

.progress-values {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #606266;
  margin-top: 2px;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.text-success {
  color: #67c23a;
  font-weight: 600;
}

/* 差异颜色 */
.variance-up {
  color: #f56c6c;
  font-weight: 600;
}

.variance-down {
  color: #67c23a;
  font-weight: 600;
}

/* 响应式 */
@media (max-width: 900px) {
  .metric-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
