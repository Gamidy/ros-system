<template>
  <el-card shadow="never" class="cost-section summary-section">
    <template #header>
      <span class="section-header">📊 项目开发总预算 &amp; 经济指标</span>
    </template>
    <el-row :gutter="16" class="summary-cards">
      <el-col :span="6">
        <div class="indicator-card total">
          <div class="indicator-label">总预算</div>
          <div class="indicator-value">{{ totalBudget.toFixed(2) }}</div>
          <div class="indicator-unit">万元</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="indicator-card">
          <div class="indicator-label">毛利率</div>
          <div class="indicator-value" :class="grossMarginColor">{{ grossMarginPercent.toFixed(1) }}%</div>
          <div class="indicator-unit">基于目标售价 {{ targetPrice || '—' }} 万元</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="indicator-card">
          <div class="indicator-label">净现值(NPV)</div>
          <div class="indicator-value">{{ npvValue.toFixed(1) }}</div>
          <div class="indicator-unit">万元（{{ npvLabel }}）</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="indicator-card">
          <div class="indicator-label">成本占比</div>
          <div class="indicator-value">{{ costToPricePercent.toFixed(1) }}%</div>
          <div class="indicator-unit">预算 ÷ 预期营收</div>
        </div>
      </el-col>
    </el-row>

    <!-- 八项费用明细表 -->
    <el-table :data="costBreakdown" size="small" border style="margin-top:16px">
      <el-table-column label="费用项目" prop="label" width="160" />
      <el-table-column label="金额(万元)" prop="value" width="120">
        <template #default="{ row }">
          <span :class="row.key === 'total' ? 'cost-total' : ''">{{ row.value.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="占比" width="100">
        <template #default="{ row }">
          <span v-if="row.key !== 'total' && totalBudget > 0">{{ (row.value / totalBudget * 100).toFixed(1) }}%</span>
          <el-tag v-else type="danger" size="small" effect="dark">100%</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="说明" prop="desc" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'

interface CostBreakdownItem {
  key: string
  label: string
  value: number
  desc: string
}

const props = defineProps<{
  data: Record<string, unknown>
}>()

const emit = defineEmits<{
  update: [patch: Record<string, unknown>]
}>()

const formData = computed(() => props.data)

// Helper: parse JSON string from data
function parseField(key: string): Record<string, unknown> | null {
  const raw = formData.value?.[key]
  if (!raw || typeof raw !== 'string') return null
  try {
    return JSON.parse(raw)
  } catch (e: unknown) {
    return null
  }
}

// Extract values from serialized sibling data
const protoCostTotal = computed(() => {
  const parsed = parseField('dev_cost_items')
  return (parsed?.total as number) || 0
})

const moldCostTotal = computed(() => {
  const parsed = parseField('mold_costs')
  return (parsed?.total as number) || 0
})

const trialCostTotal = computed(() => {
  const parsed = parseField('prototype_costs_detail')
  const trial = (parsed?.trial as Record<string, unknown>) || {}
  return (trial?.total as number) || 0
})

const testCost = computed(() => {
  const parsed = parseField('test_costs')
  return (parsed?.cost as number) || 0
})

const testRemark = computed(() => {
  const parsed = parseField('test_costs')
  return (parsed?.remark as string) || '手动填写'
})

const certCostTotal = computed(() => {
  const parsed = parseField('cert_costs')
  return (parsed?.total as number) || 0
})

const certCount = computed(() => {
  const parsed = parseField('cert_costs')
  const items = parsed?.items as Record<string, unknown>[] | undefined
  return items?.length || 0
})

const laborCostTotal = computed(() => {
  const parsed = parseField('labor_costs')
  return (parsed?.total_cost as number) || 0
})

const laborPersonMonths = computed(() => {
  const parsed = parseField('labor_costs')
  return (parsed?.person_months as number) || 0
})

const indirectCost = computed(() => {
  const raw = formData.value?.indirect_cost
  return (raw as number) || 0
})

const moldCount = computed(() => {
  const parsed = parseField('mold_costs')
  const items = parsed?.items as Record<string, unknown>[] | undefined
  return items?.length || 0
})

const protoCount = computed(() => {
  const parsed = parseField('dev_cost_items')
  const items = parsed?.proto_costs as Record<string, unknown>[] | undefined
  return items?.length || 0
})

const trialQty = computed(() => {
  const parsed = parseField('prototype_costs_detail')
  const trial = (parsed?.trial as Record<string, unknown>) || {}
  return (trial?.qty as number) || 0
})

// Economic Indicators
const totalBudget = computed(() => {
  return protoCostTotal.value
    + moldCostTotal.value
    + trialCostTotal.value
    + testCost.value
    + certCostTotal.value
    + laborCostTotal.value
    + indirectCost.value
})

const targetPrice = computed(() => {
  const tp = formData.value?.target_price
  if (!tp) return 0
  if (typeof tp === 'number') return tp
  if (typeof tp === 'string') return parseFloat(tp) || 0
  return 0
})

const grossMarginPercent = computed(() => {
  if (targetPrice.value <= 0) return 0
  return ((targetPrice.value - totalBudget.value) / targetPrice.value) * 100
})

const grossMarginColor = computed(() => {
  if (grossMarginPercent.value >= 30) return 'color-success'
  if (grossMarginPercent.value >= 15) return 'color-warning'
  return 'color-danger'
})

const npvValue = computed(() => {
  const lifespan = formData.value?.product_lifecycle
  const annualSales = formData.value?.annual_sales_forecast
  if (!lifespan || !annualSales) return totalBudget.value * -1
  const years = typeof lifespan === 'number' ? lifespan : parseFloat(String(lifespan)) || 3
  const sales = typeof annualSales === 'number' ? annualSales : parseFloat(String(annualSales)) || 0
  const annualRevenue = sales * targetPrice.value
  const totalRevenue = annualRevenue * years
  return totalRevenue - totalBudget.value
})

const npvLabel = computed(() => {
  if (npvValue.value > 0) return '盈利 📈'
  if (npvValue.value < 0) return '亏损 📉'
  return '持平'
})

const costToPricePercent = computed(() => {
  if (targetPrice.value <= 0) return 0
  return (totalBudget.value / targetPrice.value) * 100
})

const costBreakdown = computed<CostBreakdownItem[]>(() => {
  const items: CostBreakdownItem[] = [
    { key: 'proto', label: '原型开发成本', value: protoCostTotal.value, desc: `${protoCount.value} 个样机阶段` },
    { key: 'mold', label: '模具费用', value: moldCostTotal.value, desc: `${moldCount.value} 套模具` },
    { key: 'trial', label: '试制费用', value: trialCostTotal.value, desc: `试制 ${trialQty.value} 台` },
    { key: 'test', label: '测试费用', value: testCost.value, desc: testRemark.value },
    { key: 'cert', label: '认证费用', value: certCostTotal.value, desc: `${certCount.value} 项认证` },
    { key: 'labor', label: '人工成本', value: laborCostTotal.value, desc: `${laborPersonMonths.value.toFixed(1)} 人月` },
    { key: 'indirect', label: '间接成本', value: indirectCost.value, desc: '管理费用分摊' },
    { key: 'total', label: '项目开发总预算', value: totalBudget.value, desc: '八项合计' },
  ]
  return items
})

// Emit economic indicators when dependent values change
watch([totalBudget, grossMarginPercent, npvValue, costToPricePercent, protoCostTotal, moldCostTotal, trialCostTotal, testCost, certCostTotal, laborCostTotal, indirectCost], () => {
  emit('update', {
    economic_indicators: JSON.stringify({
      total_budget: totalBudget.value,
      proto_cost: protoCostTotal.value,
      mold_cost: moldCostTotal.value,
      trial_cost: trialCostTotal.value,
      test_cost: testCost.value,
      cert_cost: certCostTotal.value,
      labor_cost: laborCostTotal.value,
      indirect_cost: indirectCost.value,
      gross_margin_pct: grossMarginPercent.value,
      npv: npvValue.value,
      cost_to_price_pct: costToPricePercent.value,
    }),
  })
}, { immediate: true })
</script>

<style scoped>
.cost-section.summary-section { border-left-color: #e6a23c; background: linear-gradient(135deg, #fdf6ec 0%, #fff 100%); margin-bottom: 16px; }
.section-header { font-size: 15px; font-weight: 600; color: #303133; }
.summary-cards { margin-bottom: 8px; }
.indicator-card { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 16px; text-align: center; transition: box-shadow 0.2s; }
.indicator-card:hover { box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); }
.indicator-card.total { background: linear-gradient(135deg, #409eff 0%, #337ecc 100%); color: #fff; border-color: transparent; }
.indicator-card.total .indicator-label,
.indicator-card.total .indicator-unit { color: rgba(255, 255, 255, 0.8); }
.indicator-label { font-size: 13px; color: #909399; margin-bottom: 6px; }
.indicator-value { font-size: 28px; font-weight: 700; color: #303133; line-height: 1.2; }
.indicator-card.total .indicator-value { color: #fff; }
.indicator-unit { font-size: 12px; color: #c0c4cc; margin-top: 4px; }
.color-success { color: #67c23a !important; }
.color-warning { color: #e6a23c !important; }
.color-danger { color: #f56c6c !important; }
.cost-total { font-weight: 700; font-size: 15px; color: #e6a23c; }
@media (max-width: 1200px) { .summary-cards .el-col { margin-bottom: 12px; } }
</style>
