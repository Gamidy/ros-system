<template>
  <div class="page">
    <div v-loading="loading" style="min-height: 400px">

      <!-- █ 顶部摘要卡片 -->
      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>
          <div class="card-header">
            <span>核算单详情</span>
            <el-button @click="$router.push('/cost-accounting/sheets')">返回列表</el-button>
          </div>
        </template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="核算单编号">{{ sheet.sheet_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="产品策划名称">{{ productPlanName }}</el-descriptions-item>
          <el-descriptions-item label="期间">{{ sheet.period_name || sheet.period_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType" size="small">{{ statusLabel }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- █ 成本总览 -->
      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header><span>成本总览</span></template>
        <el-descriptions :column="4" border>
          <el-descriptions-item label="成本项" label-align="center">
            <strong>目标</strong>
          </el-descriptions-item>
          <el-descriptions-item label-align="center">
            <strong>实际</strong>
          </el-descriptions-item>
          <el-descriptions-item label-align="center">
            <strong>差异</strong>
          </el-descriptions-item>
          <el-descriptions-item label-align="center">
            <strong>差异率</strong>
          </el-descriptions-item>
          <template v-for="(row, idx) in costOverviewRows" :key="idx">
            <el-descriptions-item :label="row.label" label-align="center">
              {{ row.target }}
            </el-descriptions-item>
            <el-descriptions-item label-align="center">
              {{ row.actual }}
            </el-descriptions-item>
            <el-descriptions-item label-align="center">
              <el-tag
                :type="row.variance > 0 ? 'danger' : row.variance < 0 ? 'success' : 'info'"
                size="small"
              >
                {{ row.variance >= 0 ? '+' : '' }}{{ Number(row.variance).toFixed(2) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label-align="center">
              <el-tag
                :type="row.varianceRate > 0 ? 'danger' : row.varianceRate < 0 ? 'success' : 'info'"
                size="small"
              >
                {{ row.varianceRate >= 0 ? '+' : '' }}{{ Number(row.varianceRate).toFixed(2) }}%
              </el-tag>
            </el-descriptions-item>
          </template>
        </el-descriptions>
      </el-card>

      <!-- █ Tabs -->
      <el-card shadow="never">
        <el-tabs v-model="activeTab">
          <!-- ── 成本明细 ── -->
          <el-tab-pane label="成本明细" name="details">
            <el-table :data="detailRows" stripe border v-loading="loadingDetails" max-height="480">
              <el-table-column label="类别" width="100">
                <template #default="{ row }">{{ categoryMap[row.cost_category as string] || row.cost_category }}</template>
              </el-table-column>
              <el-table-column prop="item_name" label="项目名称" min-width="160" />
              <el-table-column prop="target_amount" label="目标金额" width="120" align="right">
                <template #default="{ row }">{{ Number(row.target_amount).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column prop="actual_amount" label="实际金额" width="120" align="right">
                <template #default="{ row }">{{ Number(row.actual_amount).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="差异" width="120" align="right">
                <template #default="{ row }">
                  <el-tag
                    :type="(Number(row.actual_amount) - Number(row.target_amount)) > 0 ? 'danger' : 'success'"
                    size="small"
                  >
                    {{ (Number(row.actual_amount) - Number(row.target_amount)).toFixed(2) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="差异率%" width="110" align="right">
                <template #default="{ row }">
                  <span v-if="Number(row.target_amount)">
                    {{ ((Number(row.actual_amount) - Number(row.target_amount)) / Number(row.target_amount) * 100).toFixed(2) }}%
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="source_type" label="来源" width="120" />
            </el-table>
          </el-tab-pane>

          <!-- ── 差异分析 ── -->
          <el-tab-pane label="差异分析" name="variance">
            <div v-loading="loadingVariance">
              <el-row :gutter="16" style="margin-bottom: 16px">
                <el-col :span="6" v-for="(card, i) in varianceCards" :key="i">
                  <div class="variance-card" :class="card.type">
                    <div class="variance-card-title">{{ card.label }}</div>
                    <div class="variance-card-value">{{ card.value }}</div>
                  </div>
                </el-col>
              </el-row>
              <el-table :data="varianceRows" stripe border max-height="400">
                <el-table-column prop="name" label="项目" min-width="160" />
                <el-table-column prop="target" label="目标" width="120" align="right" />
                <el-table-column prop="actual" label="实际" width="120" align="right" />
                <el-table-column prop="variance" label="差异" width="120" align="right" />
                <el-table-column prop="variance_pct" label="差异率%" width="110" align="right" />
                <el-table-column prop="reason" label="原因说明" min-width="200" />
              </el-table>
            </div>
          </el-tab-pane>

          <!-- ── 成本结构 ── -->
          <el-tab-pane label="成本结构" name="structure">
            <div v-loading="loadingStructure" style="padding: 20px 40px">
              <div v-for="(item, idx) in structureData" :key="idx" style="margin-bottom: 28px">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 14px">
                  <span>{{ item.label }}</span>
                  <span>{{ Number(item.amount).toFixed(2) }}（{{ item.percent }}%）</span>
                </div>
                <el-progress
                  :percentage="item.percent"
                  :color="item.color"
                  :stroke-width="24"
                  :text-inside="true"
                />
              </div>
              <el-divider />
              <div style="display: flex; justify-content: space-between; font-size: 15px; font-weight: bold">
                <span>合计</span>
                <span>{{ totalCost.toFixed(2) }}</span>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- █ 底部操作栏 -->
      <div class="action-bar">
        <el-button
          type="primary"
          @click="handleFinalize"
          :loading="finalizing"
          :disabled="sheet.status === 'finalized'"
        >
          定稿
        </el-button>
        <el-button @click="handleRecalculate" :loading="recalculating">
          重新核算
        </el-button>
        <el-button @click="handleExportCsv" :loading="exporting">
          导出CSV
        </el-button>
        <el-button @click="$router.push('/cost-accounting/sheets')">返回列表</el-button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getSheetDetail,
  getVarianceAnalysis,
  finalizeSheet,
  recalculateSheet,
  exportCostSheetCsv,
} from '../../api/costAccounting'

const route = useRoute()

// ── 状态 ──
const loading = ref(false)
const sheet = ref<Record<string, any>>({})
const activeTab = ref('details')

const loadingDetails = ref(false)
const loadingVariance = ref(false)
const loadingStructure = ref(false)
const finalizing = ref(false)
const recalculating = ref(false)
const exporting = ref(false)

// ── 数据 ──
const detailRows = ref<any[]>([])
const varianceRows = ref<any[]>([])
const varianceCards = ref<any[]>([])

// ── 类别中文映射 ──
const categoryMap: Record<string, string> = {
  material: '物料',
  labor: '人工',
  overhead: '费用',
}

// ── 状态标签 ──
const statusMap: Record<string, string> = { draft: '草稿', finalized: '已定稿' }
const statusTypeMap: Record<string, string> = { draft: 'info', finalized: 'success' }
const statusLabel = computed(() => statusMap[sheet.value.status as string] || sheet.value.status || '-')
const statusType = computed(() => (statusTypeMap[sheet.value.status as string] || 'info') as any)

// ── 产品策划名称（从 product_plan_id 取） ──
// 若 sheet 直接携带 product_plan_name 字段则直接使用，否则从 product_plan_id 推断
const productPlanName = computed(() => {
  return sheet.value.product_plan_name || sheet.value.product_plan_id || '-'
})

// ── 解析 sheet.items —— 明细行列表 ──
const parsedDetails = computed<any[]>(() => {
  const raw = sheet.value.items
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return [] }
  }
  return []
})

// ── 成本总览行 ──
const costOverviewRows = computed(() => {
  const d = parsedDetails.value
  const catGroups: Record<string, { target: number; actual: number }> = {
    material: { target: 0, actual: 0 },
    labor: { target: 0, actual: 0 },
    overhead: { target: 0, actual: 0 },
  }
  for (const item of d) {
    const cat = (item.cost_category || '').toLowerCase()
    const g = catGroups[cat]
    if (g) {
      g.target += Number(item.target_amount) || 0
      g.actual += Number(item.actual_amount) || 0
    }
  }
  const mat = catGroups.material
  const lab = catGroups.labor
  const ovh = catGroups.overhead
  const totalTarget = mat.target + lab.target + ovh.target
  const totalActual = mat.actual + lab.actual + ovh.actual

  const buildRow = (label: string, target: number, actual: number) => ({
    label,
    target: target.toFixed(2),
    actual: actual.toFixed(2),
    variance: actual - target,
    varianceRate: target ? ((actual - target) / target) * 100 : 0,
  })

  return [
    buildRow('物料', mat.target, mat.actual),
    buildRow('人工', lab.target, lab.actual),
    buildRow('制造费用', ovh.target, ovh.actual),
    buildRow('合计', totalTarget, totalActual),
  ]
})

// ── 明细表格数据（给 el-table 使用） ──
watch(parsedDetails, () => {
  detailRows.value = parsedDetails.value
}, { immediate: true })

// ── 成本结构（料/工/费占比） ──
const structureData = computed(() => {
  const d = parsedDetails.value
  const catGroups: Record<string, number> = { material: 0, labor: 0, overhead: 0 }
  for (const item of d) {
    const cat = (item.cost_category || '').toLowerCase()
    if (cat in catGroups) {
      catGroups[cat] += Number(item.actual_amount) || 0
    }
  }
  const total = catGroups.material + catGroups.labor + catGroups.overhead
  const labels: Record<string, { label: string; color: string }> = {
    material: { label: '物料成本', color: '#409EFF' },
    labor: { label: '人工成本', color: '#67C23A' },
    overhead: { label: '制造费用', color: '#E6A23C' },
  }
  const result = []
  for (const [key, amount] of Object.entries(catGroups)) {
    const meta = labels[key] || { label: key, color: '#909399' }
    result.push({
      label: meta.label,
      amount,
      percent: total ? Math.round((amount / total) * 100) : 0,
      color: meta.color,
    })
  }
  return result
})
const totalCost = computed(() => {
  return structureData.value.reduce((s, i) => s + i.amount, 0)
})

// ── 差异分析指标卡片 ──
function buildVarianceCards(data: any[]) {
  if (!Array.isArray(data) || data.length === 0) return []
  let totalTarget = 0
  let totalActual = 0
  let maxVariance = -Infinity
  let maxItem = ''
  for (const r of data) {
    const t = Number(r.target) || 0
    const a = Number(r.actual) || 0
    totalTarget += t
    totalActual += a
    const v = a - t
    if (v > maxVariance) { maxVariance = v; maxItem = r.name || '' }
  }
  return [
    { label: '目标总成本', value: totalTarget.toFixed(2), type: 'target' },
    { label: '实际总成本', value: totalActual.toFixed(2), type: 'actual' },
    { label: '总差异', value: (totalActual - totalTarget >= 0 ? '+' : '') + (totalActual - totalTarget).toFixed(2), type: 'variance' },
    { label: '最大差异项', value: maxItem || '-', type: 'max' },
  ]
}

// ── 获取核算单详情 ──
async function fetchSheet() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    if (!id) { ElMessage.warning('缺少核算单 ID'); return }
    const res = await getSheetDetail(id)
    sheet.value = res.data || {}

    // 明细行
    const details = parsedDetails.value
    detailRows.value = details

    // 若 status 为 finalized、且有 planId + periodId，自动加载差异分析
    if (sheet.value.product_plan_id && sheet.value.period_id) {
      loadVarianceAnalysis()
      loadStructure()
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载核算单详情失败')
  } finally {
    loading.value = false
  }
}

// ── 差异分析 ──
async function loadVarianceAnalysis() {
  const planId = sheet.value.product_plan_id
  const periodId = sheet.value.period_id
  if (!planId || !periodId) return
  loadingVariance.value = true
  try {
    const res = await getVarianceAnalysis(planId, periodId)
    const data = res.data
    // data 可以是 {material, labor, overhead, total} 嵌套对象，也可以是数组，
    // 也可能是 {sheet_no, items} 明细结构
    if (Array.isArray(data)) {
      varianceRows.value = data
      varianceCards.value = buildVarianceCards(data)
    } else if (data.items) {
      varianceRows.value = data.items
      varianceCards.value = buildVarianceCards(data.items)
    } else if (data.material) {
      // 嵌套结构 — 从 categories 构建详细行
      const cats = ['material', 'labor', 'overhead', 'total']
      varianceRows.value = cats.map((key) => ({
        name: { material: '物料', labor: '人工', overhead: '制造费用', total: '合计' }[key] || key,
        target: data[key]?.target ?? 0,
        actual: data[key]?.actual ?? 0,
        variance: data[key]?.variance ?? 0,
        variance_pct: data[key]?.variance_pct ?? 0,
      }))
      varianceCards.value = buildVarianceCards(varianceRows.value)
    } else {
      varianceRows.value = data.rows || data.details || []
      varianceCards.value = data.cards || buildVarianceCards(data.rows || data.details || [])
    }
  } catch {
    varianceRows.value = []
    varianceCards.value = []
  } finally {
    loadingVariance.value = false
  }
}

// ── 成本结构（仅需 computed，此处只是为了兼容 loading） ──
function loadStructure() {
  // structureData 是 computed，已经自动计算
  loadingStructure.value = false
}

// ── 定稿 ──
async function handleFinalize() {
  try {
    await ElMessageBox.confirm('确认定稿该核算单？定稿后将无法修改明细。', '确认操作', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  finalizing.value = true
  try {
    await finalizeSheet(Number(route.params.id))
    ElMessage.success('核算单已定稿')
    await fetchSheet()
  } finally {
    finalizing.value = false
  }
}

// ── 重新核算 ──
async function handleRecalculate() {
  try {
    await ElMessageBox.confirm('确认重新核算？将根据最新数据重新计算所有成本项。', '确认操作', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  recalculating.value = true
  try {
    await recalculateSheet(Number(route.params.id))
    ElMessage.success('核算单已重新核算')
    await fetchSheet()
  } finally {
    recalculating.value = false
  }
}

// ── 导出 CSV ──
async function handleExportCsv() {
  exporting.value = true
  try {
    const res = await exportCostSheetCsv(Number(route.params.id))
    // res 可能是 Blob 或 response.data 是 Blob
    const blob = res instanceof Blob ? res : res.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `核算单_${sheet.value.sheet_no || route.params.id}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('CSV 导出成功')
  } catch {
    ElMessage.error('CSV 导出失败')
  } finally {
    exporting.value = false
  }
}

// ── 初始化 ──
onMounted(() => {
  fetchSheet()
})
</script>

<style scoped>
.page {
  padding: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.action-bar {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* 差异分析指标卡片 */
.variance-card {
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
}
.variance-card.target {
  border-left: 4px solid #409eff;
}
.variance-card.actual {
  border-left: 4px solid #67c23a;
}
.variance-card.variance {
  border-left: 4px solid #e6a23c;
}
.variance-card.max {
  border-left: 4px solid #f56c6c;
}
.variance-card-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}
.variance-card-value {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}
</style>
